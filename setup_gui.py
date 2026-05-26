"""
Oracle v2 - Assistente de Configuração
GUI independente para editar o arquivo options.ini.
Modernizado com navegação lateral e um tema escuro elegante.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os

# ─── Caminhos ───
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OPTIONS_PATH = os.path.join(SCRIPT_DIR, "options.ini")

# ─── Paleta de Cores Moderna ───
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

# ─── Definições de Campos ───
FIELD_SECTIONS = [
    ("🔑 Credenciais", [
        ("user_token",           "Token do Usuário",     "password", "",                "Seu token de usuário do Discord (mantenha em segredo!)"),
        ("user_mention_text",    "Texto de Menção",      "text",     "<@0>",            "Sua menção do Discord (ex: <@123456789>)"),
        ("channel_id",           "ID do Canal",          "text",     "0",               "ID do canal do Discord onde o bot opera"),
        ("guild_id",             "ID do Servidor",       "text",     "0",               "ID do servidor (Guild) — use um servidor privado!"),
    ]),
    ("⚙️ Geral", [
        ("random_interval",      "Intervalos Aleatórios", "bool",     "true",            "Adiciona atraso aleatório de 1 a 4s entre os comandos"),
        ("typo_chance",          "Chance de Digitação",  "text",     "0.05",            "Probabilidade de simular erro de digitação (0.0 - 1.0)"),
    ]),
    ("⚔️ Adventure", [
        ("life_boost_before_adv","Life Boost antes de Adv","dropdown", "none",           "Comprar poção de vida antes de ir na aventura", ["none", "a", "b", "c"]),
        ("adventure_area",       "Adventure Area",       "dropdown", "none",            "Ir para área menor antes de iniciar aventura para receber menos dano", ["none"] + [str(i) for i in range(1, 22)]),
        ("current_area",         "Current Area",         "dropdown", "none",            "Sua área atual (para recuperação de eventos)", ["none"] + [str(i) for i in range(1, 22)]),
        ("zombie_horde_event_response", "Zombie Horde Response", "dropdown", "fight",   "O que fazer durante eventos de horda de zumbis", ["fight", "join", "cry"]),
    ]),
    ("🌾 Economy", [
        ("lootbox_type",         "Lootbox Type",         "dropdown", "ed lb",           "Qual lootbox comprar automaticamente", ["ed lb", "ep lb", "rare lb", "uncommon lb", "common lb"]),
        ("seed",                 "Farm Seed",            "dropdown", "carrot",          "Qual semente plantar no comando farm", ["carrot", "potato", "bread"]),
        ("work_command",         "Work Command",         "dropdown", "chainsaw",        "Ferramenta/comando de trabalho a ser usado", ["chainsaw", "pickaxe", "bigboat", "greenhouse", "axe", "net", "pickup"]),
        ("bankroll",             "Bankroll",             "text",     "1000000000000",   "Seu valor máximo de moedas em mãos"),
        ("max_losses",           "Max Losses",           "text",     "20",              "Máximo de perdas consecutivas antes de parar (recomendado 15-30)"),
        ("initial_step",         "Initial Step",         "text",     "1",               "Passo inicial para estratégias (recomendado 1-3)"),
    ]),
    ("📱 Telegram", [
        ("telegram_bot_token",   "Token do Bot",         "text",     "",                "Obtenha com o @BotFather no Telegram (opcional)"),
        ("telegram_chat_id",     "ID do Chat",           "text",     "",                "Seu ID de chat do Telegram para receber alertas (opcional)"),
    ]),
    ("✅ Features", [
        ("do_hunt",              "Hunt",                 "bool",     "true",            "Habilitar Hunt automática"),
        ("do_adv",               "Adventure",            "bool",     "true",            "Habilitar aventura automática"),
        ("do_farm",              "Farm",                 "bool",     "true",            "Habilitar plantação automática"),
        ("do_work",              "Work",                 "bool",     "true",            "Habilitar trabalho automático"),
        ("do_training",          "Training",             "bool",     "true",            "Habilitar treino automático"),
        ("do_daily",             "Daily",                "bool",     "true",            "Habilitar resgate diário automático"),
        ("do_weekly",            "Weekly",               "bool",     "true",            "Habilitar resgate semanal automático"),
        ("do_quest",             "Quest",                "bool",     "true",            "Habilitar missões automáticas"),
        ("do_lootbox",           "Lootbox",              "bool",     "true",            "Habilitar compra automática de lootbox"),
        ("do_dungeon",           "Dungeon",              "bool",     "true",            "Habilitar masmorra automática"),
        ("do_card_hand",         "Card Hand",            "bool",     "true",            "Habilitar minijogo de mão de cartas"),
    ]),
    ("🧪 Advanced", [
        ("do_ultr",              "ULTR Mode",            "bool",     "false",           "Sobrescreve treino: rpg ultr → double → attack → rpg use tc"),
        ("card_hand_action",     "Card Hand Action",     "dropdown", "auto",            "Jogar cartas automaticamente ou apenas notificar", ["auto", "notify"]),
        ("tc_quantity",          "TC Quantity",          "text",     "1",               "Quantidade de cápsulas de tempo (TC) por uso"),
        ("is_eternal",           "Eternal Mode",         "bool",     "false",           "Habilitar entrar em masmorras + loop eterno de dragon bite"),
        ("is_married",           "Married",              "bool",     "false",           "Habilitar funcionalidades de parceiro(a) casado"),
        ("partner_name",         "Partner Name",         "text",     "",                "Nome do parceiro(a) no jogo (se casado)"),
        ("is_ascended",          "Ascended",             "bool",     "false",           "Habilitar comportamento específico de jogador ascendido"),
        ("admin_ids",            "Extra Admin IDs",      "text",     "",                "IDs de Discord separados por vírgula para controle remoto administrativo"),
        ("tc_stop_on",           "TC Stop Conditions",   "text",     "dungeon,miniboss","Eventos separados por vírgula que pausam o uso de TC"),
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
        self.title("Configuração do Oracle v2")
        self.geometry("950x650")
        self.minsize(850, 500)
        self.configure(bg=BG_MAIN)
        try:
            self.iconname("Oracle v2")
        except:
            pass

        self.widgets = {}
        self.active_profile_path = OPTIONS_PATH
        self.existing = load_existing_options(self.active_profile_path)
        self.frames = {}
        self.current_frame = None

        self._build_layout()
        self._refresh_profiles()
        if FIELD_SECTIONS:
            self._show_section(FIELD_SECTIONS[0][0])

    def _build_layout(self):
        # Top Bar
        top_bar = tk.Frame(self, bg=BG_SIDEBAR, height=60)
        top_bar.pack(side="top", fill="x")
        top_bar.pack_propagate(False)

        title = tk.Label(top_bar, text="🔮 Oracle v2", font=("Segoe UI", 16, "bold"),
                         bg=BG_SIDEBAR, fg=ACCENT)
        title.pack(side="left", padx=20, pady=15)

        # Profile Manager Frame in Top Bar
        profile_frame = tk.Frame(top_bar, bg=BG_SIDEBAR)
        profile_frame.pack(side="left", padx=20, pady=15)

        lbl_p = tk.Label(profile_frame, text="Perfil:", font=("Segoe UI", 10, "bold"), bg=BG_SIDEBAR, fg=FG_DIM)
        lbl_p.pack(side="left", padx=5)

        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var, state="readonly", width=18, font=("Segoe UI", 10))
        self.profile_combo.pack(side="left", padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_change)

        new_profile_btn = tk.Button(profile_frame, text="➕ Novo Perfil", font=("Segoe UI", 9, "bold"),
                                    bg=SUCCESS, fg="#000", activebackground=ACCENT_HOVER,
                                    relief="flat", cursor="hand2", padx=8, command=self._create_new_profile)
        new_profile_btn.pack(side="left", padx=5)

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

        save_btn = tk.Button(bottom_bar, text="💾 Salvar Configurações", font=("Segoe UI", 11, "bold"),
                             bg=ACCENT, fg="#000", activebackground=ACCENT_HOVER,
                             relief="flat", cursor="hand2", padx=20, command=self._save)
        save_btn.pack(side="right", padx=20, pady=12)

        load_btn = tk.Button(bottom_bar, text="📂 Carregar", font=("Segoe UI", 10),
                             bg=BG_CARD, fg=FG_TEXT, activebackground=BG_INPUT,
                             relief="flat", cursor="hand2", padx=15, command=self._load)
        load_btn.pack(side="right", padx=10, pady=12)

        reset_btn = tk.Button(bottom_bar, text="🔄 Padrões", font=("Segoe UI", 10),
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

    def _refresh_profiles(self):
        try:
            ini_files = [f for f in os.listdir(SCRIPT_DIR) if f.endswith(".ini")]
        except Exception:
            ini_files = ["options.ini"]
        if not ini_files:
            ini_files = ["options.ini"]
        if "options.ini" in ini_files:
            ini_files.remove("options.ini")
            ini_files.insert(0, "options.ini")
        self.profile_combo["values"] = ini_files
        
        current_name = os.path.basename(self.active_profile_path)
        if current_name in ini_files:
            self.profile_var.set(current_name)
        else:
            self.profile_var.set(ini_files[0])

    def _on_profile_change(self, event=None):
        name = self.profile_var.get()
        new_path = os.path.join(SCRIPT_DIR, name)
        if new_path == self.active_profile_path:
            return
        
        self.active_profile_path = new_path
        self.existing = load_existing_options(new_path)
        
        for k, v in self.widgets.items():
            default_val = ""
            for _, fields in FIELD_SECTIONS:
                for f in fields:
                    if f[0] == k:
                        default_val = f[3]
                        break
            v.set(self.existing.get(k, default_val))
            
        self.status_var.set(f"📂 Perfil '{name}' carregado")
        self.after(3000, lambda: self.status_var.set(""))

    def _create_new_profile(self):
        from tkinter import simpledialog
        name = simpledialog.askstring("Novo Perfil", "Digite o nome do novo perfil (ex: options_alt):\n(Será salvo como .ini)", parent=self)
        if not name:
            return
        name = name.strip()
        if not name.endswith(".ini"):
            name += ".ini"
        
        new_path = os.path.join(SCRIPT_DIR, name)
        if os.path.exists(new_path):
            messagebox.showwarning("Aviso", f"O perfil '{name}' já existe!")
            return
            
        data = {k: v.get() for k, v in self.widgets.items()}
        try:
            save_options(data, new_path)
            self.active_profile_path = new_path
            self._refresh_profiles()
            self.status_var.set(f"✨ Perfil '{name}' criado e ativo")
            self.after(3000, lambda: self.status_var.set(""))
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao criar perfil:\n{e}")

    def _save(self):
        data = {k: v.get() for k, v in self.widgets.items()}
        errors = []
        if not data.get("user_token", "").strip(): errors.append("Token do Usuário é obrigatório")
        if not data.get("channel_id", "0").strip().isdigit(): errors.append("ID do Canal deve ser um número")
        if not data.get("guild_id", "0").strip().isdigit(): errors.append("ID do Servidor deve ser um número")

        if errors:
            messagebox.showwarning("Erro de Validação", "\n".join(errors))
            return

        try:
            save_options(data, self.active_profile_path)
            self.status_var.set(f"✅ Salvo em {os.path.basename(self.active_profile_path)}")
            self._refresh_profiles()
            self.after(3000, lambda: self.status_var.set(""))
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar:\n{e}")

    def _load(self):
        path = filedialog.askopenfilename(title="Carregar Configuração", filetypes=[("INI", "*.ini"), ("Todos", "*.*")], initialdir=SCRIPT_DIR)
        if not path: return
        self.active_profile_path = path
        loaded = load_existing_options(path)
        for k, v in self.widgets.items():
            if k in loaded: v.set(loaded[k])
        self._refresh_profiles()
        self.status_var.set("📂 Configuração carregada")
        self.after(3000, lambda: self.status_var.set(""))

    def _reset(self):
        if not messagebox.askyesno("Restaurar", "Restaurar todos os campos para os valores padrão?"): return
        for _, fields in FIELD_SECTIONS:
            for f in fields:
                if f[0] in self.widgets: self.widgets[f[0]].set(f[3])
        self.status_var.set("🔄 Padrões restaurados")
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
