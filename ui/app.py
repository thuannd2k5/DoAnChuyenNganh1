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

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Paths", total)
    col2.metric("Passed", passed)
    col3.metric("Failed", failed)
    col4.metric("Model", result["model_name"])

    tab_summary, tab_paths, tab_graph, tab_mapping, tab_files = st.tabs(
        [
            "Summary",
            "Generated Paths",
            "Graph",
            "Mapping",
            "Files"
        ]
    )

    with tab_summary:
        st.subheader("Execution Summary")

        rows = []

        for item in summary.get("results", []):
            rows.append({
                "path_id": item.get("path_id"),
                "status": item.get("status"),
                "error": item.get("error"),
                "screenshot": item.get("screenshot")
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True
        )

        st.json(summary)

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
