import json
import os

from engine.validator import validate_dfa
from engine.dfs_generator import generate_paths
from engine.visualize_graph import generate_graph

from executor.selenium_executor import (
    SeleniumExecutor
)

from pathlib import Path
from storage.supabase_storage import (
    create_test_run,
    update_test_run,
    upload_file,
    save_file_record
)

def run_framework(
    base_url,
    model_path,
    mapping_path,
    reports_dir="reports"
):

    os.makedirs(reports_dir, exist_ok=True)

    # 1. Validate DFA
    model_data = validate_dfa(model_path)

    # 2. Generate paths
    csv_path = generate_paths(
        model_path,
        output_dir=os.path.join(reports_dir, "csv"),
        validate=False
    )

    # 3. Generate graph
    graph_path = generate_graph(
        model_path,
        output_dir=os.path.join(reports_dir, "graphs")
    )

    # 4. Load mapping
    with open(
        mapping_path,
        "r",
        encoding="utf-8"
    ) as f:

        mapping = json.load(f)

    # 5. Execute Selenium
    executor = SeleniumExecutor(
        mapping,
        base_url,
        csv_path,
        reports_dir=reports_dir,
        model_data=model_data
    )

    summary = executor.run_all_from_csv()
    
    test_run_id = create_test_run(
    model_name=model_data["model_name"],
    base_url=base_url,
    summary=summary
)

    csv_storage_path = f"test-runs/{test_run_id}/csv/{Path(csv_path).name}"
    upload_file(csv_path, csv_storage_path, "text/csv")
    save_file_record(test_run_id, "csv", csv_storage_path)

    graph_storage_path = f"test-runs/{test_run_id}/graphs/{Path(graph_path).name}"
    upload_file(graph_path, graph_storage_path, "image/png")
    save_file_record(test_run_id, "graph", graph_storage_path)

    for result in summary.get("results", []):
        screenshot = result.get("screenshot")

        if screenshot and Path(screenshot).exists():
            screenshot_storage_path = (
                f"test-runs/{test_run_id}/screenshots/{Path(screenshot).name}"
            )
            upload_file(screenshot, screenshot_storage_path, "image/png")
            save_file_record(test_run_id, "screenshot", screenshot_storage_path)
            result["screenshot_storage_path"] = screenshot_storage_path

    update_test_run(test_run_id, {
        "csv_path": csv_storage_path,
        "graph_path": graph_storage_path,
        "summary": summary
    })

    return {
        "test_run_id": test_run_id,
        "model_name": model_data["model_name"],
        "base_url": base_url,
        "csv_path": csv_path,
        "graph_path": graph_path,
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
