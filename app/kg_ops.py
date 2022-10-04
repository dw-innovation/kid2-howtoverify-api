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

    print(children_nodes)

    parent_nodes, parent_links = get_parents(clicked_node,root_node)

    print(parent_nodes)

    return {
        'nodes': parent_nodes + children_nodes + [clicked_node, root_node],
        'links': children_links + parent_links
    }


def get_parents(child_node, root_node):
    parents = []
    links = []
    q = prepareQuery(
        """
        SELECT ?parentNode ?childNode where {
          ?childNode dw:parentNode* ?parentNode
        }
        """,
        initNs={"dw": DW}
    )

    for row in g.query(q, initBindings={'childNode': URIRef(child_node['id'])}):

        if row.parentNode == row.childNode:
            continue

        parent_node = node_features(row.parentNode)
        if parent_node["id"] != root_node["id"] and parent_node["type"] == root_node["type"]:
            continue

        parents.append(parent_node)

        links.append({
            'source': parent_node["id"],
            'target': str(row.childNode)
        })

    return parents, links


def get_children(parent_id):
    nodes = []
    links = []
    for subject in g.subjects(predicate=DW['parentNode'], object=URIRef(parent_id)):
        childNode = node_features(subject)
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
