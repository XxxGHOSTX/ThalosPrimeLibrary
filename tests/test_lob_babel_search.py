import unittest



from src.lob_babel_search import (

    _extract_address_info,

    _extract_book_links,

    _extract_page_text,

    search_fragments,

)





class TestLoBBabelSearch(unittest.TestCase):

    def test_extract_book_links(self) -> None:

        html = (

            "<html><body>"

            "<a href=\"book.cgi?hex=ABC&wall=1&shelf=2&volume=3&page=4\">A</a>"

            "<a href=\"/book.html?hex=DEF\">B</a>"

            "<a href=\"/other.html\">C</a>"

            "</body></html>"

        )

        links = _extract_book_links(html, "https://libraryofbabel.info/search.cgi")

        self.assertEqual(len(links), 2)

        self.assertTrue(links[0].startswith("https://"))



    def test_extract_address_info(self) -> None:

        url = "https://libraryofbabel.info/book.cgi?hex=ABC&wall=1&shelf=2&volume=3&page=4"

        info = _extract_address_info(url)

        self.assertEqual(info["hex"], "ABC")

        self.assertEqual(info["wall"], "1")

        self.assertEqual(info["shelf"], "2")

        self.assertEqual(info["volume"], "3")

        self.assertEqual(info["page"], "4")



    def test_extract_page_text_prefers_pre(self) -> None:

        html = "<html><body><pre>ABC\nDEF</pre><div>IGNORE</div></body></html>"

        text = _extract_page_text(html)

        self.assertIn("ABC", text)

        self.assertIn("DEF", text)

        self.assertNotIn("IGNORE", text)



    def test_search_fragments_splits_words(self) -> None:

        results = search_fragments("alpha beta")

        self.assertIsInstance(results, list)





if __name__ == "__main__":

    unittest.main()



