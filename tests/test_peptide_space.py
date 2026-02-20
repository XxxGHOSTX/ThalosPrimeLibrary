import unittest

from src.peptide_space import search_peptide_constraints


class TestPeptideSpace(unittest.TestCase):
    def test_peptide_search_returns_sequences(self):
        results = search_peptide_constraints("antimicrobial peptide", length=8, max_results=2)
        assert len(results) == 2
        for r in results:
            assert len(r["sequence"]) == 8
            assert "babel://peptide/" in r["address"]


if __name__ == "__main__":
    unittest.main()
