# reports/render.py
"""
builders.py ka data → HTML → PDF (Chromium / Playwright), teen bhasha mein.
Design wahi jo sample mein lock hua: black-white, sirf business ka naam maroon.

    html = render_html(report, lang, vmap)
    await html_to_pdf(html, "reports_output/x.pdf", lang)     # async (graph ke andar)
    make_pdf(db, report, lang, out_dir)                        # sync — scripts ke liye
"""
import html as _html
import os
import tempfile
from datetime import date
from pathlib import Path

from reports.i18n import t, MONTHS, MONTHS_FULL, translate_values
from reports.business_profile import BUSINESS, PHONES

FONT_DIR = Path(__file__).resolve().parent / "fonts"

# report dict ki in keys mein DB ka free-text hota hai → translate
TEXT_KEYS = {"supplier", "customer", "employee", "name", "party", "seller", "item", "unit", "note",
             "description", "location", "destination", "source", "driver", "category", "role", "mode",
             "type", "movement_type", "reason", "location_type", "source_type", "destination_type",
             "detail", "address", "member", "relation", "purpose"}
LIST_KEYS = {"work_notes", "paid_notes", "notes", "modes", "providers", "paid_types"}


# =====================================================================
#                              helpers
# =====================================================================
def collect_texts(obj, out=None):
    out = set() if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in TEXT_KEYS and isinstance(v, str) and v.strip():
                out.add(v)
            elif k in LIST_KEYS and isinstance(v, list):
                out.update(x for x in v if isinstance(x, str) and x.strip())
            elif isinstance(v, (dict, list)):
                collect_texts(v, out)
    elif isinstance(obj, list):
        for x in obj:
            collect_texts(x, out)
    return out


def inr(x, dash_zero=False):
    if x is None:
        return ""
    if dash_zero and abs(x) < 0.005:
        return "-"
    neg = x < 0
    whole, frac = f"{abs(x):.2f}".split(".")
    if len(whole) > 3:
        head, last3 = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts) + "," + last3
    return ("-" if neg else "") + whole + "." + frac


def rs(x):
    """₹ ke saath: minus ho to −₹100.00 (₹-100.00 nahi)."""
    return f"−₹{inr(abs(x))}" if x < -0.005 else f"₹{inr(x)}"


def qty(x):
    if x is None:
        return ""
    return f"{x:,.0f}" if float(x).is_integer() else f"{x:,.2f}"


class Ctx:
    def __init__(self, lang, vmap):
        self.lang = lang
        self.vmap = vmap or {}

    def t(self, key, **kw):
        return t(self.lang, key, **kw)

    def v(self, text):
        if text is None or (isinstance(text, str) and not text.strip()):
            return "-"
        return self.vmap.get(text, text)

    def vl(self, items, sep="; "):
        items = [self.v(x) for x in (items or []) if x]
        return sep.join(items) if items else "-"

    def d(self, x):
        if x is None:
            return ""
        return f"{x.day:02d}-{MONTHS[self.lang][x.month - 1]}-{str(x.year)[2:]}"

    def dlong(self, x):
        return f"{x.day:02d}-{MONTHS_FULL[self.lang][x.month - 1]}-{x.year}"

    def ym(self, ym):
        y, m = int(ym[:4]), int(ym[5:7])
        return f"{MONTHS_FULL[self.lang][m - 1]} {y}"

    def bal(self, x):
        """signed balance → '12,000.00 देना' / 'Lena' / 'Dr'"""
        if x is None or abs(x) < 0.005:
            return self.t("nil")
        return f"{inr(abs(x))} {self.t('lena' if x > 0 else 'dena')}"

    def period(self, a, b):
        return self.t("period_fmt", a=self.dlong(a), b=self.dlong(b))


def esc(x):
    s = "" if x is None else str(x)
    if any(tag in s for tag in ("<b>", "<br/>", "&nbsp;", "&amp;", "<span")):
        return s
    return _html.escape(s)


def table(headers, rows, num=(), center=(), special=None, cls=""):
    special = special or {}
    out = [f'<table class="t {cls}"><thead><tr>']
    for i, h in enumerate(headers):
        c = "r" if i in num else "c" if i in center else ""
        out.append(f'<th class="{c}">{esc(h)}</th>')
    out.append("</tr></thead><tbody>")
    for ri, r in enumerate(rows, 1):
        out.append(f'<tr class="{special.get(ri, "")}">')
        for i, v in enumerate(r):
            c = "r" if i in num else "c" if i in center else ""
            out.append(f'<td class="{c}">{esc(v)}</td>')
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


class Page:
    """HTML ke tukde jodta hai; headings ko unki table ke saath chipka ke rakhta hai."""

    def __init__(self, c: Ctx, report):
        self.c = c
        self.r = report
        self.h = []
        self.pending = []

    def letterhead(self):
        b = BUSINESS[self.c.lang]
        phones = "<br/>".join(f"📞 {p}" for p in PHONES)
        return (f'<div class="lh"><div class="lhrow"><div class="prop">{b["prop"]}</div>'
                f'<div class="co">{b["name"]}</div><div class="ph">{phones}</div></div>'
                f'<div class="cosub">{b["tagline"]}</div><div class="addr">{b["address"]}</div></div>')

    def part(self, title, sub=None, new_page=True, start=None, end=None):
        start = start or self.r["start"]
        end = end or self.r["end"]
        cls = "part newpage" if new_page else "part"
        s = (f'<div class="{cls}">{self.letterhead()}<h1 class="ptitle">{esc(title)}</h1>'
             f'<div class="psub">{self.c.t("period")}: {self.c.period(start, end)}'
             + (f' &nbsp;·&nbsp; {esc(sub)}' if sub else "") + "</div></div>")
        self.h.append(s)

    def sec(self, text):
        self.pending.append(f'<h2 class="sec">{esc(text)}</h2>')

    def title(self, text):
        self.h.append(f'<h2 class="ltitle">{esc(text)}</h2>')

    def block(self, heading, tbl, note=None, level="sub"):
        pre = "".join(self.pending)
        self.pending.clear()
        head = f'<h3 class="{level}">{esc(heading)}</h3>' if heading else ""
        self.h.append(f'<div class="block">{pre}{head}{tbl}'
                      + (f'<div class="note">{esc(note)}</div>' if note else "") + "</div>")

    def msg(self, text):
        pre = "".join(self.pending)
        self.pending.clear()
        self.h.append(f'<div class="block">{pre}<div class="empty">{esc(text)}</div></div>')

    def info(self, pairs):
        cells = "".join(f'<div class="ik">{esc(k)}</div><div class="iv">{esc(v)}</div>' for k, v in pairs)
        self.h.append(f'<div class="info">{cells}</div>')

    def raw(self, s):
        self.h.append(s)


