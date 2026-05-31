import json
import importlib
import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from streamlit_agraph import Config, Edge, Node, agraph
except ImportError:
    Config = None
    Edge = None
    Node = None
    agraph = None


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

integration_controller = importlib.import_module(
    "controller.integration_controller"
)
integration_controller = importlib.reload(
    integration_controller
)
run_framework = integration_controller.run_framework


REPORTS_DIR = ROOT_DIR / "reports"
TEMP_MODEL_PATH = REPORTS_DIR / "temp_model.json"
TEMP_MAPPING_PATH = REPORTS_DIR / "temp_mapping.json"

STEP_TYPES = [
    "click",
    "input",
    "assert_text",
    "assert_url",
    "assert_url_contains",
    "wait",
    "screenshot"
]
SELECTOR_TYPES = [
    "id",
    "css",
    "xpath"
]
STEP_TYPES_WITH_SELECTOR = {
    "click",
    "input",
    "assert_text",
    "wait"
}
STEP_TYPES_WITH_VALUE = {
    "input"
}
STEP_TYPES_WITH_EXPECTED = {
    "assert_text",
    "assert_url",
    "assert_url_contains"
}


def save_uploaded_json(uploaded_file, output_path):

    data = json.load(uploaded_file)
    save_json(data, output_path)

    return data


def save_json(data, output_path):

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def read_csv_if_exists(csv_path):

    path = Path(csv_path)

    if not path.exists():
        return None

    return pd.read_csv(path)


def build_results_dataframe(results):

    rows = []

    for item in results:
        rows.append({
            "path_id": item.get("path_id"),
            "dataset_id": item.get("dataset_id"),
            "status": item.get("status"),
            "dataset_values": json.dumps(
                item.get("dataset_map_used", {}),
                ensure_ascii=False
            ),
            "duration_seconds": item.get("duration_seconds"),
            "failed_action": item.get("failed_action"),
            "failed_state": item.get("failed_state"),
            "error": item.get("error"),
            "screenshot": item.get("screenshot")
        })

    return pd.DataFrame(rows)


def validate_test_data_csv(dataframe):

    if "action" not in dataframe.columns:
        return False, "CSV must include 'action' column."

    cleaned = dataframe.dropna(how="all").copy()
    if cleaned.empty:
        return False, "CSV has no valid data rows."

    cleaned["action"] = cleaned["action"].astype(str).str.strip()
    cleaned = cleaned[cleaned["action"] != ""]

    if cleaned.empty:
        return False, "CSV has no valid action rows."

    return True, None


def convert_test_data_csv_to_json(dataframe):

    output = {}
    rows = dataframe.dropna(how="all").to_dict(orient="records")
    data_columns = [
        col for col in dataframe.columns
        if col != "action"
    ]

    for row in rows:
        action = str(row.get("action", "")).strip()

        if not action:
            continue

        payload = {}

        for column in data_columns:
            value = row.get(column)

            if pd.isna(value):
                continue

            payload[column] = value

        output.setdefault(action, []).append(payload)

    return output


def extract_dynamic_fields(text):

    if not isinstance(text, str):
        return []

    matches = re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", text)
    return [item.strip() for item in matches if item.strip()]


def build_data_template_dataframe(mapping_data):

    if not isinstance(mapping_data, dict):
        return pd.DataFrame()

    ordered_fields = []
    seen = set()

    for action_steps in mapping_data.values():
        if not isinstance(action_steps, list):
            continue

        for step_index, step in enumerate(action_steps, start=1):
            if not isinstance(step, dict):
                continue

            step_type = step.get("type", "")

            if step_type == "input":
                placeholder_fields = extract_dynamic_fields(step.get("value", ""))

                if placeholder_fields:
                    for field in placeholder_fields:
                        if field not in seen:
                            seen.add(field)
                            ordered_fields.append(field)
                else:
                    auto_field = f"input_{step_index}_value"
                    if auto_field not in seen:
                        seen.add(auto_field)
                        ordered_fields.append(auto_field)

            if step_type in {"assert_text", "assert_url_contains", "assert_url"}:
                placeholder_fields = extract_dynamic_fields(step.get("expected", ""))

                if placeholder_fields:
                    for field in placeholder_fields:
                        if field not in seen:
                            seen.add(field)
                            ordered_fields.append(field)

    rows = []
    for action in mapping_data:
        row = {"action": action}
        for field in ordered_fields:
            row[field] = ""
        rows.append(row)

    return pd.DataFrame(rows)


