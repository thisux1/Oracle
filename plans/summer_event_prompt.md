# Manual Completo e Plano Master — Evento Summer no Oracle v3

## Missão e Visão Geral

O **Evento Sazonal Summer** do Epic RPG é um dos eventos mais lucrativos do jogo, oferecendo moedas exclusivas, boosts maciços de XP/loot, artefatos permanentes e um pet exclusivo.

O objetivo do **Oracle v3** é fornecer **100% de automação autônoma** do evento, permitindo jogar o Summer de forma perfeita, otimizada e sem intervenção humana, garantindo a coleta de todos os prêmios e a manutenção permanente dos melhores boosts.

> [!IMPORTANT]
> **Status de Desenvolvimento do Oracle v3**: O módulo principal `bot/summer.py` **já está implementado e operacional**. Ele inclui a engine de surf com fallback estático de ondas, gerenciamento simultâneo dos 5 boosts com priorização da cor do torneio na segunda-feira, sistema de fila sequencial de trabalho (`summer_work_queue`), rastreamento fino de drops em `parsers.py`, resets diários/semanais e proteção contra travamentos (*stuck state protection*).

---

## 1. Guia Completo das Mecânicas do Evento (Cruzado com Navi, Guide & Wiki)

### 1.1 Itens e Recursos do Evento

| Item / Recurso | Ícone / Tipo | Como Obter | Utilidade no Evento |
|---|---|---|---|
| **Coconut** | Moeda base | Drop de `rpg chop` e `rpg fish` | Usado para craftar Chopped Coconut (60% chance) |
| **Chopped Coconut** | Moeda principal | Craft (1 Coconut) | Comprar Summer Boost na loja e craftar drinks |
| **Palm Log** | Madeira especial | Drop raro de `rpg chop` e `rpg fish` | Utilizado nas receitas de Surfboards |
| **MEGA Palm Log** | Moeda valiosa | Drop very rare em chop/fish, prêmio de surf 3 rounds, tasks e torneio | Craft da MEGA Surfboard, receitas e troca de prêmios |
| **Coconana** | Fruta especial | Drop raro de `rpg adventure` | Utilizado no confronto do World Boss do evento (`rpg smr wb`) |
| **Summer Slime** | Mob de evento | Encontro aleatório em `rpg hunt` | Dropa recursos do evento ao ser derrotado |
| **Beach Ball** | Item de evento | Drop raro do surf | Utilizado no Beach Ball Event multiplayer (`rpg smr use beach ball`) |
| **Pool Float** | Item de boost | Craft (1 Ruby + 20 Mermaid Hairs) | Dá +2.5% de sorte no surf para TODO O SERVIDOR por 45min |
| **Sleepy Potion** | Consumível raro | Recompensa de Quest, Torneio ou Loja | Avança 24h nos cooldowns do jogo (dorme 24h) |
| **Surfboards (5 tipos)** | Equipamento de surf | Craft na loja do evento | Aumentam as chances de sucesso no surf por tipo de onda e no torneio |
| **Drinks (4 cores)** | Consumível de boost | Craft (3 Chopped + ingredientes específicos) | Concedem boosts de 3h e inscrevem no Color Tournament na segunda-feira |
| **Sunglasses** | Artefato único | Parte A (3 surfs sem cair) + Parte B (drop ao beber drinks) | Concede compensação ao cair no surf + 5% de chance de miniboost no heal |
| **Turtle Pet** | Pet exclusivo | Recompensa final da Quest semanal (`rpg smr quest`) | Pet especial de evento |

---

### 1.2 Tabela Exata de Receitas e Crafting (`rpg smr craft`)

