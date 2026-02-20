import unittest

from src.lob_babel_enumerator import enumerate_addresses


class TestBabelEnumerator(unittest.TestCase):

    def test_enumerate_returns_results(self):

        results = enumerate_addresses("thalos prime created", max_per_size=2, ngram_sizes=(1, 2))

        assert results

        # Ensure dedup and type tagging

        types = {r["type"] for r in results}

        assert "full" in types





if __name__ == "__main__":

    unittest.main()





