import json
import os

def test_pwa_manifest_file_structure():
    manifest_path = os.path.join("frontend", "public", "manifest.json")
    assert os.path.exists(manifest_path), "manifest.json file must exist in frontend/public/"

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("name") == "CineIQ"
    assert data.get("short_name") == "CineIQ"
    assert data.get("display") == "standalone"
    assert data.get("theme_color") == "#7c3aed"
    assert data.get("background_color") == "#09090b"

    icons = data.get("icons", [])
    assert len(icons) >= 2

    icon_sizes = [icon.get("sizes") for icon in icons]
    assert "192x192" in icon_sizes
    assert "512x512" in icon_sizes

    # Check physical icon files existence
    icon192_path = os.path.join("frontend", "public", "icons", "icon-192x192.png")
    icon512_path = os.path.join("frontend", "public", "icons", "icon-512x512.png")
    assert os.path.exists(icon192_path), "icon-192x192.png must exist"
    assert os.path.exists(icon512_path), "icon-512x512.png must exist"
