# Relatorio de Cruzamento de Dados — Oracle V3

> **Data:** 2026-07-26 (v2 revisada)
> **Fontes analisadas:** Navi (v3.6.0, 39 cogs), Epic RPG Guide (33 cogs + 31 content), Wiki Docs (77 .md), Oracle-V2 (22 .py)

---

## 1. Resumo das Fontes (Verificado Empiricamente)

### 1.1 Oracle (Projeto Principal)
- **Tipo:** Self-bot Discord para automacao de Epic RPG
- **Linguagem:** Python 3.12 (discord.py-self)
- **Frontend:** React + Vite + FastAPI + Textual TUI
- **Tamanho real:** 22 arquivos .py em `bot/` (~6777 linhas totais), handlers.py isolado: 3287 linhas
- **Features atuais:** Hunt/Adventure loop, Auto-enchant, Duelo, Card Hand, Captcha AI (2 modelos CNN), Dashboard Web, TUI, Telegram notifications, Sleepet, Gambling, Time Cookie
- **Dependencia externa:** Navi Lite para cooldowns, training solver, heal warning, pet catch
- **Documentacao orfa:** `docs/plan_1_existing.md` e `docs/plan_2_future.md` ainda existem mas foram substituidos por `plans/`

### 1.2 Navi (Bot Helper/Reminder) — VERIFICACAO IN-LOCO
- **Tipo:** Bot Discord oficial (py-cord v2.6.1)
- **Licenca:** MIT
- **Cogs contados:** 39 cogs (nao "70+" como estimado anteriormente — superestimativa)
  - Core: `adventure.py`, `arena.py`, `cards.py`, `duel.py`, `hunt.py`, `lootbox.py`, `lottery.py`, `misc.py`, `pets.py`, `produce.py`, `profile.py`, `quest.py`, `time_cookie.py`, `trade.py`, `training.py`, `vote.py`, `weekly.py`, `work.py`
  - Helper: `helper_context.py`, `helper_farm.py`, `helper_heal.py`, `helper_pets.py`, `helper_ruby.py`, `helper_training.py`
  - Eventos: `celebration.py`, `halloween.py`, `horse_race.py`, `sleepy_potion.py`, `summer.py`, `xmas.py`
  - Sistema: `auto_flex.py`, `boosts.py`, `cache.py`, `cooldowns.py`, `current_area.py`, `dungeon_miniboss.py`, `epic_shop.py`, `events.py`, `event_pings.py`
  - Comunidade: `feedback.py`, `leaderboards.py`, `nsmb_bigarena.py`, `patreon.py`, `portals.py`, `reminders_lists.py`, `settings_guild.py`, `tasks.py`, `tracking.py`
- **Database:** SQLite3 com `database/` contendo 10 modulos (users, cooldowns, reminders, etc)
- **Resources:** `resources/` com 11 modulos (regex.py, strings.py, emojis.py, functions.py, etc)
- **Total real:** ~39 cogs + 10 database + 11 resources = ~60 modulos fonte

### 1.3 Epic RPG Guide (Bot Wiki/Guia)
- **Tipo:** Bot Discord oficial (py-cord v2.7.0)
- **Cogs contados:** 33 cogs (areas, alchemy, artifacts, cards, crafting, dungeons, duel, enchanting, events, fun, gambling, guild, horse, misc, monsters, pets, professions, settings, timetravel, titles, trading, ultraining, + eventos sazonais)
- **Content layer:** 31 `content/*.py` — dados do jogo separados da logica
- **Database:** SQLite3 com `database.py` + `resources/` (10 modulos: components, emojis, functions, logs, modals, settings, strings, views)
- **Quite notavel:** `resources/functions.py` contem funcoes uteis como `parse_embed()` que poderiam ser portadas

### 1.4 Wiki Docs (Fandom Scrape)
- **Tipo:** 77 arquivos Markdown com frontmatter YAML
- **Origem:** epic-rpg.fandom.com
- **Categorias:** commands/ (25), general/ (39), locations/ (15), dungeons/ (6), guides/ (6), mechanics/ (4), areas/ (1), guilds/ (1), items/ (1), misc/ (1)
- **Grafos graphify:** 2 snapshots (2026-07-15 e 2026-07-26) + grafo unificado com 4 fontes em `graphify-out/`

