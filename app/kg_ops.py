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


def query_parents():
    query = '''
        SELECT DISTINCT ?parentOfBeginNode ?parentOfParentNode ?childNode ?parentOfParentRelatedMediaType ?parentOfBeginNodeRelatedMediaType ?childNodeMediaType
        WHERE
        {
            ?beginNode dw:parentNode* ?parentOfBeginNode .
            ?parentOfBeginNode dw:parentNode ?parentOfParentNode .
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

            ?parentOfParentNode dw:parentNode* ?endNode .
        }
        '''
    q = prepareQuery(query,
                     initNs={"dw": DW},
                     )
    return q


def query_paths():
    query = '''
        SELECT DISTINCT ?midEnd ?midStart ?beginNode ?endNode
        WHERE
        {   
            ?beginNode dw:parentNode* ?midEnd .
            ?midEnd dw:parentNode ?midStart .
            ?midStart dw:parentNode* ?endNode .
        }
        '''
    q = prepareQuery(query,
                     initNs={"dw": DW, "schema": SCHEMA},
                     )
    return q


def query_children():
    query = '''
         SELECT DISTINCT ?childNode ?relatedMediaType
         WHERE
         {
            ?childNode dw:parentNode ?beginNode
            OPTIONAL{
             ?beginNode dw:parentNode* ?parentOfBeginNode .
             ?parentOfBeginNode ?y ?parentOfParentNode .
             ?parentOfParentNode dw:parentNode* ?endNode .
             }

            OPTIONAL {
               ?childNode a dw:Task.
               ?childNode dw:relatedMediaType ?relatedMediaType .
            }

         }
         '''
    q = prepareQuery(query,
                     initNs={"dw": DW},
                     )
    return q


