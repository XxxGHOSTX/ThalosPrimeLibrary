import unittest



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





if __name__ == "__main__":

    unittest.main()



