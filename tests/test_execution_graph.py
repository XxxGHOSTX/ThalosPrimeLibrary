import unittest

from src.core.execution_graph import execute_graph


class TestExecutionGraph(unittest.TestCase):

    def test_graph_returns_result(self):

        results = execute_graph("sample query", max_results=2, mode="deterministic")

        assert len(results) >= 1

        assert results[0].text



    def test_provenance_present(self):

        results = execute_graph("entropy", max_results=1, mode="deterministic")

        assert "graph_id" in results[0].provenance

        assert results[0].provenance.get("mode") == "deterministic"





if __name__ == "__main__":

    unittest.main()





