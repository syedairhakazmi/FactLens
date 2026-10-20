import re
import string

_CHAR_MAP = {
    "\u064a": "\u06cc",
    "\u0649": "\u06cc",
    "\u0626": "\u0626",
    "\u0643": "\u06a9",
    "\u0647": "\u06c1",
    "\u0629": "\u06c3",
    "\u0624": "\u0624",
    "\u0640": "",
    "\u200c": " ",
    "\u200d": "",
    "\ufeff": "",
}

_DIACRITICS_REGEX = re.compile (r"[\u064b-\u065f\u0670]")

_URDU_PUNCTUATION = string.punctuation + "۔،؟؛٪«»" + "“”‘’…—–"

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

def normalize_urdu_text (text):
    if not text or not isinstance (text, str):
        return ""

    chars = []
    for ch in text:
        if ch in _CHAR_MAP:
            chars.append (_CHAR_MAP [ch])
        else:
            chars.append (ch)
    cleaned = "".join (chars)

    cleaned = _DIACRITICS_REGEX.sub ("", cleaned)
    cleaned = re.sub (r"\s+", " ", cleaned).strip ()
    return cleaned

def tokenize_urdu (text, remove_stopwords = True):
    normalized = normalize_urdu_text (text)
    if not normalized:
        return []

    for sym in _URDU_PUNCTUATION:
        normalized = normalized.replace (sym, " ")

    tokens = normalized.split ()
    clean_tokens = []
    for t in tokens:
        if len (t) > 1:
            if remove_stopwords:
                if t not in URDU_STOPWORDS:
                    clean_tokens.append (t)
            else:
                clean_tokens.append (t)
    return clean_tokens
