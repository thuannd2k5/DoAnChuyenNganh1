import io
import matplotlib.pyplot as plt
import networkx as nx

from engine.graph_builder import build_graph


def _safe_name(value):
    return value.lower().replace(" ", "_")


def generate_graph_png_bytes(model_path):
    graph, data = build_graph(model_path)

    node_colors = []

    for node in graph.nodes():
        if node == data["start_state"]:
            node_colors.append("lightgreen")
        elif node in data["final_states"]:
            node_colors.append("salmon")
        else:
            node_colors.append("lightblue")

    pos = nx.spring_layout(graph, k=2, seed=42)
    edge_labels = nx.get_edge_attributes(graph, "action")

    plt.figure(figsize=(16, 10))

    nx.draw(
        graph,
        pos,
        with_labels=True,
        node_size=7000,
        node_color=node_colors,
        font_size=12,
        arrowsize=20
    )

    nx.draw_networkx_edge_labels(
        graph,
        pos,
        edge_labels=edge_labels,
        font_size=10
    )

    plt.title(data["model_name"], fontsize=18)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()

    buffer.seek(0)

    filename = f"{_safe_name(data['model_name'])}.png"

    return buffer.getvalue(), filename