import json
import importlib
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
            "status": item.get("status"),
            "duration_seconds": item.get("duration_seconds"),
            "failed_action": item.get("failed_action"),
            "failed_state": item.get("failed_state"),
            "error": item.get("error"),
            "screenshot": item.get("screenshot")
        })

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

st.title("DFA Web Testing Tool")
st.caption("Model-Based Testing with DFA, DFS and Selenium")

st.sidebar.header("Test Configuration")

website_url = st.sidebar.text_input(
    "Website URL",
    value="https://www.saucedemo.com/"
)

mapping_file = st.sidebar.file_uploader(
    "Mapping JSON",
    type=["json"]
)

run_button = st.sidebar.button(
    "RUN",
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


if run_button:

    builder_error = validate_builder_model(generated_model)

    if not website_url:
        st.error("Website URL is required.")

    elif not mapping_file:
        st.error("Mapping JSON is required.")

    elif builder_error:
        st.error(builder_error)

    else:
        REPORTS_DIR.mkdir(exist_ok=True)

        try:
            save_json(
                generated_model,
                TEMP_MODEL_PATH
            )
            mapping_data = save_uploaded_json(
                mapping_file,
                TEMP_MAPPING_PATH
            )

            with st.spinner("Running DFA validation, path generation, graph generation and Selenium execution..."):
                result = run_framework(
                    base_url=website_url,
                    model_path=str(TEMP_MODEL_PATH),
                    mapping_path=str(TEMP_MAPPING_PATH),
                    reports_dir=str(REPORTS_DIR)
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
    st.info("Build a DFA visually, upload a mapping JSON, enter the website URL, then click RUN.")

    st.code(
        """
Pipeline:
Visual DFA builder -> generated model JSON -> validate -> DFS paths CSV -> graph image -> Selenium execution -> assertions -> screenshots -> summary report
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
                f"Action: {item.get('failed_action')} | "
                f"{item.get('duration_seconds')}s"
            )

            with st.expander(title, expanded=True):
                st.write("Error:")
                st.code(item.get("error") or "")

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
