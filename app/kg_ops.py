from typing import List

from rdflib import Graph, Namespace
from rdflib import URIRef
from rdflib.namespace import RDFS, RDF
from rdflib.plugins.sparql import prepareQuery

SCHEMA = Namespace("https://schema.org/")
DW = Namespace("http://dw.com/")

g = Graph()
g.parse("public/workflow.ttl")


def create_subgraph(click_history: List):
    clicked_node_id = click_history[-1]
    root_node_id = click_history[0]

    root_node = node_features(root_node_id)

    clicked_node = node_features(clicked_node_id)

    children_nodes, children_links = get_children(clicked_node, root_node)

    parent_nodes, parent_links = get_parents(clicked_node, root_node, click_history)

    if len(parent_nodes) == 0:
        parent_nodes.append(clicked_node)

    if len(children_nodes) == 0:
        children_nodes = []
        children_links = []

    return {
        'nodes': parent_nodes + children_nodes,
        'links': children_links + parent_links
    }


def get_parents(clicked_node, root_node, click_history):
    query = '''
    SELECT ?parentOfBeginNode ?parentOfParentNode
    WHERE
    {
        ?beginNode dw:parentNode* ?parentOfBeginNode .
        ?parentOfBeginNode ?y ?parentOfParentNode .
        FILTER(?y = dw:parentNode)
        ?parentOfParentNode dw:parentNode* ?endNode .
    }
    '''
    q = prepareQuery(query,
                     initNs={"dw": DW},
                     )

    results = g.query(q, initBindings={'beginNode': URIRef(clicked_node['id']), 'endNode': URIRef(root_node['id'])})

    links = None
    node_ids = None
    for idx, result in enumerate(results):
        if idx == 0:
            links = []
            node_ids = set()

        if str(result.parentOfParentNode) not in click_history or str(result.parentOfBeginNode) not in click_history:
            print('The node is not in click history.')
            continue

        node_ids.add(str(result.parentOfParentNode))
        node_ids.add(str(result.parentOfBeginNode))

        links.append(
            {
                'source': str(result.parentOfParentNode),
                'target': str(result.parentOfBeginNode)
            }
        )

        # TODO: add to candidate_paths

    # TODO: select best candidate similar to user clicked

    if not node_ids:
        return [], []

    nodes = [node_features(node_id) for node_id in node_ids]
    return nodes, links


def get_children(parent_node, root_node):
    query = '''
     SELECT ?childNode
     WHERE
     {
         ?childNode dw:parentNode ?beginNode .
         OPTIONAL{
         ?beginNode dw:parentNode* ?parentOfBeginNode .
         ?parentOfBeginNode ?y ?parentOfParentNode .
         ?parentOfParentNode dw:parentNode* ?endNode .
         }
     }
     '''
    q = prepareQuery(query,
                     initNs={"dw": DW},
                     )

    results = g.query(q, initBindings={'beginNode': URIRef(parent_node['id']), 'endNode': URIRef(root_node['id'])})

    links = None
    node_ids = None
    for idx, result in enumerate(results):
        if idx == 0:
            links = []
            node_ids = set()

        node_ids.add(str(result.childNode))

        links.append(
            {
                'source': str(result.childNode),
                'target': parent_node['id']
            }
        )

        # TODO: add to candidate_paths

    # TODO: select best candidate similar to user clicked

    if not node_ids:
        return [], []

    nodes = [node_features(node_id) for node_id in node_ids]
    return nodes, links


def node_features(node_id):
    return {
        'id': str(node_id),
        'name': str(g.value(URIRef(node_id), SCHEMA.name)),
        'type': str(g.value(URIRef(node_id), RDF.type))
    }
