import unittest
from typing import cast

from thalos_prime.semantic_parser import semantic_deconstruct


class TestSemanticParser(unittest.TestCase):
    def test_detects_genomic_node(self) -> None:
        out = semantic_deconstruct("Analyze DNA sequence for mutations")
        self.assertEqual(out["node"], "genomic")
        dimensions_obj = out["dimensions"]
        self.assertIsInstance(dimensions_obj, dict)
        dimensions = cast("dict[str, str]", dimensions_obj)
        self.assertIn("physical", dimensions)

    def test_detects_logical_node(self) -> None:
        out = semantic_deconstruct("Provide a proof sketch for a theorem")
        self.assertEqual(out["node"], "logical")


if __name__ == "__main__":
    unittest.main()
