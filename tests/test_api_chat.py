import unittest
import asyncio



from src.api import build_reply





class TestApiChat(unittest.TestCase):

    def test_help_reply(self):

        reply = build_reply("help", [], allow_search=False)

        self.assertIn("BABEL_CORE", reply)



    def test_time_reply(self):

        reply = build_reply("time", [], allow_search=False)

        self.assertIn("BABEL_CORE", reply)



    def test_mode_reply(self):

        reply = build_reply("mode: analyst", [], allow_search=False)

        self.assertIn("BABEL_CORE", reply)


    def test_status_endpoint_requires_fastapi(self):

        # The placeholder app still exposes the status endpoint but it must raise
        # a deterministic error when FastAPI is not installed.
        import src.api as api

        if api.FASTAPI_AVAILABLE:

            result = asyncio.run(api.status())

            self.assertIsInstance(result, dict)

            self.assertEqual(result.get("status"), "ok")

        else:

            with self.assertRaises(RuntimeError):

                asyncio.run(api.status())


    def test_build_reply_graph_mode(self):

        reply = build_reply("example query", [], allow_search=True)

        self.assertIn("BABEL_GRAPH_RESPONSE", reply)





if __name__ == "__main__":

    unittest.main()
