import unittest

from thalos_prime.lob_babel_enumerator import enumerate_addresses


class TestBabelEnumerator(unittest.TestCase):

    def test_enumerate_returns_results(self) -> None:

        results = enumerate_addresses("thalos prime created", max_results=6, depth=2)

        self.assertTrue(results)

        self.assertTrue(all("address" in item for item in results))





if __name__ == "__main__":

    unittest.main()




