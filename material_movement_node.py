# material_movement_node.py
from langgraph.types import interrupt
from db import SessionLocal
from schemas import (
    MaterialMovementHITLRequest, MaterialMovementHITLResponse,
    MaterialMovementHITLReason, LocationTypeOption,
    TransactionType, TransactionClassifierResult,
)
from helpers import lookup_movement_entity, sync_movement_entity
from models import MovementEntityType


def _parse_identity_key(identity_key: str) -> tuple[str | None, str | None]:
    if "→" not in identity_key:
        return (identity_key.strip() or None, None)
    source, destination = identity_key.split("→", 1)
    return (source.strip() or None, destination.strip() or None)

_CLASSIFICATION_TABLE = {
    (MovementEntityType.SUPPLIER, MovementEntityType.STORAGE): TransactionType.IN,
    (MovementEntityType.SUPPLIER, MovementEntityType.SITE): TransactionType.IN,
    (MovementEntityType.STORAGE, MovementEntityType.CUSTOMER): TransactionType.OUT,
    (MovementEntityType.STORAGE, MovementEntityType.STORAGE): TransactionType.INTERNAL_MOVEMENT,
    (MovementEntityType.SITE, MovementEntityType.STORAGE): TransactionType.INTERNAL_MOVEMENT,
    (MovementEntityType.SITE, MovementEntityType.SITE): TransactionType.INTERNAL_MOVEMENT,
    (MovementEntityType.SUPPLIER, MovementEntityType.CUSTOMER): TransactionType.DIRECT_SALE,
    (MovementEntityType.SITE, MovementEntityType.CUSTOMER): TransactionType.DIRECT_SALE,
}

def _classify_transaction(
    group_id: str,
    source: str | None,
    source_type: MovementEntityType | None,
    destination: str | None,
    destination_type: MovementEntityType | None,
    existing_note: str | None,
) -> TransactionClassifierResult:
    if source_type is None or destination_type is None:
        return TransactionClassifierResult(
            group_id=group_id,
            transaction_type=TransactionType.UNRESOLVED,
            source=source,
            destination=destination,
            note="Source or destination type unknown — user skipped confirmation.",
        )

    transaction_type = _CLASSIFICATION_TABLE.get(
        (source_type, destination_type),
        TransactionType.UNRESOLVED,
    )
    note = existing_note
    if transaction_type == TransactionType.UNRESOLVED and note is None:
        note = f"Unexpected combination: {source_type.value} → {destination_type.value}"

    return TransactionClassifierResult(
        group_id=group_id,
        transaction_type=transaction_type,
        source=source,
        destination=destination,
        note=note,
    )

