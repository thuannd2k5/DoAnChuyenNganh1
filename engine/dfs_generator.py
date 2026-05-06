import csv

from graph_builder import build_graph
from validator import (
    validate_json_schema,
    validate_dfa
)

from config import (
    MODEL_PATH,
    EXPORT_CSV
)

# Build graph
G, data = build_graph(MODEL_PATH)

# Validate
validate_json_schema(data)
validate_dfa(data)

start_state = data["start_state"]
final_states = data["final_states"]
MAX_DEPTH = data["max_depth"]

all_paths = []


def dfs(current_state, path, visited):

    # Prevent infinite loop
    if len(path) >= MAX_DEPTH:
        return

    # Final state
    if current_state in final_states:

        all_paths.append(path.copy())
        return

    visited.add(current_state)

    for next_state in G.successors(current_state):

        if next_state not in visited or next_state in final_states:

            action = G[current_state][next_state]["action"]

            path.append(action)

            dfs(
                next_state,
                path,
                visited.copy()
            )

            path.pop()


# Start DFS
dfs(start_state, [], set())

print("\nGenerated Test Paths:\n")

for path in all_paths:
    print(path)

# Export CSV
model_name = (
    data["model_name"]
    .lower()
    .replace(" ", "_")
)

csv_path = f"reports/{model_name}_paths.csv"

with open(csv_path, "w", newline="") as file:

    writer = csv.writer(file)

    writer.writerow([
        "path_id",
        "actions"
    ])

    for i, path in enumerate(all_paths):

        writer.writerow([
            i + 1,
            ",".join(path)
        ])

print("\nCSV exported successfully!")
print(f"CSV exported to: {csv_path}")