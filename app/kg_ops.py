from rdflib import Graph, Namespace
from rdflib import URIRef, Literal
from rdflib.namespace import RDF, RDFS, DCTERMS
from rdflib.plugins.sparql import prepareQuery
import networkx as nx

SCHEMA = Namespace("https://schema.org/")
DW = Namespace("http://dw.com/")

NS_MAPPING = {
    str(RDF.type): "type",
    str(SCHEMA.url): "url",
    str(RDFS.subClassOf): "subClass",
    str(SCHEMA.applicationUrl): "applicationUrl",
    str(SCHEMA.aboutUrl): "aboutUrl",
    str(SCHEMA.publisher): "publisher",
    str(SCHEMA.usageInfo): "usageInfo",
    str(DCTERMS.subject): "subject",
    str(DCTERMS.relation): "relation",
    str(DCTERMS.hasPart): "hasPart",
    str(RDFS.comment): "comment",
    str(SCHEMA.name): "name",
    str(SCHEMA.isPartOf): "isPartOf",
    str(DW.parentNode): "parentNode",
    str(DW.relatedMediaType): "relatedMediaType",
    str(DW.remarks): "remarks",
    str(DW.howTo): "howTo"

}

SCHEMA = Namespace("https://schema.org/")
DW = Namespace("http://dw.com/")

g = Graph()
g.parse("public/workflow.ttl")

media_objects = []
for s in g.subjects(RDF.type, DW.MediaObject):
    media_objects.append(s)


def query_paths():
    query = '''
        SELECT DISTINCT ?midEnd ?midStart ?beginNode ?endNode ?childMidStart
        WHERE
        {   
            ?beginNode dw:parentNode* ?midEnd .
            ?midEnd dw:parentNode ?midStart .
            ?midStart dw:parentNode* ?endNode .
            OPTIONAL {
                ?childMidStart dw:parentNode ?midStart .
            }
        }
        '''
    q = prepareQuery(query,
                     initNs={"dw": DW, "schema": SCHEMA},
                     )
    return q


def validate_click_history(click_history):
    for node in click_history:
        node_type = g.value(URIRef(node), RDF.type)
        if not node_type:
            return False

    return True


def construct(click_history):
    clicked_node = click_history[-1]
    root_node = click_history[0]
    sub_graph = nx.DiGraph()
    # construct parent nodes from the click history
    sub_graph.add_nodes_from(click_history)

    for idx in range(len(click_history) - 1):
        sub_graph.add_edge(click_history[idx], click_history[idx + 1])

    links = []

    for node in click_history:
        parent_class_node = g.value(URIRef(node), RDFS.subClassOf)
        if parent_class_node:
            for subject in g.subjects(DW.parentNode, parent_class_node):
                if str(g.value(URIRef(subject), RDF.type)) == "http://dw.com/Task":
                    if not exists_media_type(subject, root_node):
                        continue
                sub_graph.add_edge(str(node), str(subject))
                sub_graph.nodes(str(subject))
        else:
            for subject in g.subjects(DW.parentNode, URIRef(node)):
                if str(g.value(URIRef(subject), RDF.type)) == "http://dw.com/Task":
                    if not exists_media_type(subject, root_node):
                        continue
                sub_graph.add_edge(str(node), str(subject))
                sub_graph.nodes(str(subject))

    for edge in sub_graph.edges:
        source, target = edge
        links.append({"source": source, "target": target})

    nodes = []
    for node in sub_graph.nodes:
        data = get_feats(node, clicked_node)
        if str(node) == root_node:
            data["level"] = 0
        for path in nx.all_simple_paths(sub_graph, source=root_node, target=node):
            data["level"] = len(path) - 1

        nodes.append(data)

    return {
        'nodes': nodes,
        'links': links
    }


