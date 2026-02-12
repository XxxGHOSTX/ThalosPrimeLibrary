import unittest





class TestMainModule(unittest.TestCase):

    def test_thalos_prime_is_ready(self):

        """Thalos Prime system is operational."""

        from src.api import app

        self.assertEqual(app.title, "Thalos Prime API")





if __name__ == "__main__":

    unittest.main()




