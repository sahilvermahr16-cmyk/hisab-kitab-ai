# transaction_classifier_node.py
from schemas import TransactionType, TransactionClassifierResult
from models import MovementEntityType

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

async def transaction_classifier_node(state):
    """
    Pure rule-based classification — no LLM call, no ambiguity.

    Invoked once per MATERIAL_MOVEMENT group, within that group's own
    parallel branch (dispatched via Send in accounting_subgraph.py).
    Reads THIS group's own resolved entry from material_movement_results
    (keyed by state["single_group"].group_id) and deterministically
    assigns one of: IN / OUT / INTERNAL_MOVEMENT / DIRECT_SALE / UNRESOLVED.
    """
    group = state["single_group"]
    movement_results = state.get("material_movement_results", {})
    info = movement_results.get(group.group_id, {})

    source_type = info.get("source_type")
    destination_type = info.get("destination_type")

    if source_type is None or destination_type is None:
        result = TransactionClassifierResult(
            group_id=group.group_id,
            transaction_type=TransactionType.UNRESOLVED,
            source=info.get("source"),
            destination=info.get("destination"),
            note="Source or destination type unknown — user skipped confirmation.",
        )
    else:
        transaction_type = _CLASSIFICATION_TABLE.get(
            (source_type, destination_type),
            TransactionType.UNRESOLVED,
        )
        note = info.get("note")
        if transaction_type == TransactionType.UNRESOLVED and note is None:
            note = f"Unexpected combination: {source_type.value} → {destination_type.value}"

        result = TransactionClassifierResult(
            group_id=group.group_id,
            transaction_type=transaction_type,
            source=info.get("source"),
            destination=info.get("destination"),
            note=note,
        )

    print(f"\n=== TRANSACTION CLASSIFIER RESULT for {group.group_id} ===")
    print(result)
    print("===============================================")

    return {
        "transaction_classifier_results": {group.group_id: result},
        "single_group": group,
    }




