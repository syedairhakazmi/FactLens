import httpx

# map standard verdicts and statuses to urdu
VERDICT_URDU = {
    "Supported": "تصدیق شدہ",
    "Refuted": "مسترد شدہ",
    "Not Enough Evidence": "ناکافی شواہد",
    "Mixed": "ملا جلا",
    "Not Applicable": "ناقابل اطلاق",
    "Opinion": "رائے",
    "Non-Checkable": "ناقابل تصدیق",
    "Fact": "حقیقی دعویٰ",
}

# map common pipeline reason explanations to urdu
REASON_URDU = {
    "Sentence fragment is too brief to form a complete checkable assertion": "یہ جملہ مکمل قابل تصدیق دعویٰ بنانے کے لیے بہت مختصر ہے۔",
    "Questions are inquiries rather than verifiable factual claims": "سوالات معلومات کے حصول کے لیے ہوتے ہیں، قابل تصدیق دعوے نہیں۔",
    "Imperatives and requests are not factual claims": "احکامات اور درخواستیں حقائق پر مبنی دعوے نہیں ہوتیں۔",
    "Sentence lacks content words (nouns, adjectives, or verbs) to form a meaningful assertion": "جملے میں بامعنی دعویٰ بنانے کے لیے بنیادی الفاظ (اسم، صفت یا فعل) موجود نہیں ہیں۔",
    "Sentence lacks a verb or predicate to form a checkable assertion": "جملے میں قابل تصدیق دعویٰ بنانے کے لیے کوئی فعل موجود نہیں ہے۔",
    "Exclamatory phrase expresses subjective opinion": "یہ جملہ ذاتی رائے کا اظہار کرتا ہے۔",
    "Factual claim - sent for verification.": "حقائق پر مبنی دعویٰ - تصدیق کے لیے بھیجا گیا۔",
}

def is_urdu (text):
    # detect if text contains urdu arabic unicode characters
    if text is None:
        return False
    urdu_chars = 0
    total_letters = 0
    for char in text:
        if not char.isspace ():
            total_letters = total_letters + 1
            code = ord (char)
            # check arabic and urdu presentation form unicode blocks
            if (0x0600 <= code <= 0x06FF) or (0x0750 <= code <= 0x077F) or (0xFB50 <= code <= 0xFDFF) or (0xFE70 <= code <= 0xFEFF):
                urdu_chars = urdu_chars + 1
    if total_letters > 0 and (urdu_chars / total_letters) > 0.20:
        return True
    return False

def translate_text (text, source_lang = "ur", target_lang = "en"):
    # translate text using translation service with graceful fallback
    clean_text = text.strip ()
    if len (clean_text) == 0:
        return clean_text

    try:
        url = "https://api.mymemory.translated.net/get"
        headers = {"User-Agent": "FactLens-FYP/1.0"}
        langpair = f"{source_lang}|{target_lang}"
        params = {"q": clean_text, "langpair": langpair}
        response = httpx.get (url, params = params, headers = headers, timeout = 5.0)
        if response.status_code == 200:
            data = response.json ()
            translated_result = data.get ("responseData", {}).get ("translatedText", "")
            if len (translated_result.strip ()) > 0 and "MYMEMORY WARNING" not in translated_result:
                return translated_result.strip ()
    except Exception:
        pass

    return clean_text

def translate_ur_to_en (text):
    # convenience helper to translate urdu to english
    return translate_text (text, source_lang = "ur", target_lang = "en")

def translate_en_to_ur (text):
    # convenience helper to translate english to urdu
    return translate_text (text, source_lang = "en", target_lang = "ur")

def get_urdu_verdict (verdict):
    # get urdu label for a verdict
    if verdict in VERDICT_URDU:
        return VERDICT_URDU [verdict]
    return verdict

def get_urdu_reason (reason):
    # get urdu translation for an explanation reason
    if reason in REASON_URDU:
        return REASON_URDU [reason]
    return reason
