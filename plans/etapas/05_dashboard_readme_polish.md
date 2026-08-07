# Stage 5 — Dashboard, README, Telegram, Final Polish

## Objective

Add summer event controls to the web Dashboard, update README documentation, integrate Telegram notifications for critical errors, add comprehensive logging, and perform end-to-end validation. After this stage, the feature is complete and ready for production use.

---

## 1. Dashboard — `ConfigTab.jsx`

### Location: `dashboard/src/tabs/ConfigTab.jsx`

### Add summer fields to the config array

Find where other feature toggles are defined (look for `do_gather`, `do_pet`, etc.). Add:

```javascript
// ─── Summer Event ───
{ field: "do_summer", label: "Summer Event" },
{ field: "summer_surf_strategy", label: "Surf Strategy", type: "dropdown", options: ["conservative", "aggressive"] },
{ field: "summer_drink_choice", label: "Weekly Drink", type: "dropdown", options: ["blue", "green", "pink", "yellow"] },
{ field: "summer_use_sleepy_potion", label: "Auto Sleepy Potion (risky)" },
```

**Note:** The `field` value must match the key in `options.ini` exactly (e.g., `summer_surf_strategy`).

### Add tooltip descriptions (if ConfigTab uses tooltips)

```javascript
"do_summer": "Enable Summer Event automation (surf, tasks, boosts, crafting)",
"summer_surf_strategy": "Surf risk strategy — conservative (safe) or aggressive (more rewards, more falls)",
"summer_drink_choice": "Drink color for the weekly color tournament (blue = doubled crafting, recommended)",
"summer_use_sleepy_potion": "⚠️ Automatically use sleepy potion to complete the weekly task. Advances game 24h!",
```

---

## 2. Dashboard — Status Display

### Location: `dashboard/src/tabs/OverviewTab.jsx` (or the status display component)

### Add summer status indicator

Find the status/summary section where modes like "Sleepet", "Gather", "TC" are shown. Add:

```javascript
// In the status/overview panel:
{botState.summer_mode && (
  <div className="status-badge summer">
    <span>🏖️ Summer</span>
    <span className="sub-status">
      {botState.summer_current_work ? `Work: ${botState.summer_current_work}` : ''}
      {botState.summer_color_team ? ` | Team: ${botState.summer_color_team.toUpperCase()}` : ''}
      {botState.summer_surf_rounds > 0 ? ` | Surf: ${botState.summer_surf_rounds}r` : ''}
    </span>
  </div>
)}
```

---

## 3. Dashboard API — Summer Status Endpoint

### Location: `dashboard_server.py`

### Add summer fields to `/api/status` response

Find the status endpoint handler (look for `/api/status`). Add summer fields to the returned dict:

```python
# Summer event status (if active)
if hasattr(bot_state, 'summer_mode'):
    status_data["summer"] = {
        "active": bot_state.summer_mode,
        "strategy": config.summer_surf_strategy if hasattr(config, 'summer_surf_strategy') else None,
        "color_team": bot_state.summer_color_team,
        "drink_choice": config.summer_drink_choice if hasattr(config, 'summer_drink_choice') else None,
        "surf_rounds": bot_state.summer_surf_rounds,
        "work_queue_len": len(bot_state.summer_work_queue) if hasattr(bot_state, 'summer_work_queue') else 0,
        "current_work": bot_state.summer_current_work,
        "tasks_claimed_today": len(bot_state.summer_tasks_claimed) if hasattr(bot_state, 'summer_tasks_claimed') else 0,
        "surf_cooldown_remaining": max(0, int(bot_state.summer_surf_cooldown_until - time.time())) if hasattr(bot_state, 'summer_surf_cooldown_until') else 0,
    }
```

Add `time` import at the top if not present:
```python
import time
```

### Add error handling

The endpoint should handle cases where summer state doesn't exist (backward compatibility):

```python
try:
    summer_status = status_data.get("summer", {})
except (AttributeError, KeyError):
    summer_status = {"active": False}
```

---

## 4. Telegram Notifications

### Location: `bot/telegram.py` (no changes needed — it's already generic)

### Create notification helper in `bot/summer.py`