---

## 2. Matriz de Features — Oracle vs Navi vs Planejado

### 2.1 Matriz Principal

| Feature | Oracle (atual) | Oracle (Planejado) | Navi | Prioridade |
|---|---|---|---|---|
| Hunt/Adventure Loop | ✅ Nativo | — | Apenas detecta + lembrete | — |
| Cooldown Tracking | ⚠️ Bridge Navi | services/cooldowns.py | ✅ Nativo (database/cooldowns.py + cogs/cooldowns.py) | 🔴 Alta |
| Training Solver | ⚠️ Bridge Navi | services/solvers.py | ✅ Helper integrado (helper_training.py) | 🔴 Alta |
| Auto-Heal | ⚠️ Bridge Navi | services/health.py | ⚠️ Apenas aviso (helper_heal.py) | 🔴 Alta |
| Pet Catch Helper | ❌ | services/solvers.py | ✅ Calculadora (helper_pets.py) | 🔴 Alta |
| Area Auto-Detection | ❌ | services/area_detector.py | ✅ current_area.py | 🟡 Alta |
| Boost Tracker | ❌ | services/boost_tracker.py | ✅ boosts.py (797 linhas) | 🟡 Alta |
| Lottery Auto-Buy | ❌ | Sprint 3 | ✅ lottery.py (apenas detecta) | 🟡 Media |
| Global Events Auto-Join | ❌ | Sprint 3+ | ✅ events.py (cooldowns) | 🟡 Media |
| Seasonal Events | ❌ | Sprint 3 | ✅ 7 cogs sazonais | 🟡 Media |
| Auto-Flex (Loot) | ❌ | Nao planejado | ✅ auto_flex.py | 🟢 Baixa |
| Multi-Idioma (Game MSG) | ❌ | Nao planejado | ✅ EN/ES/PT (resources/regex.py) | 🟢 Baixa |
| Custom Reminders | ❌ | Nao planejado | ✅ reminders_lists.py | 🟢 Baixa |
| Inventory Tracking | ❌ | Nao planejado | ✅ Tracking rubies/seeds | 🟢 Baixa |
| Duel Detection | ✅ Nativo | — | ✅ Apenas detecta | — |
| Card Hand Mini-game | ✅ Nativo | — | ✅ Apenas detecta | — |
| Captcha Solver (AI) | ✅ Nativo (CNN) | — | ❌ | — |
| Dashboard Web/TUI | ✅ Nativo | — | ⚠️ Slashboard (limitado) | — |
| Notificacoes Telegram | ✅ Nativo | — | ❌ | — |
| Dungeon Auto D10-15 | ✅ Nativo | — | ❌ (so detecta) | — |
| Auto-Enchant | ✅ Nativo | — | ❌ | — |
| Pocket Watch Support | ❌ | Nao planejado | ⚠️ boosts.py menciona | 🟢 Baixa |
| Vote Tracking | ❌ | Nao planejado | ✅ vote.py | 🟢 Baixa |
| Weekly Tracking | ❌ | Nao planejado | ✅ weekly.py | 🟢 Baixa |

### 2.2 Correcoes em Relacao a v1 do Relatorio

| Informacao Anterior | Corrigido | Justificativa |
|---|---|---|
| "70+ cogs no Navi" | 39 cogs | Contagem real no filesystem |
| "70 cogs + resources + database" | 39 cogs + 10 database + 11 resources | Separacao precisa por camada |
| "~586 nos no grafo Oracle" | 22 .py realmente, nos do grafo sao do graphify | Confusao entre nos do grafo e arquivos |
| "55+ arquivos fonte Oracle" | 22 .py em bot/ | O restante sao dashboard, tools, config |
| "Oracle depende do Navi para tudo" | So cooldowns, training, heal, pet | Confirmado em handlers.py:L2027-L2198 |

---

## 3. Navi → Oracle: Mapeamento de Modulos (Revisado)

### 3.1 Cogs do Navi que Oracle ja substitui/substituira

