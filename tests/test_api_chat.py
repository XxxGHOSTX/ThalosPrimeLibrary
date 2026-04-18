import unittest

from fastapi.testclient import TestClient

from thalos_prime.api.server import app


class TestApiChat(unittest.TestCase):

    def test_chat_generative_reply(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat",
                json={
                    "message": "help",
                    "mode": "generative",
                    "max_results": 2,
                },
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("reply", body)
        self.assertIn("results", body)
        self.assertTrue(body["reply"])





if __name__ == "__main__":

    unittest.main()


