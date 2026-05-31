import os
import sys
import time
import json
import threading
import subprocess
import urllib.request
import psutil
from pypresence import Presence, DiscordNotFound, InvalidID
from http.server import BaseHTTPRequestHandler, HTTPServer

# Windows Native GUI & Image Processing Imports
import ctypes
from PIL import Image, ImageDraw
import pystray

CURRENT_VERSION = "v1.0.1"
CLIENT_ID = "1087767029236383846"
REPO_URI = "ThelostLiam/Roblox-Studio-to-DiscordRPC"

# Windows Native Handle Initializations
kernel32 = ctypes.WinDLL('kernel32')
user32 = ctypes.WinDLL('user32')
hWnd = kernel32.GetConsoleWindow()

class StudioRPCManager:
    def __init__(self, client_id):
        self.client_id = client_id
        self.rpc = None
        self.is_connected = False
        self.start_time = None
        self.last_state = {"details": "", "state": ""}
        self.last_plugin_heartbeat = 0
        self.console_visible = True
        self.is_afk = False

    def toggle_console(self, icon=None, item=None):
        if self.console_visible:
            user32.ShowWindow(hWnd, 0)
            self.console_visible = False
        else:
            user32.ShowWindow(hWnd, 5)
            self.console_visible = True

    def disable_console_close_button(self):
        if hWnd:
            hMenu = user32.GetSystemMenu(hWnd, False)
            if hMenu:
                user32.EnableMenuItem(hMenu, 0xF060, 1 | 2)

    def is_studio_running(self):
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == 'RobloxStudioBeta.exe':
                    return True
        except Exception:
            pass
        return False

    def connect_rpc(self):
        try:
            self.rpc = Presence(self.client_id)
            self.rpc.connect()
            self.is_connected = True
            self.start_time = int(time.time())
            return True
        except Exception as e:
            print(f"[ERROR] Connection handshake failed: {type(e).__name__}")
            self.is_connected = False
            self.rpc = None
            return False

    def force_reconnect(self, icon=None, item=None):
        print("\n[RPC] Manually re-indexing active pipelines...")
        if self.rpc:
            try: 
                self.rpc.clear()
            except Exception: 
                pass
        self.is_connected = False
        if self.connect_rpc():
            print("[SUCCESS] Reconnected to Discord system pipes successfully!")
        else:
            print("[ERROR] Failed to locate Discord Client process during manual override reset.")

    def update_presence(self, details, state):
        if not self.is_connected and not self.connect_rpc():
            return
        
        if self.last_state["details"] != details or self.last_state["state"] != state:
            self.last_state = {"details": details, "state": state}
            try:
                self.rpc.update(
                    details=details,
                    state=state,
                    start=self.start_time,
                    large_image="studio_logo",
                    large_text="Roblox Studio Sync"
                )
                print(f"[LIVE UPDATE] {details} | {state}")
            except Exception as e:
                print(f"[ERROR] Discord connection snapped: {e}")
                self.is_connected = False

    def monitor_lifecycle(self):
        while True:
            studio_active = self.is_studio_running()
            current_time = time.time()

            if not studio_active:
                if self.is_connected:
                    if self.rpc:
                        try: self.rpc.clear()
                        except: pass
                    self.is_connected = False
                    self.start_time = None
                    self.last_state = {"details": "", "state": ""}
            else:
                # Smart AFK Engine (120-second timeout tracking)
                if current_time - self.last_plugin_heartbeat > 120:
                    if not self.is_afk:
                        print("[SYSTEM] Idle state triggered. Shifting profile to AFK...")
                        self.is_afk = True
                    self.update_presence("Idling", "Away From Keyboard")
                else:
                    self.is_afk = False

            time.sleep(5)

manager = StudioRPCManager(CLIENT_ID)

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/update':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            manager.last_plugin_heartbeat = time.time()
            manager.update_presence(data.get('details'), data.get('state'))
            
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
            
    def log_message(self, format, *args): 
        pass