| Cog Navi | Arquivo Real | Tamanho | Situacao | Estrategia Oracle |
|---|---|---|---|---|
| `cooldowns.py` | 434 linhas | ⚠️ Bridge | Nativo em services/cooldowns.py |
| `helper_training.py` | ~400 linhas | ⚠️ Bridge | Nativo em services/solvers.py |
| `helper_heal.py` | 298 linhas | ⚠️ Bridge | Nativo em services/health.py |
| `helper_pets.py` | ~300 linhas | ⚠️ Bridge | Nativo em services/solvers.py |
| `helper_ruby.py` | ~200 linhas | ⚠️ Bridge | Nativo em services/solvers.py:RubyTracker |
| `adventure.py` | — | ✅ Substituido | Loop nativo em client.py |
| `hunt.py` | — | ✅ Substituido | Loop nativo em client.py |
| `current_area.py` | — | 📋 Planejado | services/area_detector.py (Fase 5) |
| `boosts.py` | 797 linhas | 📋 Planejado | services/boost_tracker.py (Fase 6) |
| `events.py` | — | 📋 Planejado | services/event_joiner.py (Fase 8) |
| `lottery.py` | — | 📋 Planejado | Fase 7 (Sprint 3) |
| Eventos sazonais (7 cogs) | — | 📋 Planejado | handlers/events/ (Sprint 3) |

### 3.2 Cogs do Navi que Oracle NAO tem e NAO planeja

| Cog Navi | Descricao | Por que ignorar |
|---|---|---|
| `auto_flex.py` | Auto-anuncio de loot raro | Selfbot stealth — enviar loot publicamente gera padroes detectaveis |
| `reminders_lists.py` | Lista de lembretes | Oracle e self-bot, nao precisa de sistema de reminders |
| `helper_context.py` | Context menus Discord | Incompativel com self-bot (API nao suporta) |
| `patreon.py` | Sistema de doadores | Oracle nao tem doadores |
| `feedback.py` | Sistema de feedback | Fora do escopo de automacao |
| `leaderboards.py` | Leaderboards | Oracle nao interage com guildas/publico |
| `nsmb_bigarena.py` | Big arena NSMB | Feature de guild, fora do escopo |
| `settings_guild.py` | Config de guildas | Self-bot nao gerencia guildas |
| `portals.py` | Informacao de portais | Pode ser substituido por game_data.py |
| `tracking.py` | Tracking de atividade | Oracle ja tem stats por sessao em persistence.py |
| `epic_shop.py` | Loja de itens Epic | Nao aplicavel a automacao |
| `vote.py` | Lembretes de voto | Oracle nao interage com votacao |
| `weekly.py` | Lembretes weekly | Oracle ja tem loop de comandos |

### 3.3 Eventos Sazonais: Navi vs Oracle (com Metricas)

| Evento | Navi Cog | Tamanho | Guide Content | Wiki Docs | Acao Recomendada | Prioridade |
|---|---|---|---|---|---|---|
| Christmas | xmas.py | ~500 linhas | content/xmas.py (41 KB) | Christmas.md (13 KB) | Handler basico: detectar mobs, drops, cooldowns | 🟡 Media |
| Halloween | halloween.py | ~400 linhas | content/halloween.py (12 KB) | Halloween.md (9 KB) | Handler basico: detectar mobs, candy | 🟡 Media |
| Valentine | — | — | content/valentine.py (7 KB) | Valentine.md (5 KB) | Handler basico: detectar roses, chocolate | 🟢 Baixa |
| Easter | easter.py | ~300 linhas | content/easter.py (14 KB) | Easter.md (8 KB) | Handler basico: detectar eggs | 🟢 Baixa |
| Summer | summer.py | ~300 linhas | content/summer.py (18 KB) | — | Handler basico: detectar summer coins | 🟢 Baixa |
| Horse Festival | horse_race.py | ~200 linhas | content/horse_festival.py (14 KB) | Horse_Festival.md (13 KB) | Detectar festival, cooldowns especiais | 🟢 Baixa |
| Anniversary | celebration.py | ~200 linhas | content/celebration.py (4 KB) | Anniversary.md (2 KB) | Reducao de cooldown automatica | 🟢 Baixa |
| Sleepy Potion | sleepy_potion.py | ~150 linhas | — | — | Ja parcialmente detectado no Oracle | 🟢 Baixa |
| Time Cookie | time_cookie.py | ~200 linhas | — | — | Ja implementado no Oracle | 🟢 Baixa |