def build_chart_dataframe(rows, label_key, value_key):

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).set_index(label_key)[value_key]


def image_exists(image_path):

    return bool(image_path) and Path(image_path).exists()


def init_builder_state():

    defaults = {
        "builder_states": [],
        "builder_state_labels": {},
        "builder_transitions": [],
        "builder_start_state": "",
        "builder_final_states": [],
        "builder_model_name": "login_flow",
        "builder_max_depth": 10
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def init_mapping_builder_state():

    if "mapping_builder_steps" not in st.session_state:
        st.session_state.mapping_builder_steps = {}
    if "mapping_builder_extra_actions" not in st.session_state:
        st.session_state.mapping_builder_extra_actions = []


def create_empty_mapping_step(step_type="click"):

    return {
        "type": step_type,
        "selector_type": "id",
        "selector": "",
        "value": "",
        "expected": ""
    }


def add_state(state_id, state_label):

    state_id = state_id.strip()
    state_label = state_label.strip()

    if not state_id:
        st.warning("State ID is required.")
        return

    if state_id in st.session_state.builder_states:
        st.warning(f"State already exists: {state_id}")
        return

    st.session_state.builder_states.append(state_id)
    st.session_state.builder_state_labels[state_id] = state_label or state_id

    if not st.session_state.builder_start_state:
        st.session_state.builder_start_state = state_id

    st.success(f"Added state: {state_id}")


def add_transition(from_state, to_state, action):

    action = action.strip()

    if not from_state or not to_state:
        st.warning("From state and to state are required.")
        return

    if not action:
        st.warning("Action label is required.")
        return

    duplicate = any(
        item["from"] == from_state and item["action"] == action
        for item in st.session_state.builder_transitions
    )

    if duplicate:
        st.warning(
            "DFA transition already exists for this from state and action."
        )
        return

    st.session_state.builder_transitions.append({
        "from": from_state,
        "to": to_state,
        "action": action
    })
    st.success(f"Added transition: {from_state} -> {to_state} : {action}")


def remove_transition(index):

    if 0 <= index < len(st.session_state.builder_transitions):
        st.session_state.builder_transitions.pop(index)


def import_model_to_builder(model_data):

    states = model_data.get("states", [])
    transitions = model_data.get("transitions", [])

    st.session_state.builder_states = list(states)
    st.session_state.builder_state_labels = {
        state: state
        for state in states
    }
    st.session_state.builder_transitions = [
        {
            "from": item.get("from", ""),
            "to": item.get("to", ""),
            "action": item.get("action", "")
        }
        for item in transitions
    ]
    st.session_state.builder_start_state = model_data.get(
        "start_state",
        states[0] if states else ""
    )
    st.session_state.builder_final_states = model_data.get(
        "final_states",
        []
    )
    st.session_state.builder_model_name = model_data.get(
        "model_name",
        "login_flow"
    )
    st.session_state.builder_max_depth = model_data.get("max_depth", 10)

    # Optional: force refresh UI sau khi import
    st.experimental_rerun()

def build_dfa_model():

    transitions = st.session_state.builder_transitions
    alphabet = sorted({
        item["action"]
        for item in transitions
        if item.get("action")
    })

    return {
        "model_name": st.session_state.builder_model_name.strip()
        or "visual_dfa_model",
        "alphabet": alphabet,
        "states": st.session_state.builder_states,
        "start_state": st.session_state.builder_start_state,
        "final_states": st.session_state.builder_final_states,
        "max_depth": int(st.session_state.builder_max_depth),
        "transitions": transitions
    }


def extract_actions_from_model(model_data):

    seen = set()
    actions = []

    for transition in model_data.get("transitions", []):
        action = str(transition.get("action", "")).strip()

        if action and action not in seen:
            seen.add(action)
            actions.append(action)

    return actions


def sync_mapping_builder_actions(actions):

    current_steps = st.session_state.mapping_builder_steps
    extra_actions = st.session_state.mapping_builder_extra_actions
    all_actions = list(actions) + [
        action for action in extra_actions
        if action not in actions
    ]

    for action in all_actions:
        if action not in current_steps:
            current_steps[action] = []

    stale_actions = [
        action for action in current_steps
        if action not in all_actions
    ]

    for action in stale_actions:
        del current_steps[action]


def import_mapping_to_builder(mapping_data, dfa_actions):

    if not isinstance(mapping_data, dict):
        return False, ["Mapping JSON must be an object: {action: [steps]}."]

    normalized_steps = {}
    errors = []

    for raw_action, raw_steps in mapping_data.items():
        action = str(raw_action).strip()

        if not action:
            errors.append("Action name cannot be empty.")
            continue

        if not isinstance(raw_steps, list):
            errors.append(f"{action}: steps must be a list.")
            continue

        cleaned_steps = []

        for index, raw_step in enumerate(raw_steps, start=1):
            if not isinstance(raw_step, dict):
                errors.append(f"{action} step {index}: step must be an object.")
                continue

            step_type = str(raw_step.get("type", "")).strip()
            if not step_type:
                errors.append(f"{action} step {index}: type is required.")
                continue

            if step_type not in STEP_TYPES:
                errors.append(f"{action} step {index}: invalid step type '{step_type}'.")
                continue

            selector_value = str(raw_step.get("selector", "")).strip()
            if step_type in STEP_TYPES_WITH_SELECTOR and not selector_value:
                errors.append(f"{action} step {index}: selector is required.")
                continue

            step_value = raw_step.get("value", "")
            if step_type in STEP_TYPES_WITH_VALUE and str(step_value).strip() == "":
                errors.append(f"{action} step {index}: value is required.")
                continue

            selector_type = str(raw_step.get("selector_type", "id")).strip() or "id"
            if selector_type not in SELECTOR_TYPES:
                selector_type = "id"

            cleaned_steps.append({
                "type": step_type,
                "selector_type": selector_type,
                "selector": selector_value,
                "value": step_value,
                "expected": raw_step.get("expected", "")
            })

        normalized_steps[action] = cleaned_steps

    if errors:
        return False, errors

    st.session_state.pop("mapping_builder_steps", None)
    st.session_state.pop("mapping_builder_extra_actions", None)
    st.session_state.mapping_builder_steps = normalized_steps
    st.session_state.mapping_builder_extra_actions = [
        action for action in normalized_steps
        if action not in dfa_actions
    ]

    return True, []


def add_mapping_step(action):

    st.session_state.mapping_builder_steps[action].append(
        create_empty_mapping_step()
    )


def remove_mapping_step(action, index):

    steps = st.session_state.mapping_builder_steps.get(action, [])

    if 0 <= index < len(steps):
        steps.pop(index)


def move_mapping_step(action, index, direction):

    steps = st.session_state.mapping_builder_steps.get(action, [])
    target_index = index + direction

    if 0 <= index < len(steps) and 0 <= target_index < len(steps):
        steps[index], steps[target_index] = steps[target_index], steps[index]


def clean_mapping_step(step):

    step_type = step.get("type", "click")
    cleaned = {
        "type": step_type
    }

    if step_type in STEP_TYPES_WITH_SELECTOR:
        cleaned["selector_type"] = step.get("selector_type", "id")
        cleaned["selector"] = step.get("selector", "").strip()

    if step_type in STEP_TYPES_WITH_VALUE:
        cleaned["value"] = step.get("value", "")

    if step_type in STEP_TYPES_WITH_EXPECTED:
        cleaned["expected"] = step.get("expected", "").strip()

    return cleaned


def build_mapping_from_builder(actions):

    mapping = {}

    for action in actions:
        steps = st.session_state.mapping_builder_steps.get(action, [])
        mapping[action] = [
            clean_mapping_step(step)
            for step in steps
        ]

    return mapping


def validate_mapping_builder(mapping, actions):

    errors = []

    duplicate_actions = [
        action for action in actions
        if actions.count(action) > 1
    ]

    if duplicate_actions:
        errors.append(
            "Duplicate actions: "
            + ", ".join(sorted(set(duplicate_actions)))
        )

    for action in actions:
        steps = mapping.get(action, [])

        if not steps:
            errors.append(f"{action}: add at least 1 Selenium step.")
            continue

        for index, step in enumerate(steps, start=1):
            step_type = step.get("type")

            if step_type not in STEP_TYPES:
                errors.append(f"{action} step {index}: invalid step type.")
                continue

            if step_type in STEP_TYPES_WITH_SELECTOR:
                if not step.get("selector", "").strip():
                    errors.append(
                        f"{action} step {index}: selector is required."
                    )

                if step.get("selector_type") not in SELECTOR_TYPES:
                    errors.append(
                        f"{action} step {index}: selector_type is invalid."
                    )

            if (
                step_type in STEP_TYPES_WITH_EXPECTED
                and not step.get("expected", "").strip()
            ):
                errors.append(f"{action} step {index}: expected is required.")

    return errors


def render_step_form(action, step, index):

    type_col, selector_type_col, selector_col = st.columns([1.2, 1, 2])

    with type_col:
        step["type"] = st.selectbox(
            "type",
            options=STEP_TYPES,
            index=STEP_TYPES.index(step.get("type", "click"))
            if step.get("type", "click") in STEP_TYPES else 0,
            key=f"mapping_{action}_{index}_type"
        )

    with selector_type_col:
        selector_disabled = step["type"] not in STEP_TYPES_WITH_SELECTOR
        step["selector_type"] = st.selectbox(
            "selector_type",
            options=SELECTOR_TYPES,
            index=SELECTOR_TYPES.index(step.get("selector_type", "id"))
            if step.get("selector_type", "id") in SELECTOR_TYPES else 0,
            disabled=selector_disabled,
            key=f"mapping_{action}_{index}_selector_type"
        )

    with selector_col:
        step["selector"] = st.text_input(
            "selector",
            value=step.get("selector", ""),
            disabled=step["type"] not in STEP_TYPES_WITH_SELECTOR,
            key=f"mapping_{action}_{index}_selector"
        )

    value_col, expected_col, button_col = st.columns([2, 2, 1.4])

    with value_col:
        step["value"] = st.text_input(
            "value",
            value=step.get("value", ""),
            disabled=step["type"] not in STEP_TYPES_WITH_VALUE,
            key=f"mapping_{action}_{index}_value"
        )

    with expected_col:
        step["expected"] = st.text_input(
            "expected",
            value=step.get("expected", ""),
            disabled=step["type"] not in STEP_TYPES_WITH_EXPECTED,
            key=f"mapping_{action}_{index}_expected"
        )

    with button_col:
        up_col, down_col, remove_col = st.columns(3)

        if up_col.button(
            "Up",
            key=f"mapping_{action}_{index}_up",
            disabled=index == 0
        ):
            move_mapping_step(action, index, -1)
            st.rerun()

        if down_col.button(
            "Down",
            key=f"mapping_{action}_{index}_down",
            disabled=index >= len(st.session_state.mapping_builder_steps[action]) - 1
        ):
            move_mapping_step(action, index, 1)
            st.rerun()

        if remove_col.button(
            "Remove",
            key=f"mapping_{action}_{index}_remove"
        ):
            remove_mapping_step(action, index)
            st.rerun()


def render_visual_mapping_builder(actions):

    st.subheader("Visual Mapping Builder")

    if not actions:
        st.info("Add DFA transitions first. Actions will be extracted automatically.")
        return {}, ["No DFA actions found."]

    sync_mapping_builder_actions(actions)

    st.caption(
        "Actions are extracted from DFA transitions. Each action must contain at least one Selenium step."
    )

    all_actions = list(actions) + [
        action for action in st.session_state.mapping_builder_extra_actions
        if action not in actions
    ]

    for action in all_actions:
        steps = st.session_state.mapping_builder_steps[action]
        title = f"Action: {action} ({len(steps)} step{'s' if len(steps) != 1 else ''})"

        with st.expander(title, expanded=True):
            if not steps:
                st.info("No steps yet.")

            for index, step in enumerate(steps):
                st.markdown(f"Step {index + 1}")
                render_step_form(action, step, index)

            if st.button(
                "Add Step",
                key=f"mapping_{action}_add_step"
            ):
                add_mapping_step(action)
                st.rerun()

    mapping = build_mapping_from_builder(all_actions)
    errors = validate_mapping_builder(mapping, all_actions)

    preview_col, validation_col = st.columns([1.2, 1])

    with preview_col:
        st.write("Mapping JSON preview")
        st.json(mapping)

        st.download_button(
            "Download mapping.json",
            data=json.dumps(mapping, indent=2, ensure_ascii=False),
            file_name="mapping.json",
            mime="application/json",
            use_container_width=True,
            disabled=bool(errors)
        )

    with validation_col:
        st.write("Validation")

        if errors:
            for error in errors:
                st.error(error)
        else:
            st.success("Mapping is valid.")

        if st.button(
            "Save Generated Mapping",
            use_container_width=True,
            disabled=bool(errors)
        ):
            save_json(mapping, TEMP_MAPPING_PATH)
            st.success(f"Saved mapping to {TEMP_MAPPING_PATH}")

    return mapping, errors


def render_visual_graph(model_data):

    if agraph is None:
        st.error(
            "Missing dependency: streamlit-agraph. "
            "Install it with `pip install streamlit-agraph`."
        )
        return

    state_labels = st.session_state.builder_state_labels
    final_states = set(model_data["final_states"])

    nodes = []
    for state in model_data["states"]:
        color = "#8fd19e"

        if state in final_states:
            color = "#f4a7a7"

        if state == model_data["start_state"]:
            color = "#7cc7ff"

        nodes.append(
            Node(
                id=state,
                label=state_labels.get(state, state),
                size=28,
                color=color
            )
        )

    edges = [
        Edge(
            source=item["from"],
            target=item["to"],
            label=item["action"]
        )
        for item in model_data["transitions"]
    ]

    config = Config(
        width=900,
        height=420,
        directed=True,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#f6d365",
        collapsible=False
    )

    agraph(
        nodes=nodes,
        edges=edges,
        config=config
    )


def validate_builder_model(model_data):

    if not model_data["states"]:
        return "Add at least one state before running."

    if not model_data["start_state"]:
        return "Select a start state before running."

    if model_data["start_state"] not in model_data["states"]:
        return "Start state does not exist in states."

    invalid_finals = [
        state for state in model_data["final_states"]
        if state not in model_data["states"]
    ]

    if invalid_finals:
        return f"Invalid final states: {', '.join(invalid_finals)}"

    return None


st.set_page_config(
    page_title="DFA Web Testing Tool",
    layout="wide"
)

init_builder_state()
init_mapping_builder_state()

st.title("DFA Web Testing Tool")
st.caption("Model-Based Testing with DFA, DFS and Selenium")

st.sidebar.header("Test Configuration")

website_url = st.sidebar.text_input(
    "Website URL",
    value="https://www.saucedemo.com/"
)

mapping_file = st.sidebar.file_uploader(
    "Mapping JSON fallback",
    type=["json"]
)

use_visual_mapping = st.sidebar.checkbox(
    "Use Visual Mapping Builder",
    value=True
)

if "test_data" not in st.session_state:
    st.session_state.test_data = {}

if "test_data_template_df" not in st.session_state:
    st.session_state.test_data_template_df = pd.DataFrame()

generate_template_button = st.sidebar.button(
    "Generate CSV Template",
    use_container_width=True
)

test_data_file = st.sidebar.file_uploader(
    "Upload CSV Test Data",
    type=["csv"]
)

run_button = st.sidebar.button(
    "Run Test Data-driven",
    use_container_width=True
)

if "result" not in st.session_state:
    st.session_state.result = None


st.subheader("Visual DFA Builder")

builder_left, builder_right = st.columns([1, 1])

with builder_left:
    st.text_input(
        "Model name",
        key="builder_model_name"
    )

    st.number_input(
        "Max depth",
        min_value=1,
        max_value=100,
        step=1,
        key="builder_max_depth"
    )

    with st.form("add_state_form", clear_on_submit=True):
        state_id = st.text_input("State ID", placeholder="q0")
        state_label = st.text_input(
            "State label (optional)",
            placeholder="Login Page"
        )
        add_state_button = st.form_submit_button(
            "Add State",
            use_container_width=True
        )

        if add_state_button:
            add_state(state_id, state_label)

    states = st.session_state.builder_states

    if states:
        st.selectbox(
            "Start state",
            options=states,
            key="builder_start_state"
        )

        st.multiselect(
            "Final states",
            options=states,
            key="builder_final_states"
        )

        with st.form("add_transition_form", clear_on_submit=True):
            from_state = st.selectbox(
                "From state",
                options=states,
                key="transition_from_state"
            )
            to_state = st.selectbox(
                "To state",
                options=states,
                key="transition_to_state"
            )
            action = st.text_input(
                "Action label",
                placeholder="login_success"
            )
            add_transition_button = st.form_submit_button(
                "Add Transition",
                use_container_width=True
            )

            if add_transition_button:
                add_transition(from_state, to_state, action)

    else:
        st.info("Add states first, then create transitions.")

with builder_right:
    st.write("Transitions")

    transitions = st.session_state.builder_transitions

    if not transitions:
        st.info("No transitions yet.")

    for index, transition in enumerate(transitions):
        c1, c2 = st.columns([5, 1])
        c1.write(
            f"{transition['from']} -> {transition['to']} : "
            f"{transition['action']}"
        )

        if c2.button("Remove", key=f"remove_transition_{index}"):
            remove_transition(index)
            st.rerun()

    uploaded_model = st.file_uploader(
        "Import existing DFA model JSON (optional)",
        type=["json"]
    )

    if uploaded_model and st.button(
        "Import Model Into Builder",
        use_container_width=True
    ):
        try:
            import_model_to_builder(json.load(uploaded_model))
            st.success("Imported model into visual builder.")
            st.rerun()
        except Exception as error:
            st.error(f"Cannot import model: {error}")


generated_model = build_dfa_model()
generated_actions = extract_actions_from_model(generated_model)

st.subheader("Import Mapping JSON")
uploaded_mapping_builder = st.file_uploader(
    "Import mapping into Visual Mapping Builder (optional)",
    type=["json"],
    key="mapping_builder_import_file"
)

if uploaded_mapping_builder and st.button(
    "Import Mapping Into Builder",
    use_container_width=True
):
    try:
        imported_mapping_data = json.load(uploaded_mapping_builder)
        imported_ok, imported_errors = import_mapping_to_builder(
            imported_mapping_data,
            generated_actions
        )
        if imported_ok:
            st.success("Imported mapping into visual builder.")
            st.rerun()
        else:
            for imported_error in imported_errors:
                st.error(imported_error)
    except Exception as error:
        st.error(f"Cannot import mapping: {error}")

preview_tab, json_tab = st.tabs(
    [
        "Graph Preview",
        "Generated JSON"
    ]
)

with preview_tab:
    render_visual_graph(generated_model)

with json_tab:
    st.json(generated_model)

    save_col, download_col = st.columns(2)

    if save_col.button(
        "Save Generated Model",
        use_container_width=True
    ):
        save_json(generated_model, TEMP_MODEL_PATH)
        st.success(f"Saved model to {TEMP_MODEL_PATH}")

    download_col.download_button(
        "Download Model JSON",
        data=json.dumps(generated_model, indent=2, ensure_ascii=False),
        file_name=f"{generated_model['model_name']}.json",
        mime="application/json",
        use_container_width=True
    )


generated_mapping, mapping_errors = render_visual_mapping_builder(
    generated_actions
)

current_mapping_data = {}
if use_visual_mapping:
    current_mapping_data = generated_mapping
elif mapping_file:
    try:
        current_mapping_data = json.load(mapping_file)
        mapping_file.seek(0)
    except Exception as error:
        st.error(f"Cannot read fallback mapping JSON: {error}")
        current_mapping_data = {}

if generate_template_button:
    template_df = build_data_template_dataframe(current_mapping_data)

    if template_df.empty:
        st.error("Cannot generate template. Mapping is empty or invalid.")
    else:
        st.session_state.test_data_template_df = template_df
        st.success("CSV template generated.")

template_df = st.session_state.test_data_template_df

if not template_df.empty:
    st.subheader("CSV Template")
    st.dataframe(template_df, use_container_width=True)
    st.download_button(
        "Download CSV Template",
        data=template_df.to_csv(index=False),
        file_name="test_data_template.csv",
        mime="text/csv",
        use_container_width=True
    )

if test_data_file is not None:
    try:
        test_data_df = pd.read_csv(test_data_file)
        valid_csv, csv_error = validate_test_data_csv(test_data_df)

        if not valid_csv:
            st.error(csv_error)
            st.session_state.test_data = {}
        else:
            st.session_state.test_data = convert_test_data_csv_to_json(test_data_df)
            st.success("CSV test data uploaded and converted.")
            st.json(st.session_state.test_data)

    except Exception as error:
        st.error(f"Cannot parse CSV test data: {error}")
        st.session_state.test_data = {}


if run_button:

    builder_error = validate_builder_model(generated_model)

    if not website_url:
        st.error("Website URL is required.")

    elif builder_error:
        st.error(builder_error)

    elif use_visual_mapping and mapping_errors:
        st.error("Generated mapping is not valid. Fix it before running.")

    elif not use_visual_mapping and not mapping_file:
        st.error("Upload a Mapping JSON or enable Visual Mapping Builder.")

    else:
        REPORTS_DIR.mkdir(exist_ok=True)

        try:
            save_json(
                generated_model,
                TEMP_MODEL_PATH
            )

            if use_visual_mapping:
                mapping_data = generated_mapping
                save_json(mapping_data, TEMP_MAPPING_PATH)
            else:
                mapping_file.seek(0)
                mapping_data = save_uploaded_json(
                    mapping_file,
                    TEMP_MAPPING_PATH
                )

            with st.spinner("Running DFA validation, path generation, graph generation and Selenium execution..."):
                result = run_framework(
                    base_url=website_url,
                    model_path=str(TEMP_MODEL_PATH),
                    mapping_path=str(TEMP_MAPPING_PATH),
                    reports_dir=str(REPORTS_DIR),
                    test_data=st.session_state.test_data
                )

            st.session_state.result = {
                "pipeline": result,
                "model": generated_model,
                "mapping": mapping_data
            }

            st.success("Test run completed.")

        except Exception as error:
            st.session_state.result = None
            st.error(str(error))


result_state = st.session_state.result

if not result_state:
    st.info("Build a DFA visually, configure the generated mapping, enter the website URL, then click RUN.")

    st.code(
        """
Pipeline:
Visual DFA builder -> generated model JSON -> extract actions -> Visual Mapping Builder -> validate -> DFS paths CSV -> graph image -> Selenium execution -> assertions -> screenshots -> summary report
        """.strip()
    )

else:
    result = result_state["pipeline"]
    summary = result["summary"]

    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    total_duration = summary.get("total_duration", 0)
    average_duration = summary.get("average_duration", 0)
    slowest_path = summary.get("slowest_path") or {}
    most_failed_action = summary.get("most_failed_action") or {}

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total Paths", total)
    col2.metric("Passed", passed)
    col3.metric("Failed", failed)
    col4.metric("Total Time", f"{total_duration}s")
    col5.metric("Avg Time", f"{average_duration}s")
    col6.metric(
        "Slowest Path",
        slowest_path.get("path_id", "-")
    )

    tab_summary, tab_failures, tab_analytics, tab_paths, tab_graph, tab_mapping, tab_files = st.tabs(
        [
            "Summary",
            "Failures",
            "Analytics",
            "Generated Paths",
            "Graph",
            "Mapping",
            "Files"
        ]
    )

    with tab_summary:
        st.subheader("Execution Summary")
        st.download_button(
            "Download Summary JSON",
            data=json.dumps(summary, indent=2, ensure_ascii=False),
            file_name="execution_summary.json",
            mime="application/json",
            use_container_width=True
        )

        results_df = build_results_dataframe(
            summary.get("results", [])
        )

        st.dataframe(
            results_df,
            use_container_width=True
        )

        timing_df = results_df[
            [
                "path_id",
                "duration_seconds",
                "status"
            ]
        ] if not results_df.empty else pd.DataFrame()

        if not timing_df.empty:
            st.subheader("Execution Timing")
            st.bar_chart(
                timing_df.set_index("path_id")["duration_seconds"]
            )

        st.json(summary)

    with tab_failures:
        st.subheader("Failed Test Cases")

        failed_results = [
            item for item in summary.get("results", [])
            if item.get("status") == "FAIL"
        ]

        if not failed_results:
            st.success("No failed test cases.")

        for item in failed_results:
            title = (
                f"Path {item.get('path_id')} | "
                f"Dataset {item.get('dataset_id', 'row_1')} | "
                f"Action: {item.get('failed_action')} | "
                f"{item.get('duration_seconds')}s"
            )

            with st.expander(title, expanded=True):
                st.write("Error:")
                st.code(item.get("error") or "")

                st.write("Dataset Values:")
                st.json(item.get("dataset_map_used", {}))

                st.write("Action Logs:")
                st.json(item.get("action_logs", []))

                st.write("Actions:")
                st.code(" -> ".join(item.get("actions", [])))

                st.write("State Trace:")
                st.code(" -> ".join(item.get("state_trace", [])))

                screenshot_path = item.get("screenshot")

                if image_exists(screenshot_path):
                    st.image(
                        screenshot_path,
                        caption=screenshot_path,
                        use_container_width=True
                    )
                else:
                    st.warning("No screenshot available.")

    with tab_analytics:
        st.subheader("Fail Analytics")

        a1, a2, a3 = st.columns(3)
        a1.metric(
            "Most Failed Action",
            most_failed_action.get("action", "-"),
            most_failed_action.get("count", 0)
        )
        a2.metric(
            "Most Failed Path",
            (summary.get("most_failed_path") or {}).get("path_id", "-"),
            (summary.get("most_failed_path") or {}).get("count", 0)
        )
        a3.metric(
            "Most Failed State",
            (summary.get("most_failed_state") or {}).get("state", "-"),
            (summary.get("most_failed_state") or {}).get("count", 0)
        )

        failed_actions = summary.get("failed_actions", [])
        failed_paths = summary.get("failed_paths", [])
        failed_states = summary.get("failed_states", [])

        c1, c2 = st.columns(2)

        with c1:
            st.write("Failed Actions")
            action_chart = build_chart_dataframe(
                failed_actions,
                "action",
                "fail_count"
            )

            if action_chart.empty:
                st.info("No failed actions.")
            else:
                st.bar_chart(action_chart)
                st.dataframe(
                    pd.DataFrame(failed_actions),
                    use_container_width=True
                )

        with c2:
            st.write("Failed Paths")
            path_chart = build_chart_dataframe(
                failed_paths,
                "path_id",
                "fail_count"
            )

            if path_chart.empty:
                st.info("No failed paths.")
            else:
                st.bar_chart(path_chart)
                st.dataframe(
                    pd.DataFrame(failed_paths),
                    use_container_width=True
                )

        st.write("Failed State Frequency")
        state_chart = build_chart_dataframe(
            failed_states,
            "state",
            "fail_frequency"
        )

        if state_chart.empty:
            st.info("No failed states.")
        else:
            st.bar_chart(state_chart)
            st.dataframe(
                pd.DataFrame(failed_states),
                use_container_width=True
            )

    with tab_paths:
        st.subheader("Generated Test Paths")

        csv_data = read_csv_if_exists(result["csv_path"])

        if csv_data is None:
            st.warning("CSV file was not found.")
        else:
            st.dataframe(
                csv_data,
                use_container_width=True
            )

    with tab_graph:
        st.subheader("DFA Graph")

        graph_path = Path(result["graph_path"])

        if graph_path.exists():
            st.image(str(graph_path))
        else:
            st.warning("Graph image was not found.")

    with tab_mapping:
        st.subheader("Mapping")
        st.json(result_state["mapping"])

    with tab_files:
        st.subheader("Generated Files")

        files = [
            {
                "type": "Generated DFA model",
                "path": str(TEMP_MODEL_PATH)
            },
            {
                "type": "CSV paths",
                "path": result["csv_path"]
            },
            {
                "type": "Graph image",
                "path": result["graph_path"]
            },
            {
                "type": "Summary report",
                "path": str(REPORTS_DIR / "execution_summary.json")
            },
            {
                "type": "Screenshots folder",
                "path": str(REPORTS_DIR / "screenshots")
            }
        ]

        st.dataframe(
            pd.DataFrame(files),
            use_container_width=True
        )
