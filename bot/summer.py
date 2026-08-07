import re
import time
import hashlib
import logging
from datetime import datetime, timezone

logger = logging.getLogger("Oracle")
from bot.state import bot_state, add_to_low_priority_queue, add_to_high_priority_queue
import bot.config as config
from bot.hud import HUD
from bot.telegram import send_telegram_notification
from bot.parsers import sessionData

SURF_COOLDOWN = 14400
SURF_WAVE_NAMES = [
    "completely normal wave", "inverted wave", "insanely small wave",
    "big wave", "invisible wave", "angry wave",
]
MAX_SURF_ROUNDS = 3

# ─── Boost Management Constants ───
BOOST_PATTERN = re.compile(r'\*\*(.+?)\*\*:\s*(.+?)(?:\n|$)')
BOOST_CHECK_INTERVAL = 1500   # 25 minutes between rpg boosts polling
BOOST_RENEW_BUFFER = 120      # re-queue 2 minutes before actual expiry
STUCK_TIMEOUT = 600            # 10 minutes of inactivity triggers alert

RISK_ORDER = {
    "very low risk": 0,
    "low risk": 1,
    "high risk": 2,
    "very high risk": 3,
}

SURF_WAVE_DATA = {
    "completely normal wave": {
        "A": {"risk": "low risk", "reward": "80 guild rings"},
        "B": {"risk": "very low risk", "reward": "1 wishing token"},
    },
    "inverted wave": {
        "A": {"risk": "very low risk", "reward": "20 coconuts"},
        "B": {"risk": "high risk", "reward": "3 EPIC lootboxes"},
    },
    "insanely small wave": {
        "A": {"risk": "very low risk", "reward": "30 arena cookies"},
        "B": {"risk": "very high risk", "reward": "1 OMEGA horse token"},
    },
    "big wave": {
        "A": {"risk": "low risk", "reward": "1 EDGY lootbox"},
        "B": {"risk": "high risk", "reward": "10 TIME cookies"},
    },
    "invisible wave": {
        "A": {"risk": "low risk", "reward": "35 chopped coconuts"},
        "B": {"risk": "very high risk", "reward": "4 flasks"},
    },
    "angry wave": {
        "A": {"risk": "high risk", "reward": "2 flasks"},
        "B": {"risk": "very high risk", "reward": "20 TIME cookies"},
    },
}

BOOST_DEFS = {
    "summer boost": {
        "duration": 14400,
        "craft_cmd": "rpg smr buy summer boost",
        "use_cmd": None,
    },
    "blue drink": {
        "duration": 10800,
        "craft_cmd": "rpg smr craft blue drink",
        "use_cmd": "rpg smr drink blue drink",
    },
    "green drink": {
        "duration": 10800,
        "craft_cmd": "rpg smr craft green drink",
        "use_cmd": "rpg smr drink green drink",
    },
    "pink drink": {
        "duration": 10800,
        "craft_cmd": "rpg smr craft pink drink",
        "use_cmd": "rpg smr drink pink drink",
    },
    "yellow drink": {
        "duration": 10800,
        "craft_cmd": "rpg smr craft yellow drink",
        "use_cmd": "rpg smr drink yellow drink",
    },
}

BOOST_NAME_ALIASES = {
    "summer boost": ["summer boost", "summer"],
    "blue drink": ["blue drink", "blue"],
    "green drink": ["green drink", "green"],
    "pink drink": ["pink drink", "pink"],
    "yellow drink": ["yellow drink", "yellow"],
}

TASK_PATTERN = re.compile(r'`?(\d+)/(\d+)`?\s*\|\s*(.+?)(?:\n|$|\\n)')
QUEST_PATTERN = re.compile(r'(?:🏆\s*)?([a-zA-Z0-9_ ,!]+?)\s+goal:.*?(?:progress:\s*(completed|(\d+)/(\d+)))', re.DOTALL | re.IGNORECASE)

KNOWN_TASKS = {
    "rules": r"use the `?rules`? command",
    "support": "use the `support` command",
    "fish": "fish",
    "chop_coconut": "coconut",
    "chop": r"chop|palm log",
    "deforestation": r"deforestation",
    "arena": "arena",
    "drink_chopped": "chopped coconut",
    "craft_drink": "craft.*drink",
    "duel": "duel",
    "rare_mob": "rare mob",
    "surf_rounds": r"surf round|conquer the waves",
    "sleepy": "sleepy potion",
    "slots": r"slots",
    "stonks": r"stonks",
    "trade": r"trade.*epic npc|trade of the day|rpg trade",
    "dismantle": r"dismantle|reduced to atoms",
    "altruism": r"altruism",
    "help": r"help",
    "unboxing": r"unbox|open.*lootbox|open.*(edgy|epic|lottery)",
    "completionist": r"completionist",
}

IGNORED_TASKS = ["devote", "donate"]