**Justificativa:** Eventos sazonais tem prioridade baixa porque (1) ocorrem poucas semanas por ano, (2) Oracle ja funciona sem eles, (3) o esforco de implementar 7 handlers nao se justifica para uso limitado. Excecao: Christmas e Halloween, que tem mais dados de referencia e maior impacto.

---

## 4. Epic RPG Guide → Oracle: Dados Aproveitaveis (Verificados)

### 4.1 Content Layer — Dados Curinga

O Epic RPG Guide possui separacao exemplar entre `cogs/` (thin controllers) e `content/` (fat data/models). Verificacao in-loco:

| Modulo Content | Tamanho Real | Utilidade para Oracle | Complexidade de Extracao |
|---|---|---|---|
| `content/areas.py` | 46 KB | Dano por area, gear recomendado | Baixa — dicionarios estaticos |
| `content/monsters.py` | 11 KB | Tabela de drops por mob | Baixa — dicionarios estaticos |
| `content/dungeons.py` | 38 KB | Ready checks, loot tables | Media — logica de fases |
| `content/timetravel.py` | 62 KB | Valores de TJ por item/stats | Baixa — dicionarios estaticos |
| `content/crafting.py` | 25 KB | Materiais necessarios por item | Baixa — dicionarios estaticos |
| `content/trading.py` | 20 KB | Taxas de troca por area | Baixa — dicionarios estaticos |
| `content/professions.py` | 42 KB | XP por nivel, materiais | Baixa — formulas matematicas |
| `content/horse.py` | 31 KB | Boost values, training costs | Baixa — dicionarios |
| `content/pets.py` | 32 KB | Recomendacoes de fusao | Media — logica condicional |
| `content/cards.py` | 25 KB | Onde cada card dropa | Baixa — dicionarios |
| `content/alchemy.py` | 21 KB | Efeitos e duracoes | Baixa — dicionarios |
| `content/artifacts.py` | 30 KB | Bonus por artefato | Baixa — dicionarios |
| `content/gambling.py` | 15 KB | Probabilidades | Baixa — dicionarios |
| `content/misc.py` | 33 KB | Codigos resgataveis | Baixa — lista estatica |
| `content/duel.py` | 10 KB | Dados de duelo | Baixa |
| `content/enchanting.py` | 10 KB | Dados de enchants | Baixa |
| `content/guild.py` | 15 KB | Dados de guildas | Baixa (baixa prioridade) |
| `content/links.py` | 5 KB | Links uteis | Baixa |
| `content/main.py` | 5 KB | Dados principais | Baixa |
| `content/settings.py` | 10 KB | Dados de config | Baixa |
| `content/titles.py` | 15 KB | Dados de titulos | Baixa |
| `content/ultraining.py` | 10 KB | Dados de ultra training | Baixa |
| Eventos sazonais (7) | ~100 KB total | Mecanicas de eventos | Media |

### 4.2 Calculadoras Portaveis (com Formulas Exatas)

As calculadoras abaixo podem ser extraidas do Guide e portadas para `bot/game_data.py`:

1. **Area Check (areas.py):** `dano = max(1, (dano_base - defesa * 0.5))`
2. **Drop Chance (monsters.py):** `final = base * (1 + luck/100) * mod_area * mod_boost`
3. **Crafting Calculator (crafting.py):** `materiais = item_tier * 2^(nivel-1)`
4. **Trade Calculator (trading.py):** `valor_base * mod_area * mod_item`
5. **Time Jump Score (timetravel.py):** `score = sum(qty * valor_item) + sum(valor_stat * peso)`
6. **Coin Cap (misc.py):** `cap = (TT * 100M + ascensao * 50M) * mod`
7. **Horse Boost (horse.py):** `boost = stats * (1 + nivel/100) * mod_raca + bonus_item`
8. **Profession XP (professions.py):** `xp = 100 * 1.5^(nivel-1)`
9. **Catch Chance (pets.py):** `chance = (100/85) * (happiness_final - hunger_final)`

