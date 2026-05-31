import csv
import io

from engine.graph_builder import build_graph
from engine.validator import validate_dfa


def _safe_name(value):
    return value.lower().replace(" ", "_")


def generate_paths_data(model_path, validate=True):
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

    return data, all_paths


def generate_paths_csv_bytes(model_path, validate=True):
    data, all_paths = generate_paths_data(model_path, validate=validate)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["path_id", "actions"])

    for index, path in enumerate(all_paths, start=1):
        writer.writerow([index, ",".join(path)])

    csv_bytes = output.getvalue().encode("utf-8")
    filename = f"{_safe_name(data['model_name'])}_paths.csv"

    return csv_bytes, filename, all_paths