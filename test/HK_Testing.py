# test/HK_Testing.py — Hisab-Kitab AI ka test runner (har bundle ke liye ek hi).
#
# Chalao project ke MAIN folder se:
#   python test/HK_Testing.py --bundle emp                    → Employee ke saare test (Hinglish)
#   python test/HK_Testing.py --bundle emp --only EMP-A-01    → sirf ek (comma se kai: EMP-A-01,EMP-B-03)
#   python test/HK_Testing.py --bundle emp --category B       → sirf Tricky (kai: --category A,B)
#   python test/HK_Testing.py --bundle emp --lang english     → baad mein, jab English statements bhar denge
#
# Har statement ke liye:
#   1. test DB reset + seed          (reset_test_db.py — sirf "test" naam wale DB pe)
#   2. statement graph mein bhejna   (naya thread, memory checkpointer — checkpoints.db ko nahi chhoota)
#   3. beech ke sawaalon ka jawaab khud dena (testcase file ke "roles" / "answers" se),
#      final "Execute?" pe "yes". Jo sawaal script mein nahi hai (amount missing, report, correction…)
#      → wahi record karke test wahin rok dena (ye ASK / NO-ENTRY ka saboot hai)
#   4. record: aaye hue sawaal, tool + arguments, DB mein bani entries, bot ka jawaab, error, time
#
# Output (test/results/<bundle>/):
#   <bundle>_<lang>_<tareekh_time>.log   → poora terminal output (har test ki heading ke saath)
#   <bundle>_<lang>_<tareekh_time>.json  → har test ka saaf saar — Excel isi se banega
# Runner koi pass/fail nahi lagata — sirf chalata aur save karta hai.
import argparse
import asyncio
import importlib
import json
import os
import sys
import time
import traceback
import uuid
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TEST_DIR))

from reset_test_db import use_test_database, reset  # noqa: E402

# --lang → testcase ka kaunsa field system ko diya jaye
LANG_FIELDS = {"hinglish": "hinglish", "hindi": "hindi", "english": "english_input"}

ROUTE_ONLY = False        # Router bundle: sirf router (LLM + safety nets) chalao, aage ki pipeline nahi (sasta)
MAX_ROUNDS = 25           # ek statement mein zyada se zyada itne sawaal-jawaab (infinite loop se bachne ke liye)


# =====================================================================
#                       terminal output → file bhi
# =====================================================================
class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            try:
                st.write(s)
            except UnicodeEncodeError:
                st.write(s.encode("ascii", "replace").decode())
        return len(s)

    def flush(self):
        for st in self.streams:
            st.flush()

    def isatty(self):
        return False


# =====================================================================
#                              helpers
# =====================================================================
def norm(s):
    return " ".join(str(s or "").lower().split())


def date_tokens(today):
    """Testcase ki relative dates ka asli matlab is run ke liye (Excel bharte waqt kaam aayega)."""
    def last(weekday):          # Monday=0 … Sunday=6, hamesha T se PEHLE wala
        d = today - timedelta(days=1)
        while d.weekday() != weekday:
            d -= timedelta(days=1)
        return d
    return {"T": today, "T-1": today - timedelta(days=1), "T-2": today - timedelta(days=2),
            "LAST_MONDAY": last(0), "LAST_SATURDAY": last(5)}


def to_jsonable(obj):
    """Pydantic / enum / date — sab JSON mein likhne layak."""
    if isinstance(obj, Enum):
        return to_jsonable(obj.value)
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if hasattr(obj, "model_dump"):
        return to_jsonable(obj.model_dump())
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(x) for x in obj]
    return str(obj)


def expected_role_for(person, roles):
    """Sawaal mein aaye naam ke liye testcase ka role. Pehle poora naam, fir pehla shabd."""
    p = norm(person)
    if p in roles:
        return roles[p]
    toks = p.split()
    if toks:
        for k, v in roles.items():
            if k.split()[0] == toks[0]:
                return v
    return None


# =====================================================================
#                 beech ke sawaal (HITL) — runner ka jawaab
# =====================================================================
class Abort(Exception):
    """Ye sawaal script mein nahi — test yahin rok do (sawaal record ho chuka)."""


def roles_for(tc, lang):
    """Testcase ke roles + (Hindi run mein) unke Devanagari naam."""
    roles = {norm(k): v for k, v in tc.get("roles", {}).items()}
    if lang == "hindi":
        import seed_data as S
        hi = {norm(k): v for k, v in S.HINDI_NAMES.items()}
        for k, role in list(roles.items()):
            for en, dev in hi.items():
                if k == en or k.split()[0] == en.split()[0]:
                    roles.setdefault(norm(dev), role)
    return roles


