import argparse

import html.parser

import re

import urllib.parse

import urllib.request

from typing import Any, Dict, List, Optional, Tuple



DEFAULT_BASE_URLS = [

    "https://libraryofbabel.info/search.cgi",

    "https://libraryofbabel.info/search.html",

]



DEFAULT_TIMEOUT = 10





class _TextCollector(html.parser.HTMLParser):

    def __init__(self) -> None:

        super().__init__()

        self._stack: List[str] = []

        self._chunks: List[str] = []



    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:

        self._stack.append(tag)



    def handle_endtag(self, tag: str) -> None:

        if self._stack:

            self._stack.pop()



    def handle_data(self, data: str) -> None:

        if not data or not data.strip():

            return

        # Keep tag context so we can favor preformatted blocks later.

        tag = self._stack[-1] if self._stack else ""

        self._chunks.append((tag, data))





def _fetch_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:

    request = urllib.request.Request(

        url,

        headers={"User-Agent": "ThalosPrimeBabel/1.0"},

    )

    with urllib.request.urlopen(request, timeout=timeout) as response:

        return response.read().decode("utf-8", errors="replace")





def _extract_book_links(html: str, base_url: str) -> List[str]:

    hrefs = re.findall(r"href=[\"']([^\"']+)[\"']", html, flags=re.IGNORECASE)

    results = []

    for href in hrefs:

        if "book" not in href.lower():

            continue

        if "hex=" not in href.lower():

            continue

        results.append(urllib.parse.urljoin(base_url, href))

    return list(dict.fromkeys(results))





def _extract_address_info(url: str) -> Dict[str, Optional[str]]:

    parsed = urllib.parse.urlparse(url)

    query = urllib.parse.parse_qs(parsed.query)

    def _first(key: str) -> Optional[str]:

        return query.get(key, [None])[0]

    return {

        "url": url,

        "hex": _first("hex"),

        "wall": _first("wall"),

        "shelf": _first("shelf"),

        "volume": _first("volume"),

        "page": _first("page"),

    }





def _extract_page_text(html: str) -> str:

    parser = _TextCollector()

    parser.feed(html)



    pre_chunks = [text for tag, text in parser._chunks if tag == "pre"]

    if pre_chunks:

        pre_text = "\n".join(pre_chunks).strip()

        if pre_text:

            return pre_text



    # Prefer larger blocks; fall back to full text aggregation.

    chunks = [text for _, text in parser._chunks]

    if not chunks:

        return ""

    best = max(chunks, key=len)

    if len(best) >= 3200:

        return best.strip()

    return "\n".join(chunks).strip()





def search_library(query: str, max_results: int = 10, base_urls: Optional[List[str]] = None, timeout: int = DEFAULT_TIMEOUT) -> List[Dict[str, Optional[str]]]:

    base_urls = base_urls or DEFAULT_BASE_URLS

    query = query.strip()

    if not query:

        return []



    encoded = urllib.parse.urlencode({"find": query})

    for base in base_urls:

        url = f"{base}?{encoded}"

        try:

            html = _fetch_url(url, timeout=timeout)

        except Exception:

            continue

        links = _extract_book_links(html, base)

        if links:

            results = []

            for link in links[:max_results]:

                info = _extract_address_info(link)

                results.append(info)

            return results



    return []





def fetch_page(address_url: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:

    html = _fetch_url(address_url, timeout=timeout)

    text = _extract_page_text(html)

    info = _extract_address_info(address_url)

    return {"address": info, "text": text, "length": len(text)}





def search_and_fetch(query: str, max_results: int = 10, base_urls: Optional[List[str]] = None, timeout: int = DEFAULT_TIMEOUT) -> List[Dict[str, Any]]:

    results = []

    for info in search_library(query, max_results=max_results, base_urls=base_urls, timeout=timeout):

        try:

            page = fetch_page(info["url"], timeout=timeout)

        except Exception:

            continue

        results.append(page)

    return results





def search_fragments(query: str, max_results_per_fragment: int = 5, base_urls: Optional[List[str]] = None, timeout: int = DEFAULT_TIMEOUT) -> List[Dict[str, Any]]:

    fragments = [part for part in re.split(r"\s+", query.strip()) if part]

    seen = set()

    results = []

    for fragment in fragments:

        for info in search_library(fragment, max_results=max_results_per_fragment, base_urls=base_urls, timeout=timeout):

            key = info.get("url")

            if key in seen:

                continue

            seen.add(key)

            info["matched_fragment"] = fragment

            results.append(info)

    return results





def _cli() -> None:

    parser = argparse.ArgumentParser(description="Search Library of Babel for a query.")

    parser.add_argument("query", help="Search query")

    parser.add_argument("--max", type=int, default=5, help="Max results")

    args = parser.parse_args()



    pages = search_and_fetch(args.query, max_results=args.max)

    for page in pages:

        address = page["address"]

        print(f"URL: {address['url']}")

        print(f"HEX: {address.get('hex')}")

        print(f"WALL: {address.get('wall')} SHELF: {address.get('shelf')} VOLUME: {address.get('volume')} PAGE: {address.get('page')}")

        print(page["text"][:400])

        print("-" * 40)





if __name__ == "__main__":

    _cli()





