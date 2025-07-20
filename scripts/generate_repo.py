import os
import zipfile
import toml
import json
import hashlib
from pathlib import Path
from html import escape

SRC_DIR = Path("src")
REPO_DIR = Path("repo")
ADDONS_DIR = REPO_DIR / "addons"
EXTENSIONS_DIR = REPO_DIR / "extensions"

# Hilfsfunktion: sha256 Hash berechnen
def sha256sum(filename):
    h = hashlib.sha256()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

# Manifest aus ZIP lesen (liefert dict oder None)
def read_manifest(zip_path):
    try:
        with zipfile.ZipFile(zip_path) as z:
            # Suche blender_manifest.toml im Root (Pfadname ohne Ordner)
            for name in z.namelist():
                if Path(name).name == "blender_manifest.toml":
                    with z.open(name) as mf:
                        data = mf.read().decode("utf-8")
                        return toml.loads(data)
    except Exception as e:
        print(f"Fehler beim Lesen Manifest {zip_path}: {e}")
    return None

# Kategorisieren: addon oder extension?
# Extension = type=="add-on" UND blender_version_min >= 4.3.0
def is_extension(manifest):
    if not manifest:
        return False
    t = manifest.get("type", "")
    bv_min = manifest.get("blender_version_min", "0.0.0")
    if t == "add-on":
        # Vergleich Version 4.3.0 als str
        # Einfach lexikalisch für Major.Minor.Patch reicht hier
        def ver_tuple(v):
            return tuple(int(x) for x in v.split("."))
        return ver_tuple(bv_min) >= (4,3,0)
    return False

# Index.json für Addons / Extensions schreiben
def write_index_json(target_dir, items, key_name):
    index = {
        "version": 1,
        key_name: []
    }
    for item in items:
        index[key_name].append({
            "id": item["manifest"]["id"],
            "version": item["manifest"]["version"],
            "file": item["filename"],
            "url": f"{target_dir.name}/{item['filename']}",
            "sha256": item["sha256"],
        })
    out_file = target_dir / "index.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    print(f"Index geschrieben: {out_file}")

# Einfaches HTML Dashboard erzeugen
def write_dashboard(all_addons, all_extensions):
    html_path = REPO_DIR / "index.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <title>Blender Repo Dashboard</title>
  <style>
    body {{ font-family: sans-serif; margin: 20px; }}
    h1 {{ margin-bottom: 0; }}
    table {{ border-collapse: collapse; margin-bottom: 40px; width: 100%; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
    th {{ background-color: #eee; }}
    a {{ text-decoration: none; color: #0066cc; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>Blender Repo Dashboard</h1>
  
  <h2>Add-ons</h2>
  <table>
    <tr><th>ID</th><th>Version</th><th>Blender Min</th><th>Datei</th></tr>
""")
        for item in all_addons:
            m = item["manifest"]
            f.write(f"<tr><td>{escape(m.get('id','-'))}</td><td>{escape(m.get('version','-'))}</td><td>{escape(m.get('blender_version_min','-'))}</td><td><a href='addons/{escape(item['filename'])}'>{escape(item['filename'])}</a></td></tr>\n")
        f.write("</table>\n")

        f.write("<h2>Extensions</h2>\n<table>\n<tr><th>ID</th><th>Version</th><th>Blender Min</th><th>Datei</th></tr>\n")
        for item in all_extensions:
            m = item["manifest"]
            f.write(f"<tr><td>{escape(m.get('id','-'))}</td><td>{escape(m.get('version','-'))}</td><td>{escape(m.get('blender_version_min','-'))}</td><td><a href='extensions/{escape(item['filename'])}'>{escape(item['filename'])}</a></td></tr>\n")
        f.write("</table>\n")

        f.write("""
</body>
</html>
""")
    print(f"Dashboard geschrieben: {html_path}")

def main():
    # Ordner anlegen
    ADDONS_DIR.mkdir(parents=True, exist_ok=True)
    EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)

    all_addons = []
    all_extensions = []

    # Alle ZIPs im src
    for zip_file in SRC_DIR.glob("*.zip"):
        print(f"Verarbeite {zip_file.name}...")
        manifest = read_manifest(zip_file)
        if not manifest:
            print(f"  Kein gültiges Manifest gefunden, überspringe {zip_file.name}")
            continue

        # Zielordner wählen
        if is_extension(manifest):
            target_dir = EXTENSIONS_DIR
        else:
            target_dir = ADDONS_DIR

        target_path = target_dir / zip_file.name
        # ZIP kopieren ohne umzubenennen
        with open(zip_file, "rb") as srcf, open(target_path, "wb") as dstf:
            dstf.write(srcf.read())

        sha256 = sha256sum(target_path)

        item = {
            "filename": zip_file.name,
            "manifest": manifest,
            "sha256": sha256
        }

        if target_dir == EXTENSIONS_DIR:
            all_extensions.append(item)
            print(f"  Als Extension einsortiert")
        else:
            all_addons.append(item)
            print(f"  Als Add-on einsortiert")

    # index.json schreiben
    write_index_json(ADDONS_DIR, all_addons, "addons")
    write_index_json(EXTENSIONS_DIR, all_extensions, "extensions")

    # HTML Dashboard schreiben
    write_dashboard(all_addons, all_extensions)

if __name__ == "__main__":
    main()