def answer_interrupt(value, tc, rec, used_answers, lang="hinglish"):
    import schemas as SC

    # ---------- role ka sawaal
    if isinstance(value, SC.PersonRoleHITLRequest):
        exp = expected_role_for(value.person, roles_for(tc, lang))
        q = dict(type="role", person=value.person, reason=value.reason.value,
                 interaction=value.interaction_type.value,
                 options=[dict(no=o.option_id, role=o.role.value, found=getattr(o, "found", False),
                               confidence=o.confidence) for o in value.options],
                 expected_role=exp)
        pick = None
        if exp:
            pick = next((o.option_id for o in value.options if o.role.value == exp), None)
        if pick is None:
            q["unscripted"] = True              # testcase mein is naam ka role nahi tha
            pick = value.options[0].option_id
        q["answered"] = next(o.role.value for o in value.options if o.option_id == pick)
        rec["questions"].append(q)
        print(f"[RUNNER] Role ka jawaab → {q['answered']}" + ("  (UNSCRIPTED)" if q.get("unscripted") else ""))
        if value.interaction_type == SC.HITLInteractionType.CONFIRMATION:
            if pick == value.options[0].option_id:
                return SC.PersonRoleHITLResponse(group_id=value.group_id, confirmed=True)
            return SC.PersonRoleHITLResponse(group_id=value.group_id, confirmed=False, selected_option=pick)
        return SC.PersonRoleHITLResponse(group_id=value.group_id, selected_option=pick)

    # ---------- tool ka koi zaroori field missing
    if isinstance(value, SC.ToolArgumentHITLRequest):
        tool = value.tool_name.value
        q = dict(type="missing_argument", tool=tool,
                 missing=[m.field_name for m in value.missing_arguments],
                 arguments=to_jsonable(value.arguments))
        text = (tc.get("answers") or {}).get(tool)
        if text and used_answers.get(tool, 0) < 1:
            used_answers[tool] = used_answers.get(tool, 0) + 1
            q["answered"] = text
            rec["questions"].append(q)
            print(f"[RUNNER] Missing field ka jawaab → {text}")
            return SC.ToolArgumentHITLResponse(group_id=value.group_id, updated_statement=text)
        rec["questions"].append(q)
        raise Abort(f"missing_argument: {tool} {q['missing']}")

    # ---------- material movement: jagah / jagah ki kism
    if isinstance(value, SC.MaterialMovementHITLRequest):
        q = dict(type="material_movement", reason=value.reason.value,
                 missing_field=getattr(value, "missing_field", None),
                 location=getattr(value, "location_name", None),
                 suggestions=list(getattr(value, "suggestions", []) or []))
        if value.reason == SC.MaterialMovementHITLReason.MISSING_FIELD:
            # statement mein jagah nahi thi → user jaisa jawaab: testcase ka, warna "Pata nahi"
            ans = (tc.get("locations") or {}).get(value.missing_field)
            q["answered"] = ans or "Pata nahi"
            rec["questions"].append(q)
            print(f"[RUNNER] Jagah ({value.missing_field}) → {q['answered']}")
            return SC.MaterialMovementHITLResponse(group_id=value.group_id, provided_value=ans or None)
        if value.reason == SC.MaterialMovementHITLReason.LOCATION_TYPE_CONFIRMATION:
            # naya naam jagah ki tarah aaya ("Bablu", "Yadav ji ki site") → testcase ke role se kism:
            # Customer → customer, Supplier → supplier. Naam roles mein nahi (jaise "8") → yahin roko.
            role = expected_role_for(value.location_name or "", roles_for(tc, lang))
            want = {"Customer": "customer", "Supplier": "supplier", "Site": "site", "Storage": "storage",
                    "Property / Site Owner": "site"}.get(role)
            pick = next((o.option_id for o in value.options if o.location_type.value == want), None)
            if pick is not None:
                q["answered"] = want
                rec["questions"].append(q)
                print(f"[RUNNER] Jagah '{value.location_name}' ki kism → {want}")
                return SC.MaterialMovementHITLResponse(group_id=value.group_id, selected_option=pick)
        rec["questions"].append(q)
        raise Abort(f"material_movement: {q['reason']} {q['missing_field'] or q['location']}")

    # ---------- report / correction flow — entry nahi, wahin rok do
    if isinstance(value, SC.ReportHITLRequest):
        rec["questions"].append(dict(type="report", step=value.step, question=value.question))
        rec["route"] = "report"
        raise Abort(f"report: {value.step}")
    if type(value).__name__.startswith("Correction"):
        rec["questions"].append(dict(type="correction", request=type(value).__name__,
                                     text=getattr(value, "text", None)))
        rec["route"] = "correction"
        raise Abort(f"correction: {type(value).__name__}")

    # ---------- final "Execute this tool? (yes/no)"
    if isinstance(value, dict) and "message" in value:
        rec["final_confirmations"].append(value["message"])
        print("[RUNNER] Final confirmation → yes")
        return "yes"

    rec["questions"].append(dict(type="unknown", value=to_jsonable(value)))
    raise Abort(f"unknown interrupt: {type(value).__name__}")


