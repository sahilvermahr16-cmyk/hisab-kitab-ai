from langgraph.types import interrupt
from schemas import (
    ConfidenceLevel,
    HITLInteractionType,
    HITLReason,
    HITLOption,
    PersonRole,
    PersonRoleHITLRequest,
    PersonRoleHITLResponse,
)

# Category dikhane ka fixed order (known person wale sawaal mein)
ROLE_ORDER = [
    PersonRole.EMPLOYEE, PersonRole.CUSTOMER, PersonRole.SUPPLIER,
    PersonRole.PROPERTY_OWNER, PersonRole.FAMILY_MEMBER,
]


def find_person_roles(name: str) -> set:
    """
    Ye naam kin categories ke record mein pehle se hai.
    Employee / Customer / Supplier / Family: helpers.match_known_name — seedha match, kaam ka
    naam hata ke ("Beldar Sohan"), ya Hindi ka aakhri hissa chhod ke ("SBI bhatte" → "SBI Bhatta").
    Property owner: purchases ka seller_name (seedha match).
    """
    from db import SessionLocal
    from helpers import normalize_name, match_known_name
    from sqlalchemy import func
    from models import Employee, Customer, Supplier, FamilyMember, Purchase

    if not name or not name.strip():
        return set()
    n = normalize_name(name)
    found = set()
    db = SessionLocal()
    try:
        for role, model in [(PersonRole.EMPLOYEE, Employee), (PersonRole.CUSTOMER, Customer),
                            (PersonRole.SUPPLIER, Supplier), (PersonRole.FAMILY_MEMBER, FamilyMember)]:
            if match_known_name(db, name, model):
                found.add(role)
        col = Purchase.seller_name
        rows = db.query(col).filter(func.lower(col).like(f"%{n.split()[0]}%")).all()
        if any(normalize_name(r[0] or "") == n for r in rows):
            found.add(PersonRole.PROPERTY_OWNER)
    finally:
        db.close()
    return found


def _known_request(result, found):
    """Naam pehle se mila — fixed order mein saari category, jisme mila uspe found=True."""
    scores = {o.role: o.confidence for o in result.ranking}
    order = sorted(ROLE_ORDER, key=lambda r: (r not in found, ROLE_ORDER.index(r)))  # mili hui category upar
    options = [HITLOption(option_id=i, role=r, confidence=scores.get(r, 0.0), found=r in found)
               for i, r in enumerate(order, start=1)]
    if len(found) == 1:
        it, reason = HITLInteractionType.CONFIRMATION, HITLReason.KNOWN_PERSON_CONFIRMATION
    else:
        it, reason = HITLInteractionType.SELECTION, HITLReason.KNOWN_PERSON_SELECTION
    return PersonRoleHITLRequest(group_id=result.group_id, person=result.person,
                                 interaction_type=it, reason=reason, options=options)


async def person_role_hitl_node(state):
    result = state["person_role_rankings"][0]
    group = state.get("single_group")
    name = (getattr(group, "identity_key", None) or result.person) if group else result.person
    found = find_person_roles(name)

    if found:
        # Naam pehle se hisab mein hai → role hamesha confirm/choose karwao, ✓ ke saath
        request = _known_request(result, found)
    elif result.confidence_level == ConfidenceLevel.HIGH:
        request = PersonRoleHITLRequest(
            group_id=result.group_id,
            person=result.person,
            interaction_type=HITLInteractionType.CONFIRMATION,
            reason=HITLReason.HIGH_CONFIDENCE_CONFIRMATION,
            options=[
                HITLOption(option_id=i, role=o.role, confidence=o.confidence)
                for i, o in enumerate(result.ranking, start=1)
            ],
        )
    else:
        reason = (
            HITLReason.MEDIUM_CONFIDENCE_SELECTION
            if result.confidence_level == ConfidenceLevel.MEDIUM
            else HITLReason.LOW_CONFIDENCE_SELECTION
        )
        request = PersonRoleHITLRequest(
            group_id=result.group_id, person=result.person,
            interaction_type=HITLInteractionType.SELECTION, reason=reason,
            options=[
                HITLOption(option_id=i, role=o.role, confidence=o.confidence)
                for i, o in enumerate(result.ranking, start=1)
            ],
        )

    response = interrupt(request)
    if isinstance(response, dict):          # FastAPI / plain dict resume
        response = PersonRoleHITLResponse(**response)

    if request.interaction_type == HITLInteractionType.CONFIRMATION and response.confirmed:
        resolved_role = request.options[0].role
    else:
        resolved_role = request.options[response.selected_option - 1].role

    return {
        "person_role_hitl_requests": [request],
        "person_role_hitl_responses": [response],
        "resolved_person_roles": {result.group_id: resolved_role},
    }
