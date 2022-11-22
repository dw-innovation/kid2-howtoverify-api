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


class KIDGraph:
    def __init__(self, click_history=None):

        if click_history:
            self.click_history = click_history
            self.clicked_node = click_history[-1]
            self.root_node = click_history[0]
            self.links = []
            self.sub_graph = nx.DiGraph()

    def construct(self):
        # construct parent nodes from the click history
        self.sub_graph.add_nodes_from(self.click_history)

        for idx in range(len(self.click_history) - 1):
            self.sub_graph.add_edge(self.click_history[idx], self.click_history[idx + 1])

        for node in self.click_history:
            parent_class_node = g.value(URIRef(node), RDFS.subClassOf)
            if parent_class_node:
                for subject in g.subjects(DW.parentNode, parent_class_node):
                    if str(g.value(URIRef(subject), RDF.type)) == "http://dw.com/Task":
                        if not KIDGraph.exists_media_type(subject, self.root_node):
                            continue
                    self.sub_graph.add_edge(str(node), str(subject))
                    self.sub_graph.nodes(str(subject))
            else:
                for subject in g.subjects(DW.parentNode, URIRef(node)):
                    if str(g.value(URIRef(subject), RDF.type)) == "http://dw.com/Task":
                        if not KIDGraph.exists_media_type(subject, self.root_node):
                            continue
                    self.sub_graph.add_edge(str(node), str(subject))
                    self.sub_graph.nodes(str(subject))

        for edge in self.sub_graph.edges:
            source, target = edge
            self.links.append({"source": source, "target": target})

        nodes = []
        for node in self.sub_graph.nodes:
            data = self.get_feats(node)
            if str(node) == self.root_node:
                data["level"] = 0
            for path in nx.all_simple_paths(self.sub_graph, source=self.root_node, target=node):
                data["level"] = len(path) - 1

            nodes.append(data)

        return {
            'nodes': nodes,
            'links': self.links
        }

    def get_feats(self, node_id):
        node_data = {"id": node_id,
                     "type": str(g.value(URIRef(node_id), RDF.type)),
                     "name": str(g.value(URIRef(node_id), SCHEMA.name))
                     }

        if node_id == self.clicked_node:
            node_data['comment'] = str(g.value(URIRef(node_id), RDFS.comment))

            if node_data['type'] in ['http://dw.com/SoftwareApplication', 'http://dw.com/Task']:
                node_data['howTo'] = None

            if node_data['type'] in ['http://dw.com/SoftwareApplication']:
                node_data['remarks'] = None

            for rel, obj in g.predicate_objects(URIRef(node_id)):
                mapped_key = NS_MAPPING[str(rel)]

                if mapped_key not in node_data:
                    node_data[mapped_key] = str(obj)

                elif not node_data[mapped_key]:
                    node_data[mapped_key] = str(obj)

        return node_data

    @staticmethod
    def search(begin_node: str, root_node: str):
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
        if not KIDGraph.check_path(begin_node_id, root_node, str(type)):
            return []
        paths = KIDGraph.search_by_id(begin_node_id, root_node)
        return paths

    @staticmethod
    def search_recursive(begin_node_id, root_node, nx_g):
        if (None, RDFS.subClassOf, URIRef(begin_node_id)) in g:
            for child_class_node in g.subjects(RDFS.subClassOf, URIRef(begin_node_id)):
                if str(g.value(URIRef(child_class_node), RDF.type)) == "http://dw.com/Task":
                    if not KIDGraph.exists_media_type(child_class_node, root_node):
                        continue

                    results = g.query(query_paths(),
                                      initBindings={'endNode': URIRef(root_node), 'beginNode': child_class_node})
                    if len(results) == 0:
                        KIDGraph.search_recursive(begin_node_id=str(child_class_node), root_node=root_node, nx_g=nx_g)

                    nx_g.add_node(str(child_class_node))
                    KIDGraph.search_graph(nx_g, results, root_node)

        parent_node = g.value(subject=URIRef(begin_node_id), predicate=DW.parentNode)
        if parent_node:
            if (None, RDFS.subClassOf, parent_node) in g:
                for child_class_node in g.subjects(RDFS.subClassOf, parent_node):
                    if str(g.value(URIRef(child_class_node), RDF.type)) == "http://dw.com/Task":
                        if not KIDGraph.exists_media_type(child_class_node, root_node):
                            continue

                    nx_g.add_node(str(child_class_node))
                    nx_g.add_edge(str(child_class_node), str(begin_node_id))
                    results = g.query(query_paths(),
                                      initBindings={'endNode': URIRef(root_node), 'beginNode': child_class_node})
                    if len(results) == 0:
                        KIDGraph.search_recursive(begin_node_id=str(child_class_node), root_node=root_node, nx_g=nx_g)

                    KIDGraph.search_graph(nx_g, results, root_node)
            else:
                nx_g.add_node(str(parent_node))
                nx_g.add_edge(str(parent_node), str(begin_node_id))
                for child_node in g.objects(subject=URIRef(parent_node), predicate=DW.parentNode):
                    if str(g.value(URIRef(child_node), RDF.type)) == "http://dw.com/Task":
                        if not KIDGraph.exists_media_type(child_node, root_node):
                            continue
                    nx_g.add_node(str(child_node))
                    nx_g.add_edge(str(child_node), str(parent_node))
                    results = g.query(query_paths(),
                                      initBindings={'endNode': URIRef(root_node), 'beginNode': child_node})
                    if len(results) == 0:
                        KIDGraph.search_recursive(begin_node_id=str(child_node), root_node=root_node, nx_g=nx_g)
        else:
            if begin_node_id == root_node:
                results = g.query(query_paths(),
                                  initBindings={'endNode': URIRef(begin_node_id), 'beginNode': parent_node})
                KIDGraph.search_graph(nx_g, results, root_node)

    @staticmethod
    def search_by_id(begin_node_id, root_node):
        results = g.query(query_paths(),
                          initBindings={'endNode': URIRef(root_node), 'beginNode': URIRef(begin_node_id)})

        nx_g = nx.DiGraph()
        target_node = None
        if not target_node:
            target_node = begin_node_id
            nx_g.add_nodes_from([str(target_node), str(root_node)])

        if len(results) > 0:
            KIDGraph.search_graph(nx_g, results, root_node)
        else:
            KIDGraph.search_recursive(begin_node_id, root_node, nx_g)

        feats = {x: {"id": x, "name": str(g.value(URIRef(x), SCHEMA.name))} for x in nx_g.nodes}

        paths = []
        for path in nx.all_simple_paths(nx_g, target=str(target_node), source=str(root_node)):
            paths.append(list(map(lambda node: feats[node], path)))

        return paths

    @staticmethod
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

    @staticmethod
    def search_graph(nx_g, results, root):
        end_result = None
        for idx, result in enumerate(results):
            mid_start = str(result.midStart)
            mid_end = str(result.midEnd)

            if str(g.value(result.midStart, RDF.type)) == "http://dw.com/Task":

                if not KIDGraph.exists_media_type(result.midStart, root):
                    continue

            if str(g.value(result.midEnd, RDF.type)) == "http://dw.com/Task":
                if not KIDGraph.exists_media_type(result.midEnd, root):
                    continue

            KIDGraph.handle_child_nodes(nx_g, result, root_node=root)

            end_result = mid_end
            nx_g.add_nodes_from([mid_start, mid_end])
            nx_g.add_edge(mid_start, mid_end)

        if end_result:
            nx_g.add_edge(end_result, str(root))

    @staticmethod
    def handle_child_nodes(nx_g, result, root_node):
        if str(g.value(result.childMidStart, RDF.type)) == "http://dw.com/Task":
            parent_class = g.value(result.childMidStart, RDFS.subClassOf)
            if parent_class:
                for parent_node in g.objects(result.childMidStart, DW.parentNode):
                    if str(g.value(URIRef(parent_node), RDF.type)) == "http://dw.com/Task":
                        if not KIDGraph.exists_media_type(parent_node, root_node):
                            continue

                    if str(g.value(result.childMidStart, RDF.type)) == "http://dw.com/Task":
                        if not KIDGraph.exists_media_type(str(result.childMidStart), root_node):
                            continue
                    nx_g.add_edge(str(parent_node), str(result.childMidStart))

                for subject in g.subjects(DW.parentNode, parent_class):
                    if str(g.value(URIRef(subject), RDF.type)) == "http://dw.com/Task":
                        if not KIDGraph.exists_media_type(subject, root_node):
                            continue

                        nx_g.add_node(str(subject))
                        nx_g.add_edge(str(result.childMidStart), str(subject))

                        for _g in g.subjects(DW.parentNode, subject):
                            if str(g.value(URIRef(_g), RDF.type)) == "http://dw.com/Task":
                                if not KIDGraph.exists_media_type(_g, root_node):
                                    continue
                            nx_g.add_edge(str(subject), str(_g))

    @staticmethod
    def exists_media_type(subject, reference_media_type):
        for related_media in g.objects(subject, DW.relatedMediaType):
            if str(related_media) == reference_media_type:
                return True
        return False

    @staticmethod
    def get_index():
        media_objects, index = [], []
        for s in g.subjects(RDF.type, DW.MediaObject):
            media_objects.append(s)

        types = [DW.SoftwareApplication, DW.Task]

        for type in types:
            for node in g.subjects(RDF.type, type):
                id_app = str(node)

                categories = []
                for media_object in media_objects:
                    id_media_object = str(media_object)
                    if KIDGraph.check_path(begin_node_id=id_app, root_node=id_media_object, type=str(type)):
                        categories.append(id_media_object)

                if len(categories) == 0:
                    print(f"Check {node}, it has no related media type")
                    continue

                index.append({'id': id_app,
                              'name': str(g.value(node, SCHEMA.name)),
                              'categories': categories
                              })

        return index
