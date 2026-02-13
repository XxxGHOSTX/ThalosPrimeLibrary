"""
Tests for the Babel decoder module
"""

import pytest
from thalos_prime.lob_decoder import (
    BabelDecoder,
    CoherenceScore,
    DecodedPage,
    score_coherence,
    decode_page
)


def test_babel_decoder_initialization() -> None:
    """Test decoder initialization with default weights"""
    decoder = BabelDecoder()
    
    # Weights should sum to 1.0
    total = (
        decoder.weight_language +
        decoder.weight_structure +
        decoder.weight_ngram +
        decoder.weight_exact_match
    )
    assert abs(total - 1.0) < 0.0001


def test_babel_decoder_custom_weights() -> None:
    """Test decoder with custom weights"""
    decoder = BabelDecoder(
        weight_language=0.4,
        weight_structure=0.3,
        weight_ngram=0.2,
        weight_exact_match=0.1
    )
    
    # Weights should still sum to 1.0 after normalization
    total = (
        decoder.weight_language +
        decoder.weight_structure +
        decoder.weight_ngram +
        decoder.weight_exact_match
    )
    assert abs(total - 1.0) < 0.0001


def test_score_coherence_basic() -> None:
    """Test basic coherence scoring"""
    decoder = BabelDecoder()
    
    text = "the quick brown fox jumps over the lazy dog"
    coherence = decoder.score_coherence(text)
    
    # Should return a CoherenceScore object
    assert isinstance(coherence, CoherenceScore)
    assert 0 <= coherence.overall_score <= 100
    assert coherence.confidence_level in ['high', 'medium', 'sparse', 'minimal']


def test_score_coherence_with_query() -> None:
    """Test coherence scoring with query matching"""
    decoder = BabelDecoder()
    
    text = "the quick brown fox jumps over the lazy dog"
    query = "quick brown"
    
    coherence = decoder.score_coherence(text, query)
    
    # Should have high exact match score
    assert coherence.exact_match_score > 0
    assert coherence.overall_score > 0


def test_score_language_common_words() -> None:
    """Test language scoring with common English words"""
    decoder = BabelDecoder()
    
    # Text with many common words
    text = "the and of to in is it for that as"
    score = decoder._score_language(text)
    
    # Should score highly
    assert score > 0.5


def test_score_language_gibberish() -> None:
    """Test language scoring with gibberish"""
    decoder = BabelDecoder()
    
    # Gibberish text
    text = "xyz qwp zyx mnb vcd fgh jkl"
    score = decoder._score_language(text)
    
    # Should score lowly
    assert score < 0.3


def test_score_structure_with_punctuation() -> None:
    """Test structure scoring with good punctuation"""
    decoder = BabelDecoder()
    
    # Text with good structure
    text = "This is a sentence. This is another sentence. And one more."
    score = decoder._score_structure(text)
    
    # Should score reasonably well
    assert score > 0.3


def test_score_structure_no_punctuation() -> None:
    """Test structure scoring with no punctuation"""
    decoder = BabelDecoder()
    
    # No punctuation
    text = "this is just words without any structure or punctuation marks"
    score = decoder._score_structure(text)
    
    # Should score low
    assert score < 0.3


def test_score_ngrams() -> None:
    """Test n-gram coherence scoring"""
    decoder = BabelDecoder()
    
    # Coherent text with common words
    text = "the cat sat on the mat and the dog ran"
    score = decoder._score_ngrams(text)
    
    # Should have some coherence
    assert score > 0.0


def test_score_exact_match_full() -> None:
    """Test exact match with full query match"""
    decoder = BabelDecoder()
    
    text = "the quick brown fox jumps"
    query = "quick brown"
    score = decoder._score_exact_match(text, query)
    
    # Should be 1.0 for exact match
    assert score == 1.0


def test_score_exact_match_partial() -> None:
    """Test exact match with partial word match"""
    decoder = BabelDecoder()
    
    text = "the quick fox jumps"
    query = "quick brown"
    score = decoder._score_exact_match(text, query)
    
    # Should have partial score
    assert 0 < score < 1.0


def test_score_exact_match_none() -> None:
    """Test exact match with no match"""
    decoder = BabelDecoder()
    
    text = "the quick fox jumps"
    query = "elephant giraffe"
    score = decoder._score_exact_match(text, query)
    
    # Should be 0
    assert score == 0.0


def test_confidence_levels() -> None:
    """Test that confidence levels are assigned correctly"""
    decoder = BabelDecoder()
    
    # High coherence text
    high_text = "the quick brown fox jumps over the lazy dog. this is a good sentence."
    high_score = decoder.score_coherence(high_text, query="quick brown")
    
    # Should be medium or high confidence
    assert high_score.confidence_level in ['medium', 'high']
    
    # Low coherence text (gibberish)
    low_text = "xyz qwp zyx mnb vcd fgh jkl pqr stu vwx"
    low_score = decoder.score_coherence(low_text)
    
    # Should be minimal or sparse confidence
    assert low_score.confidence_level in ['minimal', 'sparse']


