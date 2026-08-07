# Plano 07 — Jail Feedback & Dashboard Overhaul

> Revitalizacao do feedback de jail (visual, sonoro e via Telegram) + reformulacao completa da dashboard React com tab sazonal Summer.
> **Revisao em 2026-08-05** — Definicoes de escopo fechadas; nada implementado ainda.

---

## 1. Contexto

O Oracle v3 tem dois problemas independentes:

1. **Jail (prisao)** — Quando o bot trava no captcha/prisao, hoje envia **uma** notificacao no Telegram (`send_telegram_notification`) e nada mais. Nao ha feedback recorrente, nem sonoro, nem visual na dashboard.
2. **Dashboard** — As tabs (Overview/Stats) sao funcionais mas basicas: contadores crus, listas planas, sem graficos. O Summer Event aparece como badge de uma linha no card de estado, sem tab propria.

### Objetivos

1. Feedback multifacetado de jail: Telegram recorrente a cada 15m (configuravel) **sem spam**, som do SO no Windows/Linux a cada lembrete, e **tema vermelho** em toda a dashboard enquanto preso.
2. Reformular Overview e Stats com visual profissional (graficos SVG puros, sem lib nova).
3. Adicionar **tab sazonal Summer**, que aparece/desaparece conforme `do_summer`.

---

## 2. Descoberta arquitetural (critica para ambos)

> ⚠️ O bot roda como **subprocesso** (`launch_dashboard.py --run-bot` → `BotProcessManager` em `dashboard_server.py`). Portanto `from bot.state import bot_state` dentro do `dashboard_server.py` cria uma **instancia separada/stale** no processo do dashboard.

Consequencias graves:
- O bloco atual `summer` do `/api/status` (`dashboard_server.py:786-805`) le `bot_state` do processo do dashboard → retorna valores padrao (stale).
- `bot_state.jailed` no dashboard seria sempre `False` — tema vermelho nunca ligaria apenas lendo `bot_state`.

**Solucao central:** um **JSON de status vivo compartilhado** — o bot (subprocesso) grava periodicamente, o dashboard le. Mesmo canal ja usado pelos stats (`user_data/stats_totals.json`).

**Arquivo novo:** `user_data/live_<profile>.json` (perfil via `options_resolver.USER_DATA_DIR` / `profile_stem`, mesmo padrao de `persistence.py`).

---

## 3. FASE A — Jail Feedback

### A1. `bot/live_status.py` (NOVO)

Gerencia o JSON de status vivo compartilhado com o dashboard.

```python
def update_live_status() -> None:
    """Monta payload de bot_state + config + sessionData e grava live_<profile>.json.
    JSON atômico (temp + rename), try/except — nunca quebra o bot."""
```

Payload minimo da Fase A:

```json
{
  "jailed": false,
  "jail_started_at": 0.0,
  "jail_elapsed": 0.0
}
```

**Quando chamar:**
- Nas transicoes de jail (imediato, via `on_jail_detected` / `on_jail_released` do A2)
- No loop de save existente (`client.py:710`, dentro do bloco `SAVE_INTERVAL`)

**Nota: atender `get_opt_int` — ver A6.**

### A2. `bot/jail_feedback.py` (NOVO) — nucleo

```python
def play_jail_alarm()                  # som do SO (A4)
def on_jail_detected()                 # alarme + persiste status + inicia loop
def on_jail_released()                 # apaga msg telegram + cancela loop + persiste
async def _jail_repeat_loop()          # envia msg NOVA + apaga antiga a cada intervalo
```

**Fluxo de mensagens no Telegram (sem spam):**
- Estado guarda `bot_state.jail_message_id`
- A cada intervalo (configuravel):
  1. `send_telegram_raw(msg_elapsed)` → retorna `message_id` novo
  2. `delete_telegram_message(message_id_anterior)` (se existir)
  3. atualiza `jail_message_id`
- Resultado: **apenas 1 mensagem de jail visivel**, sempre com conteudo atualizado (tempo decorrido)
- No release: apaga a ultima mensagem

**Intervalo configuravel:** `interval = getattr(config, "jail_notify_interval_min", 15) * 60`, lido a cada iteracao — mudanca em runtime vale.

### A3. `bot/telegram.py` — adicionar `delete_telegram_message`

```python
async def delete_telegram_message(message_id) -> None:
    # POST https://api.telegram.org/bot<token>/deleteMessage
    # try/except, log de erro
```

### A4. `play_jail_alarm()` — a cada deteccao E a cada lembrete

- **Windows:** `winsound.Beep(1000, 400)` + `time.sleep(0.1)` + `winsound.Beep(1500, 400)`
- **Linux** (cadeia de fallback, sempre `subprocess.Popen` — nao bloqueia o loop):
  1. `paplay <arquivo>`
  2. `aplay -q <arquivo>`
  3. `ffplay -nodisp -autoexit <arquivo>`

  Arquivos candidatos: `/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga`, `/usr/share/sounds/freedesktop/stereo/complete.oga`, `/usr/share/sounds/alsa/Front_Center.wav`
  4. Ultimo recurso: `printf '\a'` (bell do terminal)
