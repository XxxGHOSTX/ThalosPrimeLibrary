import unittest

from src.lob_decoder import decode_pages, score_coherence


class TestDecoder(unittest.TestCase):

    def test_score(self):

        text = "Thalos Prime created a test sentence."

        score = score_coherence(text, "Thalos Prime")

        assert score >= 70



    def test_decode_pages(self):

        pages = [{"address": {"hex": "ABC"}, "text": "Hello world."}]

        out = decode_pages(pages, "Hello", with_normalization=False)

        assert len(out) == 1

        assert "score" in out[0]





if __name__ == "__main__":

    unittest.main()





