<!-- BANNER ANIMADO -->
<p align="center">
  <img src="docs/banner.svg" alt="Oracle v3 Banner" width="100%" style="border-radius: 8px; border: 1px solid rgba(168, 85, 247, 0.15);" />
</p>

<!-- TECH BADGES MINIMALISTAS -->
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-black?style=flat-square&logo=python&logoColor=3776AB&labelColor=050202" alt="Python" />
  <img src="https://img.shields.io/badge/TensorFlow_Lite-2.17-black?style=flat-square&logo=tensorflow&logoColor=FF6F00&labelColor=050202" alt="TensorFlow Lite" />
  <img src="https://img.shields.io/badge/Textual-TUI-black?style=flat-square&logo=terminal&logoColor=white&labelColor=050202" alt="Textual TUI" />
  <img src="https://img.shields.io/badge/FastAPI-0.111-black?style=flat-square&logo=fastapi&logoColor=009688&labelColor=050202" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-19-black?style=flat-square&logo=react&logoColor=61DAFB&labelColor=050202" alt="React" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-v4.0-black?style=flat-square&logo=tailwindcss&logoColor=38BDF8&labelColor=050202" alt="Tailwind CSS" />
  <img src="https://img.shields.io/badge/Discord.py--self-v2.0-black?style=flat-square&logo=discord&logoColor=5865F2&labelColor=050202" alt="Discord.py-self" />
</p>

---

> [!NOTE]
> 🇧🇷 **Para ler a documentação em Português, acesse: [README.pt-BR.md](docs/README.pt-BR.md).**

---

## Overview

**Oracle v3** is a state-of-the-art automation suite for Epic RPG. Designed with stealth, scalability, and ease of use in mind, it integrates a convolutional neural network (CNN) via TensorFlow Lite to solve captchas dynamically, features an anti-detection layer simulating human behaviors, and introduces a dual-interface system containing an interactive console **Terminal User Interface (TUI)** and a premium web-based **Control Dashboard**.

---

## Architecture and Data Flow

The diagram below illustrates the live data loop and interaction flow between the Discord websocket gateway, the automation state machine, and the local AI processing pipeline:

<p align="center">
  <img src="docs/architecture.svg" alt="Oracle v3 Data Flow Architecture" width="100%" style="border-radius: 8px; border: 1px solid rgba(168, 85, 247, 0.08);" />
</p>

### The Automation & AI Lifecycle

1. **Gateway Listening**: The bot establishes a secure websocket stream with Discord using `discord.py-self` to intercept incoming messages and events.
2. **State Monitoring**: The Parser monitors cool-downs and events. When a command is triggered, it enqueues actions into a priority queue.
3. **AI Captcha Solving**: If the game prompts a captcha verification, the bot isolates the raw image, crops it, and runs it through a local **TensorFlow Lite** CNN model to instantly predict symbols and solve the lock.
4. **Telemetry Broadcast**: The FastAPI server streams real-time execution statistics, logs, and state changes to the React Web Dashboard and the local Textual TUI.
5. **Human Shield Layer**: Every outbound action is evaluated by the humanization engine, which appends randomized micro-delays, schedules organic coffee breaks, and enforces nightly sleep cycles to avoid platform flags.

---

## Architectural Components and Technologies

The following table presents the technical details and responsibilities of each module within the ecosystem:

| Module / Component | Technologies Used | Role in the System |
| :--- | :--- | :--- |
| **Automation Core (Bot)** | Python 3.12, discord.py-self, asyncio, Textual | Manages bot states, websocket listeners, priority command enqueuing, and local configuration reloading. |
| **AI Captcha Engine** | TensorFlow Lite, OpenCV, NumPy | Automates image preprocessing, crop segmentation, and CNN classification to solve the Epic Guard captcha. |
| **Terminal Console (TUI)** | Textual, Rich | A console-based terminal interface featuring dynamic telemetry, mascot animations, theme selectors, and an autocomplete CLI. |
| **Dashboard Backend** | FastAPI, Uvicorn, WebSockets | Exposes API endpoints and live websocket feeds to pipe stats, manage configurations (`options.ini`), and switch profiles. |
| **Dashboard Frontend** | React 19, Vite, Tailwind CSS v4, Zustand | Premium glassmorphic web app that acts as a remote dashboard control room with integrated mini-terminal. |
| **Build & Setup Wrappers** | PyInstaller, Inno Setup, Bash Shell | Bundles dependencies, generates standalone Windows `.exe` installers, and installs global terminal command shortcuts. |

---

## How to Get Started

### Prerequisites
* **Python 3.11 or 3.12**
* **Node.js v20+** (only required if building/modifying the React frontend)
* **Discord Account Token**
* **Telegram Bot Token** (optional, for remote notifications)

<details>
<summary><b>1. Create and Activate Virtual Environment</b></summary>
<br />

Create a virtual environment (`venv`) to isolate python packages:

```bash
# Create the environment:
python3 -m venv venv

# Activate on Linux/macOS:
source venv/bin/activate

# Activate on Windows:
venv\Scripts\activate
```
</details>

<details>
<summary><b>2. Install Dependencies</b></summary>
<br />

