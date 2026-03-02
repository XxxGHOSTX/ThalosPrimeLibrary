import unittest

from src.peptide_space import search_peptide_constraints


class TestPeptideSpace(unittest.TestCase):
    def test_peptide_search_returns_sequences(self) -> None:
        results = search_peptide_constraints("antimicrobial peptide", length=8, max_results=2)
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertEqual(len(r["sequence"]), 8)
            self.assertIn("babel://peptide/", r["address"])


if __name__ == "__main__":
    unittest.main()
