# Plano Detalhado de Migracao Navi → Oracle Nativo

> Baseado nos cogs do Navi v3.6.0 (verificacao in-loco em 2026-07-26)
> **Estado atual: NADA implementado.** Todos os modulos abaixo precisam ser criados.

---

## Fase 1 — CooldownManager (Substituir `cogs/cooldowns.py` + `database/cooldowns.py`)

### Estado Atual
Oracle depende do Navi Lite para detectar cooldowns via slash commands e re-enfileirar comandos via `rdCheckNavi()` em `bot/parsers.py`.

### Referencia Navi
- `cogs/cooldowns.py` (434 linhas): Detecta `/cd` embed, extrai timestrings, cria Reminders no DB
- `database/cooldowns.py`: Tabela de cooldowns base + event reductions
- `resources/regex.py`: Padroes multi-idioma para extracao de timestrings

### Justificativa para Implementacao Nativa
1. **Latencia:** Bridge Navi adiciona ~1-3s de delay (Navi processa → envia slash → Oracle detecta)
2. **Ponto unico de falha:** Se Navi reiniciar, Oracle perde tracking de cooldowns
3. **Precisao:** Timer local e mais preciso que depender de terceiros
4. **Manutencao:** Codigo do Navi e MIT licenced, pode ser adaptado livremente

### Correcoes em Relacao ao Plano Original

| Item no Plano Original | Correcao | Justificativa |
|---|---|---|
| `BASE_COOLDOWNS` sem "lottery" | Incluir "lottery": 43200 | Necessario para Fase 7 |
| `BASE_COOLDOWNS` com "epic": 604800 | Confirmado com Wiki | Cooldowns.md: "7 days" |
| `BASE_COOLDOWNS` com "card_hand": 7200 | Confirmado com Wiki | Cooldowns.md: "2 hours" |
| `donor_cd_reduction` padrao 0.35 | Manter | Mesmo valor do Navi database/cooldowns.py |
| Falta `pocket_watch_multiplier` | **ADICIONAR** | Estava em plan_1_existing.md e foi perdido na migracao para plans/ |
| `reduce_all()` sem parametro `activity_filter` | **ADICIONAR** | Time Cookie so afeta hunt/adv, nao todos |

### Implementacao Oracle (Corrigida)

```python
# bot/services/cooldowns.py
class CooldownManager:
    BASE_COOLDOWNS = {
        "hunt": 60, "adventure": 3600, "training": 900,
        "work": 300, "farm": 600, "quest": 21600,
        "daily": 86400, "weekly": 604800, "lootbox": 10800,
        "duel": 7200, "arena": 7200, "dungeon": 14400,
        "card_hand": 7200, "epic": 604800, "horse": 7200,
        "lottery": 43200, "sell": 3600, "trade": 3600,
    }

    def __init__(self, donor_cd_reduction=0.35, event_reduction=0.0,
                 pocket_watch_multiplier=1.0):
        self._timers: dict[str, float] = {}
        self.donor_multiplier = 1.0 - donor_cd_reduction
        self.event_multiplier = 1.0 - event_reduction
        # Pocket watch: 1.0 = normal, 0.5 = dobra duracao (inverte)
        self.pocket_watch_multiplier = pocket_watch_multiplier

    def get_effective_cooldown(self, activity: str) -> int:
        base = self.BASE_COOLDOWNS[activity]
        cd = int(base * self.donor_multiplier * self.event_multiplier)
        # Pocket watch aumenta cooldown efetivo
        if self.pocket_watch_multiplier < 1.0:
            cd = int(cd / self.pocket_watch_multiplier)
        return cd

    def mark_used(self, activity: str) -> None:
        self._timers[activity] = time.monotonic() + self.get_effective_cooldown(activity)

    def is_ready(self, activity: str) -> bool:
        return time.monotonic() >= self._timers.get(activity, 0)

    def get_ready_activities(self) -> list[str]:
        return [a for a in self.BASE_COOLDOWNS if self.is_ready(a)]

    def reduce_all(self, seconds: float, activities: list[str] | None = None) -> None:
        targets = activities or list(self._timers.keys())
        for act in targets:
            if act in self._timers:
                self._timers[act] -= seconds

    def get_remaining(self, activity: str) -> float:
        return max(0, self._timers.get(activity, 0) - time.monotonic())
```

