
import os
import json
import shutil
from zipfile import ZipFile

SRC_DIR = "src"
REPO_DIR = "repo"
ADDONS_DIR = os.path.join(REPO_DIR, "addons")
EXT_DIR = os.path.join(REPO_DIR, "extensions")
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")

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

for folder in os.listdir(SRC_DIR):
    path = os.path.join(SRC_DIR, folder)
    if not os.path.isdir(path):
        continue

    zip_target = f"{folder}.zip"
    tmp_zip = os.path.join(REPO_DIR, zip_target)
    zip_dir(path, tmp_zip)

    with ZipFile(tmp_zip) as zf:
        is_ext = "extension.json" in zf.namelist()

    if is_ext:
        dest_dir = EXT_DIR
        addon_type = "extension"
        with zf.open("extension.json") as f:
            data = json.load(f)
            version = data.get("version", "0.0.0")
            name = data.get("name", folder)
    else:
        dest_dir = ADDONS_DIR
        addon_type = "legacy"
        init_path = os.path.join(path, "__init__.py")
        version, name = "0.0.0", folder
        if os.path.isfile(init_path):
            with open(init_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "bl_info" in line:
                        break
                for line in f:
                    if "'version'" in line:
                        version = line.split(":")[1].strip().strip(",()[] ").replace("'", "").replace('"', '')
                        break

    final_name = f"{name}-{version}.zip"
    final_path = os.path.join(dest_dir, final_name)
    shutil.move(tmp_zip, final_path)

    url = f"{BASE_URL}/{addon_type}s/{final_name}" if BASE_URL else f"{addon_type}s/{final_name}"

    entries.append({
        "name": name,
        "version": version,
        "description": f"{name} ({addon_type})",
        "url": url,
        "version_latest": version,
        "type": addon_type,
    })

with open(os.path.join(REPO_DIR, "index.json"), "w") as f:
    json.dump({ "extensions": entries }, f, indent=2)

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
    f.write("".join(html_parts))