def run_auto_updater():
    print("Checking for newest software definitions on GitHub...")
    url = f"https://api.github.com/repos/{REPO_URI}/releases/latest"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                latest_tag = data.get("tag_name", CURRENT_VERSION)
                
                if latest_tag != CURRENT_VERSION:
                    print(f"\n📢 New version detected: {latest_tag} (Current: {CURRENT_VERSION})")
                    download_url = None
                    for asset in data.get("assets", []):
                        if asset.get("name", "").endswith(".exe"):
                            download_url = asset.get("browser_download_url")
                            break
                    
                    if download_url:
                        print("⚡ Pulling deployment binary from GitHub CDN mirrors...")
                        new_filename = f"Studio_Status_Syncer_{latest_tag}.exe"
                        
                        update_req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(update_req) as download_stream:
                            with open(new_filename, 'wb') as out_file:
                                out_file.write(download_stream.read())
                        
                        print(f"✅ Update downloaded successfully: {new_filename}")
                        print("🚀 Launching new version and hot-swapping process pointers...")
                        time.sleep(2)
                        
                        subprocess.Popen([new_filename], creationflags=subprocess.CREATE_NEW_CONSOLE)
                        if manager.rpc:
                            try: manager.rpc.clear()
                            except: pass
                        os._exit(0)
                    else:
                        print("⚠️ Update found, but no direct executable file asset was listed in the GitHub release layout map.")
                else:
                    print(f"[SUCCESS] App version matches stable branch release ({CURRENT_VERSION})")
    except Exception as e:
        print(f"[NOTICE] Update server connectivity check bypassed or rate-limited: {e}")

def start_server():
    try:
        server = HTTPServer(('127.0.0.1', 3000), RequestHandler)
        server.serve_forever()
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Internal server socket port 3000 failed to bind: {e}")

def create_tray_image():
    image = Image.new('RGB', (64, 64), color=(45, 45, 45))
    d = ImageDraw.Draw(image)
    d.rectangle([(16, 16), (48, 48)], fill=(0, 162, 255))
    d.rectangle([(24, 24), (40, 40)], fill=(255, 115, 0))
    return image

def exit_action(icon, item):
    if manager.rpc:
        try: manager.rpc.clear()
        except: pass
    icon.stop()
    os._exit(0)

def run_diagnostic_checklist():
    print("==================================================")
    print(f"      Studio Status Syncer Bootloader ({CURRENT_VERSION})  ")
    print("==================================================")
    
    run_auto_updater()
    print("--------------------------------------------------")
    
    print("Looking for Discord Client...")
    if not manager.connect_rpc():
        print("\n[ERROR] Failed to locate or establish handshakes with active Discord Client system pipelines!")
        print("👉 Verification steps: Ensure Discord Desktop app is fully loaded and running in the background.")
        return False
        
    print("[SUCCESS] Discord Client found and synced!")
    print("--------------------------------------------------")
    
    print("Looking for Roblox Studio...")
    if not manager.is_studio_running():
        print("[INFO] Roblox Studio is not running yet. Monitoring system processes silently...")
    else:
        print("[SUCCESS] Roblox Studio process detected!")
        
    print("\n[SYSTEM] Minimizing console window to system tray in 5 seconds...")
    time.sleep(5)
    
    user32.ShowWindow(hWnd, 0)
    manager.console_visible = False
    manager.last_plugin_heartbeat = time.time()
    
    threading.Thread(target=manager.monitor_lifecycle, daemon=True).start()
    threading.Thread(target=start_server, daemon=True).start()
    return True

def init_tray():
    icon = pystray.Icon("StudioStatusSyncer")
    icon.icon = create_tray_image()
    icon.title = f"Studio Status Syncer {CURRENT_VERSION}"
    icon.menu = pystray.Menu(
        pystray.MenuItem("Show/Hide Console Terminal", manager.toggle_console),
        pystray.MenuItem("Force Restart Connection", manager.force_reconnect),
        pystray.MenuItem("Exit Daemon", exit_action)
    )
    manager.disable_console_close_button()
    threading.Thread(target=run_diagnostic_checklist, daemon=True).start()
    icon.run()

if __name__ == "__main__":
    init_tray()