DRINK_RECIPES = {
    "blue": {"ingredients": "3 chopped coconut + 2 normiefish", "command": "rpg smr craft blue drink"},
    "green": {"ingredients": "3 chopped coconut + 1 EPIC fish + 1 chip", "command": "rpg smr craft green drink"},
    "pink": {"ingredients": "3 chopped coconut + 1 EDGY lootbox", "command": "rpg smr craft pink drink"},
    "yellow": {"ingredients": "3 chopped coconut + 1 epic seed + 3 Banana + 1 lottery ticket", "command": "rpg smr craft yellow drink"},
}

def _parse_remaining_time(time_str):
    total = 0
    d_match = re.search(r'(\d+)d', time_str)
    h_match = re.search(r'(\d+)h', time_str)
    m_match = re.search(r'(\d+)m', time_str)
    s_match = re.search(r'(\d+)s', time_str)
    if d_match:
        total += int(d_match.group(1)) * 86400
    if h_match:
        total += int(h_match.group(1)) * 3600
    if m_match:
        total += int(m_match.group(1)) * 60
    if s_match:
        total += int(s_match.group(1))
    return total

def _find_wave_in_text(text):
    if text:
        for wave in SURF_WAVE_NAMES:
            if wave in text.lower():
                return wave
    return None

def parse_surf_wave(embed, content=None):
    full = (content or "").lower() + " " + _embed_text(embed)
    return _find_wave_in_text(full)

def _parse_single_choice(text, label):
    risk = "unknown risk"
    for r in ["very high risk", "high risk", "low risk", "very low risk"]:
        if r in text:
            risk = r
            break
    reward = ""
    for prefix in [f"{label})", f"{label} :", f"{label}:"]:
        if prefix in text:
            reward = text.split(prefix, 1)[-1].strip()
            break
    return {"risk": risk, "reward": reward}

def _parse_choice_text(text, result):
    if not result.get("A") and ("a)" in text or "a :" in text or "a:" in text):
        result["A"] = _parse_single_choice(text, "a")
    if not result.get("B") and ("b)" in text or "b :" in text or "b:" in text):
        result["B"] = _parse_single_choice(text, "b")

def parse_surf_choices(embed, content=None, wave=None):
    result = {}
    if embed:
        if embed.fields:
            for field in embed.fields:
                text = (field.name.lower() if field.name else "") + " " + (field.value.lower() if field.value else "")
                _parse_choice_text(text, result)
        if embed.description and len(result) < 2:
            _parse_choice_text(embed.description.lower(), result)
    if len(result) < 2 and content:
        lines = content.lower().split("\n")
        for line in lines:
            if line.startswith("a)") or line.startswith("a:"):
                result["A"] = _parse_single_choice(line, "a")
            elif line.startswith("b)") or line.startswith("b:"):
                result["B"] = _parse_single_choice(line, "b")
    if (not result or len(result) < 2 or result.get("A", {}).get("risk") == "unknown risk") and wave in SURF_WAVE_DATA:
        return SURF_WAVE_DATA[wave]
    return result if len(result) == 2 else (SURF_WAVE_DATA.get(wave) if wave else None)

def choose_surf_answer(wave, strategy, choices=None):
    if not choices and wave in SURF_WAVE_DATA:
        choices = SURF_WAVE_DATA[wave]
    if not choices or "A" not in choices or "B" not in choices:
        return "a"
    risk_a = RISK_ORDER.get(choices["A"]["risk"], 1)
    risk_b = RISK_ORDER.get(choices["B"]["risk"], 1)
    if strategy == "aggressive":
        return "b" if risk_b >= risk_a else "a"
    else:
        return "a" if risk_a <= risk_b else "b"

def _embed_text(embed):
    if not embed:
        return ""
    import json
    return json.dumps(embed.to_dict(), ensure_ascii=False).lower()

def detect_surf_result(content, embed):
    c = (content or "") + " " + _embed_text(embed)
    if "slipped off the surfboard" in c:
        return "fell"
    if "you have surfed recently" in c:
        return "cooldown"
    if "try not to slip off the surfboard" in c:
        return "prompt"
    if "deforestation" in c or "completionist" in c or "punched a tree" in c:
        return None
    if "completed" in c and ("surf" in c or "wave" in c) and not "quest" in c:
        return "completed"
    return None

def handle_surf_completion(rounds_completed):
    bot_state.summer_surf_rounds += rounds_completed
    bot_state.summer_last_action_time = time.time()
    bot_state.surf_in_progress = False
    HUD.oracle(f"Summer Surf: +{rounds_completed} round(s) ({bot_state.summer_surf_rounds} total)")

def initiate_surf():
    if bot_state.surf_in_progress:
        HUD.cooldown("Summer Surf: ja em andamento")
        return False
    now = time.time()
    if now < bot_state.summer_surf_cooldown_until:
        remaining = bot_state.summer_surf_cooldown_until - now
        HUD.cooldown(f"Summer Surf: cooldown {remaining:.0f}s restante")
        return False
    add_to_low_priority_queue("rpg smr surf")
    HUD.command("rpg smr surf (Summer)", priority="LPQ")
    bot_state.surf_in_progress = True
    bot_state.summer_surf_cooldown_until = time.time() + SURF_COOLDOWN
    return True

