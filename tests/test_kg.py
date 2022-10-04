import unittest
from app.kg_ops import create_subgraph


class TestKGMethods(unittest.TestCase):

    def test_subgraph_generation(self):
        client_input = {
            'click_history': ['Image']
        }

        output_graph = create_subgraph(client_input["click_history"])
        assert output_graph == {
            'nodes': [{'id': 'http://dw.com/Image', 'name': 'Image', 'type': 'http://dw.com/MediaObject'},
                      {'id': 'http://dw.com/How', 'name': 'How', 'type': 'http://dw.com/Question'},
                      {'id': 'http://dw.com/What', 'name': 'What', 'type': 'http://dw.com/Question'},
                      {'id': 'http://dw.com/When', 'name': 'When', 'type': 'http://dw.com/Question'},
                      {'id': 'http://dw.com/Who', 'name': 'Who', 'type': 'http://dw.com/Question'},
                      {'id': 'http://dw.com/Where', 'name': 'Where', 'type': 'http://dw.com/Question'}],
            'links': [{'source': 'http://dw.com/Image', 'target': 'http://dw.com/How'},
                      {'source': 'http://dw.com/Image', 'target': 'http://dw.com/What'},
                      {'source': 'http://dw.com/Image', 'target': 'http://dw.com/When'},
                      {'source': 'http://dw.com/Image', 'target': 'http://dw.com/Who'},
                      {'source': 'http://dw.com/Image', 'target': 'http://dw.com/Where'}]}


if __name__ == '__main__':
    unittest.main()
