import unittest



from src.lob_babel_generator import address_to_page, query_to_hex





class TestBabelGenerator(unittest.TestCase):

    def test_deterministic(self):

        hex_addr = query_to_hex("thalos prime test")

        page1 = address_to_page(hex_addr)

        page2 = address_to_page(hex_addr)

        self.assertEqual(page1, page2)

        self.assertEqual(len(page1), 3200)





if __name__ == "__main__":

    unittest.main()