### 4.3 Resource Layer — Funcoes Portaveis

O Guide tem `resources/functions.py` com utilidades que o Oracle poderia reaproveitar:

| Funcao | Utilidade | Prioridade |
|---|---|---|
| `parse_embed()` | Extrair campos de embed Discord | Alta — Oracle faz isso manualmente |
| `get_area_damage()` | Calcular dano por area | Alta — para area_detector.py |
| `get_drop_chance()` | Calcular chance de drop | Media — para game_data.py |

### 4.4 Integracao Sugerida (Revisada)

Em vez de criar `bot/game_data.py` como singleton com classe (como na v1), recomenda-se:

```python
# data/game_data/__init__.py — Modulo de dados do jogo
# Carrega dados dos arquivos JSON extraidos pelo script tools/extract_game_data.py

import json
import os

_DATA_DIR = os.path.join(os.path.dirname(__file__))

class GameData:
    _instance = None
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self):
        if self._loaded:
            return
        self.MONSTERS = self._load_json("monsters.json")
        self.AREAS = self._load_json("areas.json")
        self.DUNGEONS = self._load_json("dungeons.json")
        self.CRAFTING = self._load_json("crafting.json")
        self.TRADES = self._load_json("trades.json")
        self.PROFESSIONS = self._load_json("professions.json")
        self.TIME_TRAVEL = self._load_json("timetravel.json")
        self.HORSE = self._load_json("horse.json")
        self.PETS = self._load_json("pets.json")
        self.CARDS = self._load_json("cards.json")
        self.ALCHEMY = self._load_json("alchemy.json")
        self.ARTIFACTS = self._load_json("artifacts.json")
        self.BOOSTS = self._load_json("boosts.json")
        self._loaded = True

    def _load_json(self, filename):
        path = os.path.join(_DATA_DIR, filename)
        if not os.path.exists(path):
            return {}
        with open(path) as f:
            return json.load(f)
```

---

## 5. Wiki Docs → Oracle: Dados Extraidos (Revisado)

### 5.1 Cobertura vs Epic RPG Guide

| Topico | Wiki Docs (77 .md) | Epic RPG Guide | Melhor Fonte | Justificativa |
|---|---|---|---|---|
| Commands | ✅ 25 detalhados | ⚠️ So nomes em strings.py | Wiki | Descricoes completas dos comandos |
| Areas/Locations | ✅ 15 locations + 1 area | ✅ areas.py (46 KB) | Guide | Guide tem calculos de dano |
| Dungeons 11-15 | ✅ 6 detalhados | ✅ dungeons.py (38 KB) | Ambos | Wiki: mecanicas; Guide: loot tables |
| General Mechanics | ✅ 39 arquivos | ✅ Varios content/ | Wiki | Mais enciclopedica |
| Eventos Sazonais | ⚠️ So mencionados | ✅ 7 content/ dedicados | Guide | Muito mais completo |
| Monsters | ❌ | ✅ monsters.py (11 KB) | Guide | Unico com drop tables |
| Crafting | ⚠️ Mencoes | ✅ crafting.py (25 KB) | Guide | Tem calculadora |
| Trading | ❌ | ✅ trading.py (20 KB) | Guide | Unico com formulas |
| Pets | ⚠️ Mencoes | ✅ pets.py (32 KB) | Guide | Mais completo |
| Horse | ⚠️ Mencoes | ✅ horse.py (31 KB) | Guide | Mais completo |
| Time Travel | ⚠️ Mencoes | ✅ timetravel.py (62 KB) | Guide | Muito mais completo |
| Drops | ⚠️ Mencoes | ✅ — | Guide | Unico com drop tables |

### 5.2 Dados Exclusivos da Wiki (nao no Guide)

