"""Tests for command building and color types."""

import pytest

from excalibur_center.core.config import (
    Brightness,
    COMMAND_RE,
    RGBColor,
    Zone,
    build_command,
)


class TestRGBColor:
    def test_from_hex_basic(self):
        c = RGBColor.from_hex("FF8800")
        assert (c.r, c.g, c.b) == (255, 136, 0)

    def test_from_hex_hash_and_lowercase(self):
        assert RGBColor.from_hex("#ff8800") == RGBColor(255, 136, 0)

    def test_invalid_hex_raises(self):
        with pytest.raises(ValueError):
            RGBColor.from_hex("GGHHII")
        with pytest.raises(ValueError):
            RGBColor.from_hex("12345")

    def test_out_of_range_channel_raises(self):
        with pytest.raises(ValueError):
            RGBColor(300, 0, 0)


class TestBuildCommand:
    def test_all_zone_green_max(self):
        cmd = build_command(Zone.ALL, Brightness.MAX, RGBColor(0, 255, 0))
        assert cmd == "60200FF00"
        assert COMMAND_RE.match(cmd)

    def test_left_zone_orange_mid(self):
        cmd = build_command(Zone.LEFT, Brightness.MID, RGBColor(255, 136, 0))
        assert cmd == "301FF8800"

    def test_off_black(self):
        cmd = build_command(Zone.RIGHT, Brightness.OFF, RGBColor(0, 0, 0))
        assert cmd == "500000000"

    def test_invalid_brightness_rejected_by_backend_not_builder(self):
        # builder itself only checks shape; backend validates range
        cmd = build_command(Zone.ALL, 9, RGBColor(255, 255, 255))
        assert cmd.startswith("609")
        assert len(cmd) == 9
