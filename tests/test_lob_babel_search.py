import unittest

from src.lob_babel_search import (
    _extract_address_info,
    _extract_book_links,
    _extract_page_text,
    search_fragments,
)


class TestLoBBabelSearch(unittest.TestCase):

    def test_extract_book_links(self):

        html = (

            "<html><body>"

            '<a href="book.cgi?hex=ABC&wall=1&shelf=2&volume=3&page=4">A</a>'

            '<a href="/book.html?hex=DEF">B</a>'

            '<a href="/other.html">C</a>'

            "</body></html>"

        )

        links = _extract_book_links(html, "https://libraryofbabel.info/search.cgi")

        assert len(links) == 2

        assert links[0].startswith("https://")



    def test_extract_address_info(self):

        url = "https://libraryofbabel.info/book.cgi?hex=ABC&wall=1&shelf=2&volume=3&page=4"

        info = _extract_address_info(url)

        assert info["hex"] == "ABC"

        assert info["wall"] == "1"

        assert info["shelf"] == "2"

        assert info["volume"] == "3"

        assert info["page"] == "4"



    def test_extract_page_text_prefers_pre(self):

        html = "<html><body><pre>ABC\nDEF</pre><div>IGNORE</div></body></html>"

        text = _extract_page_text(html)

        assert "ABC" in text

        assert "DEF" in text

        assert "IGNORE" not in text



    def test_search_fragments_splits_words(self):

        results = search_fragments("alpha beta")

        assert isinstance(results, list)





if __name__ == "__main__":

    unittest.main()



