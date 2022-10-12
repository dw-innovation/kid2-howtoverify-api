from typing import List
from rdflib import Graph, Namespace
from rdflib import URIRef
from rdflib.namespace import RDF, RDFS
from rdflib.plugins.sparql import prepareQuery

SCHEMA = Namespace("https://schema.org/")
DW = Namespace("http://dw.com/")

g = Graph()
g.parse("public/workflow.ttl")


def assign_levels(all_nodes, all_links, begin_node_id, level, level_dict={}):
    links = list(filter(lambda link: link['source'] == begin_node_id, all_links))

    if len(links) == 0:
        level_dict[begin_node_id] = level
        # all_nodes.loc[all_nodes.id == begin_node_id, "level"] = level

    for link in links:
        level_dict[begin_node_id] = level
        assign_levels(all_nodes, all_links, begin_node_id=link["target"], level=level + 1, level_dict=level_dict)

    return level_dict


def create_subgraph(click_history: List):
    clicked_node_id = click_history[-1]
    root_node_id = click_history[0]

    root_node = node_features(root_node_id)

    clicked_node = node_features(clicked_node_id)

    parent_nodes, parent_links, children_nodes, children_links = [], [], [], []
    children_nodes, children_links = get_children(clicked_node, root_node)
    if root_node["id"] != clicked_node_id:
        parent_nodes, parent_links = get_parents(clicked_node, root_node, click_history, children_nodes)

    if len(parent_nodes) == 0:
        parent_nodes.append(clicked_node)

    if len(children_nodes) == 0:
        children_nodes = []
        children_links = []

    all_nodes = parent_nodes + children_nodes
    all_links = children_links + parent_links
    all_links = [dict(t) for t in {tuple(d.items()) for d in all_links}]

    del parent_nodes, children_nodes, parent_links, children_links

    level_dict = assign_levels(all_nodes, all_links, begin_node_id=root_node["id"], level=0)

    for node in all_nodes:
        node.update({"level": level_dict[node["id"]]})

    return {
        'nodes': all_nodes,
        'links': all_links
    }


def get_parents(clicked_node, root_node, click_history, children_nodes):
    children_ids = [children_node["id"] for children_node in children_nodes]
    results = g.query(query_parents(),
                      initBindings={'beginNode': URIRef(clicked_node['id']), 'endNode': URIRef(root_node['id'])})
    links = []
    node_ids = set()

    if len(results) == 0:
        sub_class_of_clicked_node = g.value(URIRef(clicked_node["id"]), DW["parentNode"])
        begin_node = None
        for subject in g.subjects(predicate=RDFS.subClassOf, object=sub_class_of_clicked_node):
            if root_node["id"] == str(g.value(subject, DW["relatedMediaType"])):
                begin_node = subject
                pass
        results_subclass = g.query(query_children(), initBindings={'beginNode': sub_class_of_clicked_node,
                                                                   'endNode': URIRef(root_node['id'])})
        for result in results_subclass:
            if str(result) not in children_ids:

                    node_ids.add(str(result.childNode))

                    links.append(
                        {
                            'source': str(begin_node),
                            'target': str(result.childNode)
                        }
                    )
        results = g.query(query_parents(), initBindings={'beginNode': begin_node, 'endNode': URIRef(root_node['id'])})

    for idx, result in enumerate(results):

        if str(result.parentOfParentNode) not in click_history or str(result.parentOfBeginNode) not in click_history:
            continue
        #
        if str(result.parentOfParentRelatedMediaType) != root_node['id'] and result.parentOfParentRelatedMediaType:
            continue

        if str(result.parentOfBeginNodeRelatedMediaType) != root_node[
            'id'] and result.parentOfBeginNodeRelatedMediaType:
            continue

        node_ids.add(str(result.parentOfParentNode))
        node_ids.add(str(result.parentOfBeginNode))

        links.append(
            {
                'source': str(result.parentOfParentNode),
                'target': str(result.parentOfBeginNode)
            }
        )

        if str(result.childNodeMediaType) != root_node[
            'id'] and result.childNodeMediaType:
            continue

        # add child nodes of subParent nodes

        if str(result.childNode) not in node_ids and str(result.childNode) not in children_ids:
            node_ids.add(str(result.childNode))

            links.append(
                {
                    'source': str(result.parentOfParentNode),
                    'target': str(result.childNode)
                }
            )

    if not node_ids:
        return [], []

    nodes = [node_features(node_id) for node_id in node_ids]
    return nodes, links