```python
def notify_summer_error(message: str):
    """Send a summer-related error notification via Telegram.
    Only for serious issues requiring user attention."""
    send_telegram_notification(f"🏖️ {message}")
    HUD.alert(f"Summer Telegram: {message}")


def notify_summer_info(message: str):
    """Send an informational summer notification via Telegram.
    Used for non-critical updates like task completion or boost renewal failure."""
    send_telegram_notification(f"ℹ️ Summer: {message}")
```

### Where to call these:

| Scenario | Function | When |
|----------|----------|------|
| Boost expired, no resources | `notify_summer_error()` | `manage_boost_renewal()` when < 50 chopped coconuts |
| Task stuck 10min | `notify_summer_error()` | `_check_stuck_state()` in summer_tick |
| Work command failed 5x | (already in `on_work_command_failed()`) | — |
| Craft failed 3x today | `notify_summer_error()` | `detect_craft_result()` in parsers |
| Work queue corrupted | `notify_summer_error()` | `_check_work_queue_consistency()` |
| Arena ignored (wrong guild) | `notify_summer_info()` | `handle_summer_message()` |
| Surf fell off board | HUD only (no Telegram) | `handle_surf_response()` |
| Task completed normally | HUD only (no Telegram) | `process_task_updates()` |
| Boost renewed ok | HUD only (no Telegram) | `manage_boost_renewal()` |

---

## 5. README.md

### Location: `README.md`

### Add to the commands table (discord `sb` commands section)

Add a new row or section:

```markdown
### Summer Event (🏖️)

| Command | Description |
|---------|-------------|
| `sb summer start` | Enable Summer Event automation |
| `sb summer stop` | Disable Summer Event automation |
| `sb summer status` | Show detailed Summer Event status |
| `sb summer sleepy` | Use sleepy potion for weekly task (manual) |
```

### Add to the config table

```markdown
| Config | Type | Default | Description |
|--------|------|---------|-------------|
| `do_summer` | bool | false | Enable Summer Event automation |
| `summer_surf_strategy` | string | conservative | Surf risk: conservative or aggressive |
| `summer_drink_choice` | string | blue | Weekly drink color: blue, green, pink, yellow |
| `summer_use_sleepy_potion` | bool | false | Auto-use sleepy potion for weekly task (⚠️ risky) |
```

---

## 6. Comprehensive Logging

### Add log points throughout the summer module

Every significant action should produce a `HUD.*()` log. Review the existing calls:

| Situation | Method | Message |
|-----------|--------|---------|
| Mode activated | `HUD.system()` | "🏖️ Summer Event Mode ATIVADO" |
| Mode deactivated | `HUD.system()` | "🏖️ Summer Event Mode DESATIVADO" |
| Surf initiated | `HUD.command()` | "rpg smr surf (Summer)" |
| Surf response | `HUD.dungeon()` | "Summer Surf: onda 'X' — escolhendo A (conservative)" |
| Surf fell | `HUD.alert()` | "Summer Surf: caiu do surfboard" |
| Surf completed | `HUD.oracle()` | "Summer Surf: +1 round(s) (X total)" |
| Surf cooldown | `HUD.cooldown()` | "Summer Surf: cooldown Xs atualizado" |
| Work task added | `HUD.system()` | "Summer Work: task 'X' adicionada (target Y)" |
| Work task completed | `HUD.oracle()` | "Summer Work: task 'X' completa!" |
| Work task failed | `HUD.alert()` | "Summer Work: falha #N/5" |
| Work queue empty | `HUD.system()` | "Summer Work: fila vazia, work original restaurado" |
| Craft success | `HUD.oracle()` | "Summer Craft: sucesso!" |
| Craft failed | `HUD.alert()` | "Summer Craft: falha (60% chance) #N" |
| Craft no resources | `HUD.alert()` | "Summer Craft: falhou — sem recursos" |
| Boost active | `HUD.system()` | "Summer Boost: ativo (Xs restante)" |
| Boost renewed | `HUD.command()` | "rpg smr buy summer boost (renew)" |
| Task detected | `HUD.system()` | "Summer Tasks: N task(s) detectadas" |
| Task completed | `HUD.oracle()` | "Summer Tasks completas: X, Y" |
| Task ignored | `HUD.system()` | "Summer Task: ignorada (excluida): X" |
| Color team set | `HUD.oracle()` | "Summer: time BLUE confirmado!" |
| Daily reset | `HUD.system()` | "Summer: reset diario — nova data: YYYY-MM-DD" |
| Stuck detected | `HUD.alert()` | "Summer: possivelmente travado — Xs sem acao" |
| Queue corrupted | `HUD.system()` | "Summer: work queue inconsistente — resetado" |
| Slime found | `HUD.oracle()` | "Summer Slime encontrado!" |
| Sunglasses found | `HUD.oracle()` | "Sunglasses artifact encontrado!" |
| Beach party joined | `HUD.command()` | "join (beach party)" |
| Beach party started | `HUD.command()` | "rpg smr beach party" |
| Coconut tracked | `HUD.system()` | "Summer: +N coconut(s) detectado(s)" |
| Weekly drink queued | `HUD.command()` | "rpg smr drink blue (weekly)" |
| Sleepy potion used | `HUD.command()` | "rpg smr use sleepy potion (manual override)" |

