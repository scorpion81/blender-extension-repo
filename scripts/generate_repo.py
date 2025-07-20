import os
import zipfile
import shutil
import json
import hashlib
import tomllib  # Python 3.11+ (alternativ: `import toml`)
from pathlib import Path, PurePosixPath

# Verzeichnisse
SRC_DIR = Path("src")
REPO_DIR = Path("repo")
EXT_DIR = REPO_DIR / "extensions"
ADDON_DIR = REPO_DIR / "addons"
INDEX_FILE = EXT_DIR / "index.json"
HTML_FILE = REPO_DIR / "index.html"

# Basis-URL (für lokalen Testserver oder GitHub Pages)
BASE_URL = "http://localhost:8000/"

def is_extension(zip_path: Path) -> bool:
    """Prüft, ob ZIP eine moderne Blender Extension (TOML) enthält."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                if PurePosixPath(name).name == "blender_manifest.toml":
                    with zf.open(name) as f:
                        manifest = tomllib.load(f)
                        return isinstance(manifest, dict) and "id" in manifest
    except Exception as e:
        print(f"[Fehler] {zip_path.name}: {e}")
    return False

def read_manifest_from_zip(zip_path: Path) -> dict:
    """Liest blender_manifest.toml aus einer ZIP-Datei."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                if PurePosixPath(name).name == "blender_manifest.toml":
                    with zf.open(name) as f:
                        return tomllib.load(f)
    except Exception as e:
        print(f"[Manifest-Fehler] {zip_path.name}: {e}")
    return {}

def sha256sum(path: Path) -> str:
    """SHA256 Hash für die ZIP-Datei berechnen."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def process_zips():
    EXT_DIR.mkdir(parents=True, exist_ok=True)
    ADDON_DIR.mkdir(parents=True, exist_ok=True)

    ext_entries = []
    addon_files = []

    for zip_file in SRC_DIR.glob("*.zip"):
        if is_extension(zip_file):
            target = EXT_DIR / zip_file.name
            shutil.copy2(zip_file, target)

            manifest = read_manifest_from_zip(zip_file)
            entry = {
                "id": manifest.get("id", zip_file.stem),
                "version": manifest.get("version", "0.0.0"),
                "file": zip_file.name,
                "url": BASE_URL + f"extensions/{zip_file.name}",
                "sha256": sha256sum(target)
            }
            ext_entries.append(entry)
            print(f"[✓] Extension erkannt: {zip_file.name}")
        else:
            target = ADDON_DIR / zip_file.name
            shutil.copy2(zip_file, target)
            addon_files.append(zip_file.name)
            print(f"[•] Addon erkannt: {zip_file.name}")

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "extensions": ext_entries}, f, indent=2)
        print(f"[📝] index.json geschrieben ({len(ext_entries)} Extension(s))")

    generate_html(ext_entries, addon_files)

def generate_html(extensions: list, addons: list):
    html = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        "<title>Blender Repository Übersicht</title>",
        "<style>body{font-family:sans-serif;padding:2em}table{border-collapse:collapse;margin-bottom:2em}th,td{border:1px solid #ccc;padding:0.5em}</style>",
        "</head><body>",
        "<h1>📦 Blender Repository Dashboard</h1>",
        "<h2>🔌 Extensions</h2>",
        "<table><tr><th>ID</th><th>Version</th><th>Datei</th><th>SHA256</th></tr>"
    ]

    for ext in extensions:
        html.append(f"<tr><td>{ext['id']}</td><td>{ext['version']}</td>"
                    f"<td><a href='extensions/{ext['file']}'>{ext['file']}</a></td>"
                    f"<td><code>{ext['sha256'][:12]}…</code></td></tr>")
    html.append("</table>")

    html.append("<h2>📁 Legacy Addons</h2><ul>")
    for addon in addons:
        html.append(f"<li><a href='addons/{addon}'>{addon}</a></li>")
    html.append("</ul></body></html>")

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
        print(f"[🧾] HTML-Dashboard geschrieben: {HTML_FILE}")

def main():
    print("🔄 Starte Repository-Generierung…")
    process_zips()
    print("✅ Fertig.")

if __name__ == "__main__":
    main()
