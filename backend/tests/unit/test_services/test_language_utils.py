"""Tests for language_utils module."""

import pytest

from app.services.language_utils import (
    LANGUAGE_INSTRUCTION,
    LANGUAGE_KEYWORDS,
    LANGUAGE_PREFIXES,
    detect_language_prefix,
    has_language_instruction,
)


class TestLanguageInstruction:
    """Tests for LANGUAGE_INSTRUCTION constant."""

    def test_language_instruction_contains_key_info(self):
        """Test that the instruction contains essential information."""
        assert "LANGUAGE" in LANGUAGE_INSTRUCTION
        assert "Portuguese" in LANGUAGE_INSTRUCTION
        assert "English" in LANGUAGE_INSTRUCTION


class TestLanguageKeywords:
    """Tests for LANGUAGE_KEYWORDS constant."""

    def test_contains_english_keywords(self):
        """Test that English keywords are included."""
        assert "respond in" in LANGUAGE_KEYWORDS
        assert "answer in" in LANGUAGE_KEYWORDS
        assert "language:" in LANGUAGE_KEYWORDS

    def test_contains_portuguese_keywords(self):
        """Test that Portuguese keywords are included."""
        assert "responda em" in LANGUAGE_KEYWORDS
        assert "idioma:" in LANGUAGE_KEYWORDS

    def test_contains_spanish_keywords(self):
        """Test that Spanish keywords are included."""
        assert "responde en" in LANGUAGE_KEYWORDS

    def test_contains_italian_keywords(self):
        """Test that Italian keywords are included."""
        assert "rispondi in" in LANGUAGE_KEYWORDS

    def test_contains_french_keywords(self):
        """Test that French keywords are included."""
        assert "répondre en" in LANGUAGE_KEYWORDS


class TestLanguagePrefixes:
    """Tests for LANGUAGE_PREFIXES constant."""

    def test_has_spanish_prefix(self):
        """Test Spanish language prefix."""
        found = False
        for keywords, prefix in LANGUAGE_PREFIXES.items():
            if "spanish" in keywords:
                found = True
                assert "Spanish" in prefix
        assert found

    def test_has_english_prefix(self):
        """Test English language prefix."""
        found = False
        for keywords, prefix in LANGUAGE_PREFIXES.items():
            if "english" in keywords:
                found = True
                assert "English" in prefix
        assert found

    def test_prefixes_have_brackets(self):
        """Test that all prefixes are formatted with brackets."""
        for _, prefix in LANGUAGE_PREFIXES.items():
            assert prefix.startswith("[")
            assert "]" in prefix


class TestHasLanguageInstruction:
    """Tests for has_language_instruction function."""

    def test_detects_respond_in_english(self):
        """Test detection of 'respond in' keyword."""
        assert has_language_instruction("Always respond in English")

    def test_detects_answer_in(self):
        """Test detection of 'answer in' keyword."""
        assert has_language_instruction("Answer in Portuguese")

    def test_detects_language_colon(self):
        """Test detection of 'language:' keyword."""
        assert has_language_instruction("LANGUAGE: Use English")

    def test_detects_portuguese_responda_em(self):
        """Test detection of Portuguese keyword."""
        assert has_language_instruction("Sempre responda em português")

    def test_detects_spanish_responde_en(self):
        """Test detection of Spanish keyword."""
        assert has_language_instruction("Siempre responde en español")

    def test_detects_italian_rispondi_in(self):
        """Test detection of Italian keyword."""
        assert has_language_instruction("Rispondi in italiano")

    def test_case_insensitive(self):
        """Test that detection is case insensitive."""
        assert has_language_instruction("RESPOND IN ENGLISH")
        assert has_language_instruction("Responda Em Português")
        assert has_language_instruction("IDIOMA: PT-BR")

    def test_no_false_positives(self):
        """Test no false positives for regular text."""
        assert not has_language_instruction("You are a helpful assistant")
        assert not has_language_instruction("Answer questions about code")
        assert not has_language_instruction("Be professional and concise")

    def test_empty_string(self):
        """Test empty string returns False."""
        assert not has_language_instruction("")


class TestDetectLanguagePrefix:
    """Tests for detect_language_prefix function."""

    def test_detects_spanish_keyword(self):
        """Test detection of Spanish language in custom prompt."""
        result = detect_language_prefix("Responda sempre em espanhol")
        assert result == "[Respond in Spanish] "

    def test_detects_english_keyword(self):
        """Test detection of English language in custom prompt."""
        result = detect_language_prefix("Responda sempre em inglês")
        assert result == "[Respond in English] "

    def test_detects_french_keyword(self):
        """Test detection of French language in custom prompt."""
        result = detect_language_prefix("Responda em francês")
        assert result == "[Respond in French] "

    def test_detects_german_keyword(self):
        """Test detection of German language in custom prompt."""
        result = detect_language_prefix("Responda em alemão")
        assert result == "[Respond in German] "

    def test_detects_italian_keyword(self):
        """Test detection of Italian language in custom prompt."""
        result = detect_language_prefix("Responda em italiano")
        assert result == "[Respond in Italian] "

    def test_no_detection_for_regular_text(self):
        """Test no prefix for regular text without language keywords."""
        result = detect_language_prefix("You are a helpful assistant")
        assert result == ""

    def test_returns_empty_for_none(self):
        """Test returns empty string for None input."""
        result = detect_language_prefix(None)
        assert result == ""

    def test_returns_empty_for_empty_string(self):
        """Test returns empty string for empty input."""
        result = detect_language_prefix("")
        assert result == ""

    def test_case_insensitive(self):
        """Test that detection is case insensitive."""
        result = detect_language_prefix("RESPONDA EM ESPANHOL")
        assert result == "[Respond in Spanish] "
