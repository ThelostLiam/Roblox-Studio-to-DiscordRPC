import os
import sys
import time
import psutil
from pypresence import Presence, DiscordNotFound, InvalidID
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading

# Windows GUI Control APIs
import ctypes
from PIL import Image, ImageDraw
import pystray

CLIENT_ID = "1087767029236383846"  # Replace with your actual Client ID

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

    def toggle_console(self, icon=None, item=None):
        if self.console_visible:
            user32.ShowWindow(hWnd, 0) # Hide
            self.console_visible = False
        else:
            user32.ShowWindow(hWnd, 5) # Show
            self.console_visible = True

    def disable_console_close_button(self):
        if hWnd:
            hMenu = user32.GetSystemMenu(hWnd, False)
            if hMenu:
                user32.EnableMenuItem(hMenu, 0xF060, 1 | 2)

    def is_studio_running(self):
        """Lightweight check for Studio process execution."""
        try:
            for proc in psutil.process_iter():
                if proc.name() == 'RobloxStudioBeta.exe':
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            pass
        return False

    def connect_rpc(self):
        try:
            self.rpc = Presence(self.client_id)
            self.rpc.connect()
            self.is_connected = True
            self.start_time = int(time.time())
            return True
        except (DiscordNotFound, InvalidID, ConnectionRefusedError, Exception):
            self.is_connected = False
            self.rpc = None
            return False

    def force_reconnect(self, icon=None, item=None):
        print("\n[RPC] Manually re-indexing active pipelines...")
        if self.rpc:
            try: self.rpc.clear()
            except: pass
        self.is_connected = False
        if self.connect_rpc():
            print("[RPC] Successfully reconnected to Discord!")
        else:
            print("[RPC] Failed to find Discord Client during manual reset.")

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
                    large_text="Roblox Studio"
                )
                print(f"[LIVE UPDATE] {details} | {state}")
            except:
                self.is_connected = False

    def monitor_lifecycle(self):
        while True:
            studio_active = self.is_studio_running()
            if not studio_active:
                if self.is_connected:
                    if self.rpc:
                        try: self.rpc.clear()
                        except: pass
                    self.is_connected = False
                    self.start_time = None
                    self.last_state = {"details": "", "state": ""}
            else:
                if time.time() - self.last_plugin_heartbeat > 15:
                    self.update_presence("Browsing Projects", "Home Screen")
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
    def log_message(self, format, *args): return

def start_server():
    try:
        server = HTTPServer(('127.0.0.1', 3000), RequestHandler)
        server.serve_forever()
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Internal server port 3000 failed: {e}")

def create_tray_image():
    image = Image.new('RGB', (64, 64), color=(45, 45, 45))
    d = ImageDraw.Draw(image)
    d.rectangle([(16, 16), (48, 48)], fill=(255, 115, 0))
    d.rectangle([(24, 24), (40, 40)], fill=(0, 162, 255))
    return image

def exit_action(icon, item):
    if manager.rpc:
        try: manager.rpc.clear()
        except: pass
    icon.stop()
    os._exit(0)

def run_diagnostic_checklist():
    print("==================================================")
    print("      Roblox Studio Discord Presence Bootloader   ")
    print("==================================================")
    
    # 1. Check for Discord in absolute isolation (Instant)
    print("Looking for Discord Client...")
    
    if not manager.connect_rpc():
        print("\n[ERROR] Failed to find Discord Client, please restart the program to try again!")
        print("👉 Make sure your Discord Desktop app is open and running in the background.")
        print("\n[STATUS] App will remain open in error mode. Do not close.")
        return False
        
    print("[SUCCESS] Discord Client found and synced!")
    print("--------------------------------------------------")
    
    # 2. Check for Roblox Studio
    print("Looking for Roblox Studio...")
    
    if not manager.is_studio_running():
        print("[INFO] Roblox Studio is not running yet.")
        print("👉 The app will hide and monitor your PC. Presence will load the second you open Studio!")
    else:
        print("[SUCCESS] Roblox Studio process detected!")
        print("--------------------------------------------------")
        # 3. Check for the Roblox Lua Plugin data stream
        print("Checking for Roblox Studio Plugin heartbeat...")
        print("(Please open a script or select an item in Studio to generate data...)")
        
        plugin_found = False
        for _ in range(4):
            if time.time() - manager.last_plugin_heartbeat < 3:
                plugin_found = True
                break
            time.sleep(1)
            
        if not plugin_found:
            print("\n⚠️  WARNING: Could not detect your Roblox Studio Lua Plugin!")
            print("👉 Error: No data received on local port 3000.")
            print("👉 Fix: Save the script as a Local Plugin in Studio and allow HTTP Requests.")
        else:
            print("[SUCCESS] Roblox Studio Plugin connected successfully!")
        
    print("\n[SYSTEM] All initial checks completed.")
    print("[SYSTEM] Minimizing console window to system tray in 5 seconds...")
    
    time.sleep(5)
    user32.ShowWindow(hWnd, 0)
    manager.console_visible = False
    
    # CRITICAL FIX: Background monitoring loops spin up ONLY after boot finishes!
    threading.Thread(target=manager.monitor_lifecycle, daemon=True).start()
    threading.Thread(target=start_server, daemon=True).start()
    return True

def init_tray():
    icon = pystray.Icon("RobloxStudioRPC")
    icon.icon = create_tray_image()
    icon.title = "Roblox Studio Discord Rich Presence"
    
    icon.menu = pystray.Menu(
        pystray.MenuItem("Show/Hide Console Terminal", manager.toggle_console),
        pystray.MenuItem("Force Restart Connection", manager.force_reconnect),
        pystray.MenuItem("Exit Daemon", exit_action)
    )
    
    manager.disable_console_close_button()
    threading.Thread(target=run_diagnostic_checklist, daemon=True).start()
    icon.run()

if __name__ == "__main__":
    # Main thread kicks off the application sequence cleanly
    init_tray()