# =====================================================================
#                         SECTIONS (overall)
# =====================================================================
def _sec_supplier(p: Page, o):
    c = p.c
    sup = o["supplier"]
    p.sec(c.t("A"))
    if sup["transactions"]:
        rows, tot = [], 0.0
        for i, x in enumerate(sup["transactions"], 1):
            rows.append([i, c.d(x["date"]), x["bill_id"] or "-", c.v(x["supplier"]), c.v(x["item"]), qty(x["qty"]),
                         c.v(x["unit"]), inr(x["rate"]) if x["rate"] else "-", inr(x["amount"]), c.v(x["driver"]),
                         c.v(x["destination"]), c.v(x["note"])])
            tot += x["amount"]
        rows.append(["", "", "", c.t("total_maal"), "", "", "", "", inr(tot), "", "", ""])
        p.block(c.t("A1"), table([c.t("no"), c.t("date"), c.t("bill"), c.t("supplier"), c.t("item"), c.t("qty"),
                                  c.t("unit"), c.t("rate"), c.t("amount"), c.t("driver"), c.t("dest"), c.t("note")],
                                 rows, num=(5, 7, 8), center=(0, 6), special={len(rows): "sub"}))
    if sup["payments"]:
        rows, tot = [], 0.0
        for i, x in enumerate(sup["payments"], 1):
            rows.append([i, c.d(x["date"]), x["bill_id"] or "-", c.v(x["supplier"]), c.v(x["mode"]), inr(x["amount"]),
                         c.v(x["note"])])
            tot += x["amount"]
        rows.append(["", "", "", c.t("total_paid"), "", inr(tot), ""])
        p.block(c.t("A2"), table([c.t("no"), c.t("date"), c.t("against_bill"), c.t("supplier"), c.t("mode"),
                                  c.t("amount"), c.t("note")], rows, num=(5,), center=(0,), special={len(rows): "sub"}))
    if sup["summary"]:
        rows = [[c.v(x["name"]), c.v(x["type"]), x["phone"] or "-", c.bal(x["opening"]), inr(x["maal"]), inr(x["paid"]),
                 c.bal(x["closing"])] for x in sup["summary"]]
        rows.append([c.t("total"), "", "", c.bal(sum(x["opening"] for x in sup["summary"])),
                     inr(sum(x["maal"] for x in sup["summary"])), inr(sum(x["paid"] for x in sup["summary"])),
                     c.bal(sum(x["closing"] for x in sup["summary"]))])
        p.block(c.t("A3"), table([c.t("supplier"), c.t("type"), c.t("phone"), c.t("open_bal"), c.t("maal_in"),
                                  c.t("paid_minus"), c.t("closing_dena")], rows, num=(3, 4, 5, 6),
                                 special={len(rows): "total"}))
    if not (sup["transactions"] or sup["payments"] or sup["summary"]):
        p.msg(c.t("no_entries"))


def _emp_day_cells(c, x):
    work = " + ".join(qty(a) for a in x["work_breakdown"]) or "-"
    paid = " + ".join(qty(a) for a in x["paid_breakdown"]) or "-"
    notes = c.vl(list(dict.fromkeys((x["work_notes"] or []) + (x["paid_notes"] or []))))
    return work, paid, notes


def _sec_employee(p: Page, o):
    c = p.c
    emp = o["employee"]
    p.sec(c.t("B"))
    if emp["days"]:
        rows, tw, tp = [], 0.0, 0.0
        for i, x in enumerate(emp["days"], 1):
            work, paid, notes = _emp_day_cells(c, x)
            rows.append([i, c.d(x["date"]), c.v(x["employee"]), c.v(x["role"]), inr(x["work_amount"], True), work,
                         inr(x["paid_amount"], True), paid, c.vl(x["modes"], " + "), c.vl(x["providers"], ", "), notes])
            tw += x["work_amount"]; tp += x["paid_amount"]
        rows.append(["", "", c.t("total"), "", inr(tw), "", inr(tp), "", "", "", ""])
        p.block(c.t("B1"), table([c.t("no"), c.t("date"), c.t("employee"), c.t("role"), c.t("work_amt"), c.t("breakdown"),
                                  c.t("paid_amt"), c.t("breakdown"), c.t("mode"), c.t("provider"), c.t("notes")],
                                 rows, num=(4, 6), center=(0,), special={len(rows): "sub"}))
    if emp["summary"]:
        rows = [[c.v(x["name"]), c.v(x["role"]), x["phone"] or "-", c.bal(x["opening"]), inr(x["work"]), inr(x["paid"]),
                 c.bal(x["closing"])] for x in emp["summary"]]
        rows.append([c.t("total"), "", "", c.bal(sum(x["opening"] for x in emp["summary"])),
                     inr(sum(x["work"] for x in emp["summary"])), inr(sum(x["paid"] for x in emp["summary"])),
                     c.bal(sum(x["closing"] for x in emp["summary"]))])
        p.block(c.t("B2"), table([c.t("employee"), c.t("role"), c.t("phone"), c.t("open_bal"), c.t("work_plus"),
                                  c.t("paid_minus_emp"), c.t("closing_dena")], rows, num=(3, 4, 5, 6),
                                 special={len(rows): "total"}), note=c.t("note_emp"))
    if not (emp["days"] or emp["summary"]):
        p.msg(c.t("no_entries"))


def _pay_detail(c, pays):
    return "<br/>".join(f"{c.d(x['date'])}: {inr(x['amount'])}" for x in pays) or "-"


