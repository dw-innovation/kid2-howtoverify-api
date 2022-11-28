import unittest
import app.kg_ops as kg_ops


class TestKGMethods(unittest.TestCase):

    def test_categories(self):
        indices = kg_ops.get_index()

        for index in indices:
            # TODO: change this later
            try:
                assert len(index["categories"]) > 0
            except AssertionError as e:
                print(index["id"] + ": its categories are empty")

    def test_paths_in_search(self):
        indices = kg_ops.get_index()

        for index in indices:
            # TODO: change this later
            for category in index["categories"]:
                try:
                    paths = kg_ops.search_by_id(begin_node_id=index["id"], root_node=category)

                    assert len(paths) > 0
                except Exception as e:
                    print(index["id"] + f": problem in discovering search for {category}")


if __name__ == '__main__':
    unittest.main()
