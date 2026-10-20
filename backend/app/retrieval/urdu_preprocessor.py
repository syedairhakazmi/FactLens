import re
import string

# Mapping for character normalization (Arabic -> standard Urdu)
_CHAR_MAP = {
    # Yeh forms
    "\u064a": "\u06cc",  # ARABIC LETTER YEH -> URDU YEH (ی)
    "\u0649": "\u06cc",  # ARABIC LETTER ALEF MAKSURA -> URDU YEH (ی)
    "\u0626": "\u0626",  # YEH WITH HAMZA ABOVE (ئ)
    # Kaf forms
    "\u0643": "\u06a9",  # ARABIC LETTER KAF -> URDU KAF (ک)
    # Heh forms
    "\u0647": "\u06c1",  # ARABIC LETTER HEH -> HEH GOAL (ہ)
    "\u0629": "\u06c3",  # TEH MARBUTA -> TEH MARBUTA GOAL (ۃ)
    # Waw with Hamza
    "\u0624": "\u0624",
    # Space & Kashida
    "\u0640": "",        # TATWEEL / KASHIDA removal
    "\u200c": " ",       # ZERO WIDTH NON-JOINER to space
    "\u200d": "",        # ZERO WIDTH JOINER removal
    "\ufeff": "",        # BYTE ORDER MARK
}

# Diacritics (Aerab) regex: Zabar, Zer, Pesh, Tanween, Tashdeed, Sukun, Superscript Alef
_DIACRITICS_REGEX = re.compile(r"[\u064b-\u065f\u0670]")

# Punctuation to strip (including English and Urdu specific punctuation: ۔ ، ؟ ؛ ٪ « »)
_URDU_PUNCTUATION = string.punctuation + "۔،؟؛٪«»" + "“”‘’…—–"

# Common Urdu stopwords (lexical filtering for BM25 keyword matching)
URDU_STOPWORDS = {
    "ہے", "ہیں", "تھا", "تھی", "تھے", "ہوں", "ہو", "ہونا", "ہوئی", "ہوئے", "ہوتا", "ہوتی", "ہوتے",
    "کا", "کے", "کی", "کو", "نے", "سے", "پر", "میں", "تک", "پہ",
    "اور", "یا", "کہ", "لیکن", "مگر", "بلکہ", "چونکہ", "کیونکہ", "تاہم", "اگر", "تو",
    "یہ", "وہ", "اس", "ان", "انھیں", "انہیں", "اسے", "اسکو", "انکو", "یہاں", "وہاں", "ادھر", "ادھر",
    "کیا", "کون", "کب", "کہاں", "کیوں", "کیسے", "کتنا", "کتنی", "کتنے",
    "اپنا", "اپنی", "اپنے", "آپ", "خود",
    "بھی", "ہی", "نہیں", "نہ", "مت", "ہر", "سب", "تمام", "کچھ", "کوئی", "چند", "بہت", "زیادہ", "کم",
    "اب", "تب", "جب", "پھر", "پہلے", "بعد", "ساتھ", "پاس", "درمیان",
    "ایک", "دو", "تین", "چار", "پانچ",
    "والا", "والی", "والے",
}

def normalize_urdu_text(text: str) -> str:
    """
    Standardize Urdu text for consistent indexing, claim decomposition, and retrieval.
    Normalizes character variants, strips Tatweel/Kashida, removes Aerab, and collapses whitespace.
    """
    if not text or not isinstance(text, str):
        return ""

    # 1. Normalize characters
    chars = []
    for ch in text:
        chars.append(_CHAR_MAP.get(ch, ch))
    cleaned = "".join(chars)

    # 2. Remove Aerab / diacritics
    cleaned = _DIACRITICS_REGEX.sub("", cleaned)

    # 3. Collapse multiple whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned

def tokenize_urdu(text: str, remove_stopwords: bool = True) -> list[str]:
    """
    Tokenize normalized Urdu text into word tokens for BM25 lexical search.
    Removes punctuation and optional stopwords.
    """
    normalized = normalize_urdu_text(text)
    if not normalized:
        return []

    # Strip punctuation
    for sym in _URDU_PUNCTUATION:
        normalized = normalized.replace(sym, " ")

    tokens = normalized.split()

    if remove_stopwords:
        clean_tokens = [t for t in tokens if t not in URDU_STOPWORDS and len(t) > 1]
    else:
        clean_tokens = [t for t in tokens if len(t) > 1]

    return clean_tokens
