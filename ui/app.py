import json
import importlib
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

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
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return data


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


st.set_page_config(
    page_title="DFA Web Testing Tool",
    layout="wide"
)

st.title("DFA Web Testing Tool")
st.caption("Model-Based Testing with DFA, DFS and Selenium")

st.sidebar.header("Test Configuration")

website_url = st.sidebar.text_input(
    "Website URL",
    value="https://www.saucedemo.com/"
)

model_file = st.sidebar.file_uploader(
    "DFA model JSON",
    type=["json"]
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

if run_button:

    if not website_url:
        st.error("Website URL is required.")

    elif not model_file:
        st.error("DFA model JSON is required.")

    elif not mapping_file:
        st.error("Mapping JSON is required.")

    else:
        REPORTS_DIR.mkdir(exist_ok=True)

        try:
            model_data = save_uploaded_json(
                model_file,
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
                "model": model_data,
                "mapping": mapping_data
            }

            st.success("Test run completed.")

        except Exception as error:
            st.session_state.result = None
            st.error(str(error))


result_state = st.session_state.result

if not result_state:
    st.info("Select a website URL, upload a DFA model JSON and mapping JSON, then click RUN.")

    st.code(
        """
Pipeline:
DFA model -> validate -> DFS paths CSV -> graph image -> Selenium execution -> assertions -> screenshots -> summary report
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
