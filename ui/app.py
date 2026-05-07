import streamlit as st
import json
import sys
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from controller.integration_controller import prepare_execution


st.set_page_config(
    page_title="DFA Web Testing Tool",
    layout="wide"
)

st.markdown(
    """
    <style>
    .main-title {
        font-size: 42px;
        font-weight: 800;
        color: #1f2937;
        margin-bottom: 4px;
    }

    .sub-title {
        font-size: 17px;
        color: #6b7280;
        margin-bottom: 28px;
    }

    .section-title {
        font-size: 24px;
        font-weight: 700;
        color: #111827;
        margin-top: 16px;
        margin-bottom: 10px;
    }

    .info-box {
        padding: 16px;
        border-radius: 12px;
        background-color: #f3f4f6;
        border: 1px solid #e5e7eb;
        margin-bottom: 16px;
    }

    .warning-box {
        padding: 16px;
        border-radius: 12px;
        background-color: #fff7ed;
        border: 1px solid #fed7aa;
        color: #9a3412;
        margin-bottom: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    '<div class="main-title">DFA Web Testing Tool</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">Automatic test case generation and execution based on DFA and Selenium</div>',
    unsafe_allow_html=True
)

st.sidebar.header("Cấu hình kiểm thử")

website_url = st.sidebar.text_input(
    "Website URL cần test",
    value="https://www.saucedemo.com/"
)

mapping_file = st.sidebar.file_uploader(
    "Upload mapping.json",
    type=["json"]
)

paths_file = st.sidebar.file_uploader(
    "Upload paths.json",
    type=["json"]
)

run_button = st.sidebar.button(
    "Generate Execution Plan",
    use_container_width=True
)

st.sidebar.markdown("---")
st.sidebar.write(
    "Phiên bản hiện tại dành cho TV3 chạy độc lập: đọc paths.json, đọc mapping.json, tạo execution_plan.json và chờ TV2 tích hợp Selenium Executor."
)

if "execution_plan" not in st.session_state:
    st.session_state.execution_plan = None

if "mapping_data" not in st.session_state:
    st.session_state.mapping_data = None

if "paths_data" not in st.session_state:
    st.session_state.paths_data = None

if "website_url" not in st.session_state:
    st.session_state.website_url = None


if run_button:
    if not mapping_file or not paths_file:
        st.error("Bạn cần upload đủ mapping.json và paths.json")

    elif not website_url:
        st.error("Bạn cần nhập Website URL")

    else:
        reports_dir = ROOT_DIR / "reports"
        reports_dir.mkdir(exist_ok=True)

        mapping_data = json.load(mapping_file)
        paths_data = json.load(paths_file)

        st.session_state.mapping_data = mapping_data
        st.session_state.paths_data = paths_data
        st.session_state.website_url = website_url

        temp_mapping_path = reports_dir / "temp_mapping.json"

        temp_mapping_path.write_text(
            json.dumps(mapping_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        with st.spinner("Đang tạo execution plan"):
            execution_plan = prepare_execution(paths_data, temp_mapping_path)

        st.session_state.execution_plan = execution_plan

        execution_plan_path = reports_dir / "execution_plan.json"

        execution_plan_path.write_text(
            json.dumps(execution_plan, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        st.success("Tạo execution_plan.json thành công")


execution_plan = st.session_state.execution_plan
mapping_data = st.session_state.mapping_data
paths_data = st.session_state.paths_data
current_url = st.session_state.website_url


if execution_plan:
    total_paths = len(execution_plan)
    total_steps = sum(len(item.get("mapped_steps", [])) for item in execution_plan)
    total_mapping_actions = len(mapping_data) if mapping_data else 0
    avg_steps = round(total_steps / total_paths, 2) if total_paths else 0

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Test Paths", total_paths)
    col2.metric("Total Steps", total_steps)
    col3.metric("Mapping Actions", total_mapping_actions)
    col4.metric("Avg Steps / Path", avg_steps)

    st.markdown("---")

    st.markdown(
        """
        <div class="warning-box">
        Selenium Executor chưa được tích hợp trong phiên bản TV3 độc lập.
        Hệ thống hiện chỉ tạo execution_plan.json. Phần chạy browser, PASS/FAIL,
        screenshot và report thực thi sẽ được bổ sung khi ghép module của TV2.
        </div>
        """,
        unsafe_allow_html=True
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Overview",
            "Execution Plan",
            "Mapping",
            "Generated Paths",
            "Export Files"
        ]
    )

    with tab1:
        st.markdown(
            '<div class="section-title">Overview</div>',
            unsafe_allow_html=True
        )

        st.write("Website URL:")
        st.code(current_url)

        overview_rows = []

        for item in execution_plan:
            overview_rows.append({
                "path_id": item.get("path_id"),
                "original_steps": " -> ".join(item.get("original_steps", [])),
                "number_of_steps": len(item.get("mapped_steps", [])),
                "status": "Waiting for TV2 Selenium Executor"
            })

        st.dataframe(
            pd.DataFrame(overview_rows),
            use_container_width=True
        )

    with tab2:
        st.markdown(
            '<div class="section-title">Execution Plan</div>',
            unsafe_allow_html=True
        )

        st.write(
            "Execution plan là dữ liệu trung gian đã được map từ path DFA sang các lệnh mà Selenium Executor có thể thực thi."
        )

        for item in execution_plan:
            path_id = item.get("path_id")
            original_steps = item.get("original_steps", [])
            mapped_steps = item.get("mapped_steps", [])

            with st.expander(f"Path {path_id}"):
                st.write("Original Steps:")
                st.code(" -> ".join(original_steps))

                st.write("Mapped Steps:")
                st.json(mapped_steps)

        st.download_button(
            "Download execution_plan.json",
            data=json.dumps(execution_plan, indent=2, ensure_ascii=False),
            file_name="execution_plan.json",
            mime="application/json"
        )

    with tab3:
        st.markdown(
            '<div class="section-title">Mapping Data</div>',
            unsafe_allow_html=True
        )

        st.write(
            "mapping.json dùng để dịch action trong DFA thành thao tác thật trên website."
        )

        mapping_table = []

        for action_name, action_data in mapping_data.items():
            mapping_table.append({
                "action_name": action_name,
                "type": action_data.get("type", ""),
                "selector_type": action_data.get("selector_type", ""),
                "selector": action_data.get("selector", ""),
                "value": action_data.get("value", ""),
                "expected": action_data.get("expected", ""),
                "path": action_data.get("path", "")
            })

        st.dataframe(
            pd.DataFrame(mapping_table),
            use_container_width=True
        )

        with st.expander("Raw mapping.json"):
            st.json(mapping_data)

    with tab4:
        st.markdown(
            '<div class="section-title">Generated Test Paths</div>',
            unsafe_allow_html=True
        )

        st.write(
            "Đây là danh sách test path được sinh từ DFA hoặc dữ liệu paths.json dùng để kiểm thử module TV3."
        )

        path_table = []

        for path in paths_data:
            path_table.append({
                "path_id": path.get("path_id"),
                "steps": " -> ".join(path.get("steps", [])),
                "number_of_steps": len(path.get("steps", []))
            })

        path_df = pd.DataFrame(path_table)

        st.dataframe(
            path_df,
            use_container_width=True
        )

        csv_data = path_df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "Download generated_testcases.csv",
            data=csv_data,
            file_name="generated_testcases.csv",
            mime="text/csv"
        )

        with st.expander("Raw paths.json"):
            st.json(paths_data)

    with tab5:
        st.markdown(
            '<div class="section-title">Export Files</div>',
            unsafe_allow_html=True
        )

        st.write("Các file mà module TV3 có thể xuất ra độc lập:")

        export_summary = [
            {
                "file": "reports/execution_plan.json",
                "description": "Dữ liệu trung gian để TV2 Selenium Executor chạy test"
            },
            {
                "file": "generated_testcases.csv",
                "description": "Danh sách test case sinh từ DFA, phục vụ báo cáo và kiểm tra thủ công"
            },
            {
                "file": "reports/temp_mapping.json",
                "description": "Bản mapping được upload và lưu tạm để xử lý"
            }
        ]

        st.dataframe(
            pd.DataFrame(export_summary),
            use_container_width=True
        )

        st.write("Raw execution_plan.json:")
        st.json(execution_plan)

        st.download_button(
            "Download raw execution_plan.json",
            data=json.dumps(execution_plan, indent=2, ensure_ascii=False),
            file_name="execution_plan.json",
            mime="application/json"
        )

else:
    st.markdown(
        '<div class="section-title">Hướng dẫn sử dụng</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="info-box">
        <p>1. Nhập URL website cần test.</p>
        <p>2. Upload file mapping.json.</p>
        <p>3. Upload file paths.json.</p>
        <p>4. Bấm Generate Execution Plan.</p>
        <p>5. Hệ thống tạo execution_plan.json và chờ tích hợp Selenium Executor từ TV2.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-title">Pipeline hệ thống</div>',
        unsafe_allow_html=True
    )

    st.code(
        """
DFA Model
   |
   v
DFS Generator
   |
   v
Generated Test Paths
   |
   v
Mapping Layer
   |
   v
Execution Plan
   |
   v
Waiting for TV2 Selenium Executor
        """
    )