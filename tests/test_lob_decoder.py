import unittest

from thalos_prime.lob_decoder import decode_pages, score_coherence


class TestDecoder(unittest.TestCase):

    def test_score(self) -> None:

        text = "Thalos Prime created a test sentence."

        score = score_coherence(text, "Thalos Prime").overall_score

        self.assertGreaterEqual(score, 50)



    def test_decode_pages(self) -> None:

        pages = [{"address": {"hex": "ABC"}, "text": "Hello world."}]

        out = decode_pages(pages, "Hello", with_normalization=False)

        self.assertEqual(len(out), 1)

        self.assertIn("score", out[0])





if __name__ == "__main__":

    unittest.main()



