"""i18n integrity: every language must cover the same keys."""

from excalibur_center.core.i18n import SUPPORTED, _STRINGS, _detect, t


class TestI18n:
    def test_all_languages_share_keys(self):
        reference = set(_STRINGS["en"].keys())
        for lang in SUPPORTED:
            missing = reference - set(_STRINGS[lang].keys())
            extra = set(_STRINGS[lang].keys()) - reference
            assert not missing, f"{lang} eksik: {missing}"
            assert not extra, f"{lang} fazla: {extra}"

    def test_no_empty_strings(self):
        for lang, table in _STRINGS.items():
            for key, value in table.items():
                assert value and value.strip(), f"{lang}:{key} boş"

    def test_fallback_to_key(self):
        assert t("nonexistent.key") == "nonexistent.key"

    def test_format_args(self):
        result = t("status.applied", zone="Sol", color="FF0000")
        assert "Sol" in result and "FF0000" in result

    def test_detect_defaults_to_en(self, monkeypatch, tmp_path):
        monkeypatch.setenv("LANG", "C.UTF-8")
        import excalibur_center.core.i18n as i18n

        i18n.SETTINGS_FILE = tmp_path / "settings.json"
        i18n._LANGUAGE = None
        assert i18n._detect() == "en"

    def test_detect_turkish_locale(self, monkeypatch, tmp_path):
        monkeypatch.setenv("LANG", "tr_TR.UTF-8")
        import excalibur_center.core.i18n as i18n

        i18n.SETTINGS_FILE = tmp_path / "settings.json"
        i18n._LANGUAGE = None
        assert i18n._detect() == "tr"

    def test_settings_override_locale(self, monkeypatch, tmp_path):
        monkeypatch.setenv("LANG", "tr_TR.UTF-8")
        import excalibur_center.core.i18n as i18n

        i18n.SETTINGS_FILE = tmp_path / "settings.json"
        i18n.SETTINGS_FILE.write_text('{"language": "en"}', encoding="utf-8")
        i18n._LANGUAGE = None
        assert i18n._detect() == "en"
        i18n._LANGUAGE = None
