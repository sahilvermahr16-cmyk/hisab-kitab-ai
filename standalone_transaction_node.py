# standalone_transaction_node.py

async def standalone_transaction_node(state):
    """
    Pass-through node for a single STANDALONE_TRANSACTION Action Group.

    This node is invoked once per STANDALONE_TRANSACTION group, via
    LangGraph's Send API (see group_dispatcher in accounting_subgraph.py).
    Each parallel invocation receives exactly one group in
    state["single_group"] — never the full groups-list.

    Standalone transactions (expenses, purchase deals, etc.) don't
    need location resolution (no material movement) or person-role
    resolution (no ambiguous named individual) — their identity_key
    is already self-contained from the Grouping stage.

    This node currently does no transformation; it exists as an
    explicit stage in the graph so:
    - the flow is symmetric with the material_movement and
      person_role branches (each branch has its own node before
      converging on Tool Decision)
    - future logic (e.g. distinguishing Expense vs Purchase Deal
      before Tool Decision) has a clear place to live without
      restructuring the graph
    """
    group = state["single_group"]
    print(f"\nSTANDALONE TRANSACTION: {group.group_id} → {group.identity_key}")
    return {}


