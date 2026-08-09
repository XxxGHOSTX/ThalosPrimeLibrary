import unittest


class TestMainModule(unittest.TestCase):

    def test_thalos_prime_is_ready(self) -> None:
        """Thalos Prime system is operational."""
        from thalos_prime.api.server import app

        self.assertEqual(app.title, "Thalos Prime API")





if __name__ == "__main__":

    unittest.main()



