import csv
import os

from engine.graph_builder import build_graph
from engine.validator import validate_dfa


def _safe_name(value):

    return value.lower().replace(" ", "_")


def generate_paths(model_path, output_dir="reports", validate=True):

    os.makedirs(output_dir, exist_ok=True)

    if validate:
        data = validate_dfa(model_path)
        graph, _ = build_graph(model_path)
    else:
        graph, data = build_graph(model_path)

    start_state = data["start_state"]
    final_states = set(data["final_states"])
    max_depth = data["max_depth"]
    all_paths = []

    def dfs(current_state, path, visited):

        if len(path) >= max_depth:
            return

        if current_state in final_states:
            all_paths.append(path.copy())
            return

        visited.add(current_state)

        for next_state in graph.successors(current_state):

            if next_state not in visited or next_state in final_states:
                action = graph[current_state][next_state]["action"]
                path.append(action)
                dfs(next_state, path, visited.copy())
                path.pop()

    dfs(start_state, [], set())

    model_name = _safe_name(data["model_name"])
    csv_path = os.path.join(output_dir, f"{model_name}_paths.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)
        writer.writerow(["path_id", "actions"])

        for index, path in enumerate(all_paths, start=1):
            writer.writerow([index, ",".join(path)])

    print(f"Generated {len(all_paths)} test paths")
    print(f"CSV exported to: {csv_path}")

    return csv_path