# =====================================================================
#                   DB mein kya bana (audit_log se)
# =====================================================================
def collect_db_entries():
    from db import SessionLocal
    from models import AuditLog, CashLedger
    from helpers import TARGET_TABLE_MODEL_MAP
    db = SessionLocal()
    try:
        tools, rows = [], []
        for a in db.query(AuditLog).order_by(AuditLog.id).all():
            tools.append(dict(tool=a.tool_name, args=to_jsonable(a.arguments), target_table=a.target_table,
                              target_id=a.target_id, entry_date=to_jsonable(a.entry_date)))
            model = TARGET_TABLE_MODEL_MAP.get(a.target_table)
            if model is not None and a.target_id is not None:
                r = db.query(model).filter(model.id == a.target_id).first()
                if r is not None:
                    d = {c.name: to_jsonable(getattr(r, c.name)) for c in model.__table__.columns
                         if c.name not in ("created_at", "business_id", "superseded_by_id", "reversal_of_id")}
                    d["_table"] = a.target_table
                    rows.append(d)
        cash = [dict(date=to_jsonable(c.entry_date), direction=c.direction, amount=c.amount, category=c.category,
                     source=f"{c.source_table}#{c.source_id}") for c in db.query(CashLedger).order_by(CashLedger.id).all()]
        return tools, rows, cash
    finally:
        db.close()


def collect_state(values):
    """Graph ki aakhri state se kaam ki cheezein (grouping, role, intent)."""
    out = {}
    if not values:
        return out
    out["intent"] = values.get("intent")
    if values.get("report_data") is not None:
        out["report_data"] = to_jsonable(values.get("report_data"))
    gi = values.get("grouped_intent")
    if gi is not None:
        out["groups"] = [dict(group_id=g.group_id, record_type=to_jsonable(g.record_type),
                              identity_key=g.identity_key, actions=[a.text for a in g.actions])
                         for g in getattr(gi, "groups", [])]
    roles = values.get("resolved_person_roles")
    if roles:
        out["resolved_roles"] = to_jsonable(roles)
    tar = values.get("tool_argument_results")
    if tar is not None and hasattr(tar, "results"):
        out["tool_arguments"] = [dict(group_id=r.group_id, tool=to_jsonable(r.tool_name),
                                      args=to_jsonable(r.arguments)) for r in tar.results]
    return out


# =====================================================================
#                          ek test case chalana
# =====================================================================
RATE_LIMIT_RETRIES = 3


def _no_credit(rec):
    err = rec.get("error") or ""
    return "insufficient_quota" in err or "credit_balance_exhausted" in err


def _is_rate_limit(rec):
    """Thoda ruk ke dobara chalane layak: 429 rate limit ya internet/connection toot-na (credit khatam NAHI)."""
    err = rec.get("error") or ""
    if _no_credit(rec):
        return False
    return ("RateLimit" in err or "429" in err or "rate_limit_exceeded" in err
            or "APIConnectionError" in err or "ConnectionError" in err or "Connection error" in err
            or "Timeout" in err)