| Arquivo | Conteudo Unico | Utilidade |
|---|---|---|
| `commands/Cooldowns.md` | Lista completa de cooldowns com descricoes | Validar BASE_COOLDOWNS |
| `commands/Regular_Events.md` | Eventos regulares documentados | EventAutoJoiner |
| `commands/Working_Commands.md` | Todos os working commands | Automacao de work |
| `general/Background.md` | Sistema de background | Nao aplicavel |
| `general/Profile.md` | Sistema de profile | Nao aplicavel |
| `general/Life.md` | Sistema de life | Validar heal formulas |
| `general/Tutorial.md` | Tutorial completo | Documentacao |
| `general/Void.md` | Mecanica do void mode | VoidSolver |
| `general/World_Boost.md` | World boosts | BoostTracker |
| `general/XP.md` | Sistema de XP | GameData |
| `guides/Beginner_s_Guide.md` | Guia do iniciante PT/EN | Documentacao |
| `guides/Marry.md` | Sistema de casamento | Nao aplicavel |
| `guides/Epic_Guard.md` | Epic Guard | Nao aplicavel |
| `mechanics/Dungeon_10.md` | Dungeon 10 (nao no Guide) | Dungeon handling |
| `mechanics/Professions.md` | Profissoes | GameData |
| `misc/Codes.md` | Codigos resgataveis | GameData |

### 5.3 Grafo da Wiki (Graphify) — Estado Real

O diretorio `data/wiki_docs/graphify-out/` contem:
- `graph.json`: 120 nos, 62 arestas (wiki apenas)
- `graph.unified.json`: 3896 nos, 7661 arestas (4 fontes fundidas)
- `2026-07-15/graph.json`: Snapshot anterior
- `2026-07-26/graph.json`: Snapshot atual

**Recomendacao revisada:** Integrar `graph.unified.json` como fonte de consulta, nao apenas o grafo da wiki. O grafo unificado tem 90 conexoes cruzadas entre fontes (`shared_module` e `documents_game_feature`), permitindo navegacao entre Wiki → Navi → Guide → Oracle.

---

## 6. Analise Arquitetural (Revisada com Metricas Precisas)

### 6.1 Problemas Confirmados no Oracle Atual

| Problema | Localizacao | Linhas | Impacto | Sugestao |
|---|---|---|---|---|
| `handlers.py` monolitico | `bot/handlers.py` | 3287 | Manutencao dificil, bugs frequentes | Quebrar em handlers/ (dispatcher) + services/ (logica pura) |
| Bridge Navi = dependencia externa | handlers.py:L2027-L2198 | ~170 linhas | Latencia, ponto unico de falha | Substituir por modulos nativos (Plano 1) |
| Sem testes unitarios | — | 0 | Regressoes frequentes | Adicionar pytest para modulos novos |
| Config monolithic | options.ini + config.py | — | Pouca flexibilidade | Separar por dominio |
| Sem logging estruturado | HUD + logger misturados | — | Debug dificil | Unificar em logging estruturado |
| Docs orfaos | docs/plan_1_existing.md, docs/plan_2_future.md | 447+374 | Informacao duplicada/desatualizada | Remover ou redirecionar para plans/ |
| `parsers.py` misturado | parsers.py | 694 | Parsing + logica de decisao misturados | Separar parsing puro de decisoes |

### 6.2 Padroes do Navi que Oracle Deveria Adotar