---

## 7. Final Validation Checklist

### Syntax Checks

```bash
python3 -c "import py_compile; py_compile.compile('bot/summer.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('bot/parsers.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('bot/client.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('bot/handlers.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('bot/state.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('bot/config.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('bot/tui_modals.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('bot/tui_input.py', doraise=True)"
```

### End-to-End API Test

```bash
# 1. Check status before activation
curl -s http://localhost:8000/api/status?profile=options.ini | python3 -m json.tool

# 2. Activate summer mode via API
curl -s -X POST http://localhost:8000/api/exec \
  -H "Content-Type: application/json" \
  -d '{"command": "say sb summer start", "profile": "options.ini"}'

# 3. Verify status shows summer active
curl -s http://localhost:8000/api/status?profile=options.ini | python3 -c "
import sys, json
data = json.load(sys.stdin)
summer = data.get('summer', {})
print(f\"Summer active: {summer.get('active')}\")
print(f\"Strategy: {summer.get('strategy')}\")
print(f\"Drink: {summer.get('drink_choice')}\")
"

# 4. Check logs for summer activity
curl -s "http://localhost:8000/api/logs?profile=options.ini&limit=30" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for entry in data.get('logs', [])[-10:]:
    if 'summer' in str(entry).lower() or 'Summer' in str(entry):
        print(entry)
"

# 5. Deactivate summer mode
curl -s -X POST http://localhost:8000/api/exec \
  -H "Content-Type: application/json" \
  -d '{"command": "say sb summer stop", "profile": "options.ini"}'

# 6. Verify config can be read
curl -s "http://localhost:8000/api/config?profile=options.ini" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for k in ['do_summer', 'summer_surf_strategy', 'summer_drink_choice']:
    val = data.get(k, 'NOT FOUND')
    print(f'{k} = {val}')
"
```

### Edge Case Tests

1. Start summer mode with `do_summer=false` → should warn and not activate
2. Start summer mode with no work queue → tick should not crash
3. Detect surf embed → parser extracts wave correctly
4. Receive task list with "devote" → task should be ignored
5. Craft fails 3x → should stop trying and notify
6. Work queue with 2 tasks → second starts after first completes
7. Same task added twice (smaller target) → kept with larger target
8. Arena invite from wrong guild → ignored with log
9. Stuck timeout (10min) → warms and resets
10. Daily date change → counters reset correctly

---

## Acceptance Criteria

1. Dashboard shows 🌴 Summer Event toggle with strategy/drink dropdowns
2. Dashboard API `/api/status` returns `summer` object with all fields
3. Telegram notifications fire for: boost no resources, stuck state, craft 3x fail, queue corruption
4. Telegram does NOT fire for: surf complete, task complete, boost renewed, drops
5. README.md updated with summer commands and config table
6. All 9 Python files pass `py_compile` syntax check
7. All curl API tests return correct data
8. All 10 edge case tests pass without crashes
9. Bot runs without errors when summer mode is off (backward compatible)
10. Bot runs without errors when summer mode is on but no summer event is happening