def get_feats(node_id, clicked_node):
    node_data = {"id": node_id,
                 "type": str(g.value(URIRef(node_id), RDF.type)),
                 "name": str(g.value(URIRef(node_id), SCHEMA.name))
                 }

    if node_id == clicked_node:
        node_data['comment'] = str(g.value(URIRef(node_id), RDFS.comment))

        if node_data['type'] == ['http://dw.com/SoftwareApplication']:
            node_data['howTo'] = []

        node_data['remarks'] = []

        for rel, obj in g.predicate_objects(URIRef(node_id)):
            mapped_key = NS_MAPPING[str(rel)]
            if mapped_key in ["remarks", "howTo"]:
                node_data[mapped_key].append(str(obj))
            else:

                if mapped_key not in node_data:
                    node_data[mapped_key] = str(obj)

                elif not node_data[mapped_key]:
                    node_data[mapped_key] = str(obj)
    return node_data


def search_with_category(begin_node: str, root_node: str):
    begin_node_id = None
    for candidate_node in g.subjects(SCHEMA.name, Literal(begin_node)):
        if (None, RDFS.subClassOf, candidate_node) in g:
            continue
        type = str(g.value(candidate_node, RDF.type))
        if type == "http://dw.com/Task":
            for related_media_type in g.objects(candidate_node, DW.relatedMediaType):
                related_media_type = str(related_media_type)
                if related_media_type == root_node:
                    begin_node_id = str(candidate_node)
                    break
        else:
            begin_node_id = str(candidate_node)

    if not begin_node_id:
        return []
    type = g.value(URIRef(begin_node_id), RDF.type)
    if not check_path(begin_node_id, root_node, str(type)):
        return []
    paths = search_by_id(begin_node_id, root_node)
    return paths


def search(begin_node: str):
    results = []
    for media_object in media_objects:
        media_object_name = str(g.value(media_object, SCHEMA.name))
        media_object = str(media_object)
        results.append(
            {
                "category": {
                    "id": media_object,
                    "name": media_object_name
                },
                "results": search_with_category(begin_node, media_object)
            }
        )

    return results


def search_recursive(begin_node_id, root_node, nx_g):
    if (None, RDFS.subClassOf, URIRef(begin_node_id)) in g:
        for child_class_node in g.subjects(RDFS.subClassOf, URIRef(begin_node_id)):
            if str(g.value(URIRef(child_class_node), RDF.type)) == "http://dw.com/Task":
                if not exists_media_type(child_class_node, root_node):
                    continue

                results = g.query(query_paths(),
                                  initBindings={'endNode': URIRef(root_node), 'beginNode': child_class_node})
                if len(results) == 0:
                    search_recursive(begin_node_id=str(child_class_node), root_node=root_node, nx_g=nx_g)

                nx_g.add_node(str(child_class_node))
                search_graph(nx_g, results, root_node)

    parent_node = g.value(subject=URIRef(begin_node_id), predicate=DW.parentNode)
    if parent_node:
        if (None, RDFS.subClassOf, parent_node) in g:
            for child_class_node in g.subjects(RDFS.subClassOf, parent_node):
                if str(g.value(URIRef(child_class_node), RDF.type)) == "http://dw.com/Task":
                    if not exists_media_type(child_class_node, root_node):
                        continue

                nx_g.add_node(str(child_class_node))
                nx_g.add_edge(str(child_class_node), str(begin_node_id))
                results = g.query(query_paths(),
                                  initBindings={'endNode': URIRef(root_node), 'beginNode': child_class_node})
                if len(results) == 0:
                    search_recursive(begin_node_id=str(child_class_node), root_node=root_node, nx_g=nx_g)

                search_graph(nx_g, results, root_node)
        else:
            nx_g.add_node(str(parent_node))
            nx_g.add_edge(str(parent_node), str(begin_node_id))
            for child_node in g.objects(subject=URIRef(parent_node), predicate=DW.parentNode):
                if str(g.value(URIRef(child_node), RDF.type)) == "http://dw.com/Task":
                    if not exists_media_type(child_node, root_node):
                        continue
                nx_g.add_node(str(child_node))
                nx_g.add_edge(str(child_node), str(parent_node))
                results = g.query(query_paths(),
                                  initBindings={'endNode': URIRef(root_node), 'beginNode': child_node})
                if len(results) == 0:
                    search_recursive(begin_node_id=str(child_node), root_node=root_node, nx_g=nx_g)
    else:
        if begin_node_id == root_node:
            results = g.query(query_paths(),
                              initBindings={'endNode': URIRef(begin_node_id), 'beginNode': parent_node})
            search_graph(nx_g, results, root_node)


