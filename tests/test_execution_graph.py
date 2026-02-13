import unittest



from src.core.execution_graph import execute_graph





class TestExecutionGraph(unittest.TestCase):

    def test_graph_returns_result(self) -> None:

        results = execute_graph("sample query", max_results=2, mode="deterministic")

        self.assertGreaterEqual(len(results), 1)

        self.assertTrue(results[0].text)



    def test_provenance_present(self) -> None:

        results = execute_graph("entropy", max_results=1, mode="deterministic")

        self.assertIn("graph_id", results[0].provenance)

        self.assertEqual(results[0].provenance.get("mode"), "deterministic")





if __name__ == "__main__":

    unittest.main()