| Item Final | Ingredientes Necessários | Comando no Discord | Efeito / Obs. |
|---|---|---|---|
| **Chopped Coconut** | 1 Coconut | `rpg smr craft chopped coconut` | 60% de chance de sucesso. Alimenta o bot e faz drinks |
| **Wooden Log x2** | 1 Palm Log | `rpg smr craft wooden log` | Converte madeira do evento em madeira comum |
| **Blue Surfboard** | 10 Palm Log + 9 Normiefish | `rpg smr craft blue surfboard` | +20% afinidade em ondas *Defensive* |
| **Pink Surfboard** | 10 Palm Log + 2 EDGY Lootbox | `rpg smr craft pink surfboard` | +20% afinidade em ondas *Creative* |
| **Green Surfboard** | 10 Palm Log + 2 EPIC Fish + 5 Chip | `rpg smr craft green surfboard` | +20% afinidade em ondas *Logical* |
| **Yellow Surfboard** | 10 Palm Log + 3 Epic Seed + 7 Banana + 2 Lottery Ticket | `rpg smr craft yellow surfboard` | +20% afinidade em ondas *Initiative* |
| **MEGA Surfboard** | 5 MEGA Palm Log + 100 Palm Log | `rpg smr craft mega surfboard` | +15% afinidade em TODAS as ondas |
| **Blue Drink** | 3 Chopped Coconut + 2 Normiefish | `rpg smr craft blue drink` | Boost 3h: +30% chance de drop de itens summer |
| **Green Drink** | 3 Chopped Coconut + 1 EPIC Fish + 1 Chip | `rpg smr craft green drink` | Boost 3h: +25% de itens em comandos de work |
| **Pink Drink** | 3 Chopped Coconut + 1 EDGY Lootbox | `rpg smr craft pink drink` | Boost 3h: +20% de drop de lootbox em hunt/adv |
| **Yellow Drink** | 3 Chopped Coconut + 1 Epic Seed + 3 Banana + 1 Lottery Ticket | `rpg smr craft yellow drink` | Boost 3h: +50% XP e +50% coins |
| **Pool Float** | 1 Ruby + 20 Mermaid Hairs | `rpg smr craft pool float` | World boost: +2.5% surf luck por 45 min |

> *Nota*: Ao craftar uma nova prancha de surf, ela **substitui** automaticamente a prancha anterior. Cada prancha correspondente também confere +2.5% de chance de sucesso no Color Tournament.

---

### 1.3 Surf Automation — A Atividade Principal (`rpg smr surf`)

- **Cooldown**: 4 horas (14400 segundos).
- **Mecânica**: Cada sessão de surf possui **3 rounds**. Em cada round, o Epic RPG apresenta uma onda e duas opções de escolha (`a` ou `b`), cada uma atrelada a um nível de risco e uma recompensa.

#### Tabela de Ondas e Opções (`SURF_WAVE_DATA`)

| Nome da Onda | Opção A (Risco & Recompensa) | Opção B (Risco & Recompensa) |
|---|---|---|
| **completely normal wave** | **Low risk**, 80 Guild Rings | **Very low risk**, 1 Wishing Token |
| **inverted wave** | **Very low risk**, 20 Coconuts | **High risk**, 3 EPIC Lootboxes |
| **insanely small wave** | **Very low risk**, 30 Arena Cookies | **Very high risk**, 1 OMEGA Horse Token |
| **big wave** | **Low risk**, 1 EDGY Lootbox | **High risk**, 10 TIME Cookies |
| **invisible wave** | **Low risk**, 35 Chopped Coconuts | **Very high risk**, 4 Flasks |
| **angry wave** | **High risk**, 2 Flasks | **Very high risk**, 20 TIME Cookies |

#### Níveis de Risco e Afinidades

- **Logical** → Very low risk (0)
- **Defensive** → Low risk (1)
- **Initiative** → High risk (2)
- **Creative** → Very high risk (3)

#### Lógica de Decisão Automatizada do Oracle v3

```
                    ┌──────────────────────────────┐
                    │ Recebe Embed de Surf do Bot  │
                    └──────────────┬───────────────┘
                                   │
                     Identifica a Onda (parse_surf_wave)
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
   Encontrou Risco no Texto?                Não encontrou no Texto?
   (Leitura Dinâmica)                       (Fallback SURF_WAVE_DATA)
              │                                         │
              └────────────────────┬────────────────────┘
                                   │
                      Aplica a Estratégia do Usuário
                                   │
            ┌──────────────────────┴──────────────────────┐
            ▼                                             ▼
   Estratégia 'conservative'                    Estratégia 'aggressive'
   (Seleciona a opção de MENOR Risco)           (Seleciona a opção de MAIOR Risco)
            │                                             │
            └──────────────────────┬──────────────────────┘
                                   │
                 Envia Resposta ('a' ou 'b') via HPQ
```

- **Recompensa por completar os 3 rounds**: +1 MEGA Palm Log.
- **Se cair da prancha**: O cooldown é resetado normalmente. Se possuir o artefato *Sunglasses*, recebe recompensa de compensação.
- **Surf Lock (Bloqueio de Filas)**: Durante o minigame de surf (`surf_in_progress = True`), o Oracle bloqueia **todas** as filas (HPQ e LPQ) e lembretes de bots terceiros (como Navi Lite), garantindo que apenas as respostas do surf (`a` ou `b`) sejam enviadas ao Discord sem interrupções.

