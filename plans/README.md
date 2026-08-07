# Planos e Relatórios — Oracle V3

Diretório central de planejamento e análise para evolução do Oracle.

## Documentos

| Documento | Descrição |
|---|---|
| `01_cross_reference_report.md` | Cruzamento completo de Navi, Epic RPG Guide, Wiki Docs e Oracle |
| `02_navi_migration_detailed.md` | Plano detalhado de migracao Navi → Oracle Nativo (8 fases) |
| `03_game_data_integration.md` | Integracao de dados do jogo (Guide + Navi + Wiki em game_data.py) |
| `04_architecture_improvements.md` | Melhorias arquiteturais propostas |
| `05_priority_matrix.md` | Matriz de prioridades com scores e roadmap |
| `06_agentic_ai_integration.md` | Arquitetura & Implementação de IA Agêntica (Harness, RAG, Anti-Injection, Custos) |

## Fontes Analisadas

- **Navi** — `~/Navi/Navi/` (v3.6.0, MIT, py-cord, 39 cogs + database layer)
- **Epic RPG Guide** — `~/Epic-RPG-Guide/` (py-cord, 33 cogs, 31 content/)
- **Wiki Docs** — `data/wiki_docs/` (77 .md do Fandom, grafos graphify)
- **Oracle-V2** — Codigo fonte atual (22 .py em bot/, 3287 linhas em handlers.py)

## Uso para Agentes

Ao receber tarefas de desenvolvimento do Oracle, consulte:
1. `05_priority_matrix.md` — para saber o que implementar primeiro
2. `02_navi_migration_detailed.md` — para detalhes de implementacao especificos
3. `03_game_data_integration.md` — para dados do jogo
4. `04_architecture_improvements.md` — para padroes arquiteturais

## Estado Atual da Implementacao (2026-07-26)

| Artefato Planejado | Status | Localizacao |
|---|---|---|
| `bot/services/` | ❌ Nao criado | — |
| `bot/handlers/` | ❌ Nao criado | — |
| `bot/cooldowns.py` | ❌ Nao criado | — |
| `bot/solvers.py` | ❌ Nao criado | — |
| `bot/health.py` | ❌ Nao criado | — |
| `data/game_data/` | ❌ Nao criado | — |
| `tools/extract_game_data.py` | ❌ Nao criado | — |
| `tests/` | ❌ Nao criado | — |
| `handlers.py` modularizado | ❌ Ainda monolitico | 3287 linhas |
| Bridge Navi independente | ❌ Ainda depende | handlers.py:L2027-L2198 |
| `docs/plan_1_existing.md` | 🟡 Obsoleto | Substituido por plans/ |
| `docs/plan_2_future.md` | 🟡 Obsoleto | Substituido por plans/ |
| Grafo unificado (4 fontes) | ✅ Existe | `graphify-out/graph.unified.json` |

## Documentacao Historica

Arquivos antigos em `docs/` que foram substituidos por estes planos:
- `docs/plan_1_existing.md` → Substituido por `02_navi_migration_detailed.md` + `05_priority_matrix.md`
- `docs/plan_2_future.md` → Substituido por `02_navi_migration_detailed.md` (Fases 5-8)

**Divergencias conhecidas entre docs antigos e novos planos:**
- Docs antigos usavam `bot/cooldowns.py`; novos usam `bot/services/cooldowns.py`
- Docs antigos incluem `pocket_watch_multiplier` no CooldownManager; novos omitem
- Docs antigos incluem `heal_on_omega_sword` e `heal_on_dragon_breath`; novos planos tem casos especiais mas sem configs explicitas
