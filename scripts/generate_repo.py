import zipfile
import ast
import re
import tomllib as toml
import json
import hashlib
import shutil
import os
from pathlib import Path
from html import escape

# Verzeichnisse
SRC_DIR = Path("src")
REPO_DIR = Path("repo")
ADDONS_DIR = REPO_DIR / "addons"
EXTENSIONS_DIR = REPO_DIR / "extensions"
INDEX_HTML = REPO_DIR / "index.html"

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
            if isinstance(v, tuple):
                return v
            return tuple(int(x) for x in v.split("."))
        return ver_tuple(bv_min) >= (4,3,0)
    return False

def read_bl_info_from_zip(zip_path):
    """
    Liest das bl_info dict aus __init__.py einer legacy addon Zip-Datei aus.
    Gibt das Dict zurück oder None, wenn nicht gefunden/fehlerhaft.
    """
    try:
        with zipfile.ZipFile(zip_path) as z:
            # Suche __init__.py im Root oder im ersten Ordner
            candidates = [f for f in z.namelist() if f.endswith("__init__.py")]
            if not candidates:
                return None
            
            # Sortiere nach Pfadtiefe, kleinste zuerst
            candidates.sort(key=lambda p: p.count('/'))
            init_file = candidates[0]

            with z.open(init_file) as f:
                content = f.read().decode("utf-8", errors="ignore")

            # Suche bl_info = { ... }
            match = re.search(r"bl_info\s*=\s*({.*?})", content, re.DOTALL)
            if not match:
                return None

            bl_info_str = match.group(1)

            # Parse als Python-Literal (nur dicts, Listen, Strings, Zahlen etc.)
            bl_info = ast.literal_eval(bl_info_str)

            return bl_info
    except Exception as e:
        print(f"Fehler beim Lesen bl_info aus {zip_path}: {e}")
        return None


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

