import unittest

from src.constraint_navigator import translate_constraints


class TestConstraintNavigator(unittest.TestCase):
    def test_detects_peptide_domain_and_length(self):
        result = translate_constraints("Design a 12 amino acid antimicrobial peptide")
        assert result is not None
        assert result["domain"] == "peptide"
        assert result["length"] == 12

    def test_defaults_length_when_missing(self):
        result = translate_constraints("Find peptide with motif")
        assert result["length"] == 10


if __name__ == "__main__":
    unittest.main()
