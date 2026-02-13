import unittest



from src.lob_decoder import score_coherence, decode_pages





class TestDecoder(unittest.TestCase):

    def test_score(self) -> None:

        text = "Thalos Prime created a test sentence."

        score = score_coherence(text, "Thalos Prime")

        self.assertGreaterEqual(score, 70)



    def test_decode_pages(self) -> None:

        pages = [{"address": {"hex": "ABC"}, "text": "Hello world."}]

        out = decode_pages(pages, "Hello", with_normalization=False)

        self.assertEqual(len(out), 1)

        self.assertIn("score", out[0])





if __name__ == "__main__":

    unittest.main()