### Integracao Detalhada

| Arquivo | Mudanca | Codigo |
|---|---|---|
| `bot/state.py` | Instanciar CooldownManager | `bot_state.cooldown_mgr = CooldownManager()` |
| `bot/client.py` | No loop principal, checar ready activities | `for act in bot_state.cooldown_mgr.get_ready_activities(): queue_command(act)` |
| `bot/parsers.py` | Detectar execucao bem-sucedida → mark_used | `bot_state.cooldown_mgr.mark_used("hunt")` |
| `bot/parsers.py` | Detectar time cookie/sleepy potion → reduce_all | `bot_state.cooldown_mgr.reduce_all(minutes * 60, activities=["hunt", "adventure"])` |
| `bot/handlers.py` | Manter bloco Navi como fallback | `if not config.use_internal_timers: usar Navi` |
| `bot/config.py` | Nova config | `use_internal_timers`, `donor_cd_reduction`, `event_cd_reduction`, `pocket_watch_multiplier` |

---

## Fase 2 — TrainingSolver (Substituir `cogs/helper_training.py`)

### Estado Atual
Oracle depende do Navi para resolver minigames de training. O Navi envia a resposta via slash command, e o Oracle extrai do texto.

### Referencia Navi
- `cogs/helper_training.py`: Detecta mensagem de training, resolve, envia resposta
- `resources/strings.py`: Constantes para cada tipo de training
- Suporte a button mode (UI buttons via discord.components) e text mode

### Modos de Training (Navi — Verificado)

| Modo | Trigger Regex | Logica | Resposta |
|---|---|---|---|
| River | `(r|river|rio)!` | `<:epicfish` → 3, `<:goldenfish` → 2, `<:normiefish` → 1 | `"3"`, `"2"`, `"1"` |
| Field | `(f|field|campo)!` | Fruta + posicao ordinal → letra | `"A"`, `"P"`, etc. |
| Casino | `(c|casino|cassino)?` | Emoji == item perguntado? | `"yes"` / `"no"` |
| Forest | `(fo|forest|bosque)!` | Contar emojis antes do `?` | `"7"`, `"3"`, etc. |
| Ruby/Mine | `(m|mine|mina)!` | X > ruby_counter? | `"yes"` / `"no"` |
| Void | `(v|void|vac o|vazio)!` | Sequencia de emojis → match posicao | `<emoji>` |

### Advertencia: Void Mode
O Void mode do Navi usa caracteres unicode especificos para emojis. O Oracle precisara de um mapa de emojis → nomes para funcionar corretamente. `resources/emojis.py` do Navi tem estes mapeamentos.

### Implementacao Oracle (Strategy Pattern)

```python
# bot/services/solvers.py
class TrainingSolver(ABC):
    @abstractmethod
    def can_solve(self, content: str) -> bool: ...
    @abstractmethod
    def solve(self, content: str) -> str | None: ...

class SolverRegistry:
    _solvers: list[TrainingSolver] = [
        RiverSolver(), FieldSolver(), CasinoSolver(),
        ForestSolver(), RubySolver(), VoidSolver(),
    ]

    def solve(self, content: str) -> str | None:
        for solver in self._solvers:
            if solver.can_solve(content):
                return solver.solve(content)
        return None
```

### RubyTracker (Baseado em `cogs/helper_ruby.py`)

| Fonte | Regex | Acao |
|---|---|---|
| Work | `got X <:ruby` / `conseguiu X <:ruby` | `ruby += X` |
| Lootbox | `+X <:ruby` | `ruby += X` |
| Trade | Trade confirmado com X rubies | `ruby += X` |
| Inventory | `ruby: X,XXX` | `ruby = X` (sync) |
| Craft | Ruby sword: -4, Ruby armor: -7 | `ruby -= custo` |
| Sell | Vendeu X rubies | `ruby -= X` |

---

## Fase 3 — HealthMonitor (Substituir `cogs/helper_heal.py`)

### Estado Atual
Oracle detecta heal via Navi. Quando o Navi posta um aviso de heal, o Oracle enfileira `rpg heal`.

