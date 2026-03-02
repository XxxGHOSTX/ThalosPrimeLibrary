import unittest

from src.semantic_parser import semantic_deconstruct


class TestSemanticParser(unittest.TestCase):
    def test_detects_genomic_node(self) -> None:
        out = semantic_deconstruct("Analyze DNA sequence for mutations")
        self.assertEqual(out["node"], "genomic")
        self.assertIn("physical", out["dimensions"])

    def test_detects_logical_node(self) -> None:
        out = semantic_deconstruct("Provide a proof sketch for a theorem")
        self.assertEqual(out["node"], "logical")


if __name__ == "__main__":
    unittest.main()
