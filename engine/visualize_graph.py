import matplotlib.pyplot as plt
import networkx as nx

from graph_builder import build_graph

from config import (
    MODEL_PATH
)

# Build graph
G, data = build_graph(MODEL_PATH)

# Node colors
node_colors = []

for node in G.nodes():

    if node == data["start_state"]:
        node_colors.append("lightgreen")

    elif node in data["final_states"]:
        node_colors.append("salmon")

    else:
        node_colors.append("lightblue")

# Better layout
pos = nx.spring_layout(
    G,
    k=2,
    seed=42
)

# Edge labels
edge_labels = nx.get_edge_attributes(
    G,
    "action"
)

# Figure
plt.figure(figsize=(16, 10))

# Draw graph
nx.draw(
    G,
    pos,
    with_labels=True,
    node_size=7000,
    node_color=node_colors,
    font_size=12,
    arrowsize=20
)

# Draw edge labels
nx.draw_networkx_edge_labels(
    G,
    pos,
    edge_labels=edge_labels,
    font_size=10
)

# Title
plt.title(
    data["model_name"],
    fontsize=18
)

plt.tight_layout()

# Save image
graph_name = (
    data["model_name"]
    .lower()
    .replace(" ", "_")
)

output_path = f"reports/screenshots/{graph_name}.png"

plt.savefig(output_path)

print(f"Graph saved to: {output_path}")

# Show graph
plt.show()