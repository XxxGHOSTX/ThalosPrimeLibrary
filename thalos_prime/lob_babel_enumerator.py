"""
Fragment enumerator for Library of Babel
Maps queries/substrings to candidate addresses

The enumerator breaks down queries into n-grams and uses seeded hashing
to generate deterministic candidate addresses where matching text might be found.
"""

import hashlib
from typing import List, Dict, Set, Tuple, Any


class BabelEnumerator:
    """
    Enumerates candidate addresses for query fragments.
    
    Given a query string, this generates a list of hexadecimal addresses
    where pages containing that text are likely to be found.
    """
    
    def __init__(self, max_ngram_size: int = 5, min_ngram_size: int = 2):
        """
        Initialize the enumerator.
        
        Args:
            max_ngram_size: Maximum n-gram size to extract
            min_ngram_size: Minimum n-gram size to extract
        """
        self.max_ngram_size = max_ngram_size
        self.min_ngram_size = min_ngram_size
    
    def enumerate_addresses(
        self,
        query: str,
        max_results: int = 20,
        depth: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Generate candidate addresses for a query.
        
        Args:
            query: Search query string
            max_results: Maximum number of addresses to return
            depth: Search depth (higher = more variations)
        
        Returns:
            List of dictionaries with 'address', 'ngrams', and 'score' keys
        """
        # Normalize query
        query = query.lower().strip()
        
        if not query:
            return []
        
        # Extract n-grams
        ngrams = self._extract_ngrams(query)
        
        if not ngrams:
            # If query is too short, use the whole thing
            ngrams = [query]
        
        # Generate candidate addresses from n-grams
        candidates = []
        seen_addresses = set()
        
        for ngram in ngrams[:10]:  # Limit to top 10 ngrams
            for depth_level in range(depth):
                # Generate address with depth offset
                address = self._ngram_to_address(ngram, offset=depth_level)
                
                if address not in seen_addresses:
                    seen_addresses.add(address)
                    candidates.append({
                        'address': address,
                        'ngrams': [ngram],
                        'score': self._score_address(ngram, query),
                        'depth': depth_level
                    })
        
        # Sort by score (highest first) and limit results
        candidates.sort(key=lambda x: float(x['score']), reverse=True)
        return candidates[:max_results]
    
    def _extract_ngrams(self, text: str) -> List[str]:
        """
        Extract n-grams from text.
        
        Args:
            text: Input text string
        
        Returns:
            List of n-gram strings, sorted by relevance
        """
        ngrams = set()
        words = text.split()
        
        # Extract word-level n-grams
        for word in words:
            word = word.strip()
            if len(word) >= self.min_ngram_size:
                ngrams.add(word)
        
        # Extract character-level n-grams for shorter queries
        if len(text) < 20:
            for size in range(self.min_ngram_size, min(len(text) + 1, self.max_ngram_size + 1)):
                for i in range(len(text) - size + 1):
                    ngram = text[i:i + size]
                    if ngram.strip():  # Avoid whitespace-only ngrams
                        ngrams.add(ngram.strip())
        
        # Convert to sorted list (longer ngrams first, then alphabetical)
        ngram_list = sorted(ngrams, key=lambda x: (-len(x), x))
        return ngram_list
    
    def _ngram_to_address(self, ngram: str, offset: int = 0) -> str:
        """
        Convert an n-gram to a deterministic hex address.
        
        Args:
            ngram: N-gram string
            offset: Depth offset for generating variations
        
        Returns:
            Hexadecimal address string
        """
        # Create deterministic seed from ngram and offset
        seed = f"{ngram}:{offset}"
        hash_digest = hashlib.sha256(seed.encode('utf-8')).hexdigest()
        
        # Return first 64 hex characters (256 bits)
        # This provides enough entropy for unique addresses
        return hash_digest[:64]
    
    def _score_address(self, ngram: str, query: str) -> float:
        """
        Score an address based on ngram relevance to query.
        
        Args:
            ngram: N-gram that generated the address
            query: Original query string
        
        Returns:
            Relevance score (0.0 to 1.0)
        """
        # Base score on n-gram length and position in query
        score = len(ngram) / max(len(query), 1)
        
        # Bonus for exact query match
        if ngram.lower() == query.lower():
            score += 0.5
        
        # Bonus for complete word matches
        query_words = set(query.lower().split())
        ngram_words = set(ngram.lower().split())
        word_overlap = len(query_words & ngram_words)
        if word_overlap > 0:
            score += 0.2 * (word_overlap / max(len(query_words), 1))
        
        # Cap at 1.0
        return min(score, 1.0)
    
    def enumerate_substrings(
        self,
        text: str,
        substring_length: int = 10
    ) -> List[Tuple[str, str]]:
        """
        Enumerate all substrings of a given length and their addresses.
        
        Useful for indexing or reverse lookups.
        
        Args:
            text: Text to extract substrings from
            substring_length: Length of substrings to extract
        
        Returns:
            List of (substring, address) tuples
        """
        results = []
        text = text.lower()
        
        # Extract all substrings of the specified length
        for i in range(len(text) - substring_length + 1):
            substring = text[i:i + substring_length]
            if substring.strip():  # Skip whitespace-only
                address = self._ngram_to_address(substring, offset=0)
                results.append((substring, address))
        
        return results
    
    def find_common_addresses(
        self,
        query1: str,
        query2: str,
        max_results: int = 10
    ) -> List[str]:
        """
        Find addresses that might contain both queries.
        
        Args:
            query1: First query string
            query2: Second query string
            max_results: Maximum number of common addresses
        
        Returns:
            List of hex addresses
        """
        # Get addresses for both queries
        addresses1 = {item['address'] for item in self.enumerate_addresses(query1, max_results=50)}
        addresses2 = {item['address'] for item in self.enumerate_addresses(query2, max_results=50)}
        
        # Find intersection
        common = list(addresses1 & addresses2)
        return common[:max_results]


# Global instance for convenience
_enumerator = BabelEnumerator()


def enumerate_addresses(query: str, max_results: int = 20, depth: int = 1) -> List[Dict[str, Any]]:
    """
    Convenience function to enumerate addresses for a query.
    
    Args:
        query: Search query string
        max_results: Maximum number of addresses to return
        depth: Search depth
    
    Returns:
        List of address dictionaries
    """
    return _enumerator.enumerate_addresses(query, max_results, depth)


def query_to_addresses(query: str, count: int = 10) -> List[str]:
    """
    Simplified function to get just the address strings.
    
    Args:
        query: Search query string
        count: Number of addresses to return
    
    Returns:
        List of hex address strings
    """
    results = enumerate_addresses(query, max_results=count)
    return [r['address'] for r in results]
