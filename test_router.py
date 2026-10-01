# test_router.py
from tool_decision_node import route_after_need_person


class DummyGroup:
    def __init__(self, need_person):
        self.need_person = need_person


class DummyGroupedIntent:
    def __init__(self, groups):
        self.groups = groups


TEST_CASES = [

    (
        "TC-01 All False",
        [False],
        "tool_decision"
    ),

    (
        "TC-02 Single True",
        [True],
        "person_role_classification"
    ),

    (
        "TC-03 False False",
        [False, False],
        "tool_decision"
    ),

    (
        "TC-04 True False",
        [True, False],
        "person_role_classification"
    ),

    (
        "TC-05 False True",
        [False, True],
        "person_role_classification"
    ),

    (
        "TC-06 True True",
        [True, True],
        "person_role_classification"
    ),

]


for name, flags, expected in TEST_CASES:

    state = {
        "grouped_intent": DummyGroupedIntent(
            [DummyGroup(f) for f in flags]
        )
    }

    actual = route_after_need_person(state)

    print("-" * 60)
    print(name)
    print("Need Person :", flags)
    print("Expected    :", expected)
    print("Actual      :", actual)

    if actual == expected:
        print("PASS")
    else:
        print("FAIL")