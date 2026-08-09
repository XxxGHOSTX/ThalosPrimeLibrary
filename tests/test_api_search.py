import unittest

from thalos_prime.lob_decoder import score_coherence


class TestApiSearch(unittest.TestCase):

    def test_score_coherence_exact_match(self) -> None:

        text = "This is a test phrase in context."

        score = score_coherence(text, "test phrase").overall_score

        self.assertGreaterEqual(score, 60)



    def test_score_coherence_empty(self) -> None:

        score = score_coherence("", "test").overall_score

        self.assertEqual(score, 0)





if __name__ == "__main__":

    unittest.main()



