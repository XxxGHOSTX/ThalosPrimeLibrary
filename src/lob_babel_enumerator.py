import hashlib

from typing import Dict, List, Tuple



from src.lob_babel_generator import query_to_hex





def _ngrams(tokens: List[str], n: int) -> List[str]:

    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]





def _hash_to_hex(text: str) -> str:

    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()[:32]





def enumerate_addresses(query: str, max_per_size: int = 3, ngram_sizes: Tuple[int, ...] = (1, 2, 3)) -> List[Dict[str, str]]:

    tokens = [t for t in query.strip().split() if t]

    seen = set()

    results: List[Dict[str, str]] = []



    # Whole-query address

    hex_addr = query_to_hex(query)

    seen.add(hex_addr)

    results.append({"fragment": query, "hex": hex_addr, "type": "full"})



    for n in ngram_sizes:

        grams = _ngrams(tokens, n)

        count = 0

        for gram in grams:

            if count >= max_per_size:

                break

            h = _hash_to_hex(gram)

            if h in seen:

                continue

            seen.add(h)

            results.append({"fragment": gram, "hex": h, "type": f"ngram_{n}"})

            count += 1



    return results





if __name__ == "__main__":

    out = enumerate_addresses("thalos prime created by tony ray macier iii")

    for item in out:

        print(item)