def _sec_purchase(p: Page, pr, heading_key="C"):
    c = p.c
    if pr["rows"]:
        rows = []
        for i, x in enumerate(pr["rows"], 1):
            rows.append([i, c.d(x["date"]), f"PUR-{x['id']}", c.v(x["seller"]), x["phone"] or "-", c.v(x["description"]),
                         c.v(x["location"]), inr(x["total"]) if not x["total_missing"] else c.t("amount_missing"),
                         inr(x["paid"]), inr(x["baaki"], True), _pay_detail(c, x["payments"]), c.v(x["note"])])
        rows.append(["", "", "", c.t("total"), "", "", "", inr(pr["total"]), inr(pr["paid"]), inr(pr["baaki"]), "", ""])
        p.block(c.t(heading_key), table([c.t("no"), c.t("date"), c.t("vch"), c.t("seller"), c.t("phone"), c.t("desc"),
                                         c.t("location"), c.t("tot"), c.t("paid"), c.t("baaki"), c.t("pay_detail"),
                                         c.t("note")], rows, num=(7, 8, 9), center=(0,), special={len(rows): "total"}),
                level="sec")
    else:
        p.sec(c.t(heading_key))
        p.msg(c.t("no_entries"))
    if pr["old_payments"]:
        rows = [[i, c.d(x["date"]), c.v(x["seller"]), c.v(x["description"]), inr(x["amount"]), c.v(x["note"])]
                for i, x in enumerate(pr["old_payments"], 1)]
        rows.append(["", "", c.t("total"), "", inr(sum(x["amount"] for x in pr["old_payments"])), ""])
        p.block(c.t("C_old"), table([c.t("no"), c.t("date"), c.t("seller"), c.t("desc"), c.t("amount"), c.t("note")],
                                    rows, num=(4,), center=(0,), special={len(rows): "sub"}))


def _sec_expense(p: Page, ex, heading_key="D"):
    c = p.c
    if ex["rows"]:
        rows = []
        for i, x in enumerate(ex["rows"], 1):
            rows.append([i, c.d(x["date"]), f"EXP-{x['id']}", c.v(x["category"]), c.v(x["description"]), inr(x["total"]),
                         inr(x["paid"]), inr(x["baaki"], True), _pay_detail(c, x["payments"]), c.v(x["note"])])
        rows.append(["", "", "", c.t("total"), "", inr(ex["total"]), inr(ex["paid"]), inr(ex["baaki"]), "", ""])
        p.block(c.t(heading_key), table([c.t("no"), c.t("date"), c.t("vch"), c.t("category"), c.t("desc"), c.t("tot"),
                                         c.t("paid"), c.t("baaki"), c.t("pay_detail"), c.t("note")], rows,
                                        num=(5, 6, 7), center=(0,), special={len(rows): "total"}), level="sec")
        rows = [[c.v(x["category"]), inr(x["amount"]), f"{x['share'] * 100:.1f}%"] for x in ex["by_category"]]
        rows.append([c.t("total"), inr(ex["total"]), "100%"])
        p.block(c.t("D1"), table([c.t("category"), c.t("amount"), c.t("share")], rows, num=(1, 2),
                                 special={len(rows): "total"}, cls="narrow"))
    else:
        p.sec(c.t(heading_key))
        p.msg(c.t("no_entries"))
    if ex["other_payments"]:
        rows = [[i, c.d(x["date"]), c.v(x["category"]), c.v(x["description"]), inr(x["amount"]), c.v(x["note"])]
                for i, x in enumerate(ex["other_payments"], 1)]
        rows.append(["", "", c.t("total"), "", inr(sum(x["amount"] for x in ex["other_payments"])), ""])
        p.block(c.t("D_old"), table([c.t("no"), c.t("date"), c.t("category"), c.t("desc"), c.t("amount"), c.t("note")],
                                    rows, num=(4,), center=(0,), special={len(rows): "sub"}))


def _sec_sale(p: Page, o):
    c = p.c
    s = o["sale"]
    p.sec(c.t("E"))
    if s["transactions"]:
        rows, tot = [], 0.0
        for i, x in enumerate(s["transactions"], 1):
            rows.append([i, c.d(x["date"]), x["bill_id"] or "-", c.v(x["customer"]), c.v(x["item"]), qty(x["qty"]),
                         c.v(x["unit"]), inr(x["rate"]) if x["rate"] else "-",
                         inr(x["amount"]) if not x["amount_missing"] else c.t("amount_missing"),
                         c.v(x["source"]), c.v(x["destination"]), c.v(x["driver"]), c.v(x["note"])])
            tot += x["amount"]
        rows.append(["", "", "", c.t("total_sale"), "", "", "", "", inr(tot), "", "", "", ""])
        p.block(c.t("E1"), table([c.t("no"), c.t("date"), c.t("bill"), c.t("customer"), c.t("item"), c.t("qty"),
                                  c.t("unit"), c.t("rate"), c.t("amount"), c.t("src"), c.t("to"), c.t("driver"),
                                  c.t("note")], rows, num=(5, 7, 8), center=(0, 6), special={len(rows): "sub"}))
    if s["payments"]:
        rows, tot = [], 0.0
        for i, x in enumerate(s["payments"], 1):
            rows.append([i, c.d(x["date"]), x["bill_id"] or "-", c.v(x["customer"]), c.v(x["mode"]), inr(x["amount"]),
                         c.v(x["note"])])
            tot += x["amount"]
        rows.append(["", "", "", c.t("total_rec"), "", inr(tot), ""])
        p.block(c.t("E2"), table([c.t("no"), c.t("date"), c.t("against_bill"), c.t("customer"), c.t("mode"),
                                  c.t("amount"), c.t("note")], rows, num=(5,), center=(0,), special={len(rows): "sub"}))
    if s["summary"]:
        rows = [[c.v(x["name"]), c.v(x["address"]), x["phone"] or "-", c.bal(x["opening"]), inr(x["sale"]),
                 inr(x["received"]), c.bal(x["closing"])] for x in s["summary"]]
        rows.append([c.t("total"), "", "", c.bal(sum(x["opening"] for x in s["summary"])),
                     inr(sum(x["sale"] for x in s["summary"])), inr(sum(x["received"] for x in s["summary"])),
                     c.bal(sum(x["closing"] for x in s["summary"]))])
        p.block(c.t("E3"), table([c.t("customer"), c.t("address"), c.t("phone"), c.t("opening_udhaar"), c.t("sale_plus"),
                                  c.t("rec_minus"), c.t("closing_dena")], rows, num=(3, 4, 5, 6),
                                 special={len(rows): "total"}))
    if not (s["transactions"] or s["payments"] or s["summary"]):
        p.msg(c.t("no_entries"))