def handle_surf_cooldown_detected(cooldown_text):
    bot_state.surf_in_progress = False
    bot_state.summer_last_action_time = time.time()
    seconds = _parse_remaining_time(cooldown_text or "")
    if seconds:
        bot_state.summer_surf_cooldown_until = time.time() + seconds
        HUD.cooldown(f"Summer Surf: cooldown {seconds}s atualizado")

def detect_active_boosts(embed_text):
    boosts = {}
    matches = BOOST_PATTERN.findall(embed_text)
    for name, remaining_str in matches:
        name = name.strip().lower()
        if not re.search(r'\d+[hdms]', remaining_str):
            continue
        remaining_seconds = _parse_remaining_time(remaining_str)
        boosts[name] = remaining_seconds
    return boosts

def _resolve_boost_key(raw_name):
    raw = raw_name.lower().strip()
    for key, aliases in BOOST_NAME_ALIASES.items():
        if any(alias in raw for alias in aliases):
            return key
    return None

def queue_boosts_check():
    if bot_state.surf_in_progress:
        return
    add_to_low_priority_queue("rpg boosts")
    HUD.command("rpg boosts (summer check)", priority="LPQ")

def handle_boost_response(boosts, raw_content=""):
    now = time.time()
    if not boosts:
        rc = raw_content.lower()
        if "boost" in rc and ("active" in rc or "remaining" in rc):
            HUD.system("Summer Boost Check: nenhum boost ativo — enfileirando todos")
        else:
            return
    active_keys = set()
    if not boosts:
        boosts = {}
    for raw_name, remaining in boosts.items():
        key = _resolve_boost_key(raw_name)
        if key and key in BOOST_DEFS:
            active_keys.add(key)
            expires_at = now + remaining
            bot_state.summer_boosts_active[key] = expires_at
            mins = remaining // 60
            secs = remaining % 60
            HUD.system(f"{key.title()}: ativo ({mins}m{secs}s restante)")

    if "summer boost" not in active_keys and not getattr(bot_state, "summer_boost_exhausted", False):
        bot_state.summer_boosts_active.pop("summer boost", None)
        defn = BOOST_DEFS["summer boost"]
        if defn["craft_cmd"]:
            add_to_low_priority_queue(defn["craft_cmd"])
            HUD.command(f"{defn['craft_cmd']} (boost renew)", priority="LPQ")

    _renew_missing_drinks()

def _request_inventory_check():
    if bot_state.summer_waiting_inventory:
        return
    bot_state.summer_waiting_inventory = True
    add_to_high_priority_queue("rpg i")
    HUD.command("rpg i (summer inventory check)", priority="HPQ")
    HUD.system("Summer Boost: inventario nao carregado — consultando rpg i para verificar materiais")

def _renew_missing_drinks():
    now = time.time()
    active_keys = {k for k, exp in bot_state.summer_boosts_active.items() if exp > now}

    all_drink_keys = ["blue drink", "green drink", "pink drink", "yellow drink"]
    fav_color = config.summer_drink_choice.lower().strip()
    fav_key = f"{fav_color} drink"

    ordered_drink_keys = []
    if fav_key in all_drink_keys:
        ordered_drink_keys.append(fav_key)
    for k in all_drink_keys:
        if k not in ordered_drink_keys:
            ordered_drink_keys.append(k)

    for key in ordered_drink_keys:
        if key in active_keys:
            continue
        defn = BOOST_DEFS[key]
        bot_state.summer_boosts_active.pop(key, None)
        color = key.split(" ")[0]
        drink_qty = getattr(bot_state, f"inventory_{color}_drink", 0)
        if drink_qty > 0:
            if defn["use_cmd"]:
                add_to_low_priority_queue(defn["use_cmd"])
                HUD.command(f"{defn['use_cmd']} (boost renew)", priority="LPQ")
        elif bot_state.summer_inventory_known:
            if has_materials_for_drink(color):
                if defn["craft_cmd"]:
                    add_to_low_priority_queue(defn["craft_cmd"])
                    HUD.command(f"{defn['craft_cmd']} (boost renew)", priority="LPQ")
            else:
                HUD.system(f"Summer Boost: {key} ignorado (faltam materiais e craft drinks).")
        else:
            _request_inventory_check()
            break

def queue_drink_craft(color):
    drink_key = f"{color} drink"
    now = time.time()
    if drink_key in bot_state.summer_boosts_active and bot_state.summer_boosts_active[drink_key] > now:
        logger.info(f"Summer: {drink_key} já está ativo ({bot_state.summer_boosts_active[drink_key] - now:.0f}s restante). Ignorando craft fallback.")
        return
    if not bot_state.summer_inventory_known:
        _request_inventory_check()
        return
    if has_materials_for_drink(color):
        bot_state.summer_last_craft_color = color
        cmd = f"rpg smr craft {color} drink"
        add_to_low_priority_queue(cmd)
        HUD.command(f"{cmd} (craft fallback)", priority="LPQ")
    else:
        HUD.system(f"Summer Boost: craft {color} drink ignorado (faltam materiais)")