async def material_movement_node(state):
    """
    Resolves source and destination for ONE MATERIAL_MOVEMENT group,
    AND — once fully resolved — classifies it (IN/OUT/Internal/
    Direct Sale) in the same final pass. Classification used to live
    in a separate transaction_classifier_node, but that intermediate
    node created a race condition with LangGraph's fan-in: because
    this node loops back on itself (via route_after_material_movement)
    across multiple super-steps for its HITL resolution, LangGraph's
    fan-in at TOOL_DECISION was firing as soon as the FASTER parallel
    branches (e.g. a single-confirmation Person-Role branch) arrived,
    without waiting for this branch's separate classifier node to run.

    Merging classification into this node's own final return
    eliminates that extra edge/node entirely — TOOL_DECISION now only
    fires once this node's SINGLE outgoing edge resolves, which
    LangGraph can track correctly.

    Still invoked once per MATERIAL_MOVEMENT group, via Send. This
    node calls interrupt() AT MOST ONCE per invocation, per the
    original multi-pass design — see git history for full rationale.
    """
    db = SessionLocal()
    group = state["single_group"]

    results = state.get("material_movement_results", {})
    progress = state.get("material_movement_progress", {})
    classifier_results = state.get("transaction_classifier_results", {})

    try:
        if group.group_id in results:
            return {
                "material_movement_results": results,
                "transaction_classifier_results": classifier_results,
                "single_group": group,
            }

        group_progress = progress.get(group.group_id, {})

        if "source" not in group_progress or "destination" not in group_progress:
            source, destination = _parse_identity_key(group.identity_key)
            group_progress.setdefault("source", source)
            group_progress.setdefault("destination", destination)
            progress[group.group_id] = group_progress

        source = group_progress.get("source")
        destination = group_progress.get("destination")

        if not source and "source" not in group_progress.get("resolved_missing", []):
            request = MaterialMovementHITLRequest(
                group_id=group.group_id,
                reason=MaterialMovementHITLReason.MISSING_FIELD,
                missing_field="source",
            )
            response: MaterialMovementHITLResponse = interrupt(request)
            group_progress["source"] = response.provided_value or None
            group_progress.setdefault("resolved_missing", []).append("source")
            progress[group.group_id] = group_progress
            db.commit()
            db.close()
            return {"material_movement_progress": progress, "single_group": group}

        if not destination and "destination" not in group_progress.get("resolved_missing", []):
            request = MaterialMovementHITLRequest(
                group_id=group.group_id,
                reason=MaterialMovementHITLReason.MISSING_FIELD,
                missing_field="destination",
            )
            response: MaterialMovementHITLResponse = interrupt(request)
            group_progress["destination"] = response.provided_value or None
            group_progress.setdefault("resolved_missing", []).append("destination")
            progress[group.group_id] = group_progress
            db.commit()
            db.close()
            return {"material_movement_progress": progress, "single_group": group}

        source = group_progress.get("source")
        destination = group_progress.get("destination")

        if source and "source_type" not in group_progress:
            record = lookup_movement_entity(db, source)
            if record:
                group_progress["source_type"] = MovementEntityType(record.entity_type)
                progress[group.group_id] = group_progress
            else:
                request = MaterialMovementHITLRequest(
                    group_id=group.group_id,
                    reason=MaterialMovementHITLReason.LOCATION_TYPE_CONFIRMATION,
                    location_name=source,
                    options=[
                        LocationTypeOption(option_id=1, location_type=MovementEntityType.STORAGE),
                        LocationTypeOption(option_id=2, location_type=MovementEntityType.SITE),
                        LocationTypeOption(option_id=3, location_type=MovementEntityType.CUSTOMER),
                        LocationTypeOption(option_id=4, location_type=MovementEntityType.SUPPLIER),
                    ],
                )
                response: MaterialMovementHITLResponse = interrupt(request)
                if response.selected_option is None:
                    group_progress["source_type"] = None
                else:
                    chosen = {1: MovementEntityType.STORAGE, 2: MovementEntityType.SITE,
                              3: MovementEntityType.CUSTOMER, 4: MovementEntityType.SUPPLIER}[response.selected_option]
                    sync_movement_entity(db, name=source, entity_type=chosen, confirmed_by="hitl")
                    group_progress["source_type"] = chosen
                progress[group.group_id] = group_progress
                db.commit()
                db.close()
                return {"material_movement_progress": progress, "single_group": group}

        elif not source:
            group_progress["source_type"] = None
            progress[group.group_id] = group_progress

        if destination and "destination_type" not in group_progress:
            record = lookup_movement_entity(db, destination)
            if record:
                group_progress["destination_type"] = MovementEntityType(record.entity_type)
                progress[group.group_id] = group_progress
            else:
                request = MaterialMovementHITLRequest(
                    group_id=group.group_id,
                    reason=MaterialMovementHITLReason.LOCATION_TYPE_CONFIRMATION,
                    location_name=destination,
                    options=[
                        LocationTypeOption(option_id=1, location_type=MovementEntityType.STORAGE),
                        LocationTypeOption(option_id=2, location_type=MovementEntityType.SITE),
                        LocationTypeOption(option_id=3, location_type=MovementEntityType.CUSTOMER),
                        LocationTypeOption(option_id=4, location_type=MovementEntityType.SUPPLIER),
                    ],
                )
                response: MaterialMovementHITLResponse = interrupt(request)
                if response.selected_option is None:
                    group_progress["destination_type"] = None
                else:
                    chosen = {1: MovementEntityType.STORAGE, 2: MovementEntityType.SITE,
                              3: MovementEntityType.CUSTOMER, 4: MovementEntityType.SUPPLIER}[response.selected_option]
                    sync_movement_entity(db, name=destination, entity_type=chosen, confirmed_by="hitl")
                    group_progress["destination_type"] = chosen
                progress[group.group_id] = group_progress
                db.commit()
                db.close()
                return {"material_movement_progress": progress, "single_group": group}

        elif not destination:
            group_progress["destination_type"] = None
            progress[group.group_id] = group_progress

        # Both fully resolved — finalize this group AND classify it,
        # all in this same final pass, so no extra node/edge is needed.
        note = None
        if source and destination and source.strip().lower() == destination.strip().lower():
            note = "WARNING: source and destination resolved to the same location."

        results[group.group_id] = {
            "source": source,
            "source_type": group_progress.get("source_type"),
            "destination": destination,
            "destination_type": group_progress.get("destination_type"),
            "note": note,
        }
        progress.pop(group.group_id, None)

        classification = _classify_transaction(
            group_id=group.group_id,
            source=source,
            source_type=group_progress.get("source_type"),
            destination=destination,
            destination_type=group_progress.get("destination_type"),
            existing_note=note,
        )
        classifier_results[group.group_id] = classification

    finally:
        db.commit()
        db.close()

    print("\n=== MATERIAL MOVEMENT NODE RESULT ===")
    print(results)
    print("=== TRANSACTION CLASSIFIER RESULT ===")
    print(classifier_results)
    print("======================================")

    return {
        "material_movement_results": results,
        "material_movement_progress": progress,
        "transaction_classifier_results": classifier_results,
        "single_group": group,
    }


