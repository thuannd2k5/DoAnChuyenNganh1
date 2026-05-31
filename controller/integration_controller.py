import json

from engine.validator import validate_dfa, validate_dfa_data
from engine.dfs_generator import generate_paths_csv_bytes
from engine.visualize_graph import generate_graph_png_bytes

from executor.selenium_executor import (
    SeleniumExecutor
)

from storage.supabase_storage import (
    create_test_run,
    update_test_run,
    upload_bytes,
    save_file_record
)

def run_framework(
    base_url,
    model_path=None,
    mapping_path=None,
    reports_dir="reports",
    test_data=None,
    model_data=None,
    mapping_data=None
):

    # 1. Validate DFA
    if model_data is None:
        model_data = validate_dfa(model_path)
    else:
        model_data = validate_dfa_data(model_data)

    # 2. Generate paths as CSV bytes for Supabase Storage
    csv_bytes, csv_filename, all_paths = generate_paths_csv_bytes(
        model_data,
        validate=False
    )
    paths_data = [
        {
            "path_id": str(index),
            "actions": path
        }
        for index, path in enumerate(all_paths, start=1)
    ]

    # 3. Generate graph image bytes for Supabase Storage
    graph_bytes, graph_filename = generate_graph_png_bytes(model_data)

    # 4. Load mapping
    if mapping_data is None:
        with open(
            mapping_path,
            "r",
            encoding="utf-8"
        ) as f:
            mapping = json.load(f)
    else:
        mapping = mapping_data

    # 5. Execute Selenium
    executor = SeleniumExecutor(
        mapping,
        base_url,
        reports_dir=reports_dir,
        model_data=model_data,
        test_data=test_data
    )

    summary = executor.run_all_from_paths(paths_data)

    test_run_id = create_test_run(
        model_name=model_data["model_name"],
        base_url=base_url,
        summary={}
    )

    csv_storage_path = f"test-runs/{test_run_id}/csv/{csv_filename}"
    upload_bytes(csv_bytes, csv_storage_path, "text/csv")
    save_file_record(test_run_id, "csv", csv_storage_path)

    graph_storage_path = f"test-runs/{test_run_id}/graphs/{graph_filename}"
    upload_bytes(graph_bytes, graph_storage_path, "image/png")
    save_file_record(test_run_id, "graph", graph_storage_path)

    for result in summary.get("results", []):
        screenshot_bytes = result.pop("screenshot_bytes", None)
        screenshot_filename = result.pop("screenshot_filename", None)

        if screenshot_bytes and screenshot_filename:
            screenshot_storage_path = (
                f"test-runs/{test_run_id}/screenshots/{screenshot_filename}"
            )
            upload_bytes(screenshot_bytes, screenshot_storage_path, "image/png")
            save_file_record(test_run_id, "screenshot", screenshot_storage_path)
            result["screenshot_storage_path"] = screenshot_storage_path

        for action_log in result.get("action_logs", []):
            screenshot_bytes = action_log.pop("screenshot_bytes", None)
            screenshot_filename = action_log.pop("screenshot_filename", None)

            if screenshot_bytes and screenshot_filename:
                screenshot_storage_path = (
                    f"test-runs/{test_run_id}/screenshots/{screenshot_filename}"
                )
                upload_bytes(
                    screenshot_bytes,
                    screenshot_storage_path,
                    "image/png"
                )
                save_file_record(
                    test_run_id,
                    "screenshot",
                    screenshot_storage_path
                )
                action_log["screenshot_storage_path"] = screenshot_storage_path

    update_test_run(test_run_id, {
        "csv_path": csv_storage_path,
        "graph_path": graph_storage_path,
        "summary": summary
    })

    return {
        "test_run_id": test_run_id,
        "model_name": model_data["model_name"],
        "base_url": base_url,
        "csv_path": csv_storage_path,
        "graph_path": graph_storage_path,
        "csv_storage_path": csv_storage_path,
        "graph_storage_path": graph_storage_path,
        "summary": summary
    }


def prepare_execution(paths_data, mapping_path):

    with open(mapping_path, "r", encoding="utf-8") as file:
        mapping = json.load(file)

    execution_plan = []

    for path in paths_data:
        steps = path.get("steps", path.get("actions", []))
        mapped_steps = [
            mapping[step]
            for step in steps
            if step in mapping
        ]

        execution_plan.append({
            "path_id": path.get("path_id"),
            "original_steps": steps,
            "mapped_steps": mapped_steps
        })

    return execution_plan