async def run_case(app, tc, lang, today):
    from langchain_core.messages import HumanMessage
    from langgraph.types import Command

    statement = tc.get(LANG_FIELDS.get(lang, lang))
    rec = dict(test_id=tc["id"], category=tc["category"], lang=lang, statement=statement,
               english=tc.get("english"), expected_outcome=tc.get("outcome"),
               expected=tc.get("expected"), expected_ask=tc.get("ask"),
               route=None, questions=[], final_confirmations=[], tools_executed=[], db_entries=[],
               cash_ledger=[], state={}, bot_reply=None, aborted=None, error=None, time_sec=None)

    print("\n" + "=" * 78)
    print(f"{tc['id']}  |  Category: {tc['category']}  |  Lang: {lang}")
    print(f"Statement: {statement}")
    print("=" * 78)

    t0 = time.perf_counter()
    try:
        reset(today=today, quiet=True, lang=lang)
        if ROUTE_ONLY or tc.get("route_only"):
            import graph as G
            out = await G.router_node({"messages": [HumanMessage(content=statement)]})
            rec["route"] = out.get("intent")
            rec["state"] = {"intent": out.get("intent")}
            rec["time_sec"] = round(time.perf_counter() - t0, 1)
            print(f"\n[RUNNER] Route: {rec['route']}  |  {rec['time_sec']} sec")
            return rec
        config = {"configurable": {"thread_id": f"test-{tc['id']}-{uuid.uuid4().hex[:8]}"}}
        result = await app.ainvoke({"messages": [HumanMessage(content=statement)],
                                    "original_user_statement": statement}, config=config)
        used_answers = {}
        rounds = 0
        try:
            while result.get("__interrupt__"):
                rounds += 1
                if rounds > MAX_ROUNDS:
                    raise Abort("too many questions (loop?)")
                resume = {}
                for it in result["__interrupt__"]:
                    resume[it.id] = answer_interrupt(it.value, tc, rec, used_answers, lang)
                result = await app.ainvoke(Command(resume=resume), config=config)
            if result.get("messages"):
                rec["bot_reply"] = result["messages"][-1].content
                print("\nBot:", rec["bot_reply"])
        except Abort as a:
            rec["aborted"] = str(a)
            print(f"\n[RUNNER] Test yahin roka: {a}")
        try:
            st = await app.aget_state(config, subgraphs=True)
            rec["state"] = collect_state(st.values)
            # report / correction subgraph mein ruka — uski state (report_data) bhi lo
            # report / correction subgraph (andar ke andar bhi) mein ruka — unki state bhi lo:
            # report_data, correction_data, aur grouping / tool arguments jo parent tak nahi pahunche
            def _walk(snap):
                for _t in getattr(snap, "tasks", []) or []:
                    _sub = getattr(_t, "state", None)
                    if _sub is None:
                        continue
                    _vals = getattr(_sub, "values", None) or {}
                    for _k in ("report_data", "correction_data"):
                        if _vals.get(_k) is not None and _k not in rec["state"]:
                            rec["state"][_k] = to_jsonable(_vals.get(_k))
                    _inner = collect_state(_vals)
                    for _k in ("groups", "tool_arguments", "resolved_roles"):
                        if _inner.get(_k) and not rec["state"].get(_k):
                            rec["state"][_k] = _inner[_k]
                    _walk(_sub)
            _walk(st)
            if rec["route"] is None:
                rec["route"] = rec["state"].get("intent")
        except Exception as e:  # noqa: BLE001
            rec["state"] = {"error": str(e)}
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {e}"
        print("\n[RUNNER] ERROR:")
        traceback.print_exc()
    try:
        rec["tools_executed"], rec["db_entries"], rec["cash_ledger"] = collect_db_entries()
    except Exception as e:  # noqa: BLE001
        rec["error"] = (rec["error"] or "") + f" | db read: {e}"
    rec["time_sec"] = round(time.perf_counter() - t0, 1)
    print(f"\n[RUNNER] Tools chale: {[t['tool'] for t in rec['tools_executed']] or 'koi nahi'}  |  "
          f"Sawaal: {[q['type'] for q in rec['questions']] or 'koi nahi'}  |  {rec['time_sec']} sec")
    return rec


# =====================================================================
#                                main
# =====================================================================
def parse_args():
    p = argparse.ArgumentParser(description="Hisab-Kitab AI test runner")
    p.add_argument("--bundle", required=True, help="emp / customer / supplier … (testcases/<bundle>_testcases.py)")
    p.add_argument("--lang", default="hinglish", help="hinglish (default) / hindi / english")
    p.add_argument("--only", default="", help="Test IDs, comma se: EMP-A-01,EMP-B-03")
    p.add_argument("--category", default="", help="A,B,C,D,E,F mein se")
    return p.parse_args()


