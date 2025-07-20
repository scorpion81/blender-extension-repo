
#!/usr/bin/env python3
import subprocess
import http.server
import socketserver
import os
import sys
import webbrowser
from pathlib import Path
import threading

REPO_DIR = Path("repo")
PORT = 8000

def run_generate():
    print("🔨 Baue ZIPs & index.json/html …")
    os.environ["BASE_URL"] = ""
    subprocess.run([sys.executable, "scripts/generate_repo.py"], check=True)

def run_server():
    os.chdir(REPO_DIR)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"🌐 Server läuft auf http://localhost:{PORT}")
        httpd.serve_forever()

def open_browser():
    url = f"http://localhost:{PORT}/index.html"
    print(f"🌍 Öffne Browser: {url}")
    webbrowser.open(url)

def run_act():
    print("⚙️ Starte GitHub Action lokal mit act …")
    subprocess.run(["act", "-j", "build"], check=True)

def main():
    if len(sys.argv) < 2:
        print("⚠️  Verwende: dev.py [build|serve|open|live|act]")
        return

    cmd = sys.argv[1]

    if cmd == "build":
        run_generate()
    elif cmd == "serve":
        run_server()
    elif cmd == "open":
        open_browser()
    elif cmd == "live":
        run_generate()
        threading.Thread(target=run_server, daemon=True).start()
        open_browser()
        print("🔁 Drücke Ctrl+C zum Beenden")
        try:
            while True: pass
        except KeyboardInterrupt:
            print("\n🛑 Server gestoppt")
    elif cmd == "act":
        run_act()
    else:
        print(f"❌ Unbekannter Befehl: {cmd}")

if __name__ == "__main__":
    main()
