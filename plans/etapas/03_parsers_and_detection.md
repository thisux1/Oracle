# Stage 3 — Parsers & Message Detection

## Objective

Add Summer Event detection logic to `bot/parsers.py` and the message processing pipeline. After this stage, the bot can detect surf prompts, task lists, boost status, summer drops, and work progress from Epic RPG messages. Stage 4 will integrate these into `client.py`.

---

## 1. `bot/parsers.py` — New Detection Functions

### Location

Add at the end of `parsers.py` (after line 694, the last line). Create a new section:

```python
# ═══════════════════════════════════════════════
# Summer Event Parsers
# ═══════════════════════════════════════════════
```

### 1.1 `detect_summer_drops(content, embed)`

```python
def detect_summer_drops(content, embed):
    """Detect summer event item drops in loot messages.
    Called from the drop detection pipeline.
    Updates sessionData['summer_coconuts'] if coconuts are detected."""
    if not content:
        return

    c = content.lower()

    # Coconut tracking (from chop)
    if "coconut" in c and bot_state.summer_mode:
        # Try to extract quantity from nearby text
        import re
        coconut_match = re.findall(r'(\d+)\s*coconut', c)
        if coconut_match:
            total = sum(int(q) for q in coconut_match)
            bot_state.summer_coconut_count += total
            HUD.system(f"Summer: +{total} coconut(s) detectado(s) (total: {bot_state.summer_coconut_count})")

    # Summer Slime detection
    if "summer slime" in c:
        HUD.oracle("Summer Slime encontrado no hunt!")

    # MEGA Palm Log
    if "mega palm log" in c:
        HUD.loot(None, "Mega Palm Log", 1)

    # Sunglasses drop (Part B)
    if "sunglasses" in c:
        HUD.oracle("Sunglasses artifact encontrado!")
```

### 1.2 `detect_work_progress(content, command_name)`

```python
def detect_work_progress(content, command_name):
    """Detect a successful work command execution for summer work queue tracking.
    Returns True if the work command appears to have executed successfully."""
    if not content or not command_name:
        return False

    c = content.lower()

    # Fish success signals
    if command_name == "fish" and ("fish" in c or "normiefish" in c or "caught" in c):
        return True

    # Chop success signals
    if command_name == "chop" and ("chop" in c or "coconut" in c or "palm log" in c):
        return True

    # Generic work success (any rpg response that is not an error)
    if command_name in ("fish", "chop") and "you don't have enough energy" in c:
        return False

    return False
```

### 1.3 `handle_summer_task_message(content)`

```python
def handle_summer_task_message(content):
    """Process a task list message from EPIC NPC during summer event.
    Detects tasks, updates work queue, and claims completed tasks.
    Uses bot.summer module functions."""
    if not content or not bot_state.summer_mode:
        return

    from bot.summer import (
        detect_tasks_in_message,
        process_task_updates,
        claim_tasks,
    )

    tasks = detect_tasks_in_message(content)
    if not tasks:
        return

    # Generate hash to avoid reprocessing the same task list
    content_hash = str(hash(str(tasks)))
    if content_hash == bot_state.summer_last_task_list:
        return
    bot_state.summer_last_task_list = content_hash

    HUD.system(f"Summer Tasks: {len(tasks)} task(s) detectadas")

    # Process each task
    completed = process_task_updates(tasks)
    if completed:
        HUD.oracle(f"Summer Tasks completas: {', '.join(completed)}")
        claim_tasks()
```

### 1.4 `handle_summer_boost_message(content, embed)`

```python
def handle_summer_boost_message(content, embed):
    """Process a boost list message (rpg boosts response).
    Detects active summer boost and drink boosts.
    Updates bot_state.summer_boost_renew_at."""
    if not content and not embed:
        return

    from bot.summer import detect_active_boosts
    import re

    embed_text = content or ""
    if embed:
        embed_text += " " + str(embed.to_dict())

    boosts = detect_active_boosts(embed_text)

    if not boosts:
        return

    # Check if summer boost is active
    has_summer_boost = any("summer" in name for name in boosts)
    if has_summer_boost:
        # Boost is active — reschedule renewal check
        remaining = max(boosts.values()) if boosts else 0
        if remaining > 300:  # More than 5 minutes left
            bot_state.summer_boost_renew_at = time.time() + max(remaining - 60, 60)
            HUD.system(f"Summer Boost: ativo ({remaining}s restante)")
```

### 1.5 `handle_surf_response(content, embed)`

```python
def handle_surf_response(content, embed):
    """Process a surf-related message from Epic RPG.
    Returns the action to take: 'respond_A', 'respond_B', 'fell', 'cooldown', or None."""
    if not content:
        return None

    from bot.summer import (
        detect_surf_result,
        parse_surf_wave,
        parse_surf_choices,
        choose_surf_answer,
        handle_surf_completion,
        handle_surf_cooldown_detected,
    )

    result = detect_surf_result(content, embed)

    if result == "prompt" and embed:
        # We need to choose A or B
        wave = parse_surf_wave(embed)
        choices = parse_surf_choices(embed)

        if wave and choices:
            strategy = config.summer_surf_strategy
            answer = choose_surf_answer(wave, strategy, choices)
            HUD.dungeon(f"Summer Surf: onda '{wave}' — escolhendo {answer} ({strategy})")
            return f"respond_{answer}"

    elif result == "completed" and embed:
        handle_surf_completion(1)

    elif result == "fell":
        HUD.alert("Summer Surf: caiu do surfboard")

    elif result == "cooldown":
        handle_surf_cooldown_detected(content)

    return None
```

