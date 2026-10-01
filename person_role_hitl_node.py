from langgraph.types import interrupt
from schemas import (
    ConfidenceLevel,
    HITLInteractionType,
    HITLReason,
    HITLOption,
    PersonRoleHITLRequest,
    PersonRoleHITLResponse,
)

async def person_role_hitl_node(state):
    result = state["person_role_rankings"][0]

    if result.confidence_level == ConfidenceLevel.HIGH:
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
        response: PersonRoleHITLResponse = interrupt(request)

        if response.confirmed:
            resolved_role = result.ranking[0].role
        else:
            resolved_role = result.ranking[response.selected_option - 1].role

    else:
        reason = (
            HITLReason.MEDIUM_CONFIDENCE_SELECTION
            if result.confidence_level == ConfidenceLevel.MEDIUM
            else HITLReason.LOW_CONFIDENCE_SELECTION
        )
        options = [
            HITLOption(option_id=i, role=o.role, confidence=o.confidence)
            for i, o in enumerate(result.ranking, start=1)
        ]
        request = PersonRoleHITLRequest(
            group_id=result.group_id, person=result.person,
            interaction_type=HITLInteractionType.SELECTION, reason=reason, options=options,
        )
        response: PersonRoleHITLResponse = interrupt(request)
        resolved_role = result.ranking[response.selected_option - 1].role

    return {
        "person_role_hitl_requests": [request],
        "person_role_hitl_responses": [response],
        "resolved_person_roles": {result.group_id: resolved_role},
    }