def handle_yellow_craft_no_resources():
    """Trata a falta de recursos ao craftar a yellow drink.
    Enfileira automaticamente os comandos de compra de ingrediente:
    - rpg epic shop buy epic seed
    - rpg buy lottery ticket
    E re-enfileira a tentativa de craft da yellow drink."""
    if getattr(bot_state, "summer_yellow_buy_attempted", False):
        HUD.alert("Summer Craft: yellow — falhou novamente apos tentativa de compra. Ignorando.")
        bot_state.summer_yellow_buy_attempted = False
        return

    bot_state.summer_yellow_buy_attempted = True
    HUD.oracle("Summer Craft: yellow sem recursos — comprando epic seed e lottery ticket!")

    # Compra dos ingredientes da Yellow Drink
    add_to_high_priority_queue("rpg epic shop buy epic seed")
    HUD.command("rpg epic shop buy epic seed (yellow drink)", priority="HPQ")

    add_to_high_priority_queue("rpg buy lottery ticket")
    HUD.command("rpg buy lottery ticket (yellow drink)", priority="HPQ")

    # Re-enfileira a tentativa de craft da yellow drink
    bot_state.summer_last_craft_color = "yellow"
    add_to_low_priority_queue("rpg smr craft yellow drink")
    HUD.command("rpg smr craft yellow drink (retry pos-compra)", priority="LPQ")

def queue_drink_use(color):
    cmd = f"rpg smr drink {color} drink"
    add_to_low_priority_queue(cmd)
    HUD.command(f"{cmd} (drink use)", priority="LPQ")

def add_summer_work_task(command: str, target: int):
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

def _complete_current_work_task(command):
    bot_state.summer_work_queue = [
        t for t in bot_state.summer_work_queue if t["command"] != command
    ]
    HUD.oracle(f"Summer Work: task '{command}' completa!")
    _advance_to_next_work()

def _advance_to_next_work():
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
        add_to_low_priority_queue("rpg smr task")

def increment_summer_work_count(command: str):
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

def on_work_command_failed():
    bot_state.summer_work_fail_count += 1
    HUD.alert(f"Summer Work: falha #{bot_state.summer_work_fail_count}/{MAX_WORK_RETRIES}")
    if bot_state.summer_work_fail_count >= MAX_WORK_RETRIES:
        failed_work = bot_state.summer_current_work
        bot_state.summer_work_queue = [
            t for t in bot_state.summer_work_queue if t["command"] != failed_work
        ]
        HUD.alert(f"Summer Work: task '{failed_work}' desistiu apos {MAX_WORK_RETRIES} falhas")
        send_telegram_notification(f"\u26a0\ufe0f Summer: work task `{failed_work}` falhou {MAX_WORK_RETRIES}x — removida da fila")
        _advance_to_next_work()

def activate_work_queue():
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

def detect_tasks_in_message(content):
    if not content:
        return []
    content = re.sub(r'\s+(weekly|daily)\s+tasks\s*\|', r'\n\1 tasks |', content, flags=re.IGNORECASE)
    tasks = []
    for match in TASK_PATTERN.finditer(content):
        current = int(match.group(1))
        target = int(match.group(2))
        full_name = match.group(3).strip()
        if any(ignored in full_name.lower() for ignored in IGNORED_TASKS):
            HUD.system(f"Summer Task: ignorada (excluida): {full_name}")
            continue
        tasks.append({
            "name": full_name,
            "current": current,
            "target": target,
            "full_name": full_name,
        })
        
    for match in QUEST_PATTERN.finditer(content):
        name = match.group(1).strip()
        name = re.sub(
            r'^(?:progress:\s*)?(?:completed\s*[|]?\s*|reward\s*claimed!?\s*[|]?\s*)+',
            '',
            name,
            flags=re.IGNORECASE,
        ).strip()

        if "!" in name and not name.endswith("!"):
            parts = name.split("!")
            if parts[-1].strip():
                name = parts[-1].strip()
                
        full_name = name
        progress_str = match.group(2).lower()
        if progress_str == "completed":
            current = 1
            target = 1
        else:
            current = int(match.group(3))
            target = int(match.group(4))
            
        if any(ignored in full_name.lower() for ignored in IGNORED_TASKS):
            HUD.system(f"Summer Quest: ignorada (excluida): {full_name}")
            continue
            
        tasks.append({
            "name": full_name,
            "current": current,
            "target": target,
            "full_name": full_name,
        })
        
    return tasks

def classify_task(task_name):
    name = task_name.lower()
    for key, pattern in KNOWN_TASKS.items():
        if re.search(pattern, name):
            return key
    return "unknown"

def has_materials_for_drink(color):
    c = bot_state.inventory_chopped_coconut >= 3
    if color == "blue":
        return c and bot_state.inventory_normiefish >= 2
    elif color == "pink":
        return c and bot_state.inventory_edgy_lootbox >= 1
    elif color == "green":
        return c and bot_state.inventory_epic_fish >= 1 and bot_state.inventory_chip >= 1
    elif color == "yellow":
        return c and bot_state.inventory_epic_seed >= 1 and bot_state.inventory_banana >= 3 and bot_state.inventory_lottery_ticket >= 1
    return False