---

### 1.4 Color Tournament — Torneio Semanal de Cores

- **Inscrição**: Ocorre automaticamente ao ingerir qualquer bebida entre **Segunda 00:01 UTC** e **Sexta 23:59 UTC**.
- **Equipes**: Blue, Green, Pink e Yellow. O time do jogador é **definido pela PRIMEIRA bebida ingerida na semana**.
- **Duração do Torneio**: De Sábado 00:01 UTC a Domingo 23:59 UTC.
- **Pontuação**: Baseada exclusivamente no desempenho individual no surf (completar rounds aumenta a pontuação, cair diminui).

#### Bônus de Cada Equipe

- 🟦 **Team Blue**: Dobra a produção de crafts (`craft doubled`).
- 🟩 **Team Green**: Dobra as recompensas do surf (`surf rewards doubled`).
- 🟨 **Team Yellow**: Dobra as recompensas das tasks (`task rewards doubled`).
- 🟪 **Team Pink**: Desconto de 30% na loja do evento (`shop 30% off`).

#### Recompensas e Códigos no Domingo

Ao final do torneio, o bot deve resgatar o código correspondente:
- **Time Vencedor**: Usar código `WINNERCOLOR` → Recompensa: 10 MEGA Palm Logs + Título *BEACH KING*.
- **Times Perdedores**: Usar código `LOSERCOLORS` → Recompensa: 5 MEGA Palm Logs.

> [!STRATEGY]
> **Estratégia do Oracle no Torneio**: Na segunda-feira entre 00:00 e 06:00 UTC, o Oracle força a ingestão da bebida configurada em `config.summer_drink_choice` (ex: `blue drink` para dobrar crafts) **em primeiro lugar**. Isso garante a entrada na equipe desejada antes de ativar todas as outras bebidas.

---

### 1.5 Gestão Integrada dos 5 Boosts Simultâneos

Para extrair 100% de rendimento do evento, o Oracle mantém **todos os 5 boosts ativos simultaneamente**:

| Boost | Origem | Custo | Duração | Efeito Principal |
|---|---|---|---|---|
| **Summer Boost** | `rpg smr buy summer boost` | 50 Chopped Coconuts | 4h (14400s) | +40% work items/rarity, +25% XP, +15% prof XP |
| **Blue Drink** | `rpg smr drink blue drink` | Craft de Blue Drink | 3h (10800s) | +30% chance de drop de itens do summer |
| **Green Drink** | `rpg smr drink green drink` | Craft de Green Drink | 3h (10800s) | +25% de itens em comandos de work |
| **Pink Drink** | `rpg smr drink pink drink` | Craft de Pink Drink | 3h (10800s) | +20% de drop de lootboxes |
| **Yellow Drink** | `rpg smr drink yellow drink` | Craft de Yellow Drink | 3h (10800s) | +50% XP e +50% coins |

#### Lógica de Execução (100% Nativa — Sem Dependência de Navi):

**Camada 1 — Polling Periódico (`queue_boosts_check`)**:
1. A cada 25 minutos (`BOOST_CHECK_INTERVAL`), dispara `rpg boosts`.
2. O parser extrai os boosts ativos e o tempo restante via regex `BOOST_PATTERN`.
3. `handle_boost_response` armazena **timestamps absolutos de expiração** em `bot_state.summer_boosts_active[key] = now + remaining_seconds`.
4. Boosts ausentes são imediatamente re-enfileirados (bebida favorita primeiro, depois as demais).

**Camada 2 — Rastreamento Nativo de Expiração (`_check_boost_expiry`)**:
1. Executada a cada tick do `summer_tick()` (~1-2s).
2. Percorre `bot_state.summer_boosts_active` e verifica se algum boost está a ≤120s (`BOOST_RENEW_BUFFER`) da expiração.
3. Se expirou: remove do dicionário e enfileira automaticamente o comando de reposição (`rpg smr buy summer boost` ou `rpg smr drink <cor> drink`).
4. Drinks expirados são priorizados pela cor favorita do torneio.
5. **Zero dependência de bots externos** — o Oracle rastreia os timestamps internamente.

