"""Built-in tag and summary extraction without LLM dependency.

Provides fallback extraction when LLM services are unavailable.
Uses TF-IDF-like keyword scoring for tags and extractive summarization.
"""

import re
import math
import logging
from collections import Counter
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class BuiltinExtractor:
    """Extract tags and summary using pure Python algorithms.
    
    This is the fallback extractor used when LLM services are unavailable.
    It uses statistical methods rather than AI for extraction.
    """
    
    # Comprehensive English stopwords
    STOPWORDS_EN = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can", "shall", "not",
        "no", "nor", "if", "then", "else", "when", "where", "while", "how",
        "what", "which", "who", "whom", "why", "this", "that", "these",
        "those", "it", "its", "i", "me", "my", "mine", "we", "us", "our",
        "ours", "you", "your", "yours", "he", "him", "his", "she", "her",
        "hers", "they", "them", "their", "theirs", "so", "than", "too",
        "very", "just", "about", "above", "after", "again", "all", "also",
        "am", "any", "because", "before", "between", "both", "each", "few",
        "get", "got", "here", "into", "more", "most", "much", "must",
        "need", "new", "now", "off", "old", "once", "only", "other", "out",
        "over", "own", "put", "same", "some", "still", "such", "take",
        "tell", "there", "through", "under", "until", "up", "upon", "use",
        "used", "using", "well", "went", "will", "yet",
    }
    
    # Common Chinese stopwords
    STOPWORDS_ZH = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
        "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会",
        "着", "没有", "看", "好", "自己", "这", "他", "她", "它", "们",
        "那", "里", "为", "什么", "对", "个", "能", "与", "或", "但",
        "如果", "而", "把", "被", "让", "给", "从", "向", "又", "得",
        "地", "还", "中", "大", "小", "等", "以", "及", "其", "可以",
        "已", "已经", "所以", "因为", "所", "这个", "那个", "可", "来",
        "过", "做", "时", "没", "比", "更", "最", "很多", "一些",
    }
    
    STOPWORDS = STOPWORDS_EN | STOPWORDS_ZH
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words, handling both English and Chinese.
        
        For English: split on non-alphanumeric characters
        For Chinese: extract character sequences (bigrams and individual chars used for matching)
        """
        if not text:
            return []
        
        tokens = []
        
        # Extract Chinese character sequences (2+ chars as meaningful terms)
        zh_pattern = re.compile(r'[\u4e00-\u9fff]+')
        zh_matches = zh_pattern.findall(text)
        for match in zh_matches:
            # Add the full match if short enough to be a term
            if 2 <= len(match) <= 6:
                tokens.append(match)
            # Also extract bigrams from longer sequences
            if len(match) > 2:
                for i in range(len(match) - 1):
                    tokens.append(match[i:i+2])
                # And trigrams
                for i in range(len(match) - 2):
                    tokens.append(match[i:i+3])
        
        # Extract English words (lowercase)
        en_pattern = re.compile(r'[a-zA-Z][a-zA-Z0-9_-]*[a-zA-Z0-9]|[a-zA-Z]')
        en_matches = en_pattern.findall(text.lower())
        tokens.extend(en_matches)
        
        return tokens
    
    def _remove_stopwords(self, tokens: List[str]) -> List[str]:
        """Remove stopwords from token list."""
        return [t for t in tokens if t.lower() not in self.STOPWORDS and len(t) >= 2]
    
    def extract_tags(self, title: str, content: str,
                     min_tags: int = 3, max_tags: int = 5) -> List[str]:
        """Extract tags using TF-IDF-like keyword scoring.
        
        Algorithm:
        1. Tokenize title and content
        2. Remove stopwords
        3. Score terms by: frequency * title_boost * position_weight
        4. Return top N unique keywords
        
        Args:
            title: Document title
            content: Document content text
            min_tags: Minimum number of tags to return
            max_tags: Maximum number of tags to return
            
        Returns:
            List of extracted tag strings
        """
        if not content and not title:
            return []
        
        # Tokenize title for boosting
        title_tokens = set(self._remove_stopwords(self._tokenize(title or "")))
        
        # Tokenize content by paragraphs for position weighting
        paragraphs = [p.strip() for p in (content or "").split("\n") if p.strip()]
        if not paragraphs and title:
            paragraphs = [title]
        
        # Score each term
        term_scores: Dict[str, float] = {}
        
        for para_idx, paragraph in enumerate(paragraphs):
            tokens = self._remove_stopwords(self._tokenize(paragraph))
            position_weight = 1.0 / (1.0 + para_idx * 0.1)
            
            token_counts = Counter(tokens)
            for token, count in token_counts.items():
                # TF component: log-normalized frequency
                tf = 1.0 + math.log(count) if count > 0 else 0
                # Title boost: 3x if token appears in title
                title_boost = 3.0 if token.lower() in {t.lower() for t in title_tokens} else 1.0
                # Length preference: slightly prefer longer terms (more specific)
                length_bonus = min(len(token) / 4.0, 1.5)
                
                score = tf * title_boost * position_weight * length_bonus
                term_scores[token] = term_scores.get(token, 0) + score
        
        # Also score title tokens directly (ensure title terms are represented)
        for token in title_tokens:
            if token not in term_scores:
                term_scores[token] = 3.0  # Base score for title-only terms
        
        # Sort by score descending, deduplicate case-insensitively
        sorted_terms = sorted(term_scores.items(), key=lambda x: x[1], reverse=True)
        
        seen_lower = set()
        tags = []
        for term, score in sorted_terms:
            term_lower = term.lower()
            if term_lower not in seen_lower:
                seen_lower.add(term_lower)
                tags.append(term)
                if len(tags) >= max_tags:
                    break
        
        return tags
    
    def extract_summary(self, title: str, content: str,
                        max_length: int = 200) -> str:
        """Extract summary using extractive approach.
        
        Algorithm:
        1. Split content into sentences
        2. Score sentences by position, title overlap, and length
        3. Select top 1-3 sentences within max_length
        4. Return joined sentences in original order
        
        Args:
            title: Document title
            content: Document content text
            max_length: Maximum summary length in characters
            
        Returns:
            Extracted summary string
        """
        if not content:
            return title or ""
        
        # Split into sentences (handle English and Chinese punctuation)
        sentence_pattern = re.compile(r'(?<=[.!?。！？\n])\s*')
        raw_sentences = sentence_pattern.split(content.strip())
        
        # Clean and filter sentences
        sentences = []
        for s in raw_sentences:
            s = s.strip()
            # Skip very short or empty sentences, skip markdown headers/formatting
            if len(s) >= 10 and not s.startswith('#') and not s.startswith('---'):
                sentences.append(s)
        
        if not sentences:
            # Fallback: just use first max_length chars of content
            return content[:max_length].strip()
        
        # Tokenize title for overlap scoring
        title_words = set(self._remove_stopwords(self._tokenize(title or "")))
        
        # Score each sentence
        scored_sentences = []
        for idx, sentence in enumerate(sentences):
            # Position score: first sentences are more important
            position_score = 1.0 / (1.0 + idx * 0.3)
            
            # Title overlap score
            sentence_words = set(self._remove_stopwords(self._tokenize(sentence)))
            if title_words and sentence_words:
                overlap = len(title_words & sentence_words) / max(len(title_words), 1)
            else:
                overlap = 0
            title_score = overlap * 2.0
            
            # Length score: prefer medium-length sentences (30-100 chars)
            sent_len = len(sentence)
            if 30 <= sent_len <= 100:
                length_score = 1.0
            elif sent_len < 30:
                length_score = sent_len / 30.0
            else:
                length_score = max(0.5, 1.0 - (sent_len - 100) / 200.0)
            
            total_score = position_score + title_score + length_score
            scored_sentences.append((idx, sentence, total_score))
        
        # Sort by score descending
        scored_sentences.sort(key=lambda x: x[2], reverse=True)
        
        # Select top sentences that fit within max_length, maintain original order
        selected = []
        current_length = 0
        for idx, sentence, score in scored_sentences:
            if current_length + len(sentence) + 1 <= max_length:
                selected.append((idx, sentence))
                current_length += len(sentence) + 1
            if current_length >= max_length * 0.8:  # Stop when 80% full
                break
        
        if not selected:
            # At least include the highest-scored sentence, truncated
            best = scored_sentences[0]
            return best[1][:max_length].strip()
        
        # Sort selected by original order
        selected.sort(key=lambda x: x[0])
        
        return " ".join(s for _, s in selected).strip()
    
    def extract(self, title: str, content: str,
                min_tags: int = 3, max_tags: int = 5,
                max_summary_length: int = 200) -> dict:
        """Extract both tags and summary.
        
        Args:
            title: Document title
            content: Document content text
            min_tags: Minimum number of tags
            max_tags: Maximum number of tags
            max_summary_length: Maximum summary length in characters
            
        Returns:
            Dict with "tags" (list of strings) and "summary" (string)
        """
        return {
            "tags": self.extract_tags(title, content, min_tags, max_tags),
            "summary": self.extract_summary(title, content, max_summary_length),
        }