def _queue_craft_drink():
    drink = config.summer_drink_choice
    if drink in DRINK_RECIPES:
        bot_state.summer_last_craft_color = drink
        if has_materials_for_drink(drink):
            add_to_low_priority_queue(DRINK_RECIPES[drink]["command"])
            HUD.command(f"{DRINK_RECIPES[drink]['command']} (summer task)", priority="LPQ")
        else:
            HUD.system(f"Summer Task: craft {drink} drink ignorada (faltam materiais)")

def _queue_duel_task(task_name=""):
    partner_id = config.duel_partner_id
    if not partner_id:
        HUD.system("Summer Task: duel ignorada — nenhum duel_partner_id configurado")
        return

    name_lower = (task_name or "").lower()
    if "win" in name_lower:
        config.win_duel = True
        mode_str = "win"
        HUD.system("Summer Task: Duel (WIN) — config.win_duel alterado para True")
    elif "lose" in name_lower or "duelisn" in name_lower:
        config.win_duel = False
        mode_str = "lose"
        HUD.system("Summer Task: Duel (LOSE) — config.win_duel alterado para False")
    else:
        config.win_duel = False
        mode_str = "lose (default)"
        HUD.system(f"Summer Task: Duel ({mode_str}) — config.win_duel alterado para False")

    add_to_low_priority_queue(f"rpg duel <@{partner_id}>")
    HUD.command(f"rpg duel @{partner_id} (summer task — {mode_str})", priority="LPQ")

def _queue_task_action(task):
    task_type = classify_task(task["name"])
    need = task["target"] - task["current"]
    logger.info(f"[SUMMER-TASK-DEBUG] _queue_task_action: type={task_type}, name={task['name']!r}, need={need}")
    if task_type == "rules":
        add_to_low_priority_queue("rpg rules")
        HUD.command("rpg rules (summer task)", priority="LPQ")
    elif task_type == "support":
        add_to_low_priority_queue("rpg support")
        HUD.command("rpg support (summer task)", priority="LPQ")
    elif task_type == "fish":
        add_summer_work_task("fish", need)
    elif task_type == "chop" or task_type == "chop_coconut" or task_type == "deforestation":
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
        _queue_duel_task(task["name"])
    elif task_type == "altruism":
        if getattr(bot_state, "inventory_ruby", 0) >= 1 and getattr(bot_state, "inventory_mermaid_hair", 0) >= 20:
            add_to_low_priority_queue("rpg smr craft pool float")
            HUD.command("rpg smr craft pool float (summer task altruism)", priority="LPQ")
        elif getattr(bot_state, "inventory_ruby", 0) < 1 and getattr(bot_state, "inventory_mermaid_hair", 0) >= 20 and getattr(bot_state, "inventory_edgy_lootbox", 0) >= 1:
            add_to_low_priority_queue("rpg open ed")
            HUD.command("rpg open ed (summer task altruism fallback)", priority="LPQ")
        else:
            HUD.system("Summer Task: altruism ignorado (faltam itens: 1 ruby, 20 mermaid hair)")
    elif task_type == "help":
        add_to_low_priority_queue("rpg help hunt")
        add_to_low_priority_queue("rpg help enchant")
        add_to_low_priority_queue("rpg help adventure")
        HUD.command("rpg help hunt/enchant/adventure (summer task)", priority="LPQ")
    elif task_type == "sleepy":
        if config.summer_use_sleepy_potion:
            add_to_high_priority_queue("rpg smr use sleepy potion")
            HUD.command("rpg smr use sleepy potion (summer task)", priority="HPQ")
        else:
            HUD.system("Summer Task: sleepy potion ignorada (config desativado)")
    elif task_type == "rare_mob":
        HUD.system("Summer Task: rare mob tracking ativo (hunt natural)")
    elif task_type == "surf_rounds":
        HUD.system(f"Summer Task: surf rounds pendente (need {need}) — loop de surf cuida disso")
    elif task_type == "completionist":
        HUD.system("Summer Task: completionist pendente — depende das outras 4 quests")
    elif task_type == "unboxing":
        add_to_low_priority_queue("rpg open ed")
        HUD.command("rpg open ed (summer task — unboxing)", priority="LPQ")
    elif task_type in ("slots", "stonks"):
        add_to_low_priority_queue("rpg slots 100")
        HUD.command("rpg slots 100 (summer task)", priority="LPQ")
    elif task_type == "trade":
        bot_state.pending_trade_letter = "a"
        add_to_low_priority_queue("rpg trade a 1")
        HUD.command("rpg trade a 1 (summer task — trade of the day)", priority="LPQ")
    elif task_type == "dismantle":
        start_dismantle_task(need, task["name"])
    else:
        logger.warning(f"[SUMMER-TASK-DEBUG] unknown task type: {task_type}, name={task['name']!r}")