**Camada 3 — Fallback de Compra de Ingredientes da Yellow Drink (`handle_yellow_craft_no_resources`)**:
1. Ao tentar craftar a **Yellow Drink** (`rpg smr craft yellow drink`), caso o bot detecte que faltam recursos (`you don't have enough items to craft this`), o Oracle enfileira automaticamente os comandos de compra de ingredientes:
   - `rpg epic shop buy epic seed` (Comprar Epic Seed na Epic Shop)
   - `rpg buy lottery ticket` (Comprar bilhete de loteria)
2. Após o envio das compras, re-enfileira automaticamente a tentativa de craft (`rpg smr craft yellow drink`) e o consumo do drink (`rpg smr drink yellow drink`).

---

### 1.6 Summer Tasks & Sistema de Work Queue

As tasks do evento renovam diariamente entre 00:01 e 23:59 UTC. Ao completar qualquer task, o bot manda `rpg smr task` para resgatar.

#### Tabela de Tasks Reconhecidas

| Task | Tipo | Ação Automatizada pelo Oracle |
|---|---|---|
| `Good player: Use the rules command` | `rules` | Enfileira `rpg rules` no LPQ |
| `Use the support command` | `support` | Enfileira `rpg support` no LPQ |
| `Wait, why does it give more: Fish 6 times` | `fish` | Adiciona `fish` (target 6) à `summer_work_queue` |
| `Can i drink this: Get 2 coconuts in rpg chop` | `chop_coconut` | Adiciona `chop` à `summer_work_queue` até obter coconuts |
| `Professional coconut dodger: Chop 6 times` | `chop` | Adiciona `chop` (target 6) à `summer_work_queue` |
| `Arena time: Start, boost or join an arena` | `arena` | Enfileira `rpg arena` e faz auto-join via bypass de filtro |
| `Last resource: Drink a chopped coconut` | `drink_chopped` | Enfileira `rpg smr drink chopped coconut` no HPQ |
| `Craft a drink` | `craft_drink` | Enfileira craft do drink preferido |
| `Duelisn't: Lose / Win duels` | `duel` | Altera `config.win_duel = True/False` dinamicamente com base na task e enfileira `rpg duel <@partner>` |
| `Rare mob: Find the rare mob in hunt` | `rare_mob` | Monitorado naturalmente durante os hunts comuns |
| `So many waves!: Pass 7 surf rounds` | `surf_rounds` | Executado automaticamente nos ciclos de surf |
| `Stonks: slots at least 100 coins` | `slots` / `stonks` | Enfileira `rpg slots 100` no LPQ |
| `Zzz: Use a sleepy potion` | `sleepy` | Executa APENAS se `summer_use_sleepy_potion = true` |

#### Funcionamento da `summer_work_queue`
Quando uma task pede múltiplos comandos de trabalho (ex: `fish 6x` ou `chop 6x`), o Oracle altera temporariamente o `config.work_command` para o comando da task. À medida que o parser confirma a execução dos drops, o contador decrementa. Quando a task conclui, a fila avança para a próxima ou restaura o `work_command` original.

---

### 1.7 Artefato Sunglasses, Quest do Pet Turtle & Sleepy Potion

- **Sunglasses Artifact**:
  - *Como obter*: Completar 3 rounds de surf sem cair 3x (Parte A) + drop aleatório ao beber drinks (Parte B).
  - *Efeito*: Concede prêmio de compensação se o bot cair no surf e dá 5% de chance de ativar um boost temporário (5 LIFE, 5% mob drop, 5% prof XP por 2 min) ao usar `rpg heal`.
- **Turtle Pet Quest (`rpg smr quest`)**:
  - Quest semanal com passos ordenados. Concede o pet *Turtle*.
- **Sleepy Potion**:
  - Dorme por 24h e reseta todos os cooldowns. Devido ao impacto no jogo, é controlada pela flag `summer_use_sleepy_potion` (padrão `false`).

---

## 2. Matriz de Auditoria: Estado Atual do Oracle vs O que Falta

A matriz abaixo detalha cada funcionalidade do evento, o estado da implementação no Oracle v3 e as ações pendentes:

