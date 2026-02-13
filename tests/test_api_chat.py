import asyncio
import unittest

import src.api as api



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


    @unittest.skipIf(api.FASTAPI_AVAILABLE, "FastAPI is installed; placeholder path not active")
    def test_status_endpoint_requires_fastapi(self):

        with self.assertRaisesRegex(RuntimeError, "FastAPI dependency not installed"):

            asyncio.run(api.status())


    @unittest.skipUnless(api.FASTAPI_AVAILABLE, "FastAPI is not installed")
    def test_status_endpoint_available_with_fastapi(self):

        result = asyncio.run(api.status())

        self.assertIsInstance(result, dict)

        self.assertEqual(result.get("status"), "ok")


    def test_build_reply_graph_mode(self):

        reply = build_reply("example query", [], allow_search=True)

        self.assertIn("BABEL_GRAPH_RESPONSE", reply)





if __name__ == "__main__":

    unittest.main()
