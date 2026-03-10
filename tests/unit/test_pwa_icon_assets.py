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


def _read_png_software_metadata(path: Path) -> str | None:
    png_bytes = path.read_bytes()
    cursor = 8
    while cursor + 8 <= len(png_bytes):
        chunk_length = int.from_bytes(png_bytes[cursor : cursor + 4], byteorder="big")
        chunk_type = png_bytes[cursor + 4 : cursor + 8]
        chunk_data_start = cursor + 8
        chunk_data_end = chunk_data_start + chunk_length
        chunk_data = png_bytes[chunk_data_start:chunk_data_end]

        if chunk_type == b"tEXt" and b"\x00" in chunk_data:
            key, value = chunk_data.split(b"\x00", maxsplit=1)
            if key == b"Software":
                return value.decode("latin-1")

        cursor = chunk_data_end + 4
    return None


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


def test_pwa_install_icons_are_exported_from_svg_source_with_inkscape() -> None:
    icons_dir = Path("src/triage_automation/infrastructure/http/static/pwa/icons")
    icon_names = (
        "chd-16.png",
        "chd-32.png",
        "chd-180.png",
        "chd-192.png",
        "chd-512.png",
        "chd-maskable-512.png",
    )

    for icon_name in icon_names:
        icon_path = icons_dir / icon_name
        assert icon_path.exists(), f"missing icon: {icon_name}"
        assert _read_png_software_metadata(icon_path) == "www.inkscape.org"
