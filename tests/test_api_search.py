import unittest



from src.api import _score_coherence





class TestApiSearch(unittest.TestCase):

    def test_score_coherence_exact_match(self):

        text = "This is a test phrase in context."

        score = _score_coherence(text, "test phrase")

        self.assertGreaterEqual(score, 70)



    def test_score_coherence_empty(self):

        score = _score_coherence("", "test")

        self.assertEqual(score, 0)





if __name__ == "__main__":

    unittest.main()