### Referencia Navi
- `cogs/helper_heal.py` (298 linhas): Formula validada em producao
- Formula: `health_lost > (health_remaining - (health_lost / 10))` para hunt solo
- Para hunt together: dividir por 9 em vez de 10

### Casos Especiais (Copiados do Navi + plan_1_existing.md)

| Situacao | Acao | Origem |
|---|---|---|
| Area 16 | `rpg buy life` em vez de `rpg heal` | Navi |
| Omega Sword forge | Heal apos forjar (HP = 1) | Navi + Plano 1 |
| Dragon Breath Potion | Heal apos usar pocao | Navi + Plano 1 |
| Event mobs (christmas slime, etc.) | **NAO** heal | Navi |
| TOP mobs (hunt/adventure top) | **NAO** heal | Navi |
| Boost ativo (mega-boost, etc.) | **NAO** heal | Navi + BoostTracker |
| Heal ja na fila | Pular | Oracle state.py |

### Configs Novas (Resgatadas do plan_1_existing.md)
```ini
auto_heal_enabled = true
auto_heal_interval = 30
heal_on_omega_sword = true
heal_on_dragon_breath = true
```

---

## Fase 4 — PetCatchSolver (Substituir `cogs/helper_pets.py`)

### Estado Atual
Nao implementado no Oracle.

### Referencia Navi
- `cogs/helper_pets.py`: Detecta pet embed, extrai happiness/hunger, calcula sequencias
- Dois modos: `Lowest Risk` e `Higher Skill Chance`

### Algoritmo de Calculo (Navi — Verificado)

```
FEED_MIN = 18, FEED_MAX = 22   # hunger reduzido por feed
PAT_MIN = 8, PAT_MAX = 12      # happiness ganho por pat
MAX_ACTIONS = 6

Lowest Risk:
  feeds = ceil(hunger / FEED_MIN)
  if hunger % FEED_MIN >= 9: feeds += 1
  happiness_needed = (hunger_rest + 85) - happiness
  pats = min(MAX_ACTIONS - feeds, ceil(happiness_needed / PAT_MIN))
  if feeds + pats > 6: pats = 6 - feeds

Higher Skill:
  feeds = ceil(hunger / FEED_MAX)
  if hunger % FEED_MAX >= 9: feeds += 1
  happiness_needed = (hunger_rest + 85) - happiness
  pats = min(MAX_ACTIONS - feeds - 1, ceil(happiness_needed / PAT_MAX))
  if pats < 0: pats = 0
```

---

## Fase 5 — AreaDetector (Substituir `cogs/current_area.py`)

### Estado Atual
Oracle tem `config.current_area` estatico. Precisa ser atualizado manualmente.

### Referencia Navi
- `cogs/current_area.py`: Detecta area de multiplas fontes
- `strings.MONSTERS_AREA`: Tabela de mobs por area (essencial)

### Fontes de Deteccao

| Trigger | Fonte | Acao |
|---|---|---|
| Time Travel | Mensagem do jogo | Area = 1 |
| Mob na hunt | Embed de hunt | Match em MONSTERS_AREA |
| Comando move | Mensagem do jogo | Area = X |
| Candy cane | Evento de natal | Area += 1 |
| Zombie event | Evento global | Area = 2 |
| Ruby dragon | Evento global | Area = None |

### MONSTERS_AREA (Dados do Navi + Guide)

Tabela completa disponivel em:
- `~/Navi/Navi/resources/strings.py` — tabela MONSTERS_AREA
- `~/Epic-RPG-Guide/content/monsters.py` — dados de monstros
- `data/wiki_docs/locations/` — descricoes de areas

---

## Fase 6 — BoostTracker (Substituir `cogs/boosts.py`)

### Referencia Navi
- `cogs/boosts.py` (797 linhas): Parse completo do embed `/boosts`
- Detecta: mega-boost, egg-blessing, potion-potion, dragon-breath, round-card, flask-potion, etc.

### Implementacao Simplificada

