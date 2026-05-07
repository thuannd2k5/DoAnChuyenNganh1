import json
import networkx as nx


def build_graph(model_path):

    with open(model_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    G = nx.DiGraph()

    for state in data["states"]:

        G.add_node(state)

    for transition in data["transitions"]:

        G.add_edge(
            transition["from"],
            transition["to"],
            action=transition["action"]
        )

    return G, data
