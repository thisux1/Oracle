# Melhorias Arquiteturais — Oracle V3

> Baseado na analise de Navi, Epic RPG Guide e Oracle-V2 atual
> **Data da analise:** 2026-07-26

---

## 1. Problemas Identificados (Verificados)

### 1.1 handlers.py Monolitico (3.287 linhas — CONFIRMADO)

O arquivo `bot/handlers.py` concentra:

- Processamento de mensagens (`responseResolver`, L1862-L3287)
- Machine states (duel L2436-L2564, enchant, card hand L633-L832, sleepet L863-L1024, gather L1027-L1322, gambling L271-L334)
- Comandos admin `sb` (L1875-L2025)
- Integracao Navi Lite (L2027-L2198, ~170 linhas)

### 1.2 Dependencia Bridge Navi → Codigo Nativo (CONFIRMADO)

Oracle depende do Navi Lite para:
- Cooldown tracking via `rdCheckNavi()` em parsers.py
- Training solving (leitura passiva dos slash commands do Navi)
- Heal warning
- Pet catch

### 1.3 Sem Banco de Dados (CONFIRMADO)

Persistencia atual: JSON files (`session_baseline_*.json`, `stats_*.json`). Sem schema, sem migracoes.

### 1.4 Config Monolitica (CONFIRMADO)

`options.ini` + `config.py` concentram 50+ opcoes sem secoes bem definidas.

### 1.5 Sem Testes (CONFIRMADO)

Zero testes unitarios ou de integracao. Qualquer refatoracao e arriscada.

### 1.6 Documentacao Orfa (NOVO)

`docs/plan_1_existing.md` e `docs/plan_2_future.md` ainda existem mas foram substituidos por `plans/`. Informacao duplicada e potencialmente conflitante.

### 1.7 parsers.py Misturado (NOVO)

`bot/parsers.py` (694 linhas) mistura parsing puro com logica de decisao. Idealmente deveria so conter funcoes de extracao.

---

## 2. Nova Arquitetura Proposta (Revisada)

### 2.1 Estrutura de Diretorios

```
Oracle-V2/
├── bot/
│   ├── client.py              # WebSocket, loop principal
│   ├── handlers.py            # DISPATCHER (~500 linhas, delega para handlers/)
│   │
│   ├── handlers/              # Submodulos por dominio
│   │   ├── __init__.py
│   │   ├── hunt.py            # Hunt/adventure result
│   │   ├── training.py        # Training minigame solving
│   │   ├── duel.py            # Duel machine state
│   │   ├── enchant.py         # Auto-enchant
│   │   ├── cardhand.py        # Card hand minigame
│   │   ├── dungeon.py         # Dungeon
│   │   ├── gambling.py        # Gambling
│   │   ├── pet.py             # Pet catch
│   │   ├── events.py          # Eventos sazonais
│   │   └── admin.py           # sb commands
│   │
│   ├── services/              # Servicos/Managers PUROS (sem logica Discord)
│   │   ├── cooldowns.py       # CooldownManager
│   │   ├── solvers.py         # TrainingSolver + PetCatchSolver + RubyTracker
│   │   ├── health.py          # HealthMonitor
│   │   ├── area_detector.py   # AreaDetector
│   │   ├── boost_tracker.py   # BoostTracker
│   │   └── event_joiner.py    # EventAutoJoiner
│   │
│   ├── parsers.py             # So parsing puro (regex, extracao)
│   ├── config.py              # Config loader (refatorado)
│   ├── state.py               # Estado global
│   ├── hud.py                 # Logging
│   ├── telegram.py            # Notificacoes
│   ├── captcha.py             # Captcha solver AI
│   ├── persistence.py         # Save/load JSON
│   ├── typo.py                # Simulacao de erros de digitacao
│   ├── utils.py               # Utilitarios
│   ├── locales.py             # Strings de jogo
│   │
│   ├── tui/                   # TUI modules
│   │   ├── tui.py, tui_input.py, tui_modals.py, etc.
│   │
│   └── __init__.py
│
├── data/
│   ├── game_data/             # JSON files extraidos
│   │   ├── __init__.py        # GameData singleton
│   │   ├── monsters.json, areas.json, dungeons.json, ...
│   └── wiki_docs/             # Existente
│
├── tools/
│   ├── scrape_wiki.py         # Existente
│   └── extract_game_data.py   # NOVO
│
├── tests/                     # Testes unitarios
│   ├── test_cooldowns.py
│   ├── test_solvers.py
│   ├── test_health.py
│   └── test_game_data.py
│
├── plans/                     # Este diretorio
├── docs/                      # ORFAO — precisa limpeza
├── graphify-out/              # Grafos
├── dashboard/                 # React + FastAPI
└── ...
```

### 2.2 Principais Diferencas para a Proposta Original

| Item | Proposta Original (04_architecture_improvements.md) | Proposta Revisada | Justificativa |
|---|---|---|---|
| `bot/data/` | Dentro de bot/ | Fora de bot/, em `data/game_data/` | Dados estaticos nao sao codigo |
| `bot/persistence/` | Pacote com sqlite_store.py | Mantido como persistence.py | SQLite nao justificado para selfbot |
| `bot/captcha.py` | Mover para handlers/ | Manter em bot/captcha.py | Logica de IA, nao de handler |
| `bot/tui/` | Subpacote | Mantido | Ja esta parcialmente separado |
| `bot/handlers/captcha.py` | Incluido | Removido | Captcha nao e handler de mensagem |