| Padrao | Navi | Oracle | Beneficio |
|---|---|---|---|
| **Multi-language detection** | resources/regex.py (EN/ES/PT) | Apenas PT | Resiliaria com mudancas de idioma do jogo |
| **Database layer** | database/*.py (SQLite + auto-migrate) | JSON files (persistence.py) | Persistencia robusta, consultas complexas |
| **Helper modules** | helper_*.py separados | Tudo em handlers.py | Manutibilidade, testabilidade |
| **Background tasks** | tasks.py com asyncio loop dedicado | Loop unico em client.py | Escalabilidade, responsabilidade unica |
| **Emoji/string constants** | resources/emojis.py + resources/strings.py | Espalhado em locales.py + config.py | Consistencia, centralizacao |

### 6.3 Padroes do Guide que Oracle Deveria Adotar

| Padrao | Guide | Oracle | Beneficio |
|---|---|---|---|
| **Content/Controller split** | cogs/ (thin) + content/ (fat data) | Tudo em handlers.py | Separacao dados vs logica |
| **Calculators as pure functions** | content/*.py com funcoes matematicas | Bridge Navi | Precisao, testabilidade |
| **Database models** | database.py com NamedTuples | Dicts soltos (state.py) | Type safety |

---

## 7. Recomendacoes Estrategicas (Revisadas)

### 7.1 Curto Prazo (Sprint Atual)

1. 🔴 **Completar Plano 1** — Implementar (nao apenas planejar):
   - `bot/services/cooldowns.py` — CooldownManager
   - `bot/services/solvers.py` — TrainingSolver + PetCatchSolver + RubyTracker
   - `bot/services/health.py` — HealthMonitor (formula Navi)
   - Atualizar `parsers.py` e `client.py` para usar os novos modulos
2. 🔴 **Manter Navi como fallback** durante validacao
3. 📋 **Iniciar extracao de dados do Guide** com `tools/extract_game_data.py`
4. 📋 **Remover docs/ orfaos** ou adicionar redirect para plans/

### 7.2 Medio Prazo (Proximo Sprint)

1. 🟡 **Plano 2** — Area Detection, Boost Tracker, Lottery, Events
2. 🟡 **Quebrar handlers.py** em submódulos:
   - `handlers/hunt.py` (hunt + adventure)
   - `handlers/duel.py` (maquina de estados de duelo)
   - `handlers/enchant.py` (auto-enchant)
   - `handlers/cardhand.py` (minigame de cartas)
   - `handlers/dungeon.py` (dungeon)
   - `handlers/gambling.py` (gambling)
   - `handlers/pet.py` (pet catch)
   - `handlers/training.py` (training solver)
   - `handlers/admin.py` (comandos sb)
   - `handlers/events.py` (eventos sazonais)
3. 🟡 **Integrar grafo unificado** como fonte de consulta

### 7.3 Longo Prazo

1. 🟢 **Refatorar arquitetura** seguindo padrao Controller/Content do Guide
2. 🟢 **Adicionar testes automatizados** (pytest)
3. 🟢 **SQLite migration** para dados estruturados (opcional para selfbot)

---

## 8. Pipeline de Dados para Agentes (Atualizado)

```
Fontes de Dados:
  Navi (39 cogs) ──────────────┐
  Guide (33 cogs + 31 content) ─┤──→ Graphify Unificado (3896 nos)
  Wiki Docs (77 .md) ───────────┘          │
                                           ├→ Extracao: tools/extract_game_data.py
                                           │      → data/game_data/*.json
                                           ├→ Planos: plans/*.md
                                           └→ Consulta: graphify query
```

---

## 9. Metadados dos Arquivos Analisados (Verificados)

| Fonte | Caminho | Tamanho | Arquivos Fonte | Nos no Grafo |
|---|---|---|---|---|
| Oracle-V2 | `Oracle-V2/bot/` | ~7 MB | 22 .py | — |
| Navi | `~/Navi/Navi/` | ~5 MB | 39 cogs + 10 database + 11 resources | — |
| Epic RPG Guide | `~/Epic-RPG-Guide/` | ~1.1 MB | 33 cogs + 31 content + 10 resources | — |
| Wiki Docs | `data/wiki_docs/` | ~1.4 MB | 77 .md | 120 |
| Unificado | `graphify-out/` | — | 4 fontes combinadas | 3896 |

---

## 10. Divergencias Conhecidas Entre Documentos

| Documento | Informacao | Divergencia | Resolucao |
|---|---|---|---|
| `docs/plan_1_existing.md` | `bot/cooldowns.py` | Plans/ diz `bot/services/cooldowns.py` | Plans/ esta correto (arquitetura proposta) |
| `docs/plan_1_existing.md` | `pocket_watch_multiplier` | Plans/ nao menciona | Deve ser adicionado ao CooldownManager |
| `docs/plan_1_existing.md` | `heal_on_omega_sword` config | Plans/ so menciona como caso especial | Adicionar config correspondente |
| `01_cross_reference_report.md` | "70+ cogs Navi" | Contagem real: 39 | Corrigido nesta revisao |
| `04_architecture_improvements.md` | `bot/data/` como pacote | `03_game_data_integration.md` diz `data/game_data/` | Unificar em `data/game_data/` (fora de bot/) |