def search_by_id(begin_node_id, root_node):
    results = g.query(query_paths(),
                      initBindings={'endNode': URIRef(root_node), 'beginNode': URIRef(begin_node_id)})

    nx_g = nx.DiGraph()
    target_node = None
    if not target_node:
        target_node = begin_node_id
        nx_g.add_nodes_from([str(target_node), str(root_node)])

    if len(results) > 0:
        search_graph(nx_g, results, root_node)
    else:
        search_recursive(begin_node_id, root_node, nx_g)

    feats = {x: {"id": x, "name": str(g.value(URIRef(x), SCHEMA.name))} for x in nx_g.nodes}

    paths = []
    for path in nx.all_simple_paths(nx_g, target=str(target_node), source=str(root_node)):
        paths.append(list(map(lambda node: feats[node], path)))

    return paths


def check_path(begin_node_id, root_node, type):
    if type == "http://dw.com/SoftwareApplication":
        for parent_node in g.objects(URIRef(begin_node_id), DW.parentNode):

            media_types = g.objects(parent_node, DW.relatedMediaType)

            for media_type in media_types:
                if str(media_type) == str(root_node):
                    return True
    elif type == "http://dw.com/Task":
        if (None, RDFS.subClassOf, URIRef(begin_node_id)) in g:
            return False
        media_types = g.objects(URIRef(begin_node_id), DW.relatedMediaType)

        for media_type in media_types:
            if str(media_type) == str(root_node):
                return True

    return False


def search_graph(nx_g, results, root):
    end_result = None
    for idx, result in enumerate(results):
        mid_start = str(result.midStart)
        mid_end = str(result.midEnd)

        if str(g.value(result.midStart, RDF.type)) == "http://dw.com/Task":

            if not exists_media_type(result.midStart, root):
                continue

        if str(g.value(result.midEnd, RDF.type)) == "http://dw.com/Task":
            if not exists_media_type(result.midEnd, root):
                continue

        handle_child_nodes(nx_g, result, root_node=root)

        end_result = mid_end
        nx_g.add_nodes_from([mid_start, mid_end])
        nx_g.add_edge(mid_start, mid_end)

    if end_result:
        nx_g.add_edge(end_result, str(root))


def handle_child_nodes(nx_g, result, root_node):
    if str(g.value(result.childMidStart, RDF.type)) == "http://dw.com/Task":
        parent_class = g.value(result.childMidStart, RDFS.subClassOf)
        if parent_class:
            for parent_node in g.objects(result.childMidStart, DW.parentNode):
                if str(g.value(URIRef(parent_node), RDF.type)) == "http://dw.com/Task":
                    if not exists_media_type(parent_node, root_node):
                        continue

                if str(g.value(result.childMidStart, RDF.type)) == "http://dw.com/Task":
                    if not exists_media_type(str(result.childMidStart), root_node):
                        continue
                nx_g.add_edge(str(parent_node), str(result.childMidStart))

            for subject in g.subjects(DW.parentNode, parent_class):
                if str(g.value(URIRef(subject), RDF.type)) == "http://dw.com/Task":
                    if not exists_media_type(subject, root_node):
                        continue

                    nx_g.add_node(str(subject))
                    nx_g.add_edge(str(result.childMidStart), str(subject))

                    for _g in g.subjects(DW.parentNode, subject):
                        if str(g.value(URIRef(_g), RDF.type)) == "http://dw.com/Task":
                            if not exists_media_type(_g, root_node):
                                continue
                        nx_g.add_edge(str(subject), str(_g))


def exists_media_type(subject, reference_media_type):
    for related_media in g.objects(subject, DW.relatedMediaType):
        if str(related_media) == reference_media_type:
            return True
    return False


def get_index():
    node_ids = set()

    types = [DW.SoftwareApplication, DW.Task]

    for type in types:
        for node in g.subjects(RDF.type, type):
            node_ids.add(str(g.value(node, SCHEMA.name)))

    index = list(map(lambda x: {"name": x}, node_ids))
    return index