# Index.json für Addons / Extensions schreiben
def write_index_json(target_dir, items, key_name):
    
    items.sort(key=lambda item: (item["version"])) # reverse=True)

    elems = {
        key_name: []
    }
    elems[key_name] = items
    out_file = target_dir / "index.json"

    index = {
        "blocklist":[],
        "data": elems[key_name],
        "version": "v1"
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    print(f"[📝]Index geschrieben: {out_file}")

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
  
  <h2>📁 Legacy Addons</h2>
  <table>
    <tr><th>ID</th><th>Version</th><th>Blender Min</th><th>Datei</th></tr>
""")
        for m in all_addons:
            f.write(f"<tr><td>{escape(m.get('id','-'))}</td><td>{escape(m.get('version','-'))}</td><td>{escape(str(m.get('blender_version_min','-')))}</td><td><a href='addons/{escape(m['archive_url'])}'>{escape(m['archive_url'])}</a></td></tr>\n")
        f.write("</table>\n")

        f.write("<h2>🔌 Extensions</h2>\n<table>\n<tr><th>ID</th><th>Version</th><th>Blender Min</th><th>Datei</th></tr>\n")
        for m in all_extensions:
            f.write(f"<tr><td>{escape(m.get('id','-'))}</td><td>{escape(m.get('version','-'))}</td><td>{escape(str(m.get('blender_version_min','-')))}</td><td><a href='extensions/{escape(m['archive_url'])}'>{escape(m['archive_url'])}</a></td></tr>\n")
        f.write("</table>\n")

        f.write("""
</body>
</html>
""")
    print(f"[📝]HTML-Dashboard geschrieben: {html_path}")

def read_toml_manifest(toml_bytes):
    return toml.loads(toml_bytes.decode("utf-8"))

def read_bl_info_from_init(zip_path, init_path):
    # liest bl_info dict aus __init__.py
    with zipfile.ZipFile(zip_path) as z:
        source = z.read(init_path).decode("utf-8")
    # einfacher parser für bl_info (Vorsicht: eval unsicher, hier nur für lokale vertrauenswürdige Dateien)
    import ast
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if getattr(target, 'id', None) == 'bl_info':
                    return ast.literal_eval(node.value)
    return {}

def extract_metadata_from_zip(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        # Suche nach blender_manifest.toml
        manifest_path = None
        for name in z.namelist():
            if name.endswith("blender_manifest.toml"):
                manifest_path = name
                break

        if manifest_path:
            manifest_bytes = z.read(manifest_path)
            manifest = read_toml_manifest(manifest_bytes)
            # Mapping für Metadata aus Manifest (einige Felder optional)
            meta = {
                "id": manifest.get("id"),
                "name": manifest.get("name"),
                "version": manifest.get("version"),
                "tagline": manifest.get("tagline", ""),
                "type": manifest.get("type", "add-on"),
                "blender_version_min": manifest.get("blender_version_min", "4.0.0"),
                "website": manifest.get("website", ""),
                "maintainer": ", ".join(manifest.get("copyright", [])) if "copyright" in manifest else manifest.get("maintainer", ""),
                "license": manifest.get("license", ["SPDX:GPL-3.0-or-later"]),
            }
            return meta

        # Wenn kein Manifest, suche nach bl_info in __init__.py (Legacy Addon)
        candidates = [f for f in z.namelist() if f.endswith("__init__.py")]
        if not candidates:
            return None
        # Priorisiere kürzeste Pfade
        candidates.sort(key=lambda p: p.count('/'))
        init_file = candidates[0]
        bl_info = read_bl_info_from_init(zip_path, init_file)
        if not bl_info:
            return None
        meta = {
            "id": bl_info.get("name", "").lower().replace(" ", "_"),
            "name": bl_info.get("name", ""),
            "version": bl_info.get("version", "0.0.0") if isinstance(bl_info.get("version"), str) else ".".join(map(str, bl_info.get("version", (0,0,0)))),
            "tagline": bl_info.get("description", ""),
            "type": "add-on",
            "blender_version_min": bl_info.get("blender", (4,0,0)),
            "website": "",
            "maintainer": bl_info.get("author", ""),
            "license": ["SPDX:GPL-3.0-or-later"],
        }
    return meta

def build_item_from_zip(zip_path, metadata):
    archive_size = os.path.getsize(zip_path)
    archive_hash = "sha256:" + sha256sum(zip_path)
    #archive_url = f"https://extensions.blender.org/download/{archive_hash}/" + os.path.basename(zip_path)
    archive_url = os.path.basename(zip_path)

    item = {
        "id": metadata["id"],
        "schema_version": "1.0.0",
        "name": metadata["name"],
        "version": metadata["version"],
        "tagline": metadata.get("tagline", ""),
        "archive_hash": archive_hash,
        "archive_size": archive_size,
        "archive_url": archive_url,
        "type": metadata["type"],
        "blender_version_min": metadata.get("blender_version_min", "4.0.0"),
        "website": metadata.get("website", ""),
        "maintainer": metadata.get("maintainer", ""),
        "license": metadata.get("license", ["SPDX:GPL-3.0-or-later"]),
    }
    return item

def generate_repo():

    # Ordner anlegen
    ADDONS_DIR.mkdir(parents=True, exist_ok=True)
    EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)

    all_addons = []
    all_extensions = []

    for filename in os.listdir(SRC_DIR):
        if not filename.endswith(".zip"):
            continue
        zip_path = os.path.join(SRC_DIR, filename)
        print(f"Verarbeite {filename}...")
        
        meta = extract_metadata_from_zip(zip_path)
        if not meta:
            print(f"WARNING: Konnte Metadaten aus {filename} nicht auslesen, überspringe...")
            continue

        # Zielordner wählen
        if is_extension(meta):
            dest_dir = EXTENSIONS_DIR
        else:
            dest_dir = ADDONS_DIR

        # Kopiere ZIP (ohne umbenennen)
        import shutil
        shutil.copy2(zip_path, dest_dir)

        item = build_item_from_zip(os.path.join(dest_dir, filename), meta)

        if dest_dir == EXTENSIONS_DIR:
            all_extensions.append(item)
            print(f"[✓] Als Extension einsortiert")
        else:
            all_addons.append(item)
            print(f"[•] Als Add-on einsortiert")

    # index.json schreiben
    write_index_json(ADDONS_DIR, all_addons, "addons")
    write_index_json(EXTENSIONS_DIR, all_extensions, "extensions")

    # HTML Dashboard schreiben
    write_dashboard(all_addons, all_extensions)

def clear_repo():

    # Lösche addons/
    if ADDONS_DIR.exists() and ADDONS_DIR.is_dir():
        print(f"Lösche {ADDONS_DIR}...")
        shutil.rmtree(ADDONS_DIR)
    else:
        print(f"{ADDONS_DIR} nicht vorhanden.")

    # Lösche extensions/
    if EXTENSIONS_DIR.exists() and EXTENSIONS_DIR.is_dir():
        print(f"Lösche {EXTENSIONS_DIR}...")
        shutil.rmtree(EXTENSIONS_DIR)
    else:
        print(f"{EXTENSIONS_DIR} nicht vorhanden.")

    # Lösche index.html
    if INDEX_HTML.exists():
        print(f"Lösche {INDEX_HTML}...")
        INDEX_HTML.unlink()
    else:
        print(f"{INDEX_HTML} nicht vorhanden.")

    print("✅ Repo-Verzeichnis wurde geleert.")


def main():
    clear_repo()
    print("🔄 Starte Repository-Generierung…")
    generate_repo()
    print("✅ Fertig.")

if __name__ == "__main__":
    main()