def start_dismantle_task(need_qty=3, task_name=""):
    name_qty_match = re.search(r'dismantle\s+(\d+)', task_name.lower())
    name_qty = int(name_qty_match.group(1)) if name_qty_match else 0
    qty = max(need_qty, name_qty, 1)

    bot_state.summer_dismantle_qty = qty
    bot_state.summer_dismantle_index = 0
    bot_state.summer_dismantle_in_progress = True
    bot_state.summer_dismantle_crafting_fallback = False

    first_item = bot_state.summer_dismantle_options[0]
    cmd = f"rpg dismantle {first_item} {bot_state.summer_dismantle_qty}"
    add_to_low_priority_queue(cmd)
    HUD.command(f"{cmd} (summer task — dismantle 1/4)", priority="LPQ")

def handle_dismantle_response(content, embed=None):
    if not getattr(bot_state, "summer_dismantle_in_progress", False) or not config.do_summer:
        return

    last_cmd = (bot_state.last_sent_command or "").lower()
    if "dismantle" not in last_cmd and not (bot_state.summer_dismantle_crafting_fallback and "craft" in last_cmd):
        return

    full_text = (content or "").lower()
    if embed:
        import json
        full_text += " " + json.dumps(embed.to_dict(), ensure_ascii=False).lower()

    # Success detection
    if "successfully dismantled" in full_text or "you dismantled" in full_text or "dismantled " in full_text or "successfully crafted" in full_text or "crafted!" in full_text:
        HUD.oracle("Summer Task: Dismantle concluído com sucesso!")
        bot_state.summer_dismantle_in_progress = False
        bot_state.summer_dismantle_index = 0
        bot_state.summer_dismantle_crafting_fallback = False
        return

    # Check for craft success when in fallback mode
    if bot_state.summer_dismantle_crafting_fallback and ("successfully crafted" in full_text or "crafted!" in full_text):
        if "epic log" in full_text:
            HUD.oracle("Summer Task: Craft de epic log para fallback realizado! Desmantelando agora...")
            cmd = f"rpg dismantle epic log {bot_state.summer_dismantle_qty}"
            add_to_low_priority_queue(cmd)
            HUD.command(f"{cmd} (summer task — pós-craft fallback)", priority="LPQ")
            return

    # Failure detection for dismantle or craft
    is_fail = any(kw in full_text for kw in ["don't have enough", "you don't have", "invalid item", "cannot dismantle", "not enough"])
    if is_fail:
        if bot_state.summer_dismantle_crafting_fallback:
            HUD.alert("Summer Task: Dismantle/Craft fallback falhou por falta de materiais. Encerrando tentativas.")
            bot_state.summer_dismantle_in_progress = False
            bot_state.summer_dismantle_crafting_fallback = False
            return

        bot_state.summer_dismantle_index += 1
        if bot_state.summer_dismantle_index < len(bot_state.summer_dismantle_options):
            next_item = bot_state.summer_dismantle_options[bot_state.summer_dismantle_index]
            cmd = f"rpg dismantle {next_item} {bot_state.summer_dismantle_qty}"
            HUD.alert(f"Summer Task: Dismantle de '{bot_state.summer_dismantle_options[bot_state.summer_dismantle_index - 1]}' falhou. Tentando '{next_item}'...")
            add_to_low_priority_queue(cmd)
            HUD.command(f"{cmd} (summer task — dismantle {bot_state.summer_dismantle_index + 1}/4)", priority="LPQ")
        else:
            bot_state.summer_dismantle_crafting_fallback = True
            HUD.oracle("Summer Task: Todas as 4 opções de dismantle falharam. Tentando craftar 1 epic log como fallback...")
            add_to_low_priority_queue("rpg craft epic log 1")
            HUD.command("rpg craft epic log 1 (summer task — craft fallback)", priority="LPQ")

def process_task_updates(tasks):
    completed = []
    for task in tasks:
        if task["target"] == 0:
            continue
        task_key = f"{task['name']}_{task['target']}"
        if task_key in bot_state.summer_tasks_claimed:
            continue
        task_type = classify_task(task["name"])
        if task["current"] >= task["target"]:
            if task_key in bot_state.summer_pending_tasks:
                completed.append(task["full_name"])
                bot_state.summer_pending_tasks.discard(task_key)
            bot_state.summer_tasks_claimed.add(task_key)
        else:
            logger.info(f"[SUMMER-TASK-DEBUG] incomplete task: name={task['name']!r}, type={task_type}, current={task['current']}, target={task['target']}")
            bot_state.summer_pending_tasks.add(task_key)
            _queue_task_action(task)
    return completed

def claim_tasks():
    add_to_low_priority_queue("rpg smr task")
    HUD.command("rpg smr task (claim)", priority="LPQ")

def claim_tournament_codes():
    add_to_low_priority_queue("WINNERCOLOR")
    add_to_low_priority_queue("LOSERCOLORS")
    HUD.command("WINNERCOLOR / LOSERCOLORS (claim torneio)", priority="LPQ")

