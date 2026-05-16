"""
Oracle v2 - Setup Wizard
Standalone GUI for editing options.ini — no bot refactoring needed.
Modernized with a Sidebar Navigation and sleek dark theme.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os

# ─── Paths ───
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OPTIONS_PATH = os.path.join(SCRIPT_DIR, "options.ini")

# ─── Modern Color Palette ───
BG_MAIN       = "#121212"
BG_SIDEBAR    = "#1e1e1e"
BG_CARD       = "#242424"
BG_INPUT      = "#2d2d2d"
FG_TEXT       = "#ffffff"
FG_DIM        = "#a0a0a0"
ACCENT        = "#bb86fc"
ACCENT_HOVER  = "#dfb8ff"
SUCCESS       = "#03dac6"
DANGER        = "#cf6679"
BORDER        = "#333333"
TOGGLE_ON     = "#03dac6"
TOGGLE_OFF    = "#555555"

# ─── Field Definitions ───
FIELD_SECTIONS = [
    ("🔑 Credentials", [
        ("user_token",           "User Token",           "password", "",                "Your Discord user token (keep secret!)"),
        ("user_mention_text",    "User Mention Text",    "text",     "<@0>",            "Your Discord mention (e.g. <@123456789>)"),
        ("channel_id",           "Channel ID",           "text",     "0",               "Discord channel ID where the bot operates"),
        ("guild_id",             "Guild (Server) ID",    "text",     "0",               "Server ID — use a private server!"),
    ]),
    ("⚙️ General", [
        ("random_interval",      "Random Intervals",     "bool",     "true",            "Add 1-4s random delay between commands"),
        ("typo_chance",          "Typo Chance",          "text",     "0.05",            "Probability of simulated typos (0.0 - 1.0)"),
    ]),
    ("⚔️ Adventure", [
        ("life_boost_before_adv","Life Boost Before Adv","dropdown", "none",            "Heal before adventure", ["none", "a", "b", "c"]),
        ("adventure_area",       "Adventure Area",       "dropdown", "none",            "Lower area for less damage", ["none"] + [str(i) for i in range(1, 22)]),
        ("current_area",         "Current Area",         "dropdown", "none",            "Your current area (for event recovery)", ["none"] + [str(i) for i in range(1, 22)]),
        ("zombie_horde_event_response", "Zombie Horde Response", "dropdown", "fight",   "What to do during zombie events", ["fight", "join", "cry"]),
    ]),
    ("🌾 Economy", [
        ("lootbox_type",         "Lootbox Type",         "dropdown", "ed lb",           "Which lootbox to buy", ["ed lb", "ep lb", "rare lb", "uncommon lb", "common lb"]),
        ("seed",                 "Farm Seed",            "dropdown", "carrot",          "Which seed to plant", ["carrot", "potato", "bread"]),
        ("work_command",         "Work Command",         "dropdown", "chainsaw",        "Work tool to use", ["chainsaw", "pickaxe", "bigboat", "greenhouse", "axe", "net", "pickup"]),
        ("bankroll",             "Bankroll",             "text",     "1000000000000",   "Your maximum money amount"),
        ("max_losses",           "Max Losses",           "text",     "20",              "Max consecutive losses (recommended 15-30)"),
        ("initial_step",         "Initial Step",         "text",     "1",               "Starting step for strategy (recommended 1-3)"),
    ]),
    ("📱 Telegram", [
        ("telegram_bot_token",   "Bot Token",            "text",     "",                "Get this from @BotFather on Telegram (optional)"),
        ("telegram_chat_id",     "Chat ID",              "text",     "",                "Your Telegram chat ID (optional)"),
    ]),
    ("✅ Features", [
        ("do_hunt",              "Hunt",                 "bool",     "true",            "Enable automatic hunting"),
        ("do_adv",               "Adventure",            "bool",     "true",            "Enable automatic adventures"),
        ("do_farm",              "Farm",                 "bool",     "true",            "Enable automatic farming"),
        ("do_work",              "Work",                 "bool",     "true",            "Enable automatic work"),
        ("do_training",          "Training",             "bool",     "true",            "Enable automatic training"),
        ("do_daily",             "Daily",                "bool",     "true",            "Enable automatic daily claim"),
        ("do_weekly",            "Weekly",               "bool",     "true",            "Enable automatic weekly claim"),
        ("do_quest",             "Quest",                "bool",     "true",            "Enable automatic questing"),
        ("do_lootbox",           "Lootbox",              "bool",     "true",            "Enable automatic lootbox buying"),
        ("do_dungeon",           "Dungeon",              "bool",     "true",            "Enable automatic dungeon"),
        ("do_card_hand",         "Card Hand",            "bool",     "true",            "Enable card hand minigame"),
    ]),
    ("🧪 Advanced", [
        ("do_ultr",              "ULTR Mode",            "bool",     "false",           "Overrides training: rpg ultr → double → attack → rpg use tc"),
        ("card_hand_action",     "Card Hand Action",     "dropdown", "auto",            "Auto-play or just notify", ["auto", "notify"]),
        ("tc_quantity",          "TC Quantity",           "text",     "1",               "Time capsules per use"),
        ("is_eternal",           "Eternal Mode",         "bool",     "false",           "Enable dungeon auto-enter + eternal dragon bite loop"),
        ("is_married",           "Married",              "bool",     "false",           "Enable married partner features"),
        ("partner_name",         "Partner Name",         "text",     "",                "In-game partner name (if married)"),
        ("is_ascended",          "Ascended",             "bool",     "false",           "Enable ascended-specific behavior"),
        ("admin_ids",            "Extra Admin IDs",      "text",     "",                "Comma-separated Discord IDs for admin access"),
        ("tc_stop_on",           "TC Stop Conditions",   "text",     "dungeon,miniboss","Comma-separated events that pause TC usage"),
    ]),
]


def load_existing_options(path):
    data = {}
    if not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                val = val.split("#")[0].strip()
                data[key.strip()] = val
    return data


def save_options(data, path):
    lines = []
    written_keys = set()
    for _, fields in FIELD_SECTIONS:
        for field in fields:
            key = field[0]
            val = data.get(key, field[3])
            comment = field[4]
            lines.append(f"{key}={val} #{comment}")
            written_keys.add(key)
            
    existing = load_existing_options(path)
    for key, val in existing.items():
        if key not in written_keys:
            lines.append(f"{key}={val}")
            
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify="left",
                         background=BG_CARD, foreground=FG_TEXT,
                         relief="solid", borderwidth=1,
                         font=("Segoe UI", 9), padx=8, pady=4)
        label.pack()

    def hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class ToggleSwitch(tk.Canvas):
    def __init__(self, parent, variable, **kwargs):
        super().__init__(parent, width=44, height=22, bg=BG_MAIN,
                         highlightthickness=0, **kwargs)
        self.variable = variable
        self.on = variable.get().lower() == "true"
        self.draw()
        self.bind("<Button-1>", self.toggle)
        self.bind("<Enter>", lambda e: self.config(cursor="hand2"))

    def draw(self):
        self.delete("all")
        bg = TOGGLE_ON if self.on else TOGGLE_OFF
        self.create_rounded_rect(2, 2, 42, 20, 10, fill=bg, outline="")
        knob_x = 24 if self.on else 4
        self.create_oval(knob_x, 4, knob_x + 16, 20, fill="#ffffff", outline="")

    def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
            x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r, x1, y1+r, x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def toggle(self, event=None):
        self.on = not self.on
        self.variable.set("true" if self.on else "false")
        self.draw()


class SetupWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Oracle v2 Configuration")
        self.geometry("900x650")
        self.minsize(800, 500)
        self.configure(bg=BG_MAIN)
        try:
            self.iconname("Oracle v2")
        except:
            pass

        self.widgets = {}
        self.existing = load_existing_options(OPTIONS_PATH)
        self.frames = {}
        self.current_frame = None

        self._build_layout()
        if FIELD_SECTIONS:
            self._show_section(FIELD_SECTIONS[0][0])

    def _build_layout(self):
        # Top Bar
        top_bar = tk.Frame(self, bg=BG_SIDEBAR, height=60)
        top_bar.pack(side="top", fill="x")
        top_bar.pack_propagate(False)

        title = tk.Label(top_bar, text="🔮 Oracle v2 Settings", font=("Segoe UI", 16, "bold"),
                         bg=BG_SIDEBAR, fg=ACCENT)
        title.pack(side="left", padx=20, pady=15)

        self.status_var = tk.StringVar()
        status_lbl = tk.Label(top_bar, textvariable=self.status_var, font=("Segoe UI", 10),
                              bg=BG_SIDEBAR, fg=SUCCESS)
        status_lbl.pack(side="right", padx=20)

        # Main Content Area
        content_area = tk.Frame(self, bg=BG_MAIN)
        content_area.pack(side="top", fill="both", expand=True)

        # Sidebar
        self.sidebar = tk.Frame(content_area, bg=BG_SIDEBAR, width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Content Frame
        self.main_content = tk.Frame(content_area, bg=BG_MAIN)
        self.main_content.pack(side="left", fill="both", expand=True, padx=30, pady=20)

        # Bottom Bar
        bottom_bar = tk.Frame(self, bg=BG_SIDEBAR, height=60)
        bottom_bar.pack(side="bottom", fill="x")
        bottom_bar.pack_propagate(False)

        save_btn = tk.Button(bottom_bar, text="💾 Save Config", font=("Segoe UI", 11, "bold"),
                             bg=ACCENT, fg="#000", activebackground=ACCENT_HOVER,
                             relief="flat", cursor="hand2", padx=20, command=self._save)
        save_btn.pack(side="right", padx=20, pady=12)

        load_btn = tk.Button(bottom_bar, text="📂 Load", font=("Segoe UI", 10),
                             bg=BG_CARD, fg=FG_TEXT, activebackground=BG_INPUT,
                             relief="flat", cursor="hand2", padx=15, command=self._load)
        load_btn.pack(side="right", padx=10, pady=12)

        reset_btn = tk.Button(bottom_bar, text="🔄 Reset Defaults", font=("Segoe UI", 10),
                              bg=BG_CARD, fg=DANGER, activebackground=BG_INPUT,
                              relief="flat", cursor="hand2", padx=15, command=self._reset)
        reset_btn.pack(side="left", padx=20, pady=12)

        # Build Navigation & Sections
        self.nav_buttons = {}
        for section_title, fields in FIELD_SECTIONS:
            btn = tk.Button(self.sidebar, text=section_title, font=("Segoe UI", 11),
                            bg=BG_SIDEBAR, fg=FG_DIM, activebackground=BG_CARD, activeforeground=FG_TEXT,
                            relief="flat", anchor="w", padx=20, pady=12, cursor="hand2",
                            command=lambda t=section_title: self._show_section(t))
            btn.pack(fill="x")
            self.nav_buttons[section_title] = btn

            # Create Section Frame
            frame = tk.Frame(self.main_content, bg=BG_MAIN)
            self.frames[section_title] = frame
            self._build_section(frame, section_title, fields)

    def _show_section(self, section_title):
        if self.current_frame:
            self.current_frame.pack_forget()
        
        # Update Nav Buttons
        for t, btn in self.nav_buttons.items():
            if t == section_title:
                btn.config(bg=BG_CARD, fg=ACCENT, font=("Segoe UI", 11, "bold"))
            else:
                btn.config(bg=BG_SIDEBAR, fg=FG_DIM, font=("Segoe UI", 11))

        self.current_frame = self.frames[section_title]
        self.current_frame.pack(fill="both", expand=True)

    def _build_section(self, parent, title, fields):
        lbl = tk.Label(parent, text=title, font=("Segoe UI", 18, "bold"), bg=BG_MAIN, fg=FG_TEXT)
        lbl.pack(anchor="w", pady=(0, 20))

        # Canvas for scrolling if needed
        canvas = tk.Canvas(parent, bg=BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG_MAIN)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=550)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        def _on_mousewheel_linux(event):
            if event.num == 4: canvas.yview_scroll(-3, "units")
            elif event.num == 5: canvas.yview_scroll(3, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel_linux)
        canvas.bind_all("<Button-5>", _on_mousewheel_linux)

        for i, field in enumerate(fields):
            key, label, ftype, default, tooltip = field[:5]
            options = field[5] if len(field) > 5 else None
            value = self.existing.get(key, default)

            row = tk.Frame(scroll_frame, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
            row.pack(fill="x", pady=5, padx=5, ipady=5)

            lbl = tk.Label(row, text=label, font=("Segoe UI", 11), bg=BG_CARD, fg=FG_TEXT, width=22, anchor="w")
            lbl.pack(side="left", padx=15)
            ToolTip(lbl, tooltip)

            if ftype == "bool":
                var = tk.StringVar(value=value)
                toggle = ToggleSwitch(row, var)
                toggle.pack(side="right", padx=15)
                self.widgets[key] = var

            elif ftype == "dropdown":
                var = tk.StringVar(value=value)
                combo = ttk.Combobox(row, textvariable=var, values=options, state="readonly", width=25, font=("Segoe UI", 10))
                combo.pack(side="right", padx=15)
                self.widgets[key] = var

            elif ftype == "password":
                var = tk.StringVar(value=value)
                entry = tk.Entry(row, textvariable=var, show="•", font=("Consolas", 11),
                                 bg=BG_INPUT, fg=FG_TEXT, insertbackground=FG_TEXT,
                                 relief="flat", highlightthickness=0, width=25)
                entry.pack(side="right", padx=15)
                self.widgets[key] = var
                
            else:
                var = tk.StringVar(value=value)
                entry = tk.Entry(row, textvariable=var, font=("Consolas", 11),
                                 bg=BG_INPUT, fg=FG_TEXT, insertbackground=FG_TEXT,
                                 relief="flat", highlightthickness=0, width=25)
                entry.pack(side="right", padx=15)
                self.widgets[key] = var

            info = tk.Label(row, text="❔", font=("Segoe UI", 10), bg=BG_CARD, fg=ACCENT, cursor="hand2")
            info.pack(side="left", padx=0)
            ToolTip(info, tooltip)

    def _save(self):
        data = {k: v.get() for k, v in self.widgets.items()}
        errors = []
        if not data.get("user_token", "").strip(): errors.append("User Token is required")
        if not data.get("channel_id", "0").strip().isdigit(): errors.append("Channel ID must be a number")
        if not data.get("guild_id", "0").strip().isdigit(): errors.append("Guild ID must be a number")

        if errors:
            messagebox.showwarning("Validation Error", "\n".join(errors))
            return

        try:
            save_options(data, OPTIONS_PATH)
            self.status_var.set(f"✅ Saved to {os.path.basename(OPTIONS_PATH)}")
            self.after(3000, lambda: self.status_var.set(""))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save:\n{e}")

    def _load(self):
        path = filedialog.askopenfilename(title="Open Config", filetypes=[("INI", "*.ini"), ("All", "*.*")], initialdir=SCRIPT_DIR)
        if not path: return
        loaded = load_existing_options(path)
        for k, v in self.widgets.items():
            if k in loaded: v.set(loaded[k])
        self.status_var.set("📂 Loaded config")
        self.after(3000, lambda: self.status_var.set(""))

    def _reset(self):
        if not messagebox.askyesno("Reset", "Reset all fields to default values?"): return
        for _, fields in FIELD_SECTIONS:
            for f in fields:
                if f[0] in self.widgets: self.widgets[f[0]].set(f[3])
        self.status_var.set("🔄 Reset to defaults")
        self.after(3000, lambda: self.status_var.set(""))

def main():
    app = SetupWizard()
    style = ttk.Style(app)
    style.theme_use("clam")
    style.configure("TCombobox", fieldbackground=BG_INPUT, background=BG_CARD, foreground=FG_TEXT, borderwidth=0, arrowcolor=ACCENT)
    style.map("TCombobox", fieldbackground=[("readonly", BG_INPUT)], foreground=[("readonly", FG_TEXT)])
    style.configure("Vertical.TScrollbar", background=BG_CARD, troughcolor=BG_MAIN, bordercolor=BG_MAIN, arrowcolor=ACCENT)
    app.mainloop()

if __name__ == "__main__":
    main()
