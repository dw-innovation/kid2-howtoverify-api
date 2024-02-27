import unittest
import app.kg_ops as kg_ops


class TestKGMethods(unittest.TestCase):

    def test_invalid_path(self):
        click_history = ['http://dw.com/Image', 'http://dw.com/Who', 'http://dw.com/Who_is_in_content',
             'http://dw.com/Person_identification', 'http://dw.com/Microsoft_Video_Indexer']


        graph = kg_ops.construct(click_history)
        assert len(graph["nodes"]) == 0

if __name__ == '__main__':
    unittest.main()