def get_quest_section_progress(full_text, section_name):
    if section_name not in full_text:
        return "not_found"
    after = full_text.split(section_name, 1)[1]
    for other in ["deforestation", "conquer", "mega", "completionist"]:
        if other != section_name and other in after:
            after = after.split(other, 1)[0]
    if "completed" in after or "claimed" in after:
        return "completed"
    if "0/1" in after or "0/2" in after or "0/3" in after or "0/15" in after:
        return "pending"
    return "unknown"

def _is_section_completed(full_text, section_name):
    return get_quest_section_progress(full_text, section_name) == "completed"

def handle_summer_quest_message(content, embed=None):
    if not config.do_summer:
        return

    full_text = (content or "").lower()
    if embed:
        import json
        full_text += " " + json.dumps(embed.to_dict(), ensure_ascii=False).lower()

    if not any(kw in full_text for kw in ["punched a tree", "deforestation", "completionist", "turtlepet"]):
        return

    HUD.system("Summer Quest: menu de quest detectado")



    completionist_claimed = _is_section_completed(full_text, "completionist")

    completed_count = 0
    for q_name in ["deforestation", "conquer", "mega"]:
        if _is_section_completed(full_text, q_name):
            completed_count += 1

    if (completed_count >= 3 or "3/3" in full_text) and not completionist_claimed:
        HUD.oracle(f"🏆 Summer Quest: {completed_count}/4 sub-quests concluídas! Reivindicando Turtle Pet...")
        add_to_low_priority_queue("I LOVE EPIC RPG")
        add_to_high_priority_queue("rpg smr quest")
    elif completionist_claimed:
        bot_state.summer_quest_completed = True
        HUD.oracle("🏆 Summer Quest TOTALMENTE CONCLUÍDA! Turtle Pet resgatado com sucesso!")

def _check_daily_reset(now):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if bot_state.summer_daily_date and bot_state.summer_daily_date != today:
        bot_state.summer_tasks_claimed = set()
        bot_state.summer_coconut_count = 0
        bot_state.summer_rules_sent = False
        bot_state.summer_craft_fail_count = 0
        bot_state.summer_work_queue = []
        bot_state.summer_current_work = None
        bot_state.summer_work_fail_count = 0
        bot_state.summer_last_task_list = ""
        bot_state.summer_last_craft_color = None
        if bot_state.summer_work_original:
            config.work_command = bot_state.summer_work_original
            bot_state.summer_work_original = ""
        bot_state.summer_last_task_check = 0
        bot_state.summer_daily_date = today
        add_to_low_priority_queue("rpg smr task")
        HUD.command("rpg smr task (reset diario)", priority="LPQ")
        HUD.system(f"Summer: reset diario — nova data: {today}")
    elif not bot_state.summer_daily_date:
        bot_state.summer_daily_date = today

def _check_work_queue_consistency():
    if bot_state.summer_current_work is None:
        return
    if not any(t["command"] == bot_state.summer_current_work for t in bot_state.summer_work_queue):
        bot_state.summer_current_work = None
        if bot_state.summer_work_original:
            config.work_command = bot_state.summer_work_original
            bot_state.summer_work_original = ""
        HUD.system("Summer: work queue inconsistente — resetado")

def _check_stuck_state(now):
    if not bot_state.summer_work_queue and not config.do_summer:
        return
    if bot_state.summer_last_action_time == 0:
        return
    idle_time = now - bot_state.summer_last_action_time
    if idle_time > STUCK_TIMEOUT:
        HUD.alert(f"Summer: possivelmente travado — {idle_time:.0f}s sem acao")
        if bot_state.summer_work_queue:
            send_telegram_notification(
                f"\u26a0\ufe0f Summer: bot parece travado a {int(idle_time)}s com tasks pendentes"
            )
        if bot_state.summer_current_work:
            config.work_command = bot_state.summer_work_original
            bot_state.summer_current_work = None
        bot_state.summer_last_action_time = now

def _check_boost_expiry(now):
    """Native boost expiry tracker. Checks each boost's absolute timestamp
    and immediately re-queues the drink/buy command when it expires.
    No dependency on Navi or any third-party bot."""
    if not bot_state.summer_boosts_active:
        return
    expired_keys = []
    for key, expires_at in bot_state.summer_boosts_active.items():
        if now >= expires_at - BOOST_RENEW_BUFFER:
            expired_keys.append(key)
    if not expired_keys:
        return
    fav_color = config.summer_drink_choice.lower().strip()
    fav_key = f"{fav_color} drink"
    if fav_key in expired_keys:
        expired_keys.remove(fav_key)
        expired_keys.insert(0, fav_key)
    for key in expired_keys:
        del bot_state.summer_boosts_active[key]
        if key not in BOOST_DEFS:
            continue
        defn = BOOST_DEFS[key]
        if key == "summer boost":
            if defn["craft_cmd"]:
                add_to_low_priority_queue(defn["craft_cmd"])
                HUD.command(f"{defn['craft_cmd']} (boost expirou)", priority="LPQ")
                HUD.alert(f"Summer Boost expirou — recomprando")
        else:
            if defn["use_cmd"]:
                add_to_low_priority_queue(defn["use_cmd"])
                HUD.command(f"{defn['use_cmd']} (drink expirou)", priority="LPQ")
                HUD.alert(f"{key.title()} expirou — reativando")