Install core dependencies and upgrade pip package manager:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```
</details>

<details>
<summary><b>3. Configure Settings</b></summary>
<br />

Rename the options example file to `options.ini` and edit it with your discord token, telegram notifications, and target macros:

```bash
cp options_example.ini options.ini
```
*Open `options.ini` in any editor to customize your credentials and cooldown variables.*
</details>

<details>
<summary><b>4. Run the Bot (Console TUI)</b></summary>
<br />

Start the classic Textual terminal user interface:

```bash
python main.py
```
</details>

<details>
<summary><b>5. Run the Web Dashboard (Desktop App)</b></summary>
<br />

Launch the FastAPI backend server and default controller app:

```bash
python launch_dashboard.py
```
*(Note: Ensure the compiled frontend is present in `dashboard/dist`. Otherwise, compile it using the instructions below).*
</details>

<details>
<summary><b>6. Compiling Frontend & Building Executables (Optional)</b></summary>
<br />

If you modify the Dashboard or want to package a standalone Windows Installer:

**Compile the React frontend:**
```bash
cd dashboard
npm install
npm run build
cd ..
```

**Generate Windows executable (.exe):**
```bash
python build_windows.py
```
</details>

<details>
<summary><b>7. Setup Global CLI Shortcut (Linux/macOS - Optional)</b></summary>
<br />

Install the `oracle` command globally:

```bash
chmod +x setup.sh && ./setup.sh
source ~/.bashrc  # or ~/.zshrc
```
After setup, run the macro from any directory by typing:
```bash
oracle
```
</details>

---

## Repository Structure

```path
Oracle-V2/
├── bot/              # Python automation core, handlers, and TUI implementation
├── dashboard/        # React Web Dashboard (Vite, Tailwind, CSS)
├── docs/             # Visual documentation resources and diagrams
│   ├── banner.svg    # High-tech animated project banner
│   └── architecture.svg # System architecture and data flow diagram
├── requirements.txt  # Python package dependencies
├── main.py           # Application entry point (TUI launcher)
├── launch_dashboard.py # Dashboard web server launcher
├── build_windows.py  # Automation script for building portable EXE wrappers
└── setup.sh          # Global terminal shortcut setup script
```

---

## CLI & Discord Commands

You can interact with Oracle using the TUI console CLI, the Dashboard mini-terminal, or directly via Discord chat (restricted to configured administrators):

| Command | Description |
| :--- | :--- |
| **`help`** / **`/help`** | Shows the keyboard shortcut modal and lists all commands. |
| **`start`** / **`resume`** | Starts or resumes the automation loops. |
| **`pause`** / **`stop`** | Pauses all active automation tasks. |
| **`reset`** | Resets command queues, cooldowns, and internal states. |
| **`stats [range]`** | Shows session telemetry metrics (e.g. `stats 1h`, `stats 30m`). |
| **`queue`** | Displays the current size and items in priority queues. |
| **`say <message>`** | Sends a custom message or raw command directly to the current channel. |
| **`tc start [c] [m]`** | Triggers Time Cookie mode (e.g. `tc start 4c 60m`). |
| **`tc stop`** | Disables Time Cookie mode. |
| **`g start`** | Activates the Fibonacci strategy coinflip/gambling macro. |
| **`g pause`** / **`g stop`** | Pauses or stops gambling tasks. |
| **`sleepet start`** | Activates the Pet Adventure loops (focuses on pet rescue tasks). |
| **`sleepet stop`** | Deactivates Pet Adventure mode and restores normal queue cycles. |
| **`<enchant/refine/transmute/transcend> <a/s> <enchant_name>`** | Automatically rolls weapon (`s`) or armor (`a`) enchantments until matching target level (e.g. `refine s godly`). |
| **`<enchant/refine/transmute/transcend> stop`** | Halts the active auto-enchant loop. |
| **`export [ini/txt]`** | Exports your current `options.ini` profile as a Discord message attachment. |
| **`log`** | Uploads the active session log file (up to 5MB). |
| **`cfg <key> <value>`** | Modifies any configuration variable on the fly and writes to `options.ini` (e.g. `cfg do_hunt false`). |
| **`theme`** | Opens the visual theme selector overlay in the TUI. |
| **`exit`** / **`quit`** | Safely terminates the bot process and UI. |

### Discord Chat Uptime & UIs Shortcuts
If typing from the authorized main Discord account inside the bot's channel:
* **`rpg s`**: Prints current session metrics locally in the logs.
* **`rpg s t`**: Sends session metrics directly to the Discord channel.
* **`rpg s p`**: Prints marriage partner metrics locally in the logs.
* **`rpg u`**: Prints bot Uptime locally in the logs.
* **`rpg u t`**: Sends bot Uptime directly to the Discord channel.

---

## Security & Best Practices

To safeguard your accounts from platform-level analysis:
* **Organic Interaction**: Do not leave the account solely automated. Occasionally message friends, join channels, and use regular Discord client features.
* **Residential IP Ranges**: Do not host the bot on major VPS providers (AWS, Google Cloud, DigitalOcean). Run it on residential internet connections or mobile hotspots.
* **Coffee Breaks**: Do not disable the built-in periodic breaks (5-15 minutes of random idling every 1-2 hours).
* **Sleep Mode**: Configure the daily Night Sleep window (`night_sleep`) to disconnect the bot during standard sleeping hours.
* **Telegram Alerts**: Always keep Telegram alerts active so you can immediately respond to manual captcha prompts if the AI solver is unsure.

---

## Disclaimer
Using self-bots violates the Discord Terms of Service. This software is designed for educational and research purposes only. The creators hold no responsibility for bans or suspensions incurred. Use at your own discretion.

---

## License

This project is open-source and licensed under the terms of the [MIT License](LICENSE). Feel free to inspect, study, adapt, and build upon it.