def _family_tables(p: Page, fr, heading_key="FAM", sub1="FAM1", sub2="FAM2"):
    c = p.c
    if heading_key:
        p.sec(c.t(heading_key))
    if not fr["rows"]:
        p.msg(c.t("no_entries"))
        return
    rows = [[i, c.d(x["date"]), c.v(x["member"]), c.v(x["type"]), c.v(x["purpose"]),
             inr(x["diya"], True), inr(x["liya"], True), c.v(x["note"])] for i, x in enumerate(fr["rows"], 1)]
    rows.append(["", "", c.t("total"), "", "", inr(fr["total_diya"]), inr(fr["total_liya"]), ""])
    p.block(c.t(sub1), table([c.t("no"), c.t("date"), c.t("member"), c.t("type"), c.t("purpose"), c.t("fam_diya"),
                              c.t("fam_liya"), c.t("note")], rows, num=(5, 6), center=(0,),
                             special={len(rows): "sub"}))
    rows = [[c.v(x["name"]), c.v(x["relation"]), x["count"], inr(x["diya"], True), inr(x["liya"], True), rs(x["net"])]
            for x in fr["summary"]]
    rows.append([c.t("total"), "", sum(x["count"] for x in fr["summary"]), inr(fr["total_diya"]),
                 inr(fr["total_liya"]), rs(fr["net"])])
    p.block(c.t(sub2), table([c.t("member"), c.t("relation"), c.t("entries"), c.t("fam_diya"), c.t("fam_liya"),
                              c.t("fam_net")], rows, num=(2, 3, 4, 5), special={len(rows): "total"}, cls="narrow"),
            note=c.t("note_family"))


def _sec_family(p: Page, o):
    _family_tables(p, o["family"])


def _family_report(p: Page, fr):
    c = p.c
    sub = c.v(fr["member"]) if fr.get("member") else c.t("family_all")
    p.part(c.t("family_title"), sub, new_page=False)
    if fr.get("long") and fr["months"]:
        rows = [[c.ym(m["ym"]), inr(m["diya"], True), inr(m["liya"], True), rs(m["diya"] - m["liya"])]
                for m in fr["months"]]
        p.block(c.t("month_summary"), table([c.t("month"), c.t("fam_diya"), c.t("fam_liya"), c.t("fam_net")], rows,
                                            num=(1, 2, 3), cls="narrow"), level="sec")
    _family_tables(p, fr, heading_key=None, sub1="fam_entries", sub2="fam_members")


def _sec_overall_balance(p: Page, o):
    c = p.c
    h = o["heads"]
    p.sec(c.t("F"))
    rows = [
        [c.t("h_sup"), inr(h["supplier"]["bill"]), inr(h["supplier"]["out"]), "", c.bal(h["supplier"]["closing"])],
        [c.t("h_emp"), inr(h["employee"]["bill"]), inr(h["employee"]["out"]), "", c.bal(h["employee"]["closing"])],
        [c.t("h_pur"), inr(h["purchase"]["bill"]), inr(h["purchase"]["out"]), "", c.bal(h["purchase"]["closing"])],
        [c.t("h_exp"), inr(h["expense"]["bill"]), inr(h["expense"]["out"]), "", c.bal(h["expense"]["closing"])],
        [c.t("h_sale"), inr(h["sale"]["bill"]), "", inr(h["sale"]["inn"]), c.bal(h["sale"]["closing"])],
    ]
    fam = h.get("family") or dict(out=0.0, inn=0.0)
    if fam["out"] or fam["inn"]:
        rows.append([c.t("h_family"), "", inr(fam["out"], True), inr(fam["inn"], True), "-"])
    out_total = sum(h[k]["out"] for k in ("supplier", "employee", "purchase", "expense")) + fam["out"]
    rows.append([c.t("total"), "", inr(out_total), inr(h["sale"]["inn"] + fam["inn"]), ""])
    p.block(c.t("F1"), table([c.t("head"), c.t("bill_value"), c.t("gaya"), c.t("aaya"), c.t("balance")], rows,
                             num=(1, 2, 3, 4), special={len(rows): "total"}))
    cash = o["cash"]
    rows = [[c.t("cash_open"), inr(cash["opening"])], [c.t("cash_in"), inr(cash["total_in"])],
            [c.t("cash_out"), inr(cash["total_out"])], [c.t("cash_close"), inr(cash["closing"])]]
    p.block(c.t("F2"), table([c.t("particulars"), c.t("amount")], rows, num=(1,), special={1: "open", 4: "total"},
                             cls="narrow"))


# =====================================================================
#                         FINAL HISAB page
# =====================================================================
def _final_page(p: Page, f):
    c = p.c
    p.part(c.t("final"), c.t("as_of", d=c.dlong(f["as_of"])))

    def reason(x):
        r = c.t("r_" + x["reason"])
        return f"{r} — {c.v(x['detail'])}" if x.get("detail") else r

    def side(title, items, total_key, cls):
        if items:
            rows = [[i, c.v(x["party"]), reason(x), inr(x["amount"])] for i, x in enumerate(items, 1)]
            rows.append(["", c.t(total_key), "", inr(sum(x["amount"] for x in items))])
            body = table([c.t("no"), c.t("who"), c.t("why"), c.t("amount")], rows, num=(3,), center=(0,),
                         special={len(rows): "total"})
        else:
            body = f'<div class="empty">{esc(c.t("nothing"))}</div>'
        return f'<div class="side {cls}"><div class="sidehead">{esc(title)}</div>{body}</div>'

    p.raw('<div class="sides">' + side(c.t("give_head"), f["give"], "total_give", "give")
          + side(c.t("take_head"), f["take"], "total_take", "take") + "</div>")
    p.raw(f'<div class="cashline">{esc(c.t("cash_hand"))} ({c.t("as_of", d=c.dlong(f["as_of"]))}): '
          f'<b>{rs(f["cash"])}</b></div>')
    G, K = f["total_give"], f["total_take"]
    if abs(G - K) < 0.005:
        diff = c.t("diff_equal")
    elif G > K:
        diff = c.t("diff_more_give", x=inr(G - K))
    else:
        diff = c.t("diff_more_take", x=inr(K - G))
    after = f["after_settlement"]
    p.raw('<div class="conclusion">' + c.t("conclusion", give=inr(G), take=inr(K), diff_line=diff, cash=rs(f["cash"]),
                                         after=inr(abs(after)),
                                         after_word=c.t("after_left" if after >= 0 else "after_short")) + "</div>")
    p.raw(f'<div class="note">{esc(c.t("note_final"))}</div>')


