"""Tests for the multi-language Translation Service."""

from immigration_compliance.services.translation_service import (
    TranslationService,
    UI_STRINGS,
    SUPPORTED_LANGUAGES,
    RTL_LANGUAGES,
    TRANSLATION_DISCLAIMERS,
)


def test_supported_languages_include_six_priority():
    expected = {"en", "zh", "es", "hi", "ar", "fr", "pt"}
    assert set(SUPPORTED_LANGUAGES) == expected


def test_arabic_is_rtl():
    assert "ar" in RTL_LANGUAGES


def test_each_language_has_disclaimer():
    for lang in SUPPORTED_LANGUAGES:
        assert lang in TRANSLATION_DISCLAIMERS


def test_each_language_has_complete_ui_strings():
    """Every supported language must translate every UI key."""
    base_keys = set(UI_STRINGS["en"].keys())
    for lang in SUPPORTED_LANGUAGES:
        if lang == "en":
            continue
        lang_keys = set(UI_STRINGS[lang].keys())
        missing = base_keys - lang_keys
        assert not missing, f"{lang} missing keys: {missing}"


def test_get_ui_strings_returns_dict():
    strs = TranslationService.get_ui_strings("zh")
    assert "onboarding_welcome" in strs
    assert isinstance(strs["onboarding_welcome"], str)


def test_get_ui_strings_unsupported_raises():
    try:
        TranslationService.get_ui_strings("xx")
        assert False
    except ValueError:
        pass


def test_get_ui_string_falls_back_to_english_for_missing_key():
    s = TranslationService.get_ui_string("nonexistent_key", "zh")
    # Falls back gracefully — returns the key when no translation exists
    assert s == "nonexistent_key"


def test_get_ui_string_returns_translated():
    s = TranslationService.get_ui_string("btn_continue", "es")
    assert "Continuar" in s


def test_translate_message_same_language_no_op():
    svc = TranslationService()
    r = svc.translate_message("Hello", source_lang="en", target_lang="en")
    assert r["translated_text"] == "Hello"


def test_translate_message_different_languages():
    svc = TranslationService()
    r = svc.translate_message("Approved", source_lang="en", target_lang="zh")
    assert r["source_lang"] == "en"
    assert r["target_lang"] == "zh"
    assert r["disclaimer"] is not None


def test_translate_message_includes_disclaimer_in_target_lang():
    svc = TranslationService()
    r = svc.translate_message("Hello", source_lang="en", target_lang="zh")
    # Disclaimer is in Chinese
    assert "AI" in r["disclaimer"]


def test_translate_message_without_disclaimer():
    svc = TranslationService()
    r = svc.translate_message("Hello", source_lang="en", target_lang="zh", include_disclaimer=False)
    assert r["disclaimer"] is None


def test_translate_message_unsupported_lang_raises():
    svc = TranslationService()
    try:
        svc.translate_message("Hello", source_lang="en", target_lang="xx")
        assert False
    except ValueError:
        pass


def test_translate_message_empty_text_raises():
    svc = TranslationService()
    try:
        svc.translate_message("", source_lang="en", target_lang="zh")
        assert False
    except ValueError:
        pass


def test_attorney_to_client_helper():
    svc = TranslationService()
    r = svc.translate_attorney_to_client("Your petition has been approved.", client_language="es")
    assert r["source_lang"] == "en"
    assert r["target_lang"] == "es"
    assert r["disclaimer"] is not None


def test_client_to_attorney_helper():
    svc = TranslationService()
    r = svc.translate_client_to_attorney("Tengo una pregunta", client_language="es")
    assert r["source_lang"] == "es"
    assert r["target_lang"] == "en"


def test_caching_returns_same_payload():
    svc = TranslationService()
    r1 = svc.translate_message("Hello", "en", "zh")
    r2 = svc.translate_message("Hello", "en", "zh")
    assert r1["id"] == r2["id"]


def test_custom_translator_callable_used():
    """If an LLM translator is wired, it's called instead of the mock."""
    def fake_translator(text, source, target):
        return f"<{target}> {text} </{target}>"
    svc = TranslationService(llm_translator=fake_translator)
    r = svc.translate_message("Hello", "en", "zh")
    assert "<zh>" in r["translated_text"]
    assert r["is_mock"] is False


def test_llm_translator_failure_falls_back_to_mock():
    def broken_translator(text, source, target):
        raise RuntimeError("provider down")
    svc = TranslationService(llm_translator=broken_translator)
    r = svc.translate_message("Hello", "en", "zh")
    # Falls back to mock format
    assert "[en→zh]" in r["translated_text"]


def test_list_supported_languages_marks_rtl():
    langs = TranslationService.list_supported_languages()
    ar = next(l for l in langs if l["code"] == "ar")
    en = next(l for l in langs if l["code"] == "en")
    assert ar["rtl"] is True
    assert en["rtl"] is False


def test_ui_keys_listing():
    keys = TranslationService.list_ui_keys()
    assert "onboarding_welcome" in keys
    assert "btn_continue" in keys
    assert len(keys) >= 40
