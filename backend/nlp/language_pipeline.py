"""
Drishti Multi-Language NLP Pipeline.
Provides language detection, translation to English, and NLP intent/sentiment analysis.
"""
import logging
from typing import Dict, List, Any

# Safe imports for langdetect and deep_translator
try:
    from langdetect import detect
except ImportError:
    detect = None

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

logger = logging.getLogger(__name__)

class LanguagePipeline:
    """Detects languages, translates content to English, and classifies intent and sentiment."""

    def __init__(self):
        # Threat keyword registry in English
        self.threat_registry = [
            "credit card dump", "credit card", "fake passport", "passport", "visa", "counterfeit",
            "explosives", "bomb", "c4", "ammunition", "firearms", "glock", "rifle",
            "weed", "cocaine", "heroin", "fentanyl", "meth", "drugs",
            "malware", "ransomware", "rat", "stealer", "botnet", "exploit", "zero-day",
            "credential dump", "combo list", "database leak", "leaked database", "breached",
            "shell access", "root access", "rdp access", "hackers for hire", "assassination"
        ]

        self.multilingual_keywords = {
            "hi": ["क्रेडिट कार्ड", "पासपोर्ट", "विस्फोटक", "ड्रग्स", "हैक", "लीक"],
            "ru": ["кредитная карта", "паспорт", "взрывчатка", "наркотики", "хакер", "утечка"],
            "ar": ["بطاقة ائتمان", "جواز سفر", "متفجرات", "مخدرات", "اختراق", "تسريب"]
        }

    def process(self, text: str) -> Dict[str, Any]:
        """
        Analyze text: detect language, translate to English if needed, and analyze sentiment/intent.

        Args:
            text: Raw input content to process.

        Returns:
            Dict containing:
                original_lang: Detected language code (e.g., 'en', 'hi', 'ru', 'ar')
                translated_text: Text translated to English (or original if already English)
                intent: "planning_attack" | "recruitment" | "selling" | "buying" | "information_sharing" | "unknown"
                sentiment: "hostile" | "neutral" | "transactional"
                threat_keywords: List of matched keywords
                confidence: float score (0.0 to 1.0)
        """
        if not text or not text.strip():
            return {
                "original_lang": "en",
                "translated_text": "",
                "intent": "unknown",
                "sentiment": "neutral",
                "threat_keywords": [],
                "confidence": 1.0
            }

        # 1. Language Detection
        detected_lang = "en"
        detection_confidence = 1.0
        if detect:
            try:
                detected_lang = detect(text)
                logger.info(f"Language detected: {detected_lang}")
            except Exception as e:
                logger.warning(f"langdetect failed: {e}. Defaulting to English.")
                detected_lang = "en"
                detection_confidence = 0.5
        else:
            logger.warning("langdetect package is not installed. Defaulting to English.")
            detected_lang = "en"
            detection_confidence = 0.5

        # 2. Translation to English
        translated_text = text
        translation_applied = False
        if detected_lang != "en":
            if GoogleTranslator:
                try:
                    # Translate to English
                    translator = GoogleTranslator(source="auto", target="en")
                    translated_text = translator.translate(text)
                    translation_applied = True
                    logger.info(f"Successfully translated from {detected_lang} to English.")
                except Exception as e:
                    logger.error(f"GoogleTranslator failed: {e}. Retaining original text.")
                    translated_text = text
            else:
                logger.warning("deep_translator package is not installed. Retaining original text.")

        # 3. Threat Keyword Extraction (Original + Translated)
        matched_keywords = []
        combined_lowercase = (text + " " + translated_text).lower()

        # Check main registry
        for keyword in self.threat_registry:
            if keyword in combined_lowercase:
                matched_keywords.append(keyword)

        # Check language-specific keywords
        if detected_lang in self.multilingual_keywords:
            for kw in self.multilingual_keywords[detected_lang]:
                if kw in text.lower():
                    matched_keywords.append(kw)

        # De-duplicate keywords
        matched_keywords = list(set(matched_keywords))

        # 4. Intent Classification (rule-based heuristic on translated English text)
        intent = "unknown"
        translated_lower = translated_text.lower()

        planning_words = ["attack", "hack", "crash", "target", "ddos", "breach", "destroy", "bomb", "explosive", "striking", "hitlist", "reconnaissance", "c2"]
        recruitment_words = ["recruit", "hire", "join", "career", "job", "team", "developers", "coders", "vacancy", "partner"]
        selling_words = ["sell", "shop", "price", "cost", "vendor", "product", "stock", "download", "btc", "escrow", "xmr", "checkout"]
        buying_words = ["buy", "purchase", "wtb", "want to buy", "rent"]
        sharing_words = ["share", "list", "guide", "tutorial", "vulnerability", "cve", "code", "release", "paste", "exploit"]

        # Score calculations for intents
        scores = {
            "planning_attack": sum(1 for w in planning_words if w in translated_lower),
            "recruitment": sum(1 for w in recruitment_words if w in translated_lower),
            "selling": sum(1 for w in selling_words if w in translated_lower),
            "buying": sum(1 for w in buying_words if w in translated_lower),
            "information_sharing": sum(1 for w in sharing_words if w in translated_lower)
        }

        max_score_intent = max(scores, key=scores.get)
        if scores[max_score_intent] > 0:
            intent = max_score_intent

        # 5. Sentiment Classification
        sentiment = "neutral"
        hostile_words = ["death", "kill", "hate", "destroy", "attack", "police", "fbi", "government", "warning", "pay or", "die", "leak soon"]
        transactional_words = ["price", "usd", "escrow", "coin", "seller", "buyer", "deal", "shop", "payment", "btc", "wallet"]

        hostile_score = sum(1 for w in hostile_words if w in translated_lower)
        trans_score = sum(1 for w in transactional_words if w in translated_lower)

        if hostile_score > trans_score and hostile_score > 0:
            sentiment = "hostile"
        elif trans_score > hostile_score and trans_score > 0:
            sentiment = "transactional"

        return {
            "original_lang": detected_lang,
            "translated_text": translated_text,
            "intent": intent,
            "sentiment": sentiment,
            "threat_keywords": matched_keywords,
            "confidence": float(detection_confidence)
        }