# =====================================================================
#                         LEDGERS
# =====================================================================
def _ledger_rows_supplier(c, led):
    rows = [["", c.t("open_bal"), "", "", "", "", "", "", "", "", "", c.bal(led["opening"]), ""]]
    for x in led["rows"]:
        if x["vtype"] == "opening":
            rows.append([c.d(x["date"]), c.t("v_opening"), "", "", "", "", "", "", "", inr(x["debit"], True),
                         inr(x["credit"], True), c.bal(x["balance"]), c.v(x.get("note"))])
        elif x["vtype"] == "maal_in":
            rows.append([c.d(x["date"]), c.t("v_maal_in"), x["bill_id"] or "-", c.v(x["item"]), qty(x["qty"]),
                         c.v(x["unit"]), inr(x["rate"]) if x["rate"] else "-", c.v(x["driver"]), c.v(x["destination"]),
                         "-", inr(x["credit"]), c.bal(x["balance"]), c.v(x["note"])])
        else:
            rows.append([c.d(x["date"]), c.t("v_payment_out"), x["bill_id"] or "-", "-", "", "", "", "", "",
                         inr(x["debit"]), "-", c.bal(x["balance"]), c.v(x["note"])])
    rows.append(["", c.t("close_bal"), "", "", "", "", "", "", "", inr(led["total_debit"]), inr(led["total_credit"]),
                 c.bal(led["closing"]), ""])
    return rows


def _supplier_ledger(p: Page, led, with_part=True):
    c = p.c
    s = led["party"]
    if with_part:
        p.part(c.t("sup_ledger"))
    p.info([(c.t("party"), c.v(s["name"])), (c.t("type"), c.v(s["type"])), (c.t("phone"), s["phone"] or "-"),
            (c.t("address"), c.v(s["address"])), (c.t("open_bal"), c.bal(led["opening"])),
            (c.t("close_bal"), c.bal(led["closing"])), (c.t("group"), c.t("g_cred")), ("", "")])
    if not led["rows"]:
        p.msg(c.t("no_entries"))
        return
    rows = _ledger_rows_supplier(c, led)
    p.block("", table([c.t("date"), c.t("vtype"), c.t("bill"), c.t("item"), c.t("qty"), c.t("unit"), c.t("rate"),
                       c.t("driver"), c.t("dest"), c.t("dr_sup"), c.t("cr_sup"), c.t("balance"), c.t("note")],
                      rows, num=(4, 6, 9, 10, 11), center=(5,), special={1: "open", len(rows): "total"}),
            note=c.t("note_sup"))


def _customer_ledger(p: Page, led, with_part=True):
    c = p.c
    s = led["party"]
    if with_part:
        p.part(c.t("cus_ledger"))
    p.info([(c.t("party"), c.v(s["name"])), (c.t("address"), c.v(s["address"])), (c.t("phone"), s["phone"] or "-"),
            (c.t("group"), c.t("g_debt")), (c.t("open_bal"), c.bal(led["opening"])),
            (c.t("sold"), inr(led["total_debit"])), (c.t("received"), inr(led["total_credit"])),
            (c.t("close_bal"), c.bal(led["closing"]))])
    if not led["rows"]:
        p.msg(c.t("no_entries"))
        return
    rows = [["", c.t("open_bal"), "", "", "", "", "", "", "", "", "", "", c.bal(led["opening"]), ""]]
    for x in led["rows"]:
        if x["vtype"] == "opening":
            rows.append([c.d(x["date"]), c.t("v_opening"), "", "", "", "", "", "", "", "", inr(x["debit"], True),
                         inr(x["credit"], True), c.bal(x["balance"]), c.v(x.get("note"))])
        elif x["vtype"] == "sale":
            rows.append([c.d(x["date"]), c.t("v_sale"), x["bill_id"] or "-", c.v(x["item"]), qty(x["qty"]), c.v(x["unit"]),
                         inr(x["rate"]) if x["rate"] else "-", c.v(x["source"]), c.v(x["destination"]), c.v(x["driver"]),
                         inr(x["debit"]) if not x["amount_missing"] else c.t("amount_missing"), "-",
                         c.bal(x["balance"]), c.v(x["note"])])
        else:
            rows.append([c.d(x["date"]), c.t("v_payment_in"), x["bill_id"] or "-", "-", "", "", "", "", "", "", "-",
                         inr(x["credit"]), c.bal(x["balance"]), c.v(x["note"])])
    rows.append(["", c.t("close_bal"), "", "", "", "", "", "", "", "", inr(led["total_debit"]), inr(led["total_credit"]),
                 c.bal(led["closing"]), ""])
    p.block("", table([c.t("date"), c.t("vtype"), c.t("bill"), c.t("item"), c.t("qty"), c.t("unit"), c.t("rate"),
                       c.t("src"), c.t("to"), c.t("driver"), c.t("dr_cus"), c.t("cr_cus"), c.t("balance"), c.t("note")],
                      rows, num=(4, 6, 10, 11, 12), center=(5,), special={1: "open", len(rows): "total"}),
            note=c.t("note_cus"))


def _employee_ledger(p: Page, led, with_part=True):
    c = p.c
    e = led["party"]
    if with_part:
        p.part(c.t("emp_ledger"))
    p.info([(c.t("employee"), c.v(e["name"])), (c.t("role"), c.v(e["role"])), (c.t("phone"), e["phone"] or "-"),
            (c.t("pay_days"), str(led["payment_days"])), (c.t("open_bal"), c.bal(led["opening"])),
            (c.t("total_work"), inr(led["total_work"])), (c.t("total_paid_emp"), inr(led["total_paid"])),
            (c.t("close_bal"), c.bal(led["closing"]))])
    if not led["rows"]:
        p.msg(c.t("no_entries"))
        return
    rows = [["", c.t("open_bal"), "", "", "", "", "", c.bal(led["opening"]), ""]]
    for x in led["rows"]:
        if x["vtype"] == "opening":
            rows.append([c.d(x["date"]), c.t("v_opening"), "", "", "", "", "", c.bal(x["balance"]), c.v(x.get("note"))])
            continue
        work, paid, notes = _emp_day_cells(c, x)
        rows.append([c.d(x["date"]), work if x["work_amount"] else "-", inr(x["work_amount"], True),
                     paid if x["paid_amount"] else "-", c.vl(x["modes"], " + "), c.vl(x["providers"], ", "),
                     inr(x["paid_amount"], True), c.bal(x["balance"]), notes])
    rows.append([c.t("total"), "", inr(led["total_work"]), "", "", "", inr(led["total_paid"]), c.bal(led["closing"]), ""])
    p.block("", table([c.t("date"), c.t("breakdown"), c.t("cr_emp"), c.t("breakdown"), c.t("mode"), c.t("provider"),
                       c.t("dr_emp"), c.t("balance"), c.t("notes")], rows, num=(2, 6, 7),
                      special={1: "open", len(rows): "total"}), note=c.t("note_emp"))


