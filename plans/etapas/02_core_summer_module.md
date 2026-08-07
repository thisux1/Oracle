# Stage 2 — Core Module: `bot/summer.py`

## Objective

Create the central Summer Event module `bot/summer.py` containing all pure logic: surf automation, boost management, drink crafting, task detection, work queue management, beach party, stuck-state protection, and daily reset. This file is a collection of stateless functions and helpers that import `bot_state`, `config`, and `sessionData`. It does NOT integrate with `client.py` (that's Stage 4).

---

## File: `bot/summer.py`

### Imports

```python
import re
import time
import hashlib
from datetime import datetime, timezone
from bot.state import bot_state, add_to_low_priority_queue, add_to_high_priority_queue
from bot.config import config
from bot.hud import HUD
from bot.telegram import send_telegram_notification
from bot.parsers import sessionData
```

---

## 1. Constants

```python
# Surf
SURF_COOLDOWN = 14400          # 4 hours in seconds
SURF_WAVE_NAMES = [
    "completely normal wave", "inverted wave", "insanely small wave",
    "big wave", "invisible wave", "angry wave",
]
MAX_SURF_ROUNDS = 3

# Risk levels for surf decision-making
RISK_ORDER = {
    "very low risk": 0,
    "low risk": 1,
    "high risk": 2,
    "very high risk": 3,
}

# Work
MAX_WORK_RETRIES = 5
MAX_CRAFT_FAIL_DAILY = 3
STUCK_TIMEOUT = 600            # 10 minutes
BOOST_CHECK_INTERVAL = 1800    # 30 minutes
SURF_RETRY_INTERVAL = 300      # 5 minutes between cooldown checks
TICK_INTERVAL = 30             # summer_tick runs every 30s
```

---

## 2. Surf Logic

### `parse_surf_wave(embed)`

Detect surf wave type from an embed's field names.

```python
def parse_surf_wave(embed):
    """Extract wave type from a surf embed.
    Returns the wave name (lowercase) or None."""
    if not embed or not embed.fields:
        return None
    for field in embed.fields:
        field_name = field.name.lower().strip()
        for wave in SURF_WAVE_NAMES:
            if wave in field_name:
                return wave
    return None
```

### `parse_surf_choices(embed)`

Extract choice A and B with their risk levels and rewards from the embed.

```python
def parse_surf_choices(embed):
    """Parse surf embed fields to extract choice options.
    Returns dict: {'A': {'risk': str, 'reward': str}, 'B': {...}} or None."""
    if not embed or not embed.fields:
        return None
    result = {}
    for field in embed.fields:
        text = field.value.lower() if field.value else ""
        if "a)" in text or "a :" in text:
            result["A"] = _parse_single_choice(text, "a")
        elif "b)" in text or "b :" in text:
            result["B"] = _parse_single_choice(text, "b")
    return result if len(result) == 2 else None


def _parse_single_choice(text, label):
    """Parse a single choice text to extract risk and reward."""
    risk = "unknown risk"
    for r in ["very high risk", "high risk", "low risk", "very low risk"]:
        if r in text:
            risk = r
            break
    # Extract reward (everything after risk description)
    reward = ""
    for prefix in [f"{label})", f"{label} :", f"{label}:"]:
        if prefix in text:
            reward = text.split(prefix, 1)[-1].strip()
            break
    return {"risk": risk, "reward": reward}
```

### `choose_surf_answer(wave, strategy, choices)`

```python
def choose_surf_answer(wave, strategy, choices):
    """Choose A or B based on strategy and wave type.
    - conservative: pick lowest risk option
    - aggressive: pick highest risk option
    Returns 'A' or 'B'."""
    if not choices or "A" not in choices or "B" not in choices:
        return "A"  # fallback

    risk_a = RISK_ORDER.get(choices["A"]["risk"], 1)
    risk_b = RISK_ORDER.get(choices["B"]["risk"], 1)

    if strategy == "aggressive":
        return "B" if risk_b >= risk_a else "A"
    else:  # conservative (default)
        return "A" if risk_a <= risk_b else "B"
```

### `detect_surf_result(content, embed)`

```python
def detect_surf_result(content, embed):
    """Detect the result of a surf attempt.
    Returns: 'completed' | 'fell' | 'cooldown' | 'prompt' | None"""
    if not content:
        return None
    c = content.lower()

    if "slipped off the surfboard" in c:
        return "fell"
    if "you have surfed recently" in c:
        return "cooldown"
    if "try not to slip off the surfboard" in c:
        return "prompt"

    # Check if round was completed successfully
    if "completed" in c and ("surf" in c or "wave" in c):
        return "completed"

    return None
```

### `handle_surf_completion(rounds_completed)`

```python
def handle_surf_completion(rounds_completed):
    """Called when a surf round completes successfully."""
    bot_state.summer_surf_rounds += rounds_completed
    bot_state.summer_last_action_time = time.time()
    HUD.oracle(f"Summer Surf: +{rounds_completed} round(s) ({bot_state.summer_surf_rounds} total)")
```

### `initiate_surf()`

```python
def initiate_surf():
    """Queue a surf command if cooldown has expired."""
    now = time.time()
    if now < bot_state.summer_surf_cooldown_until:
        remaining = bot_state.summer_surf_cooldown_until - now
        HUD.cooldown(f"Summer Surf: cooldown {remaining:.0f}s restante")
        return False

    bot_state.summer_surf_cooldown_until = now + SURF_COOLDOWN
    add_to_low_priority_queue("rpg smr surf")
    HUD.command("rpg smr surf (Summer)", priority="LPQ")
    return True
```

### `handle_surf_cooldown_detected(cooldown_text)`

```python
def handle_surf_cooldown_detected(cooldown_text):
    """Extract remaining cooldown time from the 'you have surfed recently' message."""
    import re
    match = re.search(r'(\d+)\s*[mh]', cooldown_text)
    if match:
        val = int(match.group(1))
        unit = match.group(0)[-1]
        seconds = val * 60 if unit == 'm' else val * 3600
        bot_state.summer_surf_cooldown_until = time.time() + seconds
        HUD.cooldown(f"Summer Surf: cooldown {seconds}s atualizado")
```

---

## 3. Boost Management

### `detect_active_boosts(embed_text)`

```python
BOOST_PATTERN = re.compile(r':[^:]+:\s*(.+?)\s*\((.+?)\s*remaining\)')

def detect_active_boosts(embed_text):
    """Parse the rpg boosts embed to extract active boosts.
    Returns dict: {boost_name: remaining_seconds}"""
    boosts = {}
    matches = BOOST_PATTERN.findall(embed_text)
    for name, remaining_str in matches:
        name = name.strip().lower()
        remaining_seconds = _parse_remaining_time(remaining_str)
        boosts[name] = remaining_seconds
    return boosts


def _parse_remaining_time(time_str):
    """Parse 'Xh Ym remaining' or similar to seconds."""
    total = 0
    h_match = re.search(r'(\d+)h', time_str)
    m_match = re.search(r'(\d+)m', time_str)
    if h_match:
        total += int(h_match.group(1)) * 3600
    if m_match:
        total += int(m_match.group(1)) * 60
    return total
```

### `manage_boost_renewal()`

```python
def manage_boost_renewal():
    """Check and renew summer boosts if needed.
    Called by summer_tick every BOOST_CHECK_INTERVAL."""
    now = time.time()
    if now < bot_state.summer_boost_renew_at:
        return

    # Check if we have resources for summer boost
    add_to_low_priority_queue("rpg smr buy summer boost")
    HUD.command("rpg smr buy summer boost (renew)", priority="LPQ")
    bot_state.summer_boost_renew_at = now + BOOST_CHECK_INTERVAL

    # Check drink status
    if not bot_state.summer_drink_this_week:
        _queue_weekly_drink()
```

### `_queue_weekly_drink()`

```python
def _queue_weekly_drink():
    """Queue the weekly drink based on config choice (for color tournament)."""
    drink_color = config.summer_drink_choice
    add_to_low_priority_queue(f"rpg smr drink {drink_color}")
    HUD.command(f"rpg smr drink {drink_color} (weekly)", priority="LPQ")
```

---

## 4. Work Queue Management

### `add_summer_work_task(command, target)`

```python
def add_summer_work_task(command: str, target: int):
    """Add a work task to the queue with dedup: same command keeps larger target."""
    for existing in bot_state.summer_work_queue:
        if existing["command"] == command:
            if target > existing["target"]:
                existing["target"] = target
                existing["count"] = 0
                HUD.system(f"Summer Work: task '{command}' atualizada (target {target})")
            else:
                HUD.system(f"Summer Work: task '{command}' duplicada (target {target} <= {existing['target']}), ignorada")
            return
    bot_state.summer_work_queue.append({"command": command, "target": target, "count": 0})
    HUD.system(f"Summer Work: task '{command}' adicionada (target {target})")
```

### `increment_summer_work_count(command)`

```python
def increment_summer_work_count(command: str):
    """Increment the count for an active work task.
    Called from parsers.py when a work drop is detected.
    If count >= target, the task is completed and removed from queue."""
    if not bot_state.summer_current_work or bot_state.summer_current_work != command:
        return

    for task in bot_state.summer_work_queue:
        if task["command"] == command:
            task["count"] += 1
            bot_state.summer_work_fail_count = 0
            bot_state.summer_last_action_time = time.time()
            HUD.system(f"Summer Work: '{command}' {task['count']}/{task['target']}")

            if task["count"] >= task["target"]:
                _complete_current_work_task(command)
            return
```

### `on_work_command_failed()`

```python
def on_work_command_failed():
    """Handle a work command failure (error, timeout, unexpected response).
    If MAX_WORK_RETRIES exceeded, abandon the task."""
    bot_state.summer_work_fail_count += 1
    HUD.alert(f"Summer Work: falha #{bot_state.summer_work_fail_count}/{MAX_WORK_RETRIES}")

    if bot_state.summer_work_fail_count >= MAX_WORK_RETRIES:
        failed_work = bot_state.summer_current_work
        bot_state.summer_work_queue = [
            t for t in bot_state.summer_work_queue if t["command"] != failed_work
        ]
        HUD.alert(f"Summer Work: task '{failed_work}' desistiu apos {MAX_WORK_RETRIES} falhas")
        send_telegram_notification(f"⚠️ Summer: work task `{failed_work}` falhou {MAX_WORK_RETRIES}x — removida da fila")
        _advance_to_next_work()
```

### `_complete_current_work_task(command)`

```python
def _complete_current_work_task(command):
    """Remove a completed task from the queue and advance to next."""
    bot_state.summer_work_queue = [
        t for t in bot_state.summer_work_queue if t["command"] != command
    ]
    HUD.oracle(f"Summer Work: task '{command}' completa!")
    _advance_to_next_work()
```

### `_advance_to_next_work()`

```python
def _advance_to_next_work():
    """Advance to the next work task in queue, or restore original work_command."""
    if bot_state.summer_work_queue:
        next_work = bot_state.summer_work_queue[0]["command"]
        bot_state.summer_current_work = next_work
        config.work_command = next_work
        bot_state.summer_work_fail_count = 0
        HUD.system(f"Summer Work: avancando para '{next_work}'")
    else:
        bot_state.summer_current_work = None
        if bot_state.summer_work_original:
            config.work_command = bot_state.summer_work_original
        HUD.system("Summer Work: fila vazia, work original restaurado")
        # After work queue completes, claim tasks
        add_to_high_priority_queue("rpg smr task")
```

### `activate_work_queue()`

```python
def activate_work_queue():
    """Activate the first task in the work queue.
    Called when summer_mode is enabled and work queue is non-empty."""
    if not bot_state.summer_work_queue:
        return
    if bot_state.summer_current_work is not None:
        return

    first = bot_state.summer_work_queue[0]
    bot_state.summer_current_work = first["command"]
    bot_state.summer_work_original = config.work_command
    config.work_command = first["command"]
    bot_state.summer_work_fail_count = 0
    HUD.system(f"Summer Work: fila ativada — '{first['command']}' (target {first['target']})")
```

---

## 5. Task Detection and Claiming

### `detect_tasks_in_message(content)`

```python
TASK_PATTERN = re.compile(r'(\d+)/(\d+)\s*\|\s*(.+?)(?:\n|$)')

# Tasks the bot knows how to handle
KNOWN_TASKS = {
    "rules": "use the rules command",
    "fish": "fish",
    "chop_coconut": "coconut",
    "chop": "chop",
    "arena": "arena",
    "drink_chopped": "chopped coconut",
    "craft_drink": "craft.*drink",
    "duel": "duel",
    "rare_mob": "rare mob",
    "surf_rounds": "surf round",
    "sleepy": "sleepy potion",
}

# Tasks to explicitly ignore
IGNORED_TASKS = ["devote", "donate"]


def detect_tasks_in_message(content):
    """Parse a task list message from EPIC NPC.
    Returns list of dicts: [{"name": str, "current": int, "target": int, "full_name": str}]"""
    if not content:
        return []

    tasks = []
    for match in TASK_PATTERN.finditer(content):
        current = int(match.group(1))
        target = int(match.group(2))
        full_name = match.group(3).strip()

        # Check if this is an ignored task
        if any(ignored in full_name.lower() for ignored in IGNORED_TASKS):
            HUD.system(f"Summer Task: ignorada (excluida): {full_name}")
            continue

        tasks.append({
            "name": full_name,
            "current": current,
            "target": target,
            "full_name": full_name,
        })

    return tasks
```

### `classify_task(task_name)`

```python
def classify_task(task_name):
    """Classify a task name into a known task type for processing.
    Returns: str key from KNOWN_TASKS or 'unknown'."""
    name = task_name.lower()
    for key, pattern in KNOWN_TASKS.items():
        if re.search(pattern, name):
            return key
    return "unknown"
```

### `process_task_updates(tasks)`

```python
def process_task_updates(tasks):
    """Process detected tasks — queue work, check completions.
    Returns list of completed task names."""
    completed = []

    for task in tasks:
        if task["target"] == 0:
            continue

        # Skip if already claimed today
        task_key = f"{task['name']}_{task['target']}"
        if task_key in bot_state.summer_tasks_claimed:
            continue

        if task["current"] >= task["target"]:
            completed.append(task["full_name"])
            bot_state.summer_tasks_claimed.add(task_key)
        else:
            _queue_task_action(task)

    return completed


def _queue_task_action(task):
    """Queue the appropriate action for a detected task."""
    task_type = classify_task(task["name"])
    need = task["target"] - task["current"]

    if task_type == "rules":
        add_to_low_priority_queue("rpg rules")
        HUD.command("rpg rules (summer task)", priority="LPQ")

    elif task_type == "fish":
        add_summer_work_task("fish", need)

    elif task_type == "chop" or task_type == "chop_coconut":
        add_summer_work_task("chop", need)

    elif task_type == "arena":
        add_to_low_priority_queue("rpg arena")
        HUD.command("rpg arena (summer task)", priority="LPQ")

    elif task_type == "drink_chopped":
        add_to_high_priority_queue("rpg smr drink chopped coconut")
        HUD.command("rpg smr drink chopped coconut (summer task)", priority="HPQ")

    elif task_type == "craft_drink":
        _queue_craft_drink()

    elif task_type == "duel":
        _queue_duel_task()

    elif task_type == "sleepy":
        if config.summer_use_sleepy_potion:
            add_to_high_priority_queue("rpg smr use sleepy potion")
            HUD.command("rpg smr use sleepy potion (summer task)", priority="HPQ")
        else:
            HUD.system("Summer Task: sleepy potion ignorada (config desativado)")

    elif task_type == "rare_mob":
        HUD.system("Summer Task: rare mob tracking ativo (hunt natural)")
```

### `_queue_craft_drink()`

```python
DRINK_RECIPES = {
    "blue": {"ingredients": "3 chopped coconut + 2 normiefish", "command": "rpg smr craft blue drink"},
    "green": {"ingredients": "3 chopped coconut + 1 EPIC fish + 1 chip", "command": "rpg smr craft green drink"},
    "pink": {"ingredients": "3 chopped coconut + 1 EDGY lootbox", "command": "rpg smr craft pink drink"},
    "yellow": {"ingredients": "3 chopped coconut + 1 epic seed + 3 Banana + 1 lottery ticket", "command": "rpg smr craft yellow drink"},
}


def _queue_craft_drink():
    """Queue a craft drink command for the configured color."""
    drink = config.summer_drink_choice
    if drink in DRINK_RECIPES:
        add_to_low_priority_queue(DRINK_RECIPES[drink]["command"])
        HUD.command(f"{DRINK_RECIPES[drink]['command']} (summer task)", priority="LPQ")
```

### `_queue_duel_task()`

```python
def _queue_duel_task():
    """Queue duel commands for the 'lose 2 duels' task.
    Duels are sent with partner and no weapon choice to lose intentionally."""
    partner_id = config.duel_partner_id
    if partner_id:
        add_to_low_priority_queue(f"rpg duel <@{partner_id}>")
        HUD.command(f"rpg duel @{partner_id} (summer task — lose)", priority="LPQ")
    else:
        HUD.system("Summer Task: duel ignorada — nenhum duel_partner_id configurado")
```

### `claim_tasks()`

```python
def claim_tasks():
    """Queue the claim command for completed summer tasks."""
    add_to_high_priority_queue("rpg smr task")
    HUD.command("rpg smr task (claim)", priority="HPQ")
```

---

## 6. Beach Party

### `detect_beach_party_invite(content, embed)`

```python
def detect_beach_party_invite(content, embed):
    """Detect a beach party invite that needs a 'join' response."""
    if not content:
        return False
    c = content.lower()
    return "beach party" in c and "join" in c
```

### `join_beach_party()`

```python
def join_beach_party():
    """Respond to a beach party invite."""
    add_to_high_priority_queue("join")
    HUD.command("join (beach party)", priority="HPQ")
```

### `start_beach_party()`

```python
def start_beach_party():
    """Queue starting a beach party (costs resources)."""
    add_to_low_priority_queue("rpg smr beach party")
    HUD.command("rpg smr beach party", priority="LPQ")
```

---

## 7. Stuck State Protection & Daily Reset

### `summer_tick()` — Main Tick Function

```python
def summer_tick():
    """Main tick function called periodically from client.py.
    Handles: work queue activation, stuck detection, daily reset, boost renewal."""
    now = time.time()

    # 1. Daily reset — check if date changed
    _check_daily_reset(now)

    # 2. Work queue consistency check
    _check_work_queue_consistency()

    # 3. Work queue activation (if idle and tasks pending)
    if bot_state.summer_work_queue and bot_state.summer_current_work is None:
        activate_work_queue()

    # 4. Stuck state detection
    _check_stuck_state(now)

    # 5. Boost renewal
    if now >= bot_state.summer_boost_renew_at and bot_state.summer_boost_renew_at > 0:
        manage_boost_renewal()
```

### `_check_daily_reset(now)`

```python
def _check_daily_reset(now):
    """Reset daily counters when the UTC date changes."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if bot_state.summer_daily_date and bot_state.summer_daily_date != today:
        bot_state.summer_tasks_claimed = set()
        bot_state.summer_coconut_count = 0
        bot_state.summer_rules_sent = False
        bot_state.summer_craft_fail_count = 0
        bot_state.summer_work_queue = []
        bot_state.summer_current_work = None
        bot_state.summer_work_fail_count = 0
        if bot_state.summer_work_original:
            config.work_command = bot_state.summer_work_original
            bot_state.summer_work_original = ""
        bot_state.summer_daily_date = today
        HUD.system(f"Summer: reset diario — nova data: {today}")
    elif not bot_state.summer_daily_date:
        bot_state.summer_daily_date = today
```

### `_check_work_queue_consistency()`

```python
def _check_work_queue_consistency():
    """Fix corrupted work queue state where current_work doesn't match queue."""
    if bot_state.summer_current_work is None:
        return
    if not any(t["command"] == bot_state.summer_current_work for t in bot_state.summer_work_queue):
        bot_state.summer_current_work = None
        if bot_state.summer_work_original:
            config.work_command = bot_state.summer_work_original
            bot_state.summer_work_original = ""
        HUD.system("Summer: work queue inconsistente — resetado")
```

### `_check_stuck_state(now)`

```python
def _check_stuck_state(now):
    """Detect and handle stuck state (no action for STUCK_TIMEOUT)."""
    if not bot_state.summer_work_queue and not bot_state.summer_mode:
        return
    if bot_state.summer_last_action_time == 0:
        return

    idle_time = now - bot_state.summer_last_action_time
    if idle_time > STUCK_TIMEOUT:
        HUD.alert(f"Summer: possivelmente travado — {idle_time:.0f}s sem acao")

        if bot_state.summer_work_queue:
            send_telegram_notification(
                f"⚠️ Summer: bot parece travado a {int(idle_time)}s com tasks pendentes"
            )

        # Force reset
        if bot_state.summer_current_work:
            config.work_command = bot_state.summer_work_original
            bot_state.summer_current_work = None
        bot_state.summer_last_action_time = now
```

### `_check_weekly_reset()`

```python
def _check_weekly_reset():
    """Reset weekly state when the week changes (Monday UTC)."""
    now = datetime.now(timezone.utc)
    # Monday = 0 in weekday()
    if now.weekday() == 0 and now.hour == 0 and now.minute < 5:
        if bot_state.summer_drink_this_week:
            bot_state.summer_drink_this_week = False
            bot_state.summer_color_team = None
            HUD.system("Summer: reset semanal — nova semana de torneio")
```

---

## 8. Sunglasses Tracking

### `detect_sunglasses_part_a(content)`

```python
def detect_sunglasses_part_a(content):
    """Detect 'completed the surf course' for Sunglasses Part A."""
    if not content:
        return False
    return "completed the surf course" in content.lower()
```

### `detect_sunglasses_part_b(content)`

```python
def detect_sunglasses_part_b(content):
    """Detect sunglasses drop in item loot."""
    if not content:
        return False
    return "sunglasses" in content.lower()
```

---

## 9. Utility: Summer Status Report

### `get_summer_status()`

```python
def get_summer_status():
    """Return a formatted status string for the summer event."""
    lines = []
    lines.append("=== Summer Event Status ===")
    lines.append(f"Mode: {'ON' if bot_state.summer_mode else 'OFF'}")
    if bot_state.summer_mode:
        lines.append(f"Strategy: {config.summer_surf_strategy}")
        lines.append(f"Drink: {config.summer_drink_choice}")
        lines.append(f"Color Team: {bot_state.summer_color_team or 'not set'}")
        lines.append(f"Drink This Week: {bot_state.summer_drink_this_week}")

        cooldown = bot_state.summer_surf_cooldown_until - time.time()
        if cooldown > 0:
            lines.append(f"Surf Cooldown: {cooldown:.0f}s remaining")
        else:
            lines.append("Surf Cooldown: READY")

        lines.append(f"Surf Rounds: {bot_state.summer_surf_rounds}")
        lines.append(f"Work Queue: {len(bot_state.summer_work_queue)} tasks")
        if bot_state.summer_current_work:
            lines.append(f"Current Work: {bot_state.summer_current_work}")
        lines.append(f"Boost Renew: {bot_state.summer_boost_renew_at > 0}")
        lines.append(f"Tasks Claimed Today: {len(bot_state.summer_tasks_claimed)}")
        lines.append(f"Daily Date: {bot_state.summer_daily_date}")

    return "\n".join(lines)
```

---

## Acceptance Criteria

1. `python3 -c "import py_compile; py_compile.compile('bot/summer.py', doraise=True)"` — passes
2. `python3 -c "from bot.summer import *"` — no import errors (requires bot running for state/config)
3. `parse_surf_wave()` correctly identifies wave types from embed field names
4. `choose_surf_answer()` returns correct choice for conservative vs aggressive
5. `detect_surf_result()` correctly classifies surf outcomes
6. `add_summer_work_task()` deduplicates: same command with smaller target is dropped
7. `increment_summer_work_count()` triggers completion when target reached
8. `on_work_command_failed()` abandons task after MAX_WORK_RETRIES
9. `_check_work_queue_consistency()` detects and fixes corrupted state
10. `_check_stuck_state()` triggers after STUCK_TIMEOUT seconds of inactivity
11. `_check_daily_reset()` resets counters when UTC date changes
12. `detect_tasks_in_message()` correctly parses task format "X/Y | name"
13. `detect_beach_party_invite()` recognizes beach party prompts
14. `get_summer_status()` returns formatted status with all fields
15. All functions use `HUD.*()` for logging (no `print()`)