```python
class BoostTracker:
    BOOST_DURATIONS = {
        "party-popper": 3600, "halloween-boost": 9000,
        "christmas-boost": 14400, "summer-boost": 14400,
        "easter-boost": 3600, "valentine-boost": 3600,
        "egg-blessing": 2592000, "mega-boost": 2592000,
        "potion-potion": 3600, "dragon-breath-potion": 3600,
        "flask-potion": 3600, "round-card": 3600,
    }

    def is_auto_healing_active(self) -> bool:
        return any(self.is_active(b) for b in
                   ["mega-boost", "egg-blessing", "potion-potion"])

    def should_suppress_heal(self) -> bool:
        return self.is_auto_healing_active()
```

---

## Fase 7 — EventDetector + Seasonal Events

### Eventos Globais Detectaveis

| Evento | Trigger | Acao | Janela |
|---|---|---|---|
| Coin Rain | "coins are raining" | `catch` | ~15s |
| Arena | "type `join`" | `join` | ~30s |
| Megalodon | "megalodon has spawned" | `catch` | ~20s |
| Epic Tree | "epic tree has grown" | `chop` | ~20s |
| Lootbox Summon | "lootbox summoning" | `summon` | ~30s |
| Miniboss | "type `fight`" | `fight` | ~30s |
| Legendary Boss | Embed com botao | `fight` | ~60s |

### Eventos Sazonais com Dados Completos

| Evento | Navi Cog | Fonte Guide | Prioridade |
|---|---|---|---|
| Christmas | xmas.py | content/xmas.py (41 KB) | 🟡 Media |
| Halloween | halloween.py | content/halloween.py (12 KB) | 🟡 Media |
| Valentine | — | content/valentine.py (7 KB) | 🟢 Baixa |
| Easter | easter.py | content/easter.py (14 KB) | 🟢 Baixa |
| Summer | summer.py | content/summer.py (18 KB) | 🟢 Baixa |
| Horse Festival | horse_race.py | content/horse_festival.py (14 KB) | 🟢 Baixa |
| Anniversary | celebration.py | content/celebration.py (4 KB) | 🟢 Baixa |

---

## Resumo de Novos Arquivos (Atualizado)

| Arquivo | Fase | Fonte | Descricao | Status |
|---|---|---|---|---|
| `bot/services/cooldowns.py` | Fase 1 | Navi cogs/cooldowns.py + database/cooldowns.py | CooldownManager | ❌ Nao criado |
| `bot/services/solvers.py` | Fase 2,4 | Navi helper_training.py + helper_pets.py + helper_ruby.py | TrainingSolver + PetCatchSolver + RubyTracker | ❌ Nao criado |
| `bot/services/health.py` | Fase 3 | Navi helper_heal.py + Plano 1 original | HealthMonitor | ❌ Nao criado |
| `data/game_data/__init__.py` | Data | Guide content/ + Wiki Docs | GameData singleton | ❌ Nao criado |
| `data/game_data/*.json` | Data | Guide content/ + Wiki Docs | Dados de jogo estaticos | ❌ Nao criado |
| `bot/services/area_detector.py` | Fase 5 | Navi current_area.py | AreaDetector | ❌ Nao criado |
| `bot/services/boost_tracker.py` | Fase 6 | Navi boosts.py | BoostTracker | ❌ Nao criado |
| `bot/services/event_joiner.py` | Fase 7 | Novo | EventAutoJoiner | ❌ Nao criado |
| `tools/extract_game_data.py` | Data | — | Script de extracao | ❌ Nao criado |
| `tests/` | QA | — | Testes unitarios (pytest) | ❌ Nao criado |

## Nota sobre `docs/plan_1_existing.md` e `docs/plan_2_future.md`

Os arquivos `docs/plan_1_existing.md` e `docs/plan_2_future.md` contem informacoes que NAO foram integralmente portadas para `plans/`. Divergencias documentadas:

1. `plan_1_existing.md` usa `bot/cooldowns.py` (raiz de bot/) enquanto plans/ usa `bot/services/cooldowns.py`
2. `plan_1_existing.md` tem `pocket_watch_multiplier` no CooldownManager — perdido na migracao para plans/
3. `plan_1_existing.md` tem `heal_on_omega_sword` e `heal_on_dragon_breath` como configs — em plans/ sao apenas casos especiais
4. `plan_2_future.md` Fase 5 nao menciona `AreaDetector.update_from_move()` mas plans/ sim

**Recomendacao:** Remover ou arquivar os docs antigos apos confirmacao de que plans/ cobre todos os casos.