### 1.6 `is_summer_related_message(content, embed)`

```python
SUMMER_KEYWORDS = [
    "summer", "smr", "surf", "coconut", "beach",
    "chopped coconut", "palm log", "pool float",
    "sleepy potion", "summer boost", "sunglasses",
    "beach party", "color tournament",
]


def is_summer_related_message(content, embed):
    """Quick check if a message is related to the summer event.
    Used as a pre-filter before calling detailed parsers."""
    if not content:
        return False

    c = content.lower()
    for kw in SUMMER_KEYWORDS:
        if kw in c:
            return True

    if embed:
        embed_text = str(embed.to_dict()).lower()
        for kw in SUMMER_KEYWORDS:
            if kw in embed_text:
                return True

    return False
```

### 1.7 `detect_color_team(content)`

```python
COLOR_TEAM_PATTERN = re.compile(r'(blue|green|pink|yellow)\s*(team|color|drink)', re.IGNORECASE)


def detect_color_team(content):
    """Detect which color team the bot joined in the color tournament."""
    if not content or not bot_state.summer_mode:
        return

    c = content.lower()
    match = COLOR_TEAM_PATTERN.search(c)
    if match:
        team = match.group(1).lower()
        bot_state.summer_color_team = team
        bot_state.summer_drink_this_week = True
        HUD.oracle(f"Summer: time {team.upper()} confirmado no torneio de cores!")
```

### 1.8 `detect_craft_result(content)`

```python
CRAFT_FAIL_PATTERNS = [
    "you failed to craft",
    "craft failed",
    "you don't have the required items",
    "you don't have enough",
    "not enough",
]


def detect_craft_result(content):
    """Detect the result of a summer craft attempt.
    Returns: 'success' | 'fail' | 'no_resources' | None"""
    if not content:
        return None

    c = content.lower()

    for pattern in CRAFT_FAIL_PATTERNS:
        if pattern in c:
            if "required items" in c or "don't have" in c or "not enough" in c:
                bot_state.summer_craft_fail_count += 1
                HUD.alert(f"Summer Craft: falhou — sem recursos (falha #{bot_state.summer_craft_fail_count})")

                if bot_state.summer_craft_fail_count >= 3:
                    send_telegram_notification("⚠️ Summer: craft falhou 3x hoje — recursos insuficientes")
                return "no_resources"
            else:
                bot_state.summer_craft_fail_count += 1
                HUD.alert(f"Summer Craft: falha (60% chance) #{bot_state.summer_craft_fail_count}")
                return "fail"

    if "successfully" in c and ("craft" in c or "created" in c):
        HUD.oracle("Summer Craft: sucesso!")
        return "success"

    return None
```

### 1.9 Integration Points in Existing Parser Functions

#### In `process_drops()` — Add coconut and summer item tracking

After existing item detection logic (around where `apple`, `ruby`, etc. are detected), add:

```python
if bot_state.summer_mode and "coconut" in drop_name.lower():
    from bot.state import sessionData
    bot_state.summer_coconut_count += qty
    if "summer_coconuts" not in sessionData:
        sessionData["summer_coconuts"] = 0
    sessionData["summer_coconuts"] += qty

if "summer slime" in drop_name.lower():
    HUD.oracle("Summer Slime encontrado!")
```

#### In `rdCheckEpicRPG()` — Add work counter increment

After the work command handler section (around line 350, the COMMAND_FLAGS area), add:

```python
# Summer work queue counter
if bot_state.summer_mode and bot_state.summer_current_work:
    from bot.summer import increment_summer_work_count
    if any(cmd in content.lower() for cmd in ["fish", "chop"]):
        for task in bot_state.summer_work_queue:
            if task["command"] in content.lower():
                break  # Let increment_summer_work_count handle it
```

#### In `format_session_data()` — Add summer data

In the `misc` sub-dict section (around line 561-582), add:

```python
"summer_surf_rounds": bot_state.summer_surf_rounds if bot_state.summer_mode else 0,
"summer_coconuts": bot_state.summer_coconut_count if bot_state.summer_mode else 0,
"summer_tasks": len(bot_state.summer_tasks_claimed) if bot_state.summer_mode else 0,
```

---

## 2. `bot/state.py` — Queue Blockers (Revisited)

### Add `is_summer_command()` check to HPQ (already in Stage 1)

Make sure the `is_summer_command()` function from Stage 1 correctly identifies work commands:

```python
# In add_to_low_priority_queue — after gather check (line ~415)
if bot_state.summer_mode and not is_summer_command(command):
    return

# In add_to_high_priority_queue — after gather check (line ~440)
if bot_state.summer_mode and not is_summer_command(command):
    return
```

---

## 3. Acceptance Criteria

1. `python3 -c "import py_compile; py_compile.compile('bot/parsers.py', doraise=True)"` — passes
2. `detect_summer_drops()` correctly identifies coconuts in chop messages
3. `detect_work_progress()` returns True for fish/chop success messages
4. `handle_summer_task_message()` correctly parses task list format and updates work queue
5. `handle_summer_boost_message()` identifies active summer boost and times renewal
6. `handle_surf_response()` returns correct action for each surf outcome
7. `is_summer_related_message()` pre-filters messages efficiently
8. `detect_craft_result()` distinguishes success vs fail vs no_resources
9. `detect_color_team()` sets bot_state.summer_color_team on drink confirmation
10. All new functions handle `content=None` gracefully
11. All functions use `HUD.*()` for logging (no `print()`)
