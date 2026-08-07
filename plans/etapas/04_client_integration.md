# Stage 4 — Client Integration: `client.py`

## Objective

Integrate all summer event logic into `client.py`: channel filter bypass for arena/beach party, `on_message` hooks for summer detection, `summer_tick` in the main background loop, work override integration in command dispatch, and SB summer command handlers. After this stage, the bot can actively participate in the summer event.

---

## 1. Channel Filter Bypass (Critical — Must Be in Section 2)

### Location: `client.py`, Section 2 Channel Filter (~lines 1111-1132)

**IMPORTANT:** The bypass must be placed **inside the Channel Filter section** (before the `if message.channel.id != config.channelID` gate at line 1128). If placed after, messages from other channels are already dropped.

### Add after the existing duel bypass (after line 1126, before line 1128)

```python
# ─── Summer Event Bypass ───
if bot_state.summer_mode and message.author.id == config.EPIC_RPG_ID:
    # Arena: allow join prompts from any channel in the configured guild
    if hasattr(message, 'guild') and message.guild and message.guild.id == config.GUILD_ID:
        combined_lower = combined_content.lower()
        if embed_dicts:
            combined_lower += " " + " ".join(str(e).lower() for e in embed_dicts)
        if ("arena" in combined_lower and any(kw in combined_lower for kw in ["join", "start", "boost"])):
            is_invite = True
            logger.info("Summer Arena: bypass do channel filter ativado")
```

**Note:** Do NOT add a standalone `summer_mode` bypass that allows all messages. Only specific patterns (arena, beach party) should bypass the channel filter.

---

## 2. Summer Message Detection in `on_message`

### Location: After Section 3 (Status Detection), before Section 4 (Pause Gatekeeper)

Place summer message detection at **line ~1563** (just before `# ─── 4. Pause Gatekeeper`), so summer processing occurs even when paused (except for pause-sensitive actions like sending commands).

### Add at line ~1561

```python
# ═══════════════════════════════════════════════
# Summer Event Detection
# ═══════════════════════════════════════════════
if bot_state.summer_mode and message.author.id == config.EPIC_RPG_ID:
    content = message.content or ""
    embed = message.embeds[0] if message.embeds else None

    # Quick pre-filter to avoid parsing every message
    from bot.parsers import is_summer_related_message
    if not is_summer_related_message(content, embed):
        pass  # Skip detailed parsing
    else:
        await handle_summer_message(message, content, embed)
```

### Add the `handle_summer_message` coroutine

Define this as a helper method on the bot class, or as a standalone coroutine. Place it near the summer detection section:

```python
async def handle_summer_message(self, message, content, embed=None):
    """Main dispatcher for summer event message processing.
    Routes to the correct handler based on message content."""
    from bot.parsers import (
        handle_surf_response,
        handle_summer_task_message,
        handle_summer_boost_message,
        detect_craft_result,
        detect_color_team,
        detect_summer_drops,
    )
    from bot.summer import (
        detect_beach_party_invite,
        join_beach_party,
        detect_sunglasses_part_a,
        detect_sunglasses_part_b,
        detect_surf_result,
    )

    embed_dict = embed.to_dict() if embed else {}
    embed_text = str(embed_dict)
    full_text = (content or "") + " " + embed_text

    # 1. Surf detection (highest priority)
    if "surf" in full_text or "try not to slip" in full_text:
        action = handle_surf_response(content, embed)
        if action and action.startswith("respond_"):
            answer = action.split("_")[1]  # 'A' or 'B'
            # Human-like delay before responding
            import asyncio
            delay = random.uniform(1.5, 3.0)
            await asyncio.sleep(delay)
            from bot.state import add_to_high_priority_queue
            add_to_high_priority_queue(answer)
            logger.info(f"Summer Surf: resposta {answer} enviada após delay {delay:.1f}s")
            return

    # 2. Task list detection
    if "complete these tasks" in full_text or "daily tasks" in full_text or "task" in full_text:
        handle_summer_task_message(full_text)

    # 3. Boost detection
    if "boost" in full_text and ("remaining" in full_text or "active" in full_text):
        handle_summer_boost_message(content, embed)

    # 4. Craft result
    if "craft" in full_text:
        result = detect_craft_result(full_text)
        if result == "fail":
            # Retry craft after delay
            import asyncio
            await asyncio.sleep(random.uniform(2, 5))
            if bot_state.summer_craft_fail_count < 3:
                from bot.summer import _queue_craft_drink
                _queue_craft_drink()

    # 5. Color team detection
    if "drink" in full_text and ("team" in full_text or "tournament" in full_text):
        detect_color_team(full_text)

    # 6. Drops tracking
    if any(kw in full_text for kw in ["coconut", "slime", "sunglasses", "mega palm"]):
        detect_summer_drops(content, embed)

    # 7. Beach party invite
    if detect_beach_party_invite(content, embed):
        join_beach_party()
        return

    # 8. Surf cooldown after attempt
    if "you have surfed recently" in full_text:
        from bot.summer import handle_surf_cooldown_detected
        handle_surf_cooldown_detected(content)

    # 9. Work progress detection
    if bot_state.summer_current_work:
        cmd = bot_state.summer_current_work
        from bot.parsers import detect_work_progress
        from bot.summer import increment_summer_work_count
        if detect_work_progress(content, cmd):
            increment_summer_work_count(cmd)
```

**Note:** Add `import random` at the top of `client.py` if not already present.

---

## 3. Summer Tick in Main Background Loop

