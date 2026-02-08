"""
Language Detection Module for Enhanced Cognee

Supports 28 languages with automatic detection using langdetect library.
"""

import logging
from typing import Tuple, Optional
from langdetect import detect, DetectorFactory, LangDetectException
from langdetect.lang_detect_exception import LangDetectException

# Set seed for consistent results
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

# Supported languages with metadata
SUPPORTED_LANGUAGES = {
    'en': {'name': 'English', 'native_name': 'English'},
    'es': {'name': 'Spanish', 'native_name': 'Espanol'},
    'fr': {'name': 'French', 'native_name': 'Francais'},
    'de': {'name': 'German', 'native_name': 'Deutsch'},
    'zh-cn': {'name': 'Chinese (Simplified)', 'native_name': '中文'},
    'zh-tw': {'name': 'Chinese (Traditional)', 'native_name': '中文'},
    'ja': {'name': 'Japanese', 'native_name': '日本語'},
    'ko': {'name': 'Korean', 'native_name': '한국어'},
    'ru': {'name': 'Russian', 'native_name': 'Русский'},
    'ar': {'name': 'Arabic', 'native_name': 'العربية'},
    'pt': {'name': 'Portuguese', 'native_name': 'Portugues'},
    'it': {'name': 'Italian', 'native_name': 'Italiano'},
    'nl': {'name': 'Dutch', 'native_name': 'Nederlands'},
    'pl': {'name': 'Polish', 'native_name': 'Polski'},
    'sv': {'name': 'Swedish', 'native_name': 'Svenska'},
    'da': {'name': 'Danish', 'native_name': 'Dansk'},
    'no': {'name': 'Norwegian', 'native_name': 'Norsk'},
    'fi': {'name': 'Finnish', 'native_name': 'Suomi'},
    'el': {'name': 'Greek', 'native_name': 'Ελληνικά'},
    'cs': {'name': 'Czech', 'native_name': 'Cestina'},
    'hu': {'name': 'Hungarian', 'native_name': 'Magyar'},
    'ro': {'name': 'Romanian', 'native_name': 'Romana'},
    'bg': {'name': 'Bulgarian', 'native_name': 'Български'},
    'sk': {'name': 'Slovak', 'native_name': 'Slovencina'},
    'hr': {'name': 'Croatian', 'native_name': 'Hrvatski'},
    'sr': {'name': 'Serbian', 'native_name': 'Српски'},
    'sl': {'name': 'Slovenian', 'native_name': 'Slovenski'},
    'lt': {'name': 'Lithuanian', 'native_name': 'Lietuviu'},
    'lv': {'name': 'Latvian', 'native_name': 'Latviski'}
}

class LanguageDetector:
    """Language detection with multi-language support"""

    def __init__(self):
        self.default_language = 'en'
        self.min_confidence = 0.5

    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detect language from text.

        Args:
            text: Text to analyze

        Returns:
            Tuple of (language_code, confidence_score)
        """
        if not text or len(text.strip()) < 10:
            return self.default_language, 0.0

        try:
            # Detect language
            detected = detect(text)

            # Check if supported
            if detected in SUPPORTED_LANGUAGES:
                return detected, 0.9
            else:
                # Map similar languages
                mapped = self._map_language(detected)
                if mapped:
                    return mapped, 0.7
                else:
                    # Fall back to English
                    return self.default_language, 0.0

        except (LangDetectException, Exception) as e:
            logger.warning(f"Language detection failed: {e}")
            return self.default_language, 0.0

    def _map_language(self, detected: str) -> Optional[str]:
        """Map unsupported detected languages to supported ones"""
        mapping = {
            'zh': 'zh-cn',  # Chinese -> Simplified Chinese
            'ca': 'es',     # Catalan -> Spanish
            'uk': 'ru',     # Ukrainian -> Russian
            'be': 'ru',     # Belarusian -> Russian
            'mk': 'bg',     # Macedonian -> Bulgarian
            'et': 'fi',     # Estonian -> Finnish
        }
        return mapping.get(detected)

    def is_supported(self, language_code: str) -> bool:
        """Check if language is supported"""
        return language_code in SUPPORTED_LANGUAGES

    def get_language_name(self, language_code: str, native: bool = False) -> str:
        """
        Get language name from code.

        Args:
            language_code: ISO language code
            native: Return native name if True

        Returns:
            Language name
        """
        if language_code in SUPPORTED_LANGUAGES:
            if native:
                return SUPPORTED_LANGUAGES[language_code]['native_name']
            else:
                return SUPPORTED_LANGUAGES[language_code]['name']
        return 'Unknown'

    def get_all_supported_languages(self) -> dict:
        """Get all supported languages"""
        return SUPPORTED_LANGUAGES.copy()

    def detect_with_metadata(self, text: str) -> dict:
        """
        Detect language and return full metadata.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with language metadata
        """
        lang_code, confidence = self.detect_language(text)

        return {
            'language_code': lang_code,
            'language_name': self.get_language_name(lang_code),
            'native_name': self.get_language_name(lang_code, native=True),
            'confidence': confidence,
            'supported': self.is_supported(lang_code),
            'text_length': len(text),
            'text_words': len(text.split())
        }

# Singleton instance
language_detector = LanguageDetector()


def detect_language(text: str) -> Tuple[str, float]:
    """Convenience function for language detection"""
    return language_detector.detect_language(text)


def detect_language_metadata(text: str) -> dict:
    """Convenience function for language detection with metadata"""
    return language_detector.detect_with_metadata(text)