def test_decode_page_basic() -> None:
    """Test basic page decoding"""
    decoder = BabelDecoder()
    
    address = "abc123"
    text = "the quick brown fox jumps over the lazy dog"
    
    decoded = decoder.decode_page(address, text)
    
    # Should return DecodedPage
    assert isinstance(decoded, DecodedPage)
    assert decoded.address == address
    assert decoded.raw_text == text
    assert decoded.source == 'local'
    assert isinstance(decoded.coherence, CoherenceScore)


def test_decode_page_with_query() -> None:
    """Test page decoding with query"""
    decoder = BabelDecoder()
    
    address = "test456"
    text = "the quick brown fox jumps"
    query = "brown fox"
    
    decoded = decoder.decode_page(address, text, query=query)
    
    assert decoded.coherence.exact_match_score > 0
    assert decoded.provenance['query'] == query


def test_decode_page_remote_source() -> None:
    """Test page decoding with remote source"""
    decoder = BabelDecoder()
    
    address = "remote123"
    text = "some remote text"
    
    decoded = decoder.decode_page(address, text, source='remote')
    
    assert decoded.source == 'remote'
    assert decoded.provenance['source'] == 'remote'


def test_decode_page_provenance() -> None:
    """Test that provenance is recorded correctly"""
    decoder = BabelDecoder()
    
    address = "prov123"
    text = "test text"
    query = "test"
    
    decoded = decoder.decode_page(address, text, query=query)
    
    # Check provenance fields
    assert 'address' in decoded.provenance
    assert 'source' in decoded.provenance
    assert 'query' in decoded.provenance
    assert 'timestamp' in decoded.provenance
    assert decoded.provenance['address'] == address


def test_coherence_score_metrics() -> None:
    """Test that detailed metrics are included"""
    decoder = BabelDecoder()
    
    text = "the quick brown fox"
    coherence = decoder.score_coherence(text)
    
    # Check that metrics are present
    assert 'language_score' in coherence.metrics
    assert 'structure_score' in coherence.metrics
    assert 'ngram_score' in coherence.metrics
    assert 'text_length' in coherence.metrics
    assert 'word_count' in coherence.metrics
    assert 'sentence_count' in coherence.metrics


def test_count_sentences() -> None:
    """Test sentence counting"""
    decoder = BabelDecoder()
    
    # Test with periods
    text1 = "Sentence one. Sentence two. Sentence three."
    count1 = decoder._count_sentences(text1)
    assert count1 == 3
    
    # Test with mixed punctuation
    text2 = "Question? Statement. Exclamation!"
    count2 = decoder._count_sentences(text2)
    assert count2 == 3
    
    # Test with no punctuation
    text3 = "no punctuation here"
    count3 = decoder._count_sentences(text3)
    assert count3 >= 1


def test_convenience_function_score_coherence() -> None:
    """Test module-level score_coherence function"""
    text = "the quick brown fox"
    coherence = score_coherence(text)
    
    assert isinstance(coherence, CoherenceScore)
    assert 0 <= coherence.overall_score <= 100


def test_convenience_function_decode_page() -> None:
    """Test module-level decode_page function"""
    address = "conv123"
    text = "convenience test text"
    
    decoded = decode_page(address, text)
    
    assert isinstance(decoded, DecodedPage)
    assert decoded.address == address


def test_enable_llm() -> None:
    """Test enabling LLM normalization"""
    decoder = BabelDecoder()
    
    assert decoder.llm_enabled is False
    
    decoder.enable_llm('openai', api_key='test_key')
    
    assert decoder.llm_enabled is True
    assert decoder.llm_provider == 'openai'


def test_normalize_with_llm_disabled() -> None:
    """Test that normalization returns None when LLM is disabled"""
    decoder = BabelDecoder()
    
    address = "norm123"
    text = "test text"
    
    # Decode with normalization but LLM disabled
    decoded = decoder.decode_page(address, text, normalize=True)
    
    # Should not have normalized text
    assert decoded.normalized_text is None


def test_different_queries_different_scores() -> None:
    """Test that different queries produce different scores"""
    decoder = BabelDecoder()
    
    text = "the quick brown fox jumps over the lazy dog"
    
    score1 = decoder.score_coherence(text, query="quick brown")
    score2 = decoder.score_coherence(text, query="lazy dog")
    score3 = decoder.score_coherence(text, query="elephant")
    
    # Scores should be different
    # "elephant" should score lowest (not in text)
    assert score3.exact_match_score < score1.exact_match_score
    assert score3.exact_match_score < score2.exact_match_score