async def main():
    args = parse_args()
    db_name = use_test_database()          # project import se PEHLE — test DB pe switch

    mod = importlib.import_module(f"testcases.{args.bundle}_testcases")
    global ROUTE_ONLY
    ROUTE_ONLY = bool(getattr(mod, "ROUTE_ONLY", False))
    cases = list(mod.TESTCASES)
    if args.only:
        ids = {x.strip().upper() for x in args.only.split(",") if x.strip()}
        cases = [c for c in cases if c["id"].upper() in ids]
    if args.category:
        cats = {x.strip().upper() for x in args.category.split(",") if x.strip()}
        cases = [c for c in cases if c["category"].upper() in cats]
    field = LANG_FIELDS.get(args.lang)
    if field is None:
        sys.exit(f"--lang sirf {list(LANG_FIELDS)} mein se ho sakti hai")
    missing = [c["id"] for c in cases if not c.get(field)]
    cases = [c for c in cases if c.get(field)]
    if not cases:
        sys.exit(f"Koi test nahi mila (bundle={args.bundle}, lang={args.lang}). "
                 + (f"In tests ka {args.lang} statement khaali hai: {missing}" if missing else ""))

    today = date.today()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_dir = TEST_DIR / "results" / args.bundle
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / f"{args.bundle}_{args.lang}_{stamp}"
    log_f = open(f"{base}.log", "w", encoding="utf-8")
    real_out, real_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = Tee(real_out, log_f), Tee(real_err, log_f)

    run = dict(bundle=getattr(mod, "BUNDLE", args.bundle), lang=args.lang, started=datetime.now().isoformat(),
               test_date_T=today.isoformat(),
               date_tokens={k: v.isoformat() for k, v in date_tokens(today).items()},
               database=db_name, filters=dict(only=args.only, category=args.category),
               skipped_no_statement=missing, results=[])
    try:
        from llm_setup import llm
        run["model"] = getattr(llm, "model_name", None) or getattr(llm, "model", None)
    except Exception:  # noqa: BLE001
        run["model"] = None
    # argument extraction ka prompt bundle ke hisaab se kata hai ya poora (ablation ke liye)
    run["sliced_prompt"] = os.getenv("SLICED_PROMPT", "0").strip().lower() in ("1", "true", "yes", "on")

    def save():
        with open(f"{base}.json", "w", encoding="utf-8") as f:
            json.dump(run, f, ensure_ascii=False, indent=2, default=str)

    try:
        print(f"Hisab-Kitab AI test run — bundle={run['bundle']} lang={args.lang} tests={len(cases)} "
              f"T={today} DB={db_name} model={run['model']} sliced_prompt={run['sliced_prompt']}")
        import graph as G
        from checkpointer import make_serde
        from langgraph.checkpoint.memory import MemorySaver
        app = G.graph.compile(checkpointer=MemorySaver(serde=make_serde()))

        for i, tc in enumerate(cases, 1):
            print(f"\n######## [{i}/{len(cases)}]")
            rec = await run_case(app, tc, args.lang, today)
            # OpenAI rate limit (429) — app ki galti nahi; thoda ruk ke wahi test dobara (DB phir reset hota hai)
            for attempt in range(1, RATE_LIMIT_RETRIES + 1):
                if not _is_rate_limit(rec):
                    break
                wait = 20 * attempt
                print(f"\n[RUNNER] OpenAI rate limit / connection — {wait} sec ruk ke {tc['id']} dobara "
                      f"(koshish {attempt}/{RATE_LIMIT_RETRIES})")
                await asyncio.sleep(wait)
                rec = await run_case(app, tc, args.lang, today)
                rec["rate_limit_retries"] = attempt
            run["results"].append(rec)
            if _no_credit(rec):
                save()
                print("\n" + "!" * 78)
                print("OPENAI CREDIT KHATAM (insufficient_quota) — run yahin roka. Credit daalo, phir bache hue")
                print(f"tests --only se chalao. Ye test fail mana jayega: {tc['id']}")
                print("!" * 78)
                break
            save()                              # har test ke baad — beech mein band ho to bhi data bacha rahe

        run["finished"] = datetime.now().isoformat()
        save()
        n = len(run["results"])
        aborted = [r["test_id"] for r in run["results"] if r["aborted"]]
        errors = [r["test_id"] for r in run["results"] if r["error"]]
        unscripted = [r["test_id"] for r in run["results"]
                      if any(q.get("unscripted") for q in r["questions"])]
        avg = sum(r["time_sec"] or 0 for r in run["results"]) / max(n, 1)
        print("\n" + "=" * 78)
        print(f"RUN KHATAM — {n} test chale, average {avg:.1f} sec/test")
        print(f"  Beech mein ruke (sawaal aaya / report / correction): {len(aborted)} {aborted}")
        print(f"  Error: {len(errors)} {errors}")
        if unscripted:
            print(f"  Role ka sawaal script se bahar (check karna): {unscripted}")
        print(f"\n  Output:\n    {base}.log\n    {base}.json")
        print("=" * 78)
    finally:
        sys.stdout, sys.stderr = real_out, real_err
        log_f.close()


if __name__ == "__main__":
    asyncio.run(main())
