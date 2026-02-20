import unittest

from src.semantic_parser import semantic_deconstruct


class TestSemanticParser(unittest.TestCase):
    def test_detects_genomic_node(self):
        out = semantic_deconstruct("Analyze DNA sequence for mutations")
        assert out["node"] == "genomic"
        assert "physical" in out["dimensions"]

    def test_detects_logical_node(self):
        out = semantic_deconstruct("Provide a proof sketch for a theorem")
        assert out["node"] == "logical"


if __name__ == "__main__":
    unittest.main()