class KIDGraph:
    def __init__(self, click_history=None):

        if click_history:
            self.click_history = click_history
            self.clicked_node = click_history[-1]
            self.root_node = click_history[0]
            self.node_ids = set()
            self.node_ids.add(self.clicked_node)
            self.links = {}

    def assign_levels(self, begin_node_id, level, level_dict={}):
        links = list(filter(lambda link: link['source'] == begin_node_id, self.links))

        if len(links) == 0:
            level_dict[begin_node_id] = level

        for link in links:
            level_dict[begin_node_id] = level
            self.assign_levels(begin_node_id=link["target"], level=level + 1,
                               level_dict=level_dict)

        return level_dict

    def construct(self):
        self.get_children()

        if self.root_node != self.clicked_node:
            self.get_parents()

        self.links = list(self.links.values())
        level_dict = self.assign_levels(begin_node_id=self.root_node, level=0)

        all_nodes = list(map(lambda node_id: self.get_feats(level_dict, node_id), self.node_ids))

        return {
            'nodes': all_nodes,
            'links': self.links
        }

    def get_feats(self, level_dict, node_id):
        node_data = {}
        node_data['id'] = node_id
        node_data['type'] = str(g.value(URIRef(node_id), RDF.type))
        node_data['name'] = str(g.value(URIRef(node_id), SCHEMA.name))
        node_data['level'] = level_dict[node_id]
        if node_id == self.clicked_node:
            node_data['comment'] = str(g.value(URIRef(node_id), RDFS.comment))

            if node_data['type'] in ['http://dw.com/SoftwareApplication', 'http://dw.com/Task']:
                node_data['howTo'] = None

            if node_data['type'] in ['http://dw.com/SoftwareApplication']:
                node_data['remarks'] = None

            for pred, obj in g.predicate_objects(URIRef(node_id)):
                mapped_key = NS_MAPPING[str(pred)]

                if mapped_key not in node_data:
                    node_data[mapped_key] = str(obj)

                elif not node_data[mapped_key]:
                    node_data[mapped_key] = str(obj)

        return node_data

    def get_parents(self):
        results = g.query(query_parents(),
                          initBindings={'beginNode': URIRef(self.clicked_node), 'endNode': URIRef(self.root_node)})

        if len(results) == 0:
            # e.g. Reverse Image Search
            parent_class_clicked_node = g.value(URIRef(self.clicked_node), DW["parentNode"])

            # e.g this will read the node whose media type is equal to root
            begin_node = None
            for subject in g.subjects(predicate=RDFS.subClassOf, object=parent_class_clicked_node):
                if self.root_node == str(g.value(subject, DW["relatedMediaType"])):
                    begin_node = subject
                    break

            result_of_parent_Class = g.query(query_children(),
                                             initBindings={'beginNode': parent_class_clicked_node,
                                                           'endNode': URIRef(self.root_node)})
            for result in result_of_parent_Class:
                if str(result.relatedMediaType) != self.root_node and result.relatedMediaType:
                    continue

                self.node_ids.add(str(result.childNode))

                link_key = str(begin_node) + "_" + str(result.childNode)

                if link_key not in self.links:
                    self.links[link_key] = {
                        'source': str(begin_node),
                        'target': str(result.childNode)
                    }

            results = g.query(query_parents(),
                              initBindings={'beginNode': begin_node, 'endNode': URIRef(self.root_node)})

        for result in results:
            if str(result.parentOfParentNode) not in self.click_history or str(
                    result.parentOfBeginNode) not in self.click_history:
                continue
            #
            if str(result.parentOfParentRelatedMediaType) != self.root_node and result.parentOfParentRelatedMediaType:
                continue

            if str(result.parentOfBeginNodeRelatedMediaType) != self.root_node and result.parentOfBeginNodeRelatedMediaType:
                continue

            link_key = str(result.parentOfParentNode) + "_" + str(result.parentOfBeginNode)

            if link_key not in self.links:
                self.links[link_key] = {
                    'source': str(result.parentOfParentNode),
                    'target': str(result.parentOfBeginNode)
                }

            if str(result.childNodeMediaType) != self.root_node and result.childNodeMediaType:
                continue

            # add child nodes of subParent nodes
            self.node_ids.add(str(result.childNode))
            link_key = str(result.parentOfParentNode) + "_" + str(result.childNode)
            if link_key not in self.links:
                self.links[link_key] = {
                    'source': str(result.parentOfParentNode),
                    'target': str(result.childNode)
                }

            self.node_ids.add(str(result.parentOfParentNode))
            self.node_ids.add(str(result.parentOfBeginNode))

    def get_children(self):
        q = query_children()
        results = g.query(q, initBindings={'beginNode': URIRef(self.clicked_node), 'endNode': URIRef(self.root_node)})

        if len(results) == 0:
            results = g.query(q, initBindings={'beginNode': g.value(URIRef(self.clicked_node), RDFS.subClassOf),
                                               'endNode': URIRef(self.root_node)})

        for result in results:
            if str(result.relatedMediaType) != self.root_node and result.relatedMediaType:
                continue

            self.node_ids.add(str(result.childNode))
            link_key = self.clicked_node + "_" + str(result.childNode)

            if link_key not in self.links:
                self.links[link_key] = {
                    'source': self.clicked_node,
                    'target': str(result.childNode)
                }

    @staticmethod
    def search(begin_node: str, root_node: str):
        begin_node_id = g.value(None, SCHEMA.name, Literal(begin_node))
        if not KIDGraph.check_path(begin_node_id, root_node):
            return []

        paths = KIDGraph.search_by_id(begin_node_id, root_node)
        return paths

    @staticmethod
    def search_by_id(begin_node_id, root_node):
        results = g.query(query_paths(),
                          initBindings={'endNode': URIRef(root_node), 'beginNode': URIRef(begin_node_id)})

        nx_g = nx.DiGraph()
        target_node = None
        if not target_node:
            target_node = begin_node_id
            nx_g.add_nodes_from([str(target_node), str(root_node)])

        if len(results) == 0:
            parent_node = g.value(subject=begin_node_id, predicate=DW.parentNode)

            if parent_node:
                for subject in g.subjects(predicate=RDFS.subClassOf, object=parent_node):

                    results = g.query(query_paths(),
                                      initBindings={'endNode': URIRef(root_node), 'beginNode': subject})
                    if len(results) > 0:
                        nx_g.add_edge(str(subject), str(target_node))
                        KIDGraph.search_graph(nx_g, results, root_node)
        else:
            KIDGraph.search_graph(nx_g, results, root_node)
        feats = {x: {"id": x, "name": str(g.value(URIRef(x), SCHEMA.name))} for x in nx_g.nodes}
        paths = []
        for path in nx.all_simple_paths(nx_g, target=str(target_node), source=str(root_node)):
            paths.append(list(map(lambda node: feats[node], path)))
        return paths

    @staticmethod
    def check_path(begin_node_id, root_node):
        for object in g.objects(URIRef(begin_node_id), DW.parentNode):

            media_types = g.objects(object, DW.relatedMediaType)

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

            end_result = mid_end

            nx_g.add_nodes_from([mid_start, mid_end])
            nx_g.add_edge(mid_start, mid_end)

        nx_g.add_edge(end_result, str(root))

    @staticmethod
    def get_index():
        media_objects = []
        for s in g.subjects(RDF.type, DW.MediaObject):
            media_objects.append(s)

        index = []
        for app in g.subjects(RDF.type, DW.SoftwareApplication):
            id_app = str(app)

            categories = []
            for media_object in media_objects:
                id_media_object = str(media_object)

                if KIDGraph.check_path(begin_node_id=id_app, root_node=id_media_object):
                    categories.append(id_media_object)

            index.append({'id': id_app,
                          'name': str(g.value(app, SCHEMA.name)),
                          'categories': categories
                          })
        return index
