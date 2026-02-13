import unittest

from src.constraint_navigator import translate_constraints


class TestConstraintNavigator(unittest.TestCase):
    def test_detects_peptide_domain_and_length(self) -> None:
        result = translate_constraints("Design a 12 amino acid antimicrobial peptide")
        self.assertIsNotNone(result)
        assert result is not None  # Type narrowing for mypy
        self.assertEqual(result["domain"], "peptide")
        self.assertEqual(result["length"], 12)

    def test_defaults_length_when_missing(self) -> None:
        result = translate_constraints("Find peptide with motif")
        assert result is not None  # Type narrowing for mypy
        self.assertEqual(result["length"], 10)


if __name__ == "__main__":
    unittest.main()
