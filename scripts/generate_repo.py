import os
import json
import shutil
from zipfile import ZipFile

SRC_DIR = "src"
REPO_DIR = "repo"
ADDONS_DIR = os.path.join(REPO_DIR, "addons")
EXT_DIR = os.path.join(REPO_DIR, "extensions")

os.makedirs(ADDONS_DIR, exist_ok=True)
os.makedirs(EXT_DIR, exist_ok=True)

entries = []

def zip_dir(folder_path, zip_path):
    with ZipFile(zip_path, 'w') as zf:
        for root, _, files in os.walk(folder_path):
            for f in files:
                abs_path = os.path.join(root, f)
                rel_path = os.path.relpath(abs_path, folder_path)
                zf.write(abs_path, arcname=rel_path)

def process_zip(zip_path):
    with ZipFile(zip_path) as zf:
        is_ext = "extension.json" in zf.namelist()
        if is_ext:
            with zf.open("extension.json") as f:
                data = json.load(f)
                version = data.get("version", "0.0.0")
                name = data.get("name", os.path.splitext(os.path.basename(zip_path))[0])
            addon_type = "extension"
        else:
            addon_type = "legacy"
            base_name = os.path.basename(zip_path)
            name_ver = os.path.splitext(base_name)[0]
            name = name_ver
            version = "0.0.0"
    return addon_type, name, version

for entry in os.listdir(SRC_DIR):
    path = os.path.join(SRC_DIR, entry)
    if os.path.isfile(path) and path.endswith(".zip"):
        # ZIP direkt verarbeiten
        addon_type, name, version = process_zip(path)

        dest_dir = EXT_DIR if addon_type == "extension" else ADDONS_DIR
        final_name = f"{name}-{version}.zip"
        final_path = os.path.join(dest_dir, final_name)

        shutil.copy2(path, final_path)

        entries.append({
            "name": name,
            "version": version,
            "description": f"{name} ({addon_type})",
            "url": f"{addon_type}s/{final_name}",
            "version_latest": version,
            "type": addon_type,
        })

    elif os.path.isdir(path):
        # Ordner zippen und auswerten
        tmp_zip = os.path.join(REPO_DIR, f"{entry}.zip")
        zip_dir(path, tmp_zip)

        addon_type, name, version = process_zip(tmp_zip)

        dest_dir = EXT_DIR if addon_type == "extension" else ADDONS_DIR
        final_name = f"{name}-{version}.zip"
        final_path = os.path.join(dest_dir, final_name)

        shutil.move(tmp_zip, final_path)

        entries.append({
            "name": name,
            "version": version,
            "description": f"{name} ({addon_type})",
            "url": f"{addon_type}s/{final_name}",
            "version_latest": version,
            "type": addon_type,
        })

# Index.json und index.html schreiben

with open(os.path.join(REPO_DIR, "index.json"), "w") as f:
    json.dump({"extensions": entries}, f, indent=2)

html_parts = [
    "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Blender Addon Repo</title>",
    "<style>body{font-family:sans-serif;padding:2em}input{width:100%;padding:.5em;margin-bottom:1em}",
    ".entry{border:1px solid #ccc;padding:1em;margin:1em 0}.ext{background:#e7fce7}.leg{background:#fdf3d8}</style>",
    "</head><body><h1>🧩 Blender Addons & Extensions</h1>",
    "<input placeholder='🔍 Suche…' oninput='filter(this.value)'><div id='entries'>"
]

for e in entries:
    cls = "ext" if e["type"] == "extension" else "leg"
    html_parts.append(f"<div class='entry {cls}'><h3>{e['name']} <small>v{e['version']}</small></h3><p>Type: {e['type']}</p><a href='{e['url']}'>Download</a></div>")

html_parts.append("</div><script>function filter(q){for(const el of document.querySelectorAll('.entry'))el.style.display=el.textContent.toLowerCase().includes(q.toLowerCase())?'':'none';}</script></body></html>")

with open(os.path.join(REPO_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write("\n".join(html_parts))