### Location: Inside `my_background_task()`, after the pet auto-claim section (~line 668)

### Add after line ~668

```python
# ─── Summer Event Tick ───
if config.do_summer and bot_state.summer_mode:
    if not hasattr(self, '_last_summer_tick'):
        self._last_summer_tick = 0

    now = time.time()
    if now - self._last_summer_tick >= 30:  # Every 30 seconds
        self._last_summer_tick = now
        from bot.summer import summer_tick, initiate_surf
        summer_tick()
        # Also try to surf if cooldown has expired
        initiate_surf()
```

---

## 4. Work Override Integration in Command Dispatch

### Location: In the main loop where `rpg work` equivalent commands are sent

The work command override (`config.work_command`) is already used by the main loop. When `bot_state.summer_current_work` is set (e.g., "fish" or "chop"), the main loop will use it as the work command automatically because `config.work_command` is modified by `activate_work_queue()`.

However, we need to make sure the work command integration is correct. Find where the main loop dispatches work commands (search for `config.work_command` in `client.py`).

### Add work failure detection

Where the work command response is processed, add:

```python
# In work command response handler:
if bot_state.summer_mode and bot_state.summer_current_work:
    content = message.content.lower() if message.content else ""
    if "you don't have enough energy" in content or "you're too tired" in content:
        from bot.summer import on_work_command_failed
        on_work_command_failed()
```

---

## 5. `handlers.py` — Summer State Label in `_get_state_label()`

### Location: In `_get_state_label()` (after line 90, after sleepet check)

```python
if bot_state.summer_mode:
    state_parts = ["Summer"]
    if bot_state.summer_current_work:
        state_parts.append(f"Work:{bot_state.summer_current_work}")
    if bot_state.summer_color_team:
        state_parts.append(f"Team:{bot_state.summer_color_team.upper()}")
    if bot_state.summer_surf_rounds > 0:
        state_parts.append(f"Surf:{bot_state.summer_surf_rounds}r")
    state_str = " ".join(state_parts)
    return f"🏖️ {state_str}", "special"
```

---

## 6. Handling Summer Mode Toggle (Start/Stop)

### In `client.py` — SB Commands section

Add SB summer command handler after the gather commands (after line ~763):

```python
# ─── SUMMER EVENT ───
elif msg == "sb summer start":
    if not config.do_summer:
        logger.info("Summer Event: do_summer=false — habilite em options.ini primeiro")
        return
    bot_state.summer_mode = True
    bot_state.summer_last_action_time = time.time()
    bot_state.summer_daily_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    HUD.system("🏖️ Summer Event Mode ATIVADO")
    # Queue initial actions
    from bot.summer import manage_boost_renewal
    manage_boost_renewal()
    return

elif msg == "sb summer stop":
    bot_state.summer_mode = False
    # Restore original work command if overridden
    if bot_state.summer_work_original:
        config.work_command = bot_state.summer_work_original
        bot_state.summer_work_original = ""
    bot_state.summer_current_work = None
    bot_state.summer_work_queue = []
    HUD.system("🏖️ Summer Event Mode DESATIVADO")
    return

elif msg == "sb summer status":
    from bot.summer import get_summer_status
    status = get_summer_status()
    logger.info(status)
    # Also send to Discord
    channel = self.get_channel(config.channelID)
    if channel:
        try:
            await channel.send(f"```{status}```")
        except Exception:
            pass
    return

elif msg == "sb summer sleepy":
    if config.summer_use_sleepy_potion:
        from bot.state import add_to_high_priority_queue
        add_to_high_priority_queue("rpg smr use sleepy potion")
        HUD.command("rpg smr use sleepy potion (manual override)", priority="HPQ")
        logger.info("Summer: sleepy potion manual acionado via sb summer sleepy")
    else:
        logger.info("Summer: summer_use_sleepy_potion=false — nao e possivel usar sleepy potion")
    return
```

---

## 7. Help Text for `sb help`

### Location: `client.py` SB command section, in the help text message (~lines 987-1003)

This is the **Discord** help text (sent as a message to the channel). Add a summer section to it.

In the help message construction (where other commands are listed), add:

```python
"\n=== Summer Event ===\n"
"sb summer start   : Ativa automacao do evento Summer\n"
"sb summer stop    : Desativa automacao do Summer\n"
"sb summer status  : Mostra status detalhado do Summer\n"
"sb summer sleepy  : Usa sleepy potion manualmente (task weekly)\n"
```

---

## Acceptance Criteria

1. `python3 -c "import py_compile; py_compile.compile('bot/client.py', doraise=True)"` — passes
2. `python3 -c "import py_compile; py_compile.compile('bot/handlers.py', doraise=True)"` — passes
3. Channel filter bypass works: arena invites on guild channels are allowed through
4. Summer message detection only activates when `bot_state.summer_mode is True`
5. `handle_summer_message()` routes correctly: surf → A/B response, tasks → queue work, boosts → track renewal
6. Summer tick runs every ~30s in the background loop
7. Work queue override changes `config.work_command` correctly
8. `sb summer start` activates mode and queues initial boost renewal
9. `sb summer stop` deactivates mode and restores original work command
10. `sb summer status` returns formatted status to Discord
11. `sb summer sleepy` sends sleepy potion command (only if config allows)
12. State label shows `🏖️ Summer` with work/team/surf info when active
13. Human-like delay (1.5-3s) before surf responses
14. Work failure detection catches "no energy" / "too tired" errors