---

## 3. Padroes de Codigo Recomendados

### 3.1 Baseados no Navi

| Padrao | Navi | Oracle Atual | Recomendacao | Prioridade |
|---|---|---|---|---|
| Multi-language detection | resources/regex.py | Apenas PT | Adicionar EN/ES patterns | 🟢 Baixa |
| Helper modules | helper_*.py | Tudo em handlers.py | Criar services/ | 🔴 Alta |
| Database layer | database/*.py | JSON files | Manter JSON, SQLite e overkill | 🟢 Baixa |
| Background tasks | tasks.py | client.py | Separar se houver crescimento | 🟡 Media |
| Emoji constants | resources/emojis.py | Espalhado | Centralizar emojis | 🟡 Media |

### 3.2 Baseados no Guide

| Padrao | Guide | Oracle Atual | Recomendacao | Prioridade |
|---|---|---|---|---|
| Content/Controller | cogs/ + content/ | Monolitico | handlers/ + services/ | 🔴 Alta |
| Calculators as functions | content/*.py | Bridge Navi | Mover para services/ | 🔴 Alta |
| String constants | resources/strings.py | locales.py + config.py | Unificar | 🟢 Baixa |

---

## 4. Plano de Migracao Arquitetural (Atualizado)

### Sprint 1 — Implementar Plano 1 (Servicos Core)

1. Criar `bot/services/` com `__init__.py`
2. Implementar `services/cooldowns.py` (CooldownManager)
3. Implementar `services/solvers.py` (TrainingSolver + PetCatchSolver + RubyTracker)
4. Implementar `services/health.py` (HealthMonitor)
5. Integrar em `parsers.py` e `client.py`
6. Manter fallback Navi

### Sprint 2 — Modularizacao de handlers.py

1. Criar `bot/handlers/` com `__init__.py`
2. Extrair machine states para submódulos:
   - `duel_state` → `handlers/duel.py`
   - `enchant_state` → `handlers/enchant.py`
   - `cardhand_state` → `handlers/cardhand.py`
   - `sleepet_mode` → `handlers/hunt.py`
   - `gambling_state` → `handlers/gambling.py`
3. Extrair comandos `sb` → `handlers/admin.py`
4. `handlers.py` vira dispatcher que importa e delega

### Sprint 2 (paralelo) — Data Layer

1. Extrair dados do Guide com script `tools/extract_game_data.py`
2. Gerar `data/game_data/*.json`
3. Implementar `data/game_data/__init__.py` (GameData)
4. Integrar GameData nos servicos

### Sprint 3 — Plano 2 (Deteccao e Eventos)

1. `services/area_detector.py` — AreaDetector
2. `services/boost_tracker.py` — BoostTracker
3. `services/event_joiner.py` — EventAutoJoiner
4. Handlers sazonais basicos

### Sprint 4 — Testes e Qualidade

1. Configurar pytest
2. Testes para services/ (logica pura, sem Discord)
3. Remover docs/ orfaos

---

## 5. Riscos e Mitigacoes

| Risco | Impacto | Mitigacao |
|---|---|---|
| handlers.py refactor quebra fluxo existente | Alto | Fazer por etapas, cada submodulo testado manualmente |
| Dados do Guide desatualizados (patch novo) | Medio | GameData versionado, script de extracao refazivel |
| Navi bridge removal prematura | Alto | Manter fallback desativavel por 2 sprints |
| Aumento de complexidade | Medio | Seguir principios de clean architecture |

---

## 6. Decisoes Arquiteturais e Justificativas

### 6.1 Por que services/ em vez de helpers/?
Terminologia do Navi usa "helpers", mas "services" e mais semantico: servicos sao unidades de logica de negocio que nao dependem do Discord. Helpers sao utilitarios.

### 6.2 Por que manter JSON em vez de migrar para SQLite?
- Selfbot single-user: sem concorrencia real
- 500 KB de dados cabem em memoria
- JSON e git-friendly (diff textual)
- SQLite adicionaria complexidade sem beneficio mensuravel

### 6.3 Por que separar parsers.py de handlers/ ?
- Parsing puro (regex, extracao de dados) deve ser testavel isoladamente
- Decisoes de negocio (o que fazer quando X acontece) devem ficar nos handlers
- Facilita testes: parsers tem input/output deterministicos

### 6.4 Por que manter captcha.py na raiz de bot/ em vez de mover?
- Captcha usa modelos de IA (TensorFlow), nao processa mensagens do Discord
- E um servico ortogonal aos handlers de mensagem

### 6.5 Por que docs/ orfaos precisam ser limpos?
- Duas versoes da mesma informacao causam confusao para agentes de codigo
- plans/ tem a versao mais atualizada e revisada
- Manter docs/ antigos aumenta custo cognitivo

---

## 7. Metricas de Sucesso

| Métrica | Atual | Sprint 1 | Sprint 2 | Sprint 3 |
|---|---|---|---|---|
| handlers.py linhas | 3287 | ~2500 | ~500 | ~500 |
| Dependencia Navi bridge | 100% | 50% | 10% | 0% |
| Modulos services/ | 0 | 3 | 6 | 9 |
| Testes unitarios | 0 | 5 | 15 | 25 |
| Arquivos em data/game_data/ | 0 | 0 | 14 | 14 |
| Docs orfaos | 2 | 2 | 0 | 0 |
