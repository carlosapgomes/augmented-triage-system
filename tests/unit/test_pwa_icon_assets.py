from __future__ import annotations

from pathlib import Path


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _read_png_dimensions(path: Path) -> tuple[int, int]:
    png_bytes = path.read_bytes()
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert png_bytes[12:16] == b"IHDR"
    width = int.from_bytes(png_bytes[16:20], byteorder="big")
    height = int.from_bytes(png_bytes[20:24], byteorder="big")
    return width, height


def test_pwa_base_icon_art_uses_square_chd_dashboard_composition() -> None:
    icon_path = Path("src/triage_automation/infrastructure/http/static/pwa/icons/chd-base.svg")

    assert icon_path.exists()
    icon_svg = _read_text(str(icon_path))
    assert "viewBox=\"0 0 512 512\"" in icon_svg
    assert ">CHD<" in icon_svg
    assert ">dashboard<" in icon_svg
    assert "#0b4263" in icon_svg
    assert "#1b5f78" in icon_svg
    assert "#2f8f9d" in icon_svg


def test_pwa_install_icons_include_required_sizes_and_maskable_variant() -> None:
    icons_dir = Path("src/triage_automation/infrastructure/http/static/pwa/icons")
    expected_icons = {
        "chd-16.png": 16,
        "chd-32.png": 32,
        "chd-180.png": 180,
        "chd-192.png": 192,
        "chd-512.png": 512,
        "chd-maskable-512.png": 512,
    }

    for icon_name, expected_size in expected_icons.items():
        icon_path = icons_dir / icon_name
        assert icon_path.exists(), f"missing icon: {icon_name}"
        width, height = _read_png_dimensions(icon_path)
        assert width == expected_size
        assert height == expected_size