# =====================================================================
#                         REGISTERS
# =====================================================================
def _work_log(p: Page, wl, with_part=True):
    c = p.c
    if with_part:
        p.part(c.t("worklog"), c.t("worklog_sub"))
    if not wl["rows"]:
        p.msg(c.t("no_entries"))
        return
    rows = []
    for i, x in enumerate(wl["rows"], 1):
        works = " + ".join(f"{c.v(w['description'])}" + (f" ({w['labour']})" if w["labour"] else "") for w in x["works"])
        rows.append([i, c.d(x["date"]), c.v(x["location_type"]), c.v(x["location"]), x["entries"], x["labour"] or "-",
                     works, c.vl(x["notes"])])
    p.block("", table([c.t("no"), c.t("date"), c.t("loc_type"), c.t("location"), c.t("entries"), c.t("labour"),
                       c.t("work"), c.t("note")], rows, num=(4, 5), center=(0,)))


def _material(p: Page, mm, with_part=True):
    c = p.c
    if with_part:
        p.part(c.t("mm"))
    if not mm["rows"]:
        p.msg(c.t("no_entries"))
        return
    rows = [[i, c.d(x["date"]), c.v(x["item"]), qty(x["qty"]), c.v(x["unit"]), c.v(x["source_type"]), c.v(x["source"]),
             c.v(x["destination_type"]), c.v(x["destination"]), c.v(x["movement_type"]), c.v(x["reason"]), c.v(x["note"])]
            for i, x in enumerate(mm["rows"], 1)]
    p.block("", table([c.t("no"), c.t("date"), c.t("item"), c.t("qty"), c.t("unit"), c.t("from_type"), c.t("src"),
                       c.t("to_type"), c.t("to"), c.t("mtype"), c.t("reason"), c.t("note")], rows, num=(3,),
                      center=(0, 4)))


def _cash_book(p: Page, cb, with_part=True):
    c = p.c
    if with_part:
        p.part(c.t("cashbook"))
    rows = [["", c.t("open_bal"), "", "", "", "", "", "", inr(cb["opening"])]]
    for x in cb["rows"]:
        src = f"{x['source_table']} #{x['source_id']}" if x.get("source_table") else "-"
        rows.append([c.d(x["date"]), c.v(x["category"]), c.v(x["party"]), c.v(x["mode"]), src, c.v(x["note"]),
                     inr(x["amount"]) if x["direction"] == "in" else "-",
                     inr(x["amount"]) if x["direction"] != "in" else "-", inr(cb["closing"] if False else x["balance"])])
    rows.append(["", c.t("close_bal"), "", "", "", "", inr(cb["total_in"]), inr(cb["total_out"]), inr(cb["closing"])])
    p.block("", table([c.t("date"), c.t("category"), c.t("party"), c.t("mode"), c.t("source"), c.t("note"), c.t("in_"),
                       c.t("out"), c.t("balance")], rows, num=(6, 7, 8), special={1: "open", len(rows): "total"}),
            note=c.t("note_cash"))


# =====================================================================
#                   PERIOD (> 1 mahina) tables
# =====================================================================
def _month_label(c, m):
    return c.ym(m["ym"]) + (f" {c.t('partial')}" if m["partial"] else "")


def _overall_months(p: Page, months):
    c = p.c
    rows = [[_month_label(c, m), inr(m["supplier_maal"], True), inr(m["supplier_paid"], True),
             inr(m["employee_paid"], True), inr(m["purchase_bill"], True), inr(m["expense_bill"], True),
             inr(m["sale"], True), inr(m["received"], True), inr(m.get("family_out", 0), True),
             inr(m["cash_close"])] for m in months]
    tot = lambda k: inr(sum(m.get(k, 0) for m in months))
    rows.append([c.t("total"), tot("supplier_maal"), tot("supplier_paid"), tot("employee_paid"), tot("purchase_bill"),
                 tot("expense_bill"), tot("sale"), tot("received"), tot("family_out"),
                 inr(months[-1]["cash_close"]) if months else ""])
    p.block(c.t("month_summary"), table([c.t("month"), c.t("m_maal"), c.t("m_sup_paid"), c.t("m_emp"), c.t("m_pur"),
                                         c.t("m_exp"), c.t("m_sale"), c.t("m_rec"), c.t("m_family"), c.t("m_cash")],
                                        rows, num=tuple(range(1, 10)), special={len(rows): "total"}), level="sec")


_PARTY_LABELS = dict(
    supplier=("supplier", "dr_sup", "cr_sup"),
    customer=("customer", "dr_cus", "cr_cus"),
    employee=("employee", "dr_emp", "cr_emp"),
)


def _party_months(p: Page, rep, ltype):
    c = p.c
    _, dk, ck = _PARTY_LABELS[ltype]
    rows = [[_month_label(c, m), c.bal(m["opening"]), inr(m["debit"], True), inr(m["credit"], True), c.bal(m["closing"])]
            for m in rep["months"]]
    rows.append([c.t("total"), c.bal(rep["opening"]), inr(rep["total_debit"]), inr(rep["total_credit"]),
                 c.bal(rep["closing"])])
    p.block(c.t("month_summary"), table([c.t("month"), c.t("open_bal"), c.t(dk), c.t(ck), c.t("close_bal")], rows,
                                        num=(1, 2, 3, 4), special={len(rows): "total"}), level="sec")


def _parties_period(p: Page, parties):
    c = p.c
    for lt, key in (("supplier", "A3"), ("employee", "B2"), ("customer", "E3")):
        rows_in = parties.get(lt) or []
        if not rows_in:
            continue
        name_key, dk, ck = _PARTY_LABELS[lt]
        rows = [[c.v(x["name"]), c.bal(x["opening"]), inr(x["debit"], True), inr(x["credit"], True), c.bal(x["closing"])]
                for x in rows_in]
        rows.append([c.t("total"), c.bal(sum(x["opening"] for x in rows_in)), inr(sum(x["debit"] for x in rows_in)),
                     inr(sum(x["credit"] for x in rows_in)), c.bal(sum(x["closing"] for x in rows_in))])
        p.block(c.t(key), table([c.t(name_key), c.t("open_bal"), c.t(dk), c.t(ck), c.t("close_bal")], rows,
                                num=(1, 2, 3, 4), special={len(rows): "total"}))