- Tudo em `try/except: pass` — nunca quebra o bot

### A5. Pontos de chamada

**Entrada** (`on_jail_detected()`):
- `client.py:1453` (deteccao primaria "is now in the jail")
- `client.py:1478` (feedback imediato / ja preso antes do start)
- `captcha.py:245` (captcha falhou)

**Saida** (`on_jail_released()`):
- `client.py:1503` (liberdade detectada)
- `handlers.py:3238` ("fine, i will let you go")
- `captcha.py:241` (Epic Guard liberou)
- `state.py:542` (`reset_bot_state`)

**`bot/state.py` — novos campos em `BotState.__init__`:**
```python
self.jail_repeat_task = None      # asyncio.Task
self.jail_started_at = 0.0
self.jail_message_id = None
```

### A6. Config `jail_notify_interval_min` (padrao AGENTS.md §4.2)

- `config.py`: `get_opt_int("jail_notify_interval_min", 15)` (adicionar helper `get_opt_int` junto de `get_opt`/`get_opt_bool`, `config.py:191-202`)
- `options_example.ini`: `jail_notify_interval_min=15`
- `tui_modals.py`: adicionar em `CONFIG_FIELDS` e `CONFIG_METADATA`
- `ConfigTab.jsx`: `<TextField field="jail_notify_interval_min" ...>`

### A7. Dashboard — TEMA VERMELHO (tela inteira, automatico)

- **Backend** `dashboard_server.py` `/api/status`: carregar `live_<profile>.json` → adicionar `jailed`, `jailElapsed` ao `status_data`
- **Store** `useOracleStore.js`: novos campos `jailed: false`, `jailElapsed: 0` (setar em `fetchStatus` e no handler WS `status`). **Nao** reutilizar `botState` (preserva logica Start/Stop)
- **App.jsx**: root div `className={jailed ? "theme-jailed" : ""}`
- **index.css**: bloco `.theme-jailed` sobrescreve variaveis:
  - `--accent-danger` → vermelho vivo pulsante
  - `--bg-void` → tingido de vermelho
  - borda vermelha nos `.glass`, `scanline` avermelhado
  - banner superior "🚨 PRESO"
- **StatusBadge.jsx**: estado `jailed` → pill vermelha "PRESO" (reuso nas 3 instancias: OverviewTab, Header, ProfileSidebar)

---

## 4. FASE B — Dashboard Overhaul + Tab Summer

### B0. Adaptacoes obrigatorias ao plano original

1. **Payload do summer NAO le `bot_state`** no dashboard (stale) — vem do `live_<profile>.json` (Fase A). O bloco em `dashboard_server.py:786` sera substituido para ler o JSON.
2. **Inventario**: `summer_coconut_count` / `summer_palm_log_count` / `summer_mega_palm_log_count` vem do live JSON; demais itens (`banana`, `ruby`, `mermaid_hair`, `lottery_ticket`, `chip`, `epic_seed`, peixes) vem de `sessionData["loot_data"]` (ja compartilhado via stats).
3. **Cooldowns da Overview** (hunt/adv/quest/daily/weekly) tambem via live JSON.

### B1. Backend — expandir payload do live status (summer)

Adicionar ao `update_live_status()`:

```python
summer = {
  "active": config.do_summer,
  "strategy": config.summer_surf_strategy,
  "color_team": bot_state.summer_color_team,
  "drink_choice": config.summer_drink_choice,
  "surf_rounds": bot_state.summer_surf_rounds,
  "surf_cooldown_remaining": ...,
  "tasks_claimed": list(bot_state.summer_tasks_claimed),
  "pending_tasks": list(bot_state.summer_pending_tasks),
  "quest_completed": bot_state.summer_quest_completed,
  "daily_date": bot_state.summer_daily_date,
  "drink_this_week": bot_state.summer_drink_this_week,
  "beach_party_active": bot_state.summer_beach_party_active,
  "arena_in_progress": bot_state.arena_in_progress,
  "boost_exhausted": bot_state.summer_boost_exhausted,
  "inventory": { coconut, chopped_coconut, normiefish, epic_fish, edgy_lootbox, chip, epic_seed, banana, lottery_ticket, ruby, mermaid_hair, palm_log, mega_palm_log },
  "drinks": { blue, pink, green, yellow },
  "boosts_active": {...},
  "boost_count": ...,
}
```

Nota: campos `summer_drink_*` (estoque dos drinks) — verificar nomes reais em `bot/summer.py` no momento da implementacao.

### B2. Summer Tab sazonal