def _check_weekly_reset():
    now = datetime.now(timezone.utc)
    if now.weekday() == 0 and now.hour == 0 and now.minute < 5:
        if bot_state.summer_drink_this_week:
            bot_state.summer_drink_this_week = False
            bot_state.summer_color_team = None
            bot_state.summer_last_task_list = ""
            claim_tournament_codes()
            HUD.system("Summer: reset semanal — resgatando códigos do torneio e nova semana")

def check_mega_surfboard_craft():
    if not config.do_summer:
        return
    if bot_state.summer_mega_surfboard_crafted:
        return
    if bot_state.summer_mega_palm_log_count >= 5 and bot_state.summer_palm_log_count >= 100:
        bot_state.summer_mega_surfboard_crafted = True
        HUD.oracle(
            f"Summer: Requisitos atingidos! ({bot_state.summer_mega_palm_log_count} Mega Palm Logs, {bot_state.summer_palm_log_count} Palm Logs) -> Craftando MEGA Surfboard!"
        )
        add_to_low_priority_queue("rpg smr craft mega surfboard")
        HUD.command("rpg smr craft mega surfboard (auto-craft)", priority="LPQ")

def summer_tick():
    now = time.time()
    if bot_state.surf_in_progress and (now - bot_state.summer_last_action_time) > 45:
        bot_state.surf_in_progress = False
        HUD.system("Summer Surf: watchdog liberou trava de surf inativo")
    _check_daily_reset(now)
    check_mega_surfboard_craft()
    if now - bot_state.summer_last_task_check >= 43200:
        bot_state.summer_last_task_check = now
        add_to_low_priority_queue("rpg smr task")
        HUD.command("rpg smr task (check)", priority="LPQ")
    if not bot_state.summer_quest_completed and now - bot_state.summer_last_quest_check >= 43200:
        bot_state.summer_last_quest_check = now
        add_to_low_priority_queue("rpg smr quest")
        HUD.command("rpg smr quest (check)", priority="LPQ")
    _check_work_queue_consistency()
    if bot_state.summer_work_queue and bot_state.summer_current_work is None:
        activate_work_queue()
    _check_stuck_state(now)
    _check_boost_expiry(now)
    if now >= bot_state.summer_boosts_check_at:
        bot_state.summer_boosts_check_at = now + BOOST_CHECK_INTERVAL
        queue_boosts_check()
    if not bot_state.summer_drink_this_week:
        now_dt = datetime.now(timezone.utc)
        if now_dt.weekday() == 0 and 0 <= now_dt.hour < 6:
            drink_color = config.summer_drink_choice
            drink_key = f"{drink_color} drink"
            if drink_key in bot_state.summer_boosts_active and bot_state.summer_boosts_active[drink_key] > now:
                bot_state.summer_drink_this_week = True
            else:
                queue_drink_use(drink_color)
                bot_state.summer_drink_this_week = True
                HUD.system(f"Summer: segunda-feira — enfileirando {drink_color} drink para torneio")

def detect_sunglasses_part_a(content):
    if not content:
        return False
    return "completed the surf course" in content.lower()

def detect_sunglasses_part_b(content):
    if not content:
        return False
    return "sunglasses" in content.lower()

def get_summer_status():
    lines = []
    lines.append("=== Summer Event Status ===")
    lines.append(f"Mode: {'ON' if config.do_summer else 'OFF'}")
    if config.do_summer:
        now = time.time()
        lines.append(f"Strategy: {config.summer_surf_strategy}")
        lines.append(f"Drink: {config.summer_drink_choice}")
        lines.append(f"Color Team: {bot_state.summer_color_team or 'not set'}")
        lines.append(f"Drink This Week: {bot_state.summer_drink_this_week}")
        cooldown = bot_state.summer_surf_cooldown_until - now
        if cooldown > 0:
            lines.append(f"Surf Cooldown: {cooldown:.0f}s remaining")
        else:
            lines.append("Surf Cooldown: READY")
        lines.append(f"Surf Rounds: {bot_state.summer_surf_rounds}")
        lines.append(f"Work Queue: {len(bot_state.summer_work_queue)} tasks")
        if bot_state.summer_current_work:
            lines.append(f"Current Work: {bot_state.summer_current_work}")
        lines.append("--- Boosts Ativos ---")
        if bot_state.summer_boosts_active:
            for key, expires_at in bot_state.summer_boosts_active.items():
                remaining = expires_at - now
                if remaining > 0:
                    m, s = divmod(int(remaining), 60)
                    h, m = divmod(m, 60)
                    lines.append(f"  {key.title()}: {h}h{m}m{s}s")
                else:
                    lines.append(f"  {key.title()}: EXPIRADO")
        else:
            lines.append("  Nenhum boost ativo")
        lines.append(f"Tasks Claimed Today: {len(bot_state.summer_tasks_claimed)}")
        lines.append(f"Daily Date: {bot_state.summer_daily_date}")
    return "\n".join(lines)