def _register_months(p: Page, rep, kind):
    c = p.c
    ms = rep["months"]
    if kind == "purchase":
        rows = [[_month_label(c, m), inr(m["purchase_bill"], True), inr(m["purchase_paid"], True)] for m in ms]
        heads = [c.t("month"), c.t("m_bill"), c.t("m_paid")]
    elif kind == "expense":
        rows = [[_month_label(c, m), inr(m["expense_bill"], True), inr(m["expense_paid"], True)] for m in ms]
        heads = [c.t("month"), c.t("m_bill"), c.t("m_paid")]
    elif kind == "cash_flow":
        rows = [[_month_label(c, m), inr(m["cash_open"]), inr(m["cash_in"], True), inr(m["cash_out"], True),
                 inr(m["cash_close"])] for m in ms]
        heads = [c.t("month"), c.t("cash_open"), c.t("in_"), c.t("out"), c.t("cash_close")]
    else:
        return
    p.block(c.t("month_summary"), table(heads, rows, num=tuple(range(1, len(heads))), cls="narrow"), level="sec")


# =====================================================================
#                         TOP-LEVEL
# =====================================================================
def _overall_body(p: Page, o):
    _sec_supplier(p, o)
    _sec_employee(p, o)
    _sec_purchase(p, o["purchase"])
    _sec_expense(p, o["expense"])
    _sec_sale(p, o)
    _sec_family(p, o)
    _sec_overall_balance(p, o)


def _index(p: Page, items):
    c = p.c
    lis = "".join(f"<li>{esc(x)}</li>" for x in items)
    p.raw(f'<div class="index"><div class="ihead">{esc(c.t("index"))}</div><ol>{lis}</ol></div>')


def render_body(p: Page, r):
    c = p.c
    k = r["kind"]
    if k == "overall":
        p.part(c.t("overall"), c.t("overall_order"), new_page=False)
        _index(p, [c.t(x) for x in ("A", "B", "C", "D", "E", "FAM", "F")] + [c.t("cashbook"), c.t("final")])
        _overall_body(p, r)
        _cash_book(p, r["cash_book"])
        _final_page(p, r["final"])
    elif k == "overall_period":
        p.part(c.t("overall"), c.t("period_note"), new_page=False)
        _index(p, [c.t("month_summary"), c.t("party_summary"), c.t("last_month_detail"), c.t("final")])
        _overall_months(p, r["months"])
        p.sec(c.t("party_summary"))
        _parties_period(p, r["parties"])
        d = r["last_month_detail"]
        p.part(c.t("last_month_detail"), start=d["start"], end=d["end"])
        if d["empty"]:
            p.msg(c.t("empty_last_month"))
        else:
            _overall_body(p, d)
            _cash_book(p, d["cash_book"])
        _final_page(p, r["final"])
    elif k == "supplier_ledger":
        _supplier_ledger(p, r)
    elif k == "customer_ledger":
        _customer_ledger(p, r)
    elif k == "employee_ledger":
        _employee_ledger(p, r)
    elif k in ("supplier_period", "customer_period", "employee_period"):
        lt = k.split("_")[0]
        title = {"supplier": "sup_ledger", "customer": "cus_ledger", "employee": "emp_ledger"}[lt]
        p.part(c.t(title), c.t("period_note"), new_page=False)
        _party_months(p, r, lt)
        d = r["last_month_detail"]
        p.part(c.t("last_month_detail"), start=d["start"], end=d["end"])
        if not d["rows"]:
            p.msg(c.t("empty_last_month"))
        else:
            {"supplier": _supplier_ledger, "customer": _customer_ledger,
             "employee": _employee_ledger}[lt](p, d, with_part=False)
    elif k in ("purchase_register", "purchase_period"):
        p.part(c.t("pur_register"), c.t("period_note") if k.endswith("_period") else None, new_page=False)
        if k.endswith("_period"):
            _register_months(p, r, "purchase")
        _sec_purchase(p, r, heading_key="pur_register")
    elif k in ("expense_register", "expense_period"):
        p.part(c.t("exp_register"), c.t("period_note") if k.endswith("_period") else None, new_page=False)
        if k.endswith("_period"):
            _register_months(p, r, "expense")
        _sec_expense(p, r, heading_key="exp_register")
    elif k in ("cash_book", "cash_flow_period"):
        p.part(c.t("cashbook"), c.t("period_note") if k.endswith("_period") else None, new_page=False)
        if k.endswith("_period"):
            _register_months(p, r, "cash_flow")
        _cash_book(p, r, with_part=False)
    elif k in ("work_log", "work_log_period"):
        p.part(c.t("worklog"), c.t("worklog_sub"), new_page=False)
        _work_log(p, r, with_part=False)
    elif k == "family_report":
        _family_report(p, r)
    elif k in ("material_movement", "material_movement_period"):
        p.part(c.t("mm"), new_page=False)
        _material(p, r, with_part=False)
    else:
        raise ValueError(f"render: unknown kind {k}")