def query_parents():
    query = '''
    SELECT ?parentOfBeginNode ?parentOfParentNode ?childNode ?parentOfParentRelatedMediaType ?parentOfBeginNodeRelatedMediaType ?childNodeMediaType
    WHERE
    {
        ?beginNode dw:parentNode* ?parentOfBeginNode .
        ?parentOfBeginNode ?y ?parentOfParentNode .
        OPTIONAL {
            ?childNode dw:parentNode ?parentOfParentNode .
        }
        OPTIONAL {
               ?parentOfParentNode a dw:Task.
               ?parentOfParentNode dw:relatedMediaType ?parentOfParentRelatedMediaType .
        }
        OPTIONAL {
               ?parentOfBeginNode a dw:Task.
               ?parentOfBeginNode dw:relatedMediaType ?parentOfBeginNodeRelatedMediaType .
        }
        
        OPTIONAL {
               ?childNode a dw:Task.
               ?childNode dw:relatedMediaType ?childNodeMediaType .
        }
        
        FILTER(?y = dw:parentNode)
        ?parentOfParentNode dw:parentNode* ?endNode .
    }
    '''
    q = prepareQuery(query,
                     initNs={"dw": DW},
                     )
    return q


def get_children(parent_node, root_node):
    q = query_children()

    results = g.query(q, initBindings={'beginNode': URIRef(parent_node['id']), 'endNode': URIRef(root_node['id'])})

    if len(results) == 0:
        query = '''
         SELECT ?childNode ?relatedMediaType ?parentClassNode ?beginNode
         WHERE
         {  
            ?beginNode rdfs:subClassOf ?parentClassNode .
            ?childNode dw:parentNode ?parentClassNode .
            
            OPTIONAL{
             ?parentClassNode dw:parentNode* ?parentOfBeginNode .
             ?parentOfBeginNode ?y ?parentOfParentNode .
             ?parentOfParentNode dw:parentNode* ?endNode .
             }

            OPTIONAL {
               ?parentClassNode a dw:Task .
               ?parentClassNode dw:relatedMediaType ?relatedMediaType .
            }

         }
         '''
        q = prepareQuery(query,
                         initNs={"dw": DW, "rdfs": RDFS},
                         )

        results = g.query(q, initBindings={'beginNode': URIRef(parent_node['id']), 'endNode': URIRef(root_node['id'])})

    links = None
    node_ids = None
    for idx, result in enumerate(results):
        if idx == 0:
            links = []
            node_ids = set()

        if str(result.relatedMediaType) != root_node['id'] and result.relatedMediaType:
            continue

        node_ids.add(str(result.childNode))

        links.append(
            {
                'source': parent_node['id'],
                'target': str(result.childNode)
            }
        )

    if not node_ids:
        return [], []

    nodes = [node_features(node_id) for node_id in node_ids]

    return nodes, links


def query_children():
    query = '''
     SELECT ?childNode ?relatedMediaType ?beginNode
     WHERE
     {
        ?childNode dw:parentNode ?beginNode
        OPTIONAL{
         ?beginNode dw:parentNode* ?parentOfBeginNode .
         ?parentOfBeginNode ?y ?parentOfParentNode .
         ?parentOfParentNode dw:parentNode* ?endNode .
         }
    
        OPTIONAL {
           ?childNode a dw:Task .
           ?childNode dw:relatedMediaType ?relatedMediaType .
        }
        
     }
     '''
    q = prepareQuery(query,
                     initNs={"dw": DW, "rdfs": RDFS},
                     )
    return q


def node_features(node_id):
    return {
        'id': str(node_id),
        'name': str(g.value(URIRef(node_id), SCHEMA.name)),
        'type': str(g.value(URIRef(node_id), RDF.type))
    }
