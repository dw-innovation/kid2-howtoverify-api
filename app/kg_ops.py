from rdflib import Graph, Namespace
from typing import List
from rdflib.namespace import RDF
from rdflib.plugins.sparql import prepareQuery
from rdflib import URIRef

SCHEMA = Namespace("https://schema.org/")
DW = Namespace("http://dw.com/")

g = Graph()
g.parse("public/workflow.ttl")


def create_subgraph(click_history: List):
    clicked_node_id = click_history[-1]
    root_node_id = click_history[0]

    root_node = node_features(root_node_id)
    clicked_node = node_features(clicked_node_id)

    children_nodes, children_links = get_children(clicked_node_id)

    parent_nodes, parent_links = get_parents(clicked_node, root_node)

    if len(children_nodes) == 0:
        children_nodes = []

    return {
        'nodes': parent_nodes + children_nodes + [clicked_node],
        'links': children_links + parent_links
    }


def get_parents(child_node, root_node, parents={}, links={}):
    parent_node = None

    if child_node["id"] == root_node["id"]:
        return [], []

    for parent in g.objects(predicate=DW['parentNode'], subject=URIRef(child_node["id"])):

        parent_node = node_features(parent)

        if child_node["type"] == root_node["type"]:
            print(child_node)
            continue

        if parent_node["id"] != root_node["id"] and parent_node["type"] == root_node["type"]:
            continue

        if parent_node["id"] not in parents:
            parents[parent_node["id"]] = parent_node

        if f'{parent_node["name"]}_{child_node["name"]}' not in links:
            links[f'{parent_node["name"]}_{child_node["name"]}'] = {
                'source': parent_node["id"],
                'target': str(child_node["id"])
            }

    if not parent_node:
        return list(parents.values()), list(links.values())

    return get_parents(child_node=parent_node, root_node=root_node, parents=parents, links=links)


def get_children(parent_id):
    nodes = []
    links = []
    for subject in g.subjects(predicate=DW['parentNode'], object=URIRef(parent_id)):
        childNode = node_features(subject)

        if parent_id == childNode["id"]:
            continue

        nodes.append(childNode)
        links.append(
            {
                'source': parent_id,
                'target': childNode['id']
            }
        )
    return nodes, links


def node_features(node_id):
    return {
        'id': str(node_id),
        'name': str(g.value(URIRef(node_id), SCHEMA.name)),
        'type': str(g.value(URIRef(node_id), RDF.type))
    }
