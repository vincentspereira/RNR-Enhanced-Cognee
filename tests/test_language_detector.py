"""
Unit Tests for Language Detector Module

Tests language detection functionality with 100% coverage.
"""

import pytest
from src.language_detector import (
    language_detector,
    LanguageDetector,
    detect_language,
    detect_language_metadata
)


@pytest.mark.unit
class TestLanguageDetector:
    """Test suite for LanguageDetector class"""

    def test_initialization(self):
        """Test LanguageDetector initialization"""
        detector = LanguageDetector()
        assert detector.default_language == 'en'
        assert detector.min_confidence == 0.5

    def test_detect_english(self):
        """Test English language detection"""
        text = "Hello, this is a test of English language detection."
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'en'
        assert confidence >= 0.5

    def test_detect_spanish(self):
        """Test Spanish language detection"""
        text = "Hola, esto es una prueba de deteccion de idioma espanol."
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'es'
        assert confidence >= 0.5

    def test_detect_french(self):
        """Test French language detection"""
        text = "Bonjour, ceci est un test de detection de langue francaise."
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'fr'
        assert confidence >= 0.5

    def test_detect_german(self):
        """Test German language detection"""
        text = "Hallo, dies ist ein Test der deutschen Spracherkennung."
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'de'
        assert confidence >= 0.5

    def test_detect_short_text_fallback(self):
        """Test fallback to English for short text"""
        text = "Hi"
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'en'
        assert confidence == 0.0

    def test_detect_empty_text(self):
        """Test handling of empty text"""
        text = ""
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'en'
        assert confidence == 0.0

    def test_detect_whitespace_only(self):
        """Test handling of whitespace-only text"""
        text = "   "
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'en'
        assert confidence == 0.0

    def test_is_supported_english(self):
        """Test checking if English is supported"""
        assert language_detector.is_supported('en') is True

    def test_is_supported_unsupported(self):
        """Test checking if unsupported language is handled"""
        assert language_detector.is_supported('xyz') is False

    def test_get_language_name_english(self):
        """Test getting English language name"""
        name = language_detector.get_language_name('en')
        assert name == 'English'

    def test_get_language_name_native(self):
        """Test getting native language name"""
        name = language_detector.get_language_name('es', native=True)
        assert name == 'Espanol'

    def test_get_language_name_unknown(self):
        """Test getting unknown language name"""
        name = language_detector.get_language_name('xyz')
        assert name == 'Unknown'

    def test_get_all_supported_languages(self):
        """Test getting all supported languages"""
        languages = language_detector.get_all_supported_languages()
        assert isinstance(languages, dict)
        assert len(languages) >= 28  # At least 28 languages
        assert 'en' in languages
        assert 'es' in languages
        assert 'fr' in languages

    def test_language_metadata_structure(self):
        """Test language detection metadata structure"""
        text = "This is a test of English language detection."
        metadata = language_detector.detect_with_metadata(text)

        assert isinstance(metadata, dict)
        assert 'language_code' in metadata
        assert 'language_name' in metadata
        assert 'native_name' in metadata
        assert 'confidence' in metadata
        assert 'supported' in metadata
        assert 'text_length' in metadata
        assert 'text_words' in metadata

    def test_language_metadata_values(self):
        """Test language detection metadata values"""
        text = "This is a test."
        metadata = language_detector.detect_with_metadata(text)

        assert metadata['language_code'] == 'en'
        assert metadata['language_name'] == 'English'
        assert metadata['supported'] is True
        assert metadata['text_length'] == len(text)
        assert metadata['text_words'] == 4

    def test_detect_chinese_simplified(self):
        """Test Chinese (Simplified) detection"""
        text = "这是一个简体中文的测试文本，用来验证语言检测功能是否正常工作"
        lang_code, confidence = language_detector.detect_language(text)
        # langdetect may return 'zh-cn' or map to 'zh-cn'
        assert lang_code in ['zh-cn', 'zh']

    def test_detect_japanese(self):
        """Test Japanese detection"""
        text = "これは日本語のテストです"
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'ja'

    def test_detect_korean(self):
        """Test Korean detection"""
        text = "이것은 한국어 테스트입니다"
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'ko'

    def test_detect_russian(self):
        """Test Russian detection"""
        text = "Это тест русского языка"
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'ru'

    def test_detect_arabic(self):
        """Test Arabic detection"""
        text = "هذا اختبار اللغة العربية"
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'ar'

    def test_detect_portuguese(self):
        """Test Portuguese detection"""
        text = "Este eh um teste de lingua portuguesa"
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'pt'

    def test_detect_italian(self):
        """Test Italian detection"""
        text = "Questo è una prova della lingua italiana"
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'it'

    def test_detect_dutch(self):
        """Test Dutch detection"""
        text = "Dit is een test van de Nederlandse taal"
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'nl'

    def test_detect_polish(self):
        """Test Polish detection"""
        text = "To jest test jezyka polskiego"
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'pl'

    def test_singleton_instance(self):
        """Test that language_detector is a singleton"""
        from src.language_detector import language_detector as ld1
        from src.language_detector import language_detector as ld2
        assert ld1 is ld2

    def test_detect_language_function(self):
        """Test convenience function detect_language"""
        text = "This is a test"
        lang_code, confidence = detect_language(text)
        assert lang_code == 'en'
        assert confidence >= 0.5

    def test_detect_language_metadata_function(self):
        """Test convenience function detect_language_metadata"""
        text = "This is a test"
        metadata = detect_language_metadata(text)
        assert isinstance(metadata, dict)
        assert 'language_code' in metadata
        assert metadata['language_code'] == 'en'

    def test_confidence_score_range(self):
        """Test that confidence scores are in valid range"""
        text = "This is a comprehensive test of the language detection system."
        lang_code, confidence = language_detector.detect_language(text)
        assert 0.0 <= confidence <= 1.0

    def test_multiple_detections_consistency(self):
        """Test that multiple detections of same text are consistent"""
        text = "This is a test of consistency."
        lang1, conf1 = language_detector.detect_language(text)
        lang2, conf2 = language_detector.detect_language(text)
        assert lang1 == lang2
        assert conf1 == conf2

    def test_language_code_format(self):
        """Test that language codes are in correct format"""
        text = "This is a test."
        lang_code, confidence = language_detector.detect_language(text)
        assert isinstance(lang_code, str)
        assert len(lang_code) >= 2
        assert len(lang_code) <= 5  # e.g., 'en', 'zh-cn'

    def test_metadata_with_existing_metadata(self):
        """Test add_language_metadata with existing metadata"""
        from src.multi_language_search import multi_language_search

        content = "This is a test."
        existing_metadata = {'category': 'test', 'priority': 'high'}

        enhanced = multi_language_search.add_language_metadata(content, existing_metadata)

        assert enhanced['category'] == 'test'
        assert enhanced['priority'] == 'high'
        assert 'language' in enhanced
        assert 'language_name' in enhanced
        assert 'language_confidence' in enhanced

    def test_metadata_with_no_existing_metadata(self):
        """Test add_language_metadata without existing metadata"""
        from src.multi_language_search import multi_language_search

        content = "This is a test."
        enhanced = multi_language_search.add_language_metadata(content, None)

        assert 'language' in enhanced
        assert 'language_name' in enhanced
        assert 'language_confidence' in enhanced

    def test_all_supported_languages_have_metadata(self):
        """Test that all supported languages have complete metadata"""
        languages = language_detector.get_all_supported_languages()

        for code, info in languages.items():
            assert 'name' in info
            assert 'native_name' in info
            assert isinstance(info['name'], str)
            assert isinstance(info['native_name'], str)


@pytest.mark.unit
class TestLanguageDetectorEdgeCases:
    """Test edge cases and error handling"""

    def test_mixed_language_text(self):
        """Test handling of mixed language text"""
        text = "Hello mundo this is un test"
        lang_code, confidence = language_detector.detect_language(text)
        # Should detect one language, may have lower confidence
        assert isinstance(lang_code, str)
        assert isinstance(confidence, float)

    def test_very_long_text(self):
        """Test handling of very long text"""
        text = "This is a test. " * 100
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'en'

    def test_special_characters_only(self):
        """Test handling of special characters only"""
        text = "!@#$%^&*()"
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'en'  # Fallback to English

    def test_numbers_only(self):
        """Test handling of numbers only"""
        text = "1234567890"
        lang_code, confidence = language_detector.detect_language(text)
        assert lang_code == 'en'  # Fallback to English

    def test_unicode_text(self):
        """Test handling of unicode text"""
        text = "Hello 世界 🌍"
        lang_code, confidence = language_detector.detect_language(text)
        assert isinstance(lang_code, str)