- **`TabNav.jsx`**: prop `summerActive` → adiciona `{ key: "summer", label: "Summer", Icon: Sun }` quando `live.summer.active === true`
- **`App.jsx`**: renderiza `<SummerTab/>` condicional; `useEffect` volta p/ overview se a tab summer desaparecer
- **`useOracleStore.js`**: `fetchStatus` extrai `status.summer` → `summerData`; armazena historico p/ sparklines (30 pontos client-side)
- **Timers**: `setInterval(1000)` decrementa localmente usando `remaining` da API como seed; recalibra a cada poll de 5s; flash verde "READY" a 0

Layout: Summer Status Hero → Timers (surf CD + boosts) → Tasks & Quest → Drink Crafting Station (4 cards) → Inventory Grid.

### B3. Overview redesign

- Hero Card unificado (estado + perfil + event badges, com glow)
- KPI Strip (6 mini-cards + trend arrows ▲▼)
- Activity Sparklines (ultimos 30 polls)
- Cooldown Tracker (barras de progresso: hunt/adv/quest/daily/weekly)
- Quick Actions re-agrupadas com icones e separadores
- Drops com barras proporcionais por categoria

### B4. Stats redesign

- Donut/Pie Chart de distribuicao de comandos (SVG puro)
- Horizontal stacked bars p/ drops por categoria
- Card collection estilo "card game" (raridades com gradient e brilho proporcional)
- Modo comparativo session/total lado a lado com delta indicators (▲)
- Stat highlight cards ("Most dropped: Wolf Skin (32x)")

### B5. Componentes novos reutilizaveis

| Componente | Descricao | Usado em |
|---|---|---|
| `CountdownTimer.jsx` | Timer frontend (recalibra no poll). Variantes `ring` e `bar` | Summer, Overview |
| `ProgressRing.jsx` | SVG circular progress com label central | Summer surf CD |
| `SparklineChart.jsx` | Mini grafico SVG inline (ultimos N pontos) | Overview |
| `DonutChart.jsx` | Grafico donut SVG puro | Stats |
| `InventoryGrid.jsx` | Grid de itens com icones e tooltips | Summer |
| `DrinkCard.jsx` | Card de drink com receita e viabilidade | Summer |
| `TaskTracker.jsx` | Lista de tasks com estados visuais | Summer |
| `BoostTimeline.jsx` | Barras de boost horizontais com timers | Summer |
| `CooldownBar.jsx` | Barra de cooldown com label e timer | Overview |

### B6. Visual Polish global

- `index.css`: `--accent-summer #f59e0b`, `--accent-summer-dim`, `--shadow-glow-summer`; classes `glass-summer`, `pulse-ready`, `fade-in-up`, `glow-on-hover`
- GlassCards: hover `translateY(-1px)` + box-shadow; entrada animada framer-motion
- Header: event badges dinâmicos (Summer, Arena, Beach Party) + HPQ/LPQ inline
- ProfileSidebar: mini-status summer por perfil; gradients sutis nos cards

---

## 5. Ordem de execucao

1. **FASE A compartilhada** — `live_status.py`, `save_live_status`, `delete_telegram_message` (pre-requisito de ambos)
2. **FASE A jail** — feedback, alarme, tema vermelho, config
3. **FASE B1 backend** — expandir payload summer no live status
4. **FASE B2** — Summer Tab
5. **FASE B3/B4/B5/B6** — Overview, Stats, componentes, polish

---

## 6. Checklist de validacao (AGENTS.md §3)

- [ ] `py_compile` em todos os .py modificados (`bot/live_status.py`, `bot/jail_feedback.py`, `bot/telegram.py`, `bot/state.py`, `bot/client.py`, `bot/captcha.py`, `bot/handlers.py`, `bot/config.py`)
- [ ] Verificar todas as interfaces (AGENTS.md §2): config no config.py + tui_modals + ConfigTab
- [ ] 1 mensagem de jail visivel por vez no Telegram (nova + apaga antiga)
- [ ] Som reproduz ao detectar e a cada 15m (ou intervalo configurado)
- [ ] Tema vermelho liga/desliga automaticamente com `jailed`
- [ ] Tab Summer aparece/desaparece com `do_summer` sem dados residuais
- [ ] Dashboard offline: dados vazios sem crash / fallback
- [ ] Timers decrementam suavemente e recalibram no poll
- [ ] `cd dashboard && npm run build` sem erros
- [ ] Latencia de ~5-10s aceita no status vivo (poll de 5s)

---

## 7. Decisoes confirmadas

| Tema | Decisao |
|---|---|
| Tema vermelho | Automatico quando preso (sem toggle manual) |
| Telegram | Mensagem nova + apaga antiga (1 visivel por vez, sem spam) |
| Intervalo | Configuravel `jail_notify_interval_min` (default 15) |
| Alarme | A cada deteccao E a cada lembrete |
| Latencia | 5-10s aceitavel por enquanto (poll de 5s do dashboard) |
| Graficos | SVG puro, sem lib extra |

---

## 8. Documentacao

- Este documento: `plans/07_jail_feedback_and_dashboard_overhaul.md`
- Ao implementar, atualizar `README.md` e `docs/README.pt-BR.md` conforme AGENTS.md §8.2