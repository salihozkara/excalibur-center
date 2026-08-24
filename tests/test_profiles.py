"""Tests for profile persistence."""

import pytest

from excalibur_center.core.profiles import ProfileManager

SNAPSHOT = {
    "left": {"brightness": 2, "color": "FF0000"},
    "center": {"brightness": 1, "color": "00FF00"},
    "right": {"brightness": 2, "color": "0000FF"},
}


@pytest.fixture()
def manager(tmp_path):
    return ProfileManager(config_dir=tmp_path / "cfg")


class TestProfiles:
    def test_save_and_list(self, manager):
        manager.save_profile("Oyun", SNAPSHOT)
        assert manager.list_profiles() == ["Oyun"]

    def test_load_roundtrip(self, manager):
        manager.save_profile("Oyun", SNAPSHOT)
        assert manager.load_profile("Oyun") == SNAPSHOT

    def test_delete(self, manager):
        manager.save_profile("X", SNAPSHOT)
        assert manager.delete_profile("X") is True
        assert manager.delete_profile("X") is False
        assert manager.list_profiles() == []

    def test_invalid_name(self, manager):
        from pathlib import Path

        bad = ProfileManager(config_dir=Path(manager.dir).parent)
        with pytest.raises(ValueError):
            bad.validate_name("boşluk/slash")
        with pytest.raises(ValueError):
            bad.validate_name("")
        assert bad.validate_name("Oyun-1_test") == "Oyun-1_test"

    def test_last_state_roundtrip(self, manager):
        snap, name = manager.get_last_state()
        assert snap is None
        manager.set_last_state(SNAPSHOT, profile_name="Oyun")
        snap, name = manager.get_last_state()
        assert snap == SNAPSHOT
        assert name == "Oyun"
