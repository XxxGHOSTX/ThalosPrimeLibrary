import hashlib

from typing import List



CHARSET = "abcdefghijklmnopqrstuvwxyz ,.;:'\"!?-()[]{}<>@#$%^&*+=/\\|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"

PAGE_LENGTH = 3200



# Linear congruential generator constants (similar structure; deterministic)

# These values are chosen for reproducibility, not cryptographic strength.

LCG_A = 1103515245

LCG_C = 12345

LCG_M = 2 ** 31





def _lcg(seed: int) -> int:

    return (LCG_A * seed + LCG_C) % LCG_M





def _seed_from_hex(hex_addr: str) -> int:

    # Hash the hex address to a 32-bit seed to drive the LCG.

    h = hashlib.sha256(hex_addr.encode("utf-8")).digest()

    return int.from_bytes(h[:4], "big")





def address_to_page(hex_addr: str) -> str:

    """Deterministically generate a 3200-char page from a hex address."""

    seed = _seed_from_hex(hex_addr)

    state = seed

    out_chars: List[str] = []

    clen = len(CHARSET)

    for _ in range(PAGE_LENGTH):

        state = _lcg(state)

        out_chars.append(CHARSET[state % clen])

    return "".join(out_chars)





def query_to_hex(query: str) -> str:

    """Derive a stable hex address from an arbitrary query string."""

    h = hashlib.sha256(query.strip().encode("utf-8")).hexdigest().upper()

    return h[:32]





def query_to_page(query: str) -> str:

    return address_to_page(query_to_hex(query))





if __name__ == "__main__":

    sample = query_to_page("thalos prime test")

    print(sample[:400])