| Funcionalidade / Módulo | Estado no Oracle v3 | Arquivo(s) Responsável(is) | Detalhes do Status | O que Falta para 100% |
|---|---|---|---|---|
| **Engine de Surf** | 🟢 Concluído | `bot/summer.py`<br>`bot/parsers.py` | Detecta prompts, calcula risco via `SURF_WAVE_DATA` (fallback) e responde `a`/`b` via HPQ. | Nenhum. 100% operacional. |
| **Gestão de Boosts** | 🟢 Concluído | `bot/summer.py` | Compra Summer Boost e mantém os 4 drinks ativos simultaneamente com priorização da cor favorita. | Nenhum. 100% operacional. |
| **Tasks & Work Queue** | 🟢 Concluído | `bot/summer.py` | Parseia tasks diárias/semanais, gerencia a fila `summer_work_queue`, executa `slots`, `rules`, `arena` e claima. | Nenhum. 100% operacional. |
| **Torneio de Cores (Inscrição)** | 🟢 Concluído | `bot/summer.py` | Força a ingestão da bebida da cor configurada na Segunda 00:00 UTC. | Nenhum. 100% operacional. |
| **Resgate do Torneio (Códigos)** | 🟢 Concluído | `bot/summer.py` | Resgata automaticamente os códigos `WINNERCOLOR` e `LOSERCOLORS` no reset semanal. | Nenhum. 100% operacional. |
| **Summer Quest & Turtle Pet** | 🟢 Concluído | `bot/summer.py`<br>`bot/client.py` | Parseia as 5 sub-quests de `rpg smr quest`, auto-crafta Pool Float para Altruism e auto-claima o Turtle Pet. | Nenhum. 100% operacional. |
| **Tracking de Coconuts/Slime** | 🟢 Concluído | `bot/parsers.py` | Rastreia coconuts, palm logs, slime e sunglasses nos drops de work/hunt e incrementa a work queue. | Nenhum. 100% operacional. |
| **Bypass Filtro de Canal (Arena)** | 🟢 Concluído | `bot/client.py` | Permite responder a arenas de summer em qualquer canal do servidor configurado. | Nenhum. 100% operacional. |
| **TUI (Interface de Terminal)** | 🟢 Concluído | `bot/tui_sidebar.py`<br>`bot/tui_input.py` | Exibe painel `SUMMER` na sidebar com tempo de surf, rounds e time. Autocomplete `/summer`. | Nenhum. 100% operacional. |
| **Web Dashboard React** | 🟢 Concluído | `dashboard/src/tabs/ConfigTab.jsx` | Possui toggles e selects para `do_summer`, `summer_surf_strategy`, `summer_drink_choice` e `summer_use_sleepy_potion`. | Nenhum. 100% operacional. |
| **Template de Configuração** | 🟢 Concluído | `options_example.ini` | Seção `[summer]` documentada com as 4 configs (`do_summer`, `summer_surf_strategy`, etc.). | Nenhum. 100% operacional. |
| **Documentação Pública** | 🟢 Concluído | `README.md`<br>`docs/README.pt-BR.md` | Inclui tabela de comandos `sb summer` e especificações de configuração nos READMEs em EN e PT-BR. | Nenhum. 100% operacional. |

---

## 3. Checklist Técnico de Integração e Validação

Para garantir conformidade estrita com o `AGENTS.md` do repositório, todo novo ajuste no evento summer deve seguir o checklist abaixo:

### 3.1 Checklist de Interfaces (`AGENTS.md` Seção 2)

- [x] **Core (bot)**: `summer.py`, `state.py`, `config.py`, `parsers.py`, `client.py` sincronizados.
- [x] **Discord `sb`**: Comandos `sb summer status`, `sb summer surf`, `sb summer sleepy` integrados em `handlers.py`.
- [x] **TUI comandos**: Autocomplete de `/summer status` e `/summer sleepy` em `tui_input.py`.
- [x] **TUI config**: Campos editáveis no modal em `tui_modals.py`.
- [x] **TUI Sidebar**: Painel telemétrico de Surf e Boosts em `tui_sidebar.py`.
- [x] **Dashboard Web**: Seção Summer Event com `<ToggleSwitch>` e `<Select>` em `ConfigTab.jsx`.
- [x] **Telegram**: Alertas configurados exclusivamente para falhas críticas (5x falhas de work, travamentos >10min).
- [x] **options_example.ini**: Seção `[summer]` configurada.
- [x] **README.md**: Tabela de comandos e parâmetros documentada em EN e PT-BR.

### 3.2 Comando de Verificação Sintática

Sempre executar após alterar qualquer arquivo Python do módulo:

```bash
/home/thiago/Documentos/codesnippets/discbot/Epic-Rpg-Macro-main/venv_311/bin/python3 -c "
import py_compile
py_compile.compile('bot/summer.py', doraise=True)
py_compile.compile('bot/parsers.py', doraise=True)
py_compile.compile('bot/client.py', doraise=True)
print('Sintaxe OK!')
"
```
