from schemas import RecordType

async def correction_node(state):
    groups = [
        g for g in state["grouped_intent"].groups
        if g.record_type == RecordType.CORRECTION
    ]

    if not groups:
        return {}   # is message mein koi correction nahi

    print("\n" + "=" * 60)
    print("CORRECTION NODE (placeholder)")
    print("=" * 60)
    for group in groups:
        print("Group:", group.group_id, "| identity_key:", group.identity_key)
        for action in group.actions:
            print("Action:", action.text, "|", action.date)
    print("=" * 60)

    return {}

