"""
Enhanced decoder and coherence scoring for Library of Babel pages

This module provides advanced heuristics for scoring the coherence and
readability of generated pages, with optional LLM-based normalization.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import time


@dataclass
class CoherenceScore:
    """Result of coherence analysis"""
    overall_score: float  # 0-100 scale
    language_score: float  # English word density
    structure_score: float  # Punctuation and sentence structure
    ngram_score: float  # N-gram coherence
    exact_match_score: float  # Query match score
    confidence_level: str  # 'high', 'medium', 'sparse', 'minimal'
    metrics: Dict[str, any]  # Detailed metrics


@dataclass
class DecodedPage:
    """A decoded page with scores and metadata"""
    address: str
    raw_text: str
    normalized_text: Optional[str]
    coherence: CoherenceScore
    source: str  # 'local' or 'remote'
    timestamp: float
    provenance: Dict[str, any]


class BabelDecoder:
    """
    Enhanced decoder with multi-metric coherence scoring.
    
    Provides configurable weights for different scoring components:
    - Language detection (English word density)
    - Structure analysis (punctuation, capitalization)
    - N-gram coherence (bigram/trigram probabilities)
    - Exact match detection (query matching)
    """
    
    # Common English words for language detection
    COMMON_WORDS = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
        'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
        'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me',
        'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take',
        'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other',
        'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also',
        'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way',
        'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us'
    }
    
    def __init__(
        self,
        weight_language: float = 0.30,
        weight_structure: float = 0.20,
        weight_ngram: float = 0.20,
        weight_exact_match: float = 0.30
    ):
        """
        Initialize the decoder with configurable weights.
        
        Args:
            weight_language: Weight for language detection (0-1)
            weight_structure: Weight for structure analysis (0-1)
            weight_ngram: Weight for n-gram coherence (0-1)
            weight_exact_match: Weight for exact matching (0-1)
        """
        # Normalize weights to sum to 1.0
        total = weight_language + weight_structure + weight_ngram + weight_exact_match
        self.weight_language = weight_language / total
        self.weight_structure = weight_structure / total
        self.weight_ngram = weight_ngram / total
        self.weight_exact_match = weight_exact_match / total
        
        self.llm_enabled = False
        self.llm_provider = None
    
    def score_coherence(self, text: str, query: str = None) -> CoherenceScore:
        """
        Score the coherence of a text using multiple heuristics.
        
        Args:
            text: Text to analyze (typically 3200 characters)
            query: Optional query string for match scoring
        
        Returns:
            CoherenceScore with detailed metrics
        """
        # Calculate individual scores
        language_score = self._score_language(text)
        structure_score = self._score_structure(text)
        ngram_score = self._score_ngrams(text)
        exact_match_score = self._score_exact_match(text, query) if query else 0.0
        
        # Calculate weighted overall score (0-100 scale)
        overall = (
            language_score * self.weight_language +
            structure_score * self.weight_structure +
            ngram_score * self.weight_ngram +
            exact_match_score * self.weight_exact_match
        ) * 100.0
        
        # Determine confidence level
        if overall >= 80:
            confidence = 'high'
        elif overall >= 60:
            confidence = 'medium'
        elif overall >= 40:
            confidence = 'sparse'
        else:
            confidence = 'minimal'
        
        # Collect detailed metrics
        metrics = {
            'language_score': language_score,
            'structure_score': structure_score,
            'ngram_score': ngram_score,
            'exact_match_score': exact_match_score,
            'text_length': len(text),
            'word_count': len(text.split()),
            'sentence_count': self._count_sentences(text)
        }
        
        return CoherenceScore(
            overall_score=overall,
            language_score=language_score * 100,
            structure_score=structure_score * 100,
            ngram_score=ngram_score * 100,
            exact_match_score=exact_match_score * 100,
            confidence_level=confidence,
            metrics=metrics
        )
    
    def _score_language(self, text: str) -> float:
        """
        Score based on English word density.
        
        Args:
            text: Text to analyze
        
        Returns:
            Score between 0.0 and 1.0
        """
        words = text.lower().split()
        if not words:
            return 0.0
        
        # Count common English words
        common_word_count = sum(1 for word in words if word in self.COMMON_WORDS)
        density = common_word_count / len(words)
        
        # Bonus for having some less common words (not all noise)
        unique_words = len(set(words))
        diversity_bonus = min(0.1, unique_words / len(words) * 0.1)
        
        return min(1.0, density + diversity_bonus)
    
    def _score_structure(self, text: str) -> float:
        """
        Score based on punctuation and sentence structure.
        
        Args:
            text: Text to analyze
        
        Returns:
            Score between 0.0 and 1.0
        """
        score = 0.0
        
        # Check for punctuation (periods, commas, question marks, etc.)
        period_count = text.count('.')
        comma_count = text.count(',')
        
        # Presence of periods suggests sentence structure
        if period_count > 0:
            score += 0.3
            
            # Good punctuation density (not too much, not too little)
            punct_density = (period_count + comma_count) / max(1, len(text) / 100)
            if 0.5 <= punct_density <= 3.0:
                score += 0.2
        
        # Check for capital letters (sentence starts)
        # In Library of Babel, we mostly have lowercase, but structure matters
        sentences = text.split('.')
        if len(sentences) > 1:
            # Multiple sentences present
            score += 0.2
            
            # Reasonable sentence length
            avg_sentence_len = len(text) / len(sentences)
            if 20 <= avg_sentence_len <= 200:
                score += 0.2
        
        # Bonus for paragraph-like structure
        if '\n' in text or '  ' in text:
            score += 0.1
        
        return min(1.0, score)
    
    def _score_ngrams(self, text: str) -> float:
        """
        Score based on n-gram coherence (bigram/trigram patterns).
        
        Args:
            text: Text to analyze
        
        Returns:
            Score between 0.0 and 1.0
        """
        words = text.lower().split()
        if len(words) < 2:
            return 0.0
        
        # Check bigram coherence (very simple heuristic)
        # Real implementation would use language model probabilities
        score = 0.0
        
        # Count reasonable bigrams (both words are common)
        coherent_bigrams = 0
        for i in range(len(words) - 1):
            if words[i] in self.COMMON_WORDS or words[i + 1] in self.COMMON_WORDS:
                coherent_bigrams += 1
        
        bigram_ratio = coherent_bigrams / max(1, len(words) - 1)
        score += bigram_ratio * 0.6
        
        # Check for repeated patterns (sign of structure)
        unique_bigrams = set()
        for i in range(len(words) - 1):
            bigram = (words[i], words[i + 1])
            unique_bigrams.add(bigram)
        
        # Some repetition is good, too much is bad
        repetition_ratio = len(unique_bigrams) / max(1, len(words) - 1)
        if 0.3 <= repetition_ratio <= 0.9:
            score += 0.4
        
        return min(1.0, score)
    
    def _score_exact_match(self, text: str, query: str) -> float:
        """
        Score based on exact or fuzzy query matching.
        
        Args:
            text: Text to analyze
            query: Query string to match
        
        Returns:
            Score between 0.0 and 1.0
        """
        if not query:
            return 0.0
        
        text_lower = text.lower()
        query_lower = query.lower()
        
        # Exact match gets highest score
        if query_lower in text_lower:
            return 1.0
        
        # Check for word-level matches
        query_words = set(query_lower.split())
        text_words = set(text_lower.split())
        
        matching_words = query_words & text_words
        if query_words:
            word_match_ratio = len(matching_words) / len(query_words)
            return word_match_ratio * 0.8
        
        return 0.0
    
    def _count_sentences(self, text: str) -> int:
        """Count approximate number of sentences."""
        return max(1, text.count('.') + text.count('!') + text.count('?'))
    
    def decode_page(
        self,
        address: str,
        text: str,
        query: str = None,
        source: str = 'local',
        normalize: bool = False
    ) -> DecodedPage:
        """
        Fully decode a page with coherence scoring and optional normalization.
        
        Args:
            address: Hex address of the page
            text: Page text content
            query: Optional query for relevance scoring
            source: 'local' or 'remote'
            normalize: Whether to apply LLM normalization
        
        Returns:
            DecodedPage with all metadata
        """
        # Score coherence
        coherence = self.score_coherence(text, query)
        
        # Optional normalization
        normalized_text = None
        if normalize and self.llm_enabled:
            normalized_text = self._normalize_with_llm(text, query)
        
        # Create provenance record
        provenance = {
            'address': address,
            'source': source,
            'query': query,
            'normalized': normalize and self.llm_enabled,
            'timestamp': time.time()
        }
        
        return DecodedPage(
            address=address,
            raw_text=text,
            normalized_text=normalized_text,
            coherence=coherence,
            source=source,
            timestamp=time.time(),
            provenance=provenance
        )
    
    def _normalize_with_llm(self, text: str, query: str = None) -> str:
        """
        Normalize text using LLM (placeholder for future implementation).
        
        Args:
            text: Raw text to normalize
            query: Optional query context
        
        Returns:
            Normalized text
        """
        # Placeholder - would integrate with LLM provider
        # For now, just return the original text
        return text
    
    def enable_llm(self, provider: str, **kwargs):
        """
        Enable LLM normalization.
        
        Args:
            provider: LLM provider name ('openai', 'anthropic', etc.)
            **kwargs: Provider-specific configuration
        """
        self.llm_enabled = True
        self.llm_provider = provider
        # Store additional config as needed


# Global decoder instance
_decoder = BabelDecoder()


def score_coherence(text: str, query: str = None) -> CoherenceScore:
    """
    Convenience function to score text coherence.
    
    Args:
        text: Text to analyze
        query: Optional query for relevance
    
    Returns:
        CoherenceScore
    """
    return _decoder.score_coherence(text, query)


def decode_page(
    address: str,
    text: str,
    query: str = None,
    source: str = 'local'
) -> DecodedPage:
    """
    Convenience function to decode a page.
    
    Args:
        address: Hex address
        text: Page text
        query: Optional query
        source: 'local' or 'remote'
    
    Returns:
        DecodedPage
    """
    return _decoder.decode_page(address, text, query, source)