def _css():
    def ff(fam, file, weight):
        return (f"@font-face {{ font-family: {fam}; src: url('{(FONT_DIR / file).as_uri()}') format('woff2'); "
                f"font-weight: {weight}; }}")
    fonts = "\n".join([
        ff("NS", "noto-sans-latin-400-normal.woff2", 400), ff("NS", "noto-sans-latin-700-normal.woff2", 700),
        ff("NSX", "noto-sans-latin-ext-400-normal.woff2", 400), ff("NSX", "noto-sans-latin-ext-700-normal.woff2", 700),
        ff("NSD", "noto-sans-devanagari-devanagari-400-normal.woff2", 400),
        ff("NSD", "noto-sans-devanagari-devanagari-700-normal.woff2", 700),
    ])
    return fonts + """
@page { size: A4 landscape; margin: 10mm 11mm 13mm 11mm; }
* { box-sizing: border-box; }
body { font-family: NS, NSX, NSD, sans-serif; font-size: 7.6pt; color: #111; margin: 0; background: #fff; }
.lh { text-align: center; border-bottom: 1.2pt solid #111; padding-bottom: 4pt; margin-bottom: 6pt; }
.lhrow { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; }
.prop { text-align: left; font-size: 8.5pt; font-weight: 700; }
.ph { text-align: right; font-size: 8pt; font-weight: 700; line-height: 1.35; }
.co { font-size: 16pt; font-weight: 700; color: #8a1c1c; letter-spacing: .3pt; }
.cosub { font-size: 7.8pt; color: #444; margin-top: 1pt; }
.addr { font-size: 8pt; font-weight: 700; margin-top: 1pt; }
.part { margin-bottom: 4pt; }
.newpage { break-before: page; }
h1.ptitle { text-align: center; font-size: 12pt; font-weight: 700; margin: 2pt 0 0; }
.psub { text-align: center; font-size: 7.8pt; color: #333; margin: 2pt 0 4pt; }
h2.sec { font-size: 9.8pt; font-weight: 700; margin: 8pt 0 3pt; padding-bottom: 1pt; border-bottom: .8pt solid #111; }
h3.sub { font-size: 8.3pt; font-weight: 700; color: #333; margin: 6pt 0 2pt; }
h3.sec { font-size: 9.8pt; font-weight: 700; margin: 8pt 0 3pt; padding-bottom: 1pt; border-bottom: .8pt solid #111; }
h2.ltitle { text-align: center; font-size: 11pt; font-weight: 700; margin: 12pt 0 4pt; }
.block { break-inside: avoid; }
table.t { width: 100%; border-collapse: collapse; margin-bottom: 2pt; }
table.t.narrow { width: 55%; }
.t th, .t td { border: .5pt solid #888; padding: 2.2pt 3pt; vertical-align: middle; text-align: left; }
.t th { background: #ececec; font-weight: 700; border-bottom: 1pt solid #111; }
.t .r { text-align: right; white-space: nowrap; }
.t .c { text-align: center; }
.t tr.sub td { font-weight: 700; border-top: .9pt solid #111; }
.t tr.total td { font-weight: 700; border-top: 1pt solid #111; border-bottom: 2.2pt double #111; }
.t tr.open td { font-style: italic; color: #333; }
.note { font-size: 7.2pt; font-style: italic; color: #444; margin: 2pt 0 4pt; }
.empty { font-size: 9pt; color: #444; border: .6pt dashed #888; padding: 6pt 8pt; margin: 4pt 0; }
.info { display: grid; grid-template-columns: repeat(4, auto 1fr); border: .7pt solid #111; padding: 3pt 6pt;
        gap: 2pt 6pt; margin-bottom: 5pt; }
.ik { font-weight: 700; }
.index { border: .7pt solid #111; padding: 4pt 10pt; margin: 4pt 0 6pt; width: 55%; }
.ihead { font-weight: 700; font-size: 9pt; }
.index ol { margin: 2pt 0 0 14pt; padding: 0; font-size: 8.5pt; line-height: 1.5; }
.sides, .conclusion { margin-right: 3pt; }
.sides { display: flex; gap: 10pt; margin-top: 8pt; }
.side { flex: 1; border: 1pt solid #111; padding: 6pt; break-inside: avoid; }
.sidehead { font-size: 11pt; font-weight: 700; margin-bottom: 4pt; }
.side .t td, .side .t th { font-size: 8.4pt; padding: 3pt 4pt; }
.cashline { margin-top: 10pt; font-size: 10pt; }
.conclusion { margin-top: 8pt; border: 1.2pt solid #111; padding: 8pt 10pt; font-size: 11pt; line-height: 1.6; }
"""


def render_html(report, lang, vmap=None):
    c = Ctx(lang, vmap)
    p = Page(c, report)
    render_body(p, report)
    body = "\n".join(p.h)
    html_lang = "hi" if lang == "hi" else "en"
    return (f'<!doctype html><html lang="{html_lang}"><head><meta charset="utf-8"><style>{_css()}</style></head>'
            f'<body>{body}</body></html>')


def _footer(lang, report):
    c = Ctx(lang, {})
    left = f"{c.t('footer')} · {c.period(report['start'], report['end'])} · {c.t('generated')}: {c.dlong(date.today())}"
    return (f'<div style="font-family: Arial, Nirmala UI, Mangal, sans-serif; font-size:7px; color:#555; width:100%; '
            f'padding:0 11mm; display:flex; justify-content:space-between;"><span>{left}</span>'
            f'<span>{c.t("page")} <span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')


_PDF_OPTS = dict(format="A4", landscape=True, print_background=True, display_header_footer=True,
                 header_template="<div></div>", outline=True,
                 margin=dict(top="10mm", bottom="13mm", left="11mm", right="11mm"))


def _tmp_html(html, out_path):
    fd, tmp = tempfile.mkstemp(suffix=".html", dir=os.path.dirname(os.path.abspath(out_path)))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(html)
    return tmp


async def html_to_pdf(html, out_path, lang, report):
    from playwright.async_api import async_playwright
    tmp = _tmp_html(html, out_path)
    try:
        async with async_playwright() as pw:
            br = await pw.chromium.launch()
            pg = await br.new_page()
            await pg.goto(Path(tmp).as_uri())
            await pg.evaluate("document.fonts.ready")
            await pg.pdf(path=out_path, footer_template=_footer(lang, report), **_PDF_OPTS)
            await br.close()
    finally:
        os.remove(tmp)
    return out_path


def html_to_pdf_sync(html, out_path, lang, report):
    from playwright.sync_api import sync_playwright
    tmp = _tmp_html(html, out_path)
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            pg = br.new_page()
            pg.goto(Path(tmp).as_uri())
            pg.evaluate("document.fonts.ready")
            pg.pdf(path=out_path, footer_template=_footer(lang, report), **_PDF_OPTS)
            br.close()
    finally:
        os.remove(tmp)
    return out_path


# =====================================================================
#                         file name + one-call helpers
# =====================================================================
OUT_DIR = Path(__file__).resolve().parent.parent / "reports_output"


def output_path(report, lang, out_dir=None):
    out_dir = Path(out_dir or OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    who = ""
    party = report.get("party") or {}
    name = party.get("name") or report.get("member")
    if name:
        who = "_" + "".join(ch if ch.isalnum() else "-" for ch in name).strip("-")
    kind = report["kind"].replace("_ledger", "").replace("_register", "").replace("_report", "")
    return str(out_dir / f"{kind}{who}_{report['start']}_{report['end']}_{lang}.pdf")


def prepare_html(db, report, lang, llm=None):
    vmap = translate_values(db, lang, collect_texts(report), llm=llm)
    return render_html(report, lang, vmap)


def make_pdf(db, report, lang, out_dir=None, llm=None):
    """Sync: report dict → PDF file path (scripts / tests ke liye)."""
    html = prepare_html(db, report, lang, llm=llm)
    return html_to_pdf_sync(html, output_path(report, lang, out_dir), lang, report)


async def make_pdf_async(db, report, lang, out_dir=None, llm=None):
    """Async: graph node ke andar se."""
    html = prepare_html(db, report, lang, llm=llm)
    return await html_to_pdf(html, output_path(report, lang, out_dir), lang, report)
