REQUIRED_KEYS = [
    "model_name",
    "alphabet",
    "states",
    "start_state",
    "final_states",
    "max_depth",
    "transitions"
]


def validate_json_schema(data):

    print("Validating JSON schema...")

    # Check required fields
    for key in REQUIRED_KEYS:

        if key not in data:

            raise Exception(
                f"Missing required field: {key}"
            )

    # Check start state exists
    if data["start_state"] not in data["states"]:

        raise Exception(
            "Start state does not exist"
        )

    # Check final states exist
    for state in data["final_states"]:

        if state not in data["states"]:

            raise Exception(
                f"Final state invalid: {state}"
            )

    # Check transitions
    for transition in data["transitions"]:

        if transition["from"] not in data["states"]:

            raise Exception(
                f"Invalid FROM state: {transition['from']}"
            )

        if transition["to"] not in data["states"]:

            raise Exception(
                f"Invalid TO state: {transition['to']}"
            )

        if transition["action"] not in data["alphabet"]:

            raise Exception(
                f"Invalid action: {transition['action']}"
            )

    print("JSON schema valid!")

def validate_dfa(data):

    print("Validating DFA rules...")

    transition_map = {}

    for transition in data["transitions"]:

        key = (
            transition["from"],
            transition["action"]
        )

        if key in transition_map:

            raise Exception(
                f"DFA ERROR: duplicate transition {key}"
            )

        transition_map[key] = transition["to"]

    print("DFA validation passed!")