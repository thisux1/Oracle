# Stage 1 — Foundation: State, Config, TUI, Options

## Objective

Add all Summer Event state fields, configuration variables, TUI entries, and option file scaffolding. After this stage, the bot will know about summer mode but won't execute any logic yet.

---

## 1. `bot/config.py` — New Config Vars

### Location

After `do_gather` at line 276 (in the Togglable Command Flags section — ~line 277).

### Add after line 276

```python
# ─── Summer Event ───
do_summer = get_opt_bool("do_summer", False)
summer_surf_strategy = get_opt("summer_surf_strategy", "conservative").lower()
summer_drink_choice = get_opt("summer_drink_choice", "blue").lower()
summer_use_sleepy_potion = get_opt_bool("summer_use_sleepy_potion", False)
```

### In `reload_config()` — Global Declarations (line 354)

Append to the `global` statement:
```python
global language, do_gather, do_summer, summer_surf_strategy, summer_drink_choice, summer_use_sleepy_potion
```

### In `reload_config()` — Re-read Section (after line 417)

```python
# ─── Summer Event ───
do_summer = get_opt_bool("do_summer", False)
summer_surf_strategy = get_opt("summer_surf_strategy", "conservative").lower()
summer_drink_choice = get_opt("summer_drink_choice", "blue").lower()
summer_use_sleepy_potion = get_opt_bool("summer_use_sleepy_potion", False)
```

---

## 2. `bot/state.py` — New State Fields

### In `BotState.__init__` (after line 186, before closing blank line)

```python
# ─── Summer Event ───
self.summer_mode = False                              # Active flag
self.summer_surf_cooldown_until = 0.0                 # Timestamp next surf allowed
self.summer_drink_this_week = False                   # True if drank this week
self.summer_color_team = None                         # 'blue'|'green'|'pink'|'yellow'|None
self.summer_boost_renew_at = 0.0                      # Next boost renewal timestamp
self.summer_surf_rounds = 0                           # Rounds completed (weekly: 7 needed)
self.summer_tasks_claimed = set()                     # Task names claimed today
self.summer_daily_date = ""                           # YYYY-MM-DD for daily reset detection
self.summer_rules_sent = False                        # Whether rpg rules sent today
self.summer_coconut_count = 0                         # Coconuts obtained from chop today
self.summer_work_original = ""                        # Original work_command before override
self.summer_work_queue = []                           # [{"command": str, "target": int, "count": int}]
self.summer_current_work = None                       # Active work command (str or None)
self.summer_work_fail_count = 0                       # Consecutive work failures
self.summer_craft_fail_count = 0                      # Total craft failures today
self.summer_task_stuck_since = 0.0                    # When current task got stuck
self.summer_last_action_time = 0.0                    # Last successful summer action
self.summer_last_task_list = ""                       # Hash of last processed task list
self.summer_beach_party_active = False                # Whether beach party boost is active
```

### In `reset_bot_state()` (after line 540, before LPQ clear at line 541)

```python
# ─── Summer Event Reset ───
bot_state.summer_mode = False
bot_state.summer_surf_cooldown_until = 0.0
bot_state.summer_drink_this_week = False
bot_state.summer_color_team = None
bot_state.summer_boost_renew_at = 0.0
bot_state.summer_surf_rounds = 0
bot_state.summer_tasks_claimed = set()
bot_state.summer_daily_date = ""
bot_state.summer_rules_sent = False
bot_state.summer_coconut_count = 0
bot_state.summer_work_original = ""
bot_state.summer_work_queue = []
bot_state.summer_current_work = None
bot_state.summer_work_fail_count = 0
bot_state.summer_craft_fail_count = 0
bot_state.summer_task_stuck_since = 0.0
bot_state.summer_last_action_time = 0.0
bot_state.summer_last_task_list = ""
bot_state.summer_beach_party_active = False
if getattr(bot_state, "summer_work_original", "") and hasattr(config, "work_command"):
    config.work_command = bot_state.summer_work_original
```

### Queue Blockers

#### In `add_to_low_priority_queue` (after line 415, gather_mode check)

```python
if bot_state.summer_mode and not is_summer_command(command):
    return
```

#### In `add_to_high_priority_queue` (after line 440, gather_mode check)

```python
if bot_state.summer_mode and not is_summer_command(command):
    return
```

Add the helper function **before** both queue functions (around line 400):

```python
def is_summer_command(command: str) -> bool:
    """Check if a command is allowed during summer event mode."""
    cmd = command.lower().strip()
    # Summer event commands are always allowed
    if cmd.startswith("rpg smr ") or cmd == "rpg smr":
        return True
    # Surf responses (single letters A or B)
    if cmd in ("a", "b") and bot_state.summer_mode:
        return True
    # Arena join is allowed during summer (for summer tasks)
    if cmd == "join" and bot_state.summer_mode:
        return True
    # Work commands during summer mode
    if bot_state.summer_current_work and cmd == f"rpg {bot_state.summer_current_work}":
        return True
    # Regular commands that are needed for summer tasks
    if cmd in ("rpg rules", "rpg i", "rpg boosts", "rpg arena", "rpg smr task"):
        return True
    # Queue management commands
    if cmd.startswith("sb summer") or cmd == "sb status":
        return True
    # Allow the same commands that gather/sleepet mode allows
    if cmd.startswith("sb "):
        return True
    return False
```

---

## 3. `options_example.ini` — New Section

Add **before line 48** (before `theme`):

```ini
# ─── Summer Event ───
do_summer=false                # Ativa automacao do evento Summer
summer_surf_strategy=conservative # Estrategia de surf: conservative (menor risco) ou aggressive (maior risco)
summer_drink_choice=blue       # Drink da segunda-feira: blue, green, pink, yellow (blue = craft dobrado)
summer_use_sleepy_potion=false # Usar sleepy potion automaticamente para task weekly (perigoso — avanca 24h!)
```

---

## 4. `bot/tui_modals.py` — TUI Config Schema

### In `CONFIG_SCHEMA` — Add to "✅ Features" section (after line 558, after `do_pet`)

```python
("do_summer", "bool", "false"),
```

### In `CONFIG_SCHEMA` — Add to "🧪 Advanced" section (after line 574, before `theme`)

```python
("summer_surf_strategy", "dropdown", "conservative", ["conservative", "aggressive"]),
("summer_drink_choice", "dropdown", "blue", ["blue", "green", "pink", "yellow"]),
("summer_use_sleepy_potion", "bool", "false"),
```

### In `load_example_comments()` (after line 601, before closing brace of dict)

```python
"do_summer": "Ativa automacao completa do evento Summer (surf, tasks, boosts, craft)",
"summer_surf_strategy": "Estrategia de surf: conservative (menor risco) ou aggressive (maior recompensa)",
"summer_drink_choice": "Cor da drink para segunda-feira (blue = craft dobrado, green = surf dobrado, pink = shop 30%% off, yellow = task dobrado)",
"summer_use_sleepy_potion": "Atencao: sleepy potion avanca 24h do jogo — usar apenas se tiver ciente do risco",
```

---

## 5. `bot/tui_input.py` — TUI Commands

### In `COMMANDS` dict (after line 40, after `/sleepet stop`)

```python
"/summer start": "Ativa o Summer Event Mode (surf, tasks, boosts)",
"/summer stop": "Desativa o Summer Event Mode",
"/summer status": "Mostra status do Summer Event",
"/summer sleepy": "Usa sleepy potion manualmente para task weekly",
```

### In `CONFIG_METADATA` dict (after line 97, after `do_pet`)

```python
"do_summer": "Ativa automacao completa do evento Summer (surf, tasks, boosts, craft, drink)",
"summer_surf_strategy": "Estrategia de surf: conservative (menor risco, recomendado) ou aggressive (maior recompensa, mais risco de cair)",
"summer_drink_choice": "Cor da drink para iniciar o torneio semanal na segunda: blue|green|pink|yellow",
"summer_use_sleepy_potion": "Habilitar uso automatico de sleepy potion para completar task weekly (avanca 24h do jogo!)",
```

### In `_is_accepted_command()` (after line 288, sleepet check)

Add summer base command recognition alongside sleepet/gather.

---

## 6. `bot/handlers.py` — Config Categories

### In `CONFIG_CATEGORIES["commands"]` (after line 1343, after `do_gather`)

```python
"do_summer": {"desc": "Ativa automacao do evento Summer.", "type": "bool", "syntax": "do_summer <true/false>"},
"summer_surf_strategy": {"desc": "Estrategia de surf: conservative (recomendado) ou aggressive.", "type": "str", "syntax": "summer_surf_strategy <conservative|aggressive>"},
"summer_drink_choice": {"desc": "Cor da drink semanal.", "type": "str", "syntax": "summer_drink_choice <blue|green|pink|yellow>"},
```

### In `TOGGLE_ALIASES` (after line 1415, after `gather`)

```python
"do_summer": "summer",
```

### In `find_bool_param()` aliases map (after line 1526)

```python
"summer": "do_summer", "summerevent": "do_summer",
```

---

## Acceptance Criteria

1. `python3 -c "import py_compile; py_compile.compile('bot/config.py', doraise=True)"` — passes
2. `python3 -c "import py_compile; py_compile.compile('bot/state.py', doraise=True)"` — passes
3. `python3 -c "import py_compile; py_compile.compile('bot/tui_modals.py', doraise=True)"` — passes
4. `python3 -c "import py_compile; py_compile.compile('bot/tui_input.py', doraise=True)"` — passes
5. `python3 -c "import py_compile; py_compile.compile('bot/handlers.py', doraise=True)"` — passes
6. All new state fields are present in `BotState.__init__`
7. All new state fields are reset in `reset_bot_state()`
8. `do_summer` appears in `options_example.ini` with proper section
9. TUI shows 4 summer fields in Config modal
10. TUI autocomplete shows `/summer start`, `/summer stop`, `/summer status`, `/summer sleepy`
11. Queue blockers return `True` for summer commands, `False` for unrelated rpg commands during summer mode
12. `config.do_summer`, `config.summer_surf_strategy`, `config.summer_drink_choice` all accessible
