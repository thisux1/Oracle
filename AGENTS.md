# Oracle v3 — Agent Guide

Guia de referência para agentes de código trabalhando neste repositório.

---

## 1. Arquitetura do Projeto

```
Oracle-V2/
├── bot/                        # Core do bot (Python)
│   ├── client.py               # WebSocket do Discord, filtro de canais, loop principal
│   ├── handlers.py             # Processamento de mensagens, machine states, sb commands
│   ├── parsers.py              # Detecção de eventos Epic RPG (drops, ready, duel, etc.)
│   ├── config.py               # Carregamento do options.ini, constantes, tipos
│   ├── state.py                # Estado global do bot (filas, flags, contadores)
│   ├── telegram.py             # Notificações via Telegram
│   ├── hud.py                  # Output formatado (logs, display)
│   ├── tui.py                  # Interface TUI (Textual)
│   ├── tui_input.py            # CLI com autocomplete da TUI
│   ├── tui_modals.py           # Modais de configuração da TUI
│   ├── tui_sidebar.py          # Sidebar de telemetria da TUI
│   ├── captcha.py              # Resolução de captchas com IA
│   ├── persistence.py          # Save/load de session data e stats
│   ├── typo.py                 # Simulação de erros de digitação
│   └── utils.py                # Utilitários gerais
├── dashboard/                  # Web Dashboard (React + FastAPI)
│   ├── src/
│   │   ├── tabs/               # OverviewTab, ConfigTab, StatsTab, TerminalTab
│   │   ├── components/         # Componentes React reutilizáveis
│   │   ├── stores/             # Zustand stores (useOracleStore)
│   │   └── lib/                # Utilitários do frontend
│   └── dist/                   # Build de produção
├── .github/workflows/
│   └── build-windows.yml       # CI/CD: build .exe + release a cada tag v*
├── oracle_v2_color.h5          # Modelo CNN colorido (21 MB)
├── oracle_v2_gray.h5           # Modelo CNN grayscale (21 MB)
├── oracle_v2_color.tflite      # Modelo TFLite colorido (9.2 MB)
├── oracle_v2_gray.tflite       # Modelo TFLite grayscale (9.2 MB)
├── setup.iss                   # Script Inno Setup para instalador Windows
├── build_windows.py            # Pipeline de build: frontend → PyInstaller → Inno Setup
├── dashboard_server.py         # Backend FastAPI do dashboard
├── launch_dashboard.py         # Launcher do dashboard (pywebview)
├── main.py                     # Entry point
├── options_resolver.py         # Parser do options.ini
├── options.ini                 # Configuração do usuário
├── options_example.ini         # Template documentado de configuração
├── classes.txt                 # 16 labels das classes do captcha
├── setup.sh                    # Instalador de atalho CLI (Linux/macOS)
└── requirements.txt            # Dependências Python
```

---

## 2. Interfaces

Feature novo **deve** ser refletido em todas as interfaces aplicáveis. Siga esta tabela como checklist única:

| Interface        | Onde atualizar                                                              | O quê                             |
| ---------------- | --------------------------------------------------------------------------- | --------------------------------- |
| **Core (bot)**   | `handlers.py`, `parsers.py`, `state.py`, `config.py`                        | Lógica, estado, config            |
| **Discord `sb`** | `handlers.py` (bloco de comandos `sb`, próximo ao final)                    | Help text + handler               |
| **TUI comandos** | `tui_input.py` (dict `COMMANDS`)                                            | Entrada de autocomplete           |
| **TUI config**   | `tui_modals.py` (tupla em `CONFIG_FIELDS` + descrição em `CONFIG_METADATA`) | Campo editável no modal           |
| **Dashboard**    | `ConfigTab.jsx` (array de campos)                                           | `<TextField>` ou `<ToggleSwitch>` |
| **Telegram**     | `telegram.py` + chamada em `handlers.py` ou `parsers.py`                    | Notificação relevante             |
| **README**       | `README.md` (tabela de comandos, seção de features)                         | Documentação pública              |
| **Help (todas)** | `sb help` no Discord, `/help` na TUI, `README.md`                           | Descrição do feature              |
| **Dashboard API**| `dashboard_server.py` (endpoints FastAPI) + WebSocket no `/ws/terminal`     | Novo endpoint ou evento WS        |
| **Modelo IA**    | `captcha.py` (lógica de inferência) + `config.py` (constantes do modelo)    | Nova rota de modelo ou classe     |
| **Build/CI**     | `build_windows.py` + `.github/workflows/build-windows.yml`                  | Etapa nova no pipeline            |

---

## 3. Checklist de Validação

### 3.1 Antes de escrever código

- [ ] Entender o fluxo completo (entry point → state → output)
- [ ] Identificar quais interfaces da seção 2 precisam ser atualizadas
- [ ] Verificar se existe padrão similar no código para seguir

### 3.2 Após escrever código

- [ ] `python3 -c "import py_compile; py_compile.compile('bot/arquivo.py', doraise=True)"` — syntax check
- [ ] Verificar o feature em **todas** as interfaces da seção 2
- [ ] Verificar tipos: `config.ADMIN_IDS` é `list[int]`, `duel_partner_id` é `str`, `partner_name` é `str | None`
- [ ] Tratar exceções em chamadas de API do Discord (`fetch_member`, `send_message`)
- [ ] Não quebrar fluxo existente — feature novo não altera comportamento de features antigos
- [ ] Se mexeu no modelo: verificar predição com ambas as rotas (color + gray) e fallback
- [ ] Se mexeu no dashboard API: testar com `curl` ou Swagger em `/docs`
- [ ] Se mexeu no build: rodar `python build_windows.py --frontend` e verificar `dashboard/dist/`

### 3.3 Após o deploy

- [ ] Testar com ambas as contas ativas (thix*.* e thix2)
- [ ] Verificar logs por erros silenciosos (`except Exception: pass`)
- [ ] Confirmar que o bot não trava em cenários de borda (DM, guild None, cache vazio)

---

## 4. Padrões de Implementação

### 4.1 Comandos `sb`

Em `handlers.py`, bloco de comandos do admin (próximo ao final, seção `# ─── SB COMMANDS ───`):

```python
elif msg == "sb novo_comando":
    ...
    return
```

### 4.2 Configs

```python
# config.py
nova_config = userOptions.get("nova_config", "default").lower() == "true"

# tui_modals.py — adicionar na tupla CONFIG_FIELDS:
("nova_config", "bool", "false"),   # (campo, tipo, default)

# tui_modals.py — adicionar em CONFIG_METADATA:
"nova_config": "Descrição do que faz",

# ConfigTab.jsx — adicionar no array de campos do ConfigSection:
{ field: "nova_config", label: "Nova Config" },
```

### 4.3 Estados

Em `state.py`, dentro de `BotState.__init__`:

```python
self.novo_estado = False
self.novo_estado_dados = None
```

### 4.4 Queue de Comandos

```python
from bot.state import add_to_high_priority_queue, add_to_low_priority_queue

add_to_high_priority_queue("rpg cmd")   # resposta imediata (remove da LPQ se existir)
add_to_low_priority_queue("rpg cmd")    # comando periódico

# Duelos e auto-enchant: limpam LPQ automaticamente ao adicionar à HPQ
bot_state.duel_in_progress = True  # bloqueia novos comandos rpg na LPQ
```

---

## 5. Convenções de Código

### 5.1 Python

- Seguir estilo existente (sem type hints excessivos, sem docstrings em métodos simples)
- Imports: `bot.config as config`, `from bot.state import bot_state, ...`
- Nunca fazer `import` dentro de funções — nem para imports condicionais ou circulares
- Logging: `logger.info()`, `HUD.system()`, `HUD.alert()` (ver seção 5.4)
- Filas: `add_to_high_priority_queue()` / `add_to_low_priority_queue()`
- Exceções da API do Discord: `try/except Exception: pass`

### 5.2 React (Dashboard)

- Componentes funcionais com hooks
- Estado via Zustand (`useOracleStore`)
- Estilos via Tailwind CSS + CSS variables (temas)
- Componentes: `ConfigSection`, `ToggleSwitch`, `TextField`

### 5.3 Selfbot

- A API do Discord para selfbots é limitada — não usar `guild.members` para member lookup
- Usar `guild.fetch_member(id)` para dados confiáveis
- Cache do selfbot é unreliable — sempre ir direto à API quando preciso de dados atualizados
- Mensagens entre canais diferentes precisam de bypass no channel filter

### 5.4 HUD — Output e Estilo

`bot/hud.py` expõe os seguintes métodos estáticos para logging visual. Use cada um de acordo com a semântica:

| Método                             | Prefixo           | Ícone | Quando usar                                    | Tom                        |
| ---------------------------------- | ----------------- | ----- | ---------------------------------------------- | -------------------------- |
| `HUD.system(msg)`                  | `[SIS]`           | ⚙️    | Eventos técnicos (inicialização, pause, reset) | Neutro, informativo        |
| `HUD.alert(msg)`                   | `[ALERTA]`        | 🚨    | Erros, captcha, jail, watchdog                 | Urgente, tudo em maiúsculo |
| `HUD.oracle(msg)`                  | `[ORACLE]`        | 🔮    | Ações do bot (vitórias, conclusões)            | Solene, positivo           |
| `HUD.loot(player, item, qty)`      | `[LOOT]`          | 📦    | Drops de loot                                  | Comemorativo               |
| `HUD.command(cmd, priority="LPQ")` | `[HPQ]/[LPQ]`     | ⚡⚙️  | Comandos enviados ao Discord                   | Técnico, descritivo        |
| `HUD.cooldown(msg)`                | `[COOLDOWN]`      | ⏳    | Cooldowns e timers                             | Informativo                |
| `HUD.dungeon(msg)`                 | `[DUNGEON]`       | ⚔️    | Eventos de dungeon                             | Temático, tom de batalha   |
| `HUD.tc(msg)`                      | `[TIME COOKIE]`   | 🍪    | Modo Time Cookie                               | Descontraído               |
| `HUD.cardhand(msg)`                | `[MÃO DE CARTAS]` | 🃏    | Minijogo de cartas                             | Lúdico                     |
| `HUD.navi(msg)`                    | `[NAVI]`          | 🧚    | Tutoriais, dicas, lembretes                    | Amigável, tom de ajuda     |
| `HUD.separator()`                  | `─` × 60          | —     | Separador visual entre seções                  | —                          |

Regras de estilo:

- **Nunca** usar `print()` diretamente — sempre usar `HUD.*()` ou `logger.*()`
- Emojis são obrigatórios em todas as mensagens HUD (cada método já tem o seu)
- Evitar texto em maiúsculo exceto em `HUD.alert()` (que já aplica `.upper()`)
- Para logs técnicos (debug/diagnóstico), usar `logger.info()` ou `logger.debug()` do módulo `logging`

### 5.5 Telegram — Notificações

`bot/telegram.py` expõe funções `async` para enviar notificações externas:

```python
from bot.telegram import (
    send_telegram_notification,  # MarkdownV2 com auto-escape
    send_telegram_raw,           # Texto plano, sem escape
    send_telegram_photo,         # Foto com legenda
    send_telegram_keyboard,      # Mensagem com botões inline
    edit_telegram_message,       # Editar mensagem existente
    get_telegram_override,       # Poll do último comando recebido
)
```

**Quando notificar:**

- Captcha detectado (foto + alerta no Telegram)
- Jail detectado
- Duelo aceito/recusado pelo parceiro
- Erro grave que requer intervenção humana
- Eventos importantes (dungeon concluída, loot raro)

**Tom de voz:**

- Mensagens incluem perfil e usuário via `append_profile_info()` (automático nas funções)
- Preferir `send_telegram_notification` (MarkdownV2) para textos formatados
- Usar `send_telegram_raw` quando o texto contém caracteres especiais não escapáveis
- Manter o tom informativo e direto — sem emojis excessivos (ao contrário do HUD)
- Mensagens de erro devem prefixar com `⚠️`

### 5.6 Persistence — Save/Load

`bot/persistence.py` gerencia dados persistentes com nomes de arquivo baseados no perfil ativo:

```python
from bot.persistence import load_session_data, save_session_data, save_session_baseline

# Carregar dados no startup:
session_data = load_session_data(DEFAULT_SESSION_DATA)

# Salvar durante a sessão:
save_session_data(session_data, save_snapshot=False)

# Salvar snapshot histórico (para stats por período):
save_session_data(session_data, save_snapshot=True)

# Salvar baseline no início da sessão (para o dashboard calcular stats da sessão):
save_session_baseline(session_data)

# Consultar stats de um período:
from bot.persistence import get_stats_for_period
period_data = get_stats_for_period(current_data, "24h")  # "10h", "10d", "1m"
```

Regras:

- Chamar `save_session_data()` automaticamente em intervalos (já implementado em `state.py:last_save_time`)
- `sessionData` é o singleton global em `state.py` — importar de lá, não do persistence
- Nunca salvar em loops apertados — usar o timer existente ou throttle manual

---

## 6. Padrões Importantes

### 6.1 Channel Filter (client.py)

O bot bloqueia mensagens do Epic RPG que não vêm do canal configurado. Para features que recebem mensagens em canais diferentes (como duels), adicionar bypass:

```python
# Em client.py, seção "Channel Filter":
invite_keywords = ["will you accept", "do you want to join"]
has_invite = any(kw in combined_content for kw in invite_keywords)
has_my_name = config.user_name_lower in combined_content
if has_invite and has_my_name:
    is_invite = True
```

### 6.2 Machine States (handlers.py)

Features complexos usam máquina de estados com `bot_state`:

- `duel_in_progress`, `duel_step`, `duel_channel_id`, `duel_weapon_chosen`
- `auto_enchant_active`, `auto_enchant_tier`, etc.
- `sleepet_mode`, `sleepet_state`

### 6.3 IDs e Tipos

```python
config.ADMIN_IDS          # list[int] — IDs de admins
config.duel_partner_id    # str — ID do parceiro (pode ser vazio)
config.partner_name       # str | None — nome do parceiro
config.userID             # int — ID da conta atual
config.user_name_lower    # str — nome da conta em lowercase
config.channelID          # int — ID do canal principal
```

---

## 7. Erros Comuns e Como Evitar

| Erro                                    | Causa                                              | Solução                                     |
| --------------------------------------- | -------------------------------------------------- | ------------------------------------------- |
| Duelo não aceita                        | Channel filter bloqueia mensagem                   | Adicionar bypass em `client.py` (ver 6.1)   |
| `guild.get_member_named()` retorna None | Cache do selfbot vazio                             | Usar `guild.fetch_member(id)`               |
| `message.guild` é None                  | Mensagem veio de DM                                | Checar `if guild:` antes de usar            |
| Config não aparece na TUI               | Falta entrada em `CONFIG_METADATA`/`CONFIG_FIELDS` | Adicionar em `tui_modals.py`                |
| Help não menciona feature               | Falta entrada no `sb help`                         | Adicionar no bloco de help do `handlers.py` |
| Dashboard não mostra config             | Falta campo no `ConfigTab.jsx`                     | Adicionar `<TextField>` ou `<ToggleSwitch>` |
| Feature quebra outro feature            | Alteração em fluxo compartilhado                   | Verificar impacto em todos os caminhos      |
| HUD não aparece na TUI                  | Usou `print()` em vez de `HUD.*()`                 | Substituir por método HUD adequado          |
| Modelo não carrega                      | `.h5` ou `.tflite` ausente ou corrompido           | Verificar `config.captcha_model_color/gray` |
| Captcha sempre falha                    | Modelo errado para o tipo de imagem                | `captcha.py` faz fallback automático (color↔gray) |
| Dashboard não inicia                    | `dashboard/dist/` não existe ou vazio              | Rodar `cd dashboard && npm run build`       |
| WebSocket desconecta                    | Bot process crashou ou timeout                     | Verificar `dashboard_server.py` watchdog em `_watch_process()` |
| `build_windows.py` falha                | Python sem shared library (Linux)                  | Usar `find_build_python()` que cria `.venv_build/` com Python 3.12 |
| `.exe` não abre                         | PyInstaller frozen mode sem hidden import          | Adicionar hidden import em `build_windows.py` |
| Scroll do terminal buga/rolagem na página | Evento wheel propaga até a página ou entra em conflito com xterm.js | Chamar `e.preventDefault()` no handle do event `wheel` e realizar a rolagem programaticamente com a API `term.scrollLines(lines)` |

---

## 8. Commits e Deploy

### 8.1 Formato de commit

```
tipo(escopo): descrição curta

- detalhe 1
- detalhe 2
```

Tipos: `feat`, `fix`, `refactor`, `chore`, `docs`

### 8.2 Antes de commitar

- [ ] Syntax check em todos os arquivos .py modificados
- [ ] Verificar que nenhuma feature existente quebrou (rodar testes manuais nos fluxos principais)
- [ ] Testar o fluxo principal do feature novo
- [ ] Atualizar documentação se aplicável (README, `sb help`, TUI help, AGENTS.md)

### 8.3 Deploy — Pipeline de Build (3 etapas)

O projeto tem um pipeline completo que transforma código fonte em um instalador Windows `.exe`:

```
Código → npm build (React) → PyInstaller (Python bundle) → Inno Setup (Instalador .exe)
```

**Etapa 1 — Frontend:**
```bash
cd dashboard && npm install && npm run build
```
Gera `dashboard/dist/` com os assets estáticos (JS, CSS, HTML).

**Etapa 2 — PyInstaller:**
```bash
python build_windows.py --package
```
Empacota o bot + dashboard em um executável `OracleOS.exe` usando `--onedir`. Inclui:
- Modelos `.h5` e `.tflite` (se existirem)
- Frontend buildado (`dashboard/dist/`)
- `options_example.ini`, `classes.txt`, `bot/tui_theme.tcss`
- Hidden imports: TensorFlow, Uvicorn, FastAPI, Starlette, Pydantic, Textual, discord, aiohttp

**Etapa 3 — Inno Setup (Windows):**
```bash
python build_windows.py --installer   # ou: ISCC.exe setup.iss
```
Gera `Output/OracleOS_Setup.exe` — instalador Windows com ícone, desinstalador, atalhos.

### 8.4 CI/CD — GitHub Actions (Automático)

O arquivo `.github/workflows/build-windows.yml` executa o pipeline completo automaticamente:

**Trigger:** Toda tag `v*` (ex: `v3.0.1`) ou manual via `workflow_dispatch`

**Pipeline:**
```
checkout → setup Python 3.12 + Node.js 20
         → pip install -r requirements.txt pyinstaller
         → npm install && npm run build  (frontend)
         → python build_windows.py --package  (PyInstaller)
         → choco install innosetup && ISCC.exe setup.iss  (instalador)
         → upload artifact (OracleOS_Setup.exe)
         → criar GitHub Release (se tag v*)
```

**Importante:**
- A pipeline roda no `windows-latest` — o `.exe` gerado é nativo Windows
- Se for adicionar nova dependência Python, testar se o PyInstaller a detecta. Se não, adicionar em `hidden_imports` dentro de `build_windows.py`
- O artifact fica disponível por 90 dias nos detalhes da Action

---

## 9. Modelo de IA (Captcha)

### 9.1 Arquitetura do Sistema

O Oracle usa **dois modelos CNN independentes** para resolver captchas do Epic RPG, com fallback automático cross-model:

| Modelo | Arquivo | Tamanho | Acurácia | Confiança Média |
|--------|---------|---------|----------|-----------------|
| Colorido (RGB) | `oracle_v2_color.h5` | 21 MB | 96.28% | 97.01% |
| Grayscale | `oracle_v2_gray.h5` | 21 MB | 95.15% | 95.55% |
| Colorido (TFLite) | `oracle_v2_color.tflite` | 9.2 MB | *mesmo modelo, formato otimizado* | — |
| Grayscale (TFLite) | `oracle_v2_gray.tflite` | 9.2 MB | *mesmo modelo, formato otimizado* | — |

**16 classes** de captcha definidas em `classes.txt`.

### 9.2 Roteamento de Inferência

O fluxo em `bot/captcha.py:tentar_resolver_captcha()`:

```
1. Salvar attachment → detectar se é grayscale (função is_grayscale())
2. Rota primária: modelo COLOR (preferencial — maior acurácia)
3. Se confiança < 80% E modelo alternativo existe:
   → Fallback: rodar modelo GRAY
   → Se confiança do gray > color: usar predição gray
4. Top-3 predictions como palpites
5. Enviar para o canal do Discord (com delay humano 1.5-3s entre tentativas)
6. Se falhar: marcar como jailed + notificar Telegram
```

**Regras:**
- Modelo colorido é sempre preferido (96.28% vs 95.15%), mesmo em imagens grayscale
- `config.captcha_model_color` e `config.captcha_model_gray` são carregados em `config.py`
- Fallback cross-model é ativado quando confiança < 80%
- Se nenhum modelo estiver disponível: aguarda override manual via Telegram

### 9.3 TFLite

Os arquivos `.tflite` existem no repositório mas **não são usados atualmente** pelo `captcha.py`. Foram convertidos para potencial uso futuro em dispositivos com recursos limitados. Para ativar:

```python
import tflite_runtime.interpreter as tflite
interpreter = tflite.Interpreter(model_path="oracle_v2_color.tflite")
```

### 9.4 Como adicionar/retreinar

- Modelos são carregados em `config.py` via `tf.keras.models.load_model()`
- Pipeline de treino: `train_model_no_aug.py` (em `Epic-Rpg-Macro-main/`)
- Dataset: `dataset_cropped/` (imagens de captcha recortadas)
- Para substituir um modelo: colocar novo `.h5` na raiz com o mesmo nome

---

## 10. FastAPI Dashboard — API de Referência

O backend do dashboard em `dashboard_server.py` expõe uma API REST + WebSocket.

### 10.1 Endpoints REST

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/config?profile=` | Retorna configuração do perfil (tokens mascarados) |
| `POST` | `/api/config` | Atualiza settings do perfil (restaura tokens se mascarados) |
| `GET` | `/api/status?profile=` | Estado do bot (offline/starting/online/stopping) + filas |
| `GET` | `/api/stats?profile=&mode=session` | Estatísticas da sessão (baseline subtraction) |
| `GET` | `/api/logs?profile=&limit=50` | Últimas N linhas do log |
| `POST` | `/api/bot/start` | Inicia o bot como subprocesso |
| `POST` | `/api/bot/stop` | Para o bot |
| `GET` | `/api/profiles` | Lista perfis com estado e flag de incomplete |
| `POST` | `/api/profiles` | Cria perfil (cópia de existente ou do example) |
| `DELETE` | `/api/profiles?name=` | Deleta perfil (exceto default) |
| `POST` | `/api/profiles/import` | Importa `.ini` via upload |
| `GET` | `/api/profiles/export?name=` | Exporta `.ini` como download |
| `WS` | `/ws/terminal?profile=` | WebSocket bidirecional (telemetria + input) |

### 10.2 WebSocket (`/ws/terminal`)

**Conexão:** `ws://127.0.0.1:8000/ws/terminal?profile=options.ini`

**Mensagens do servidor:**
- `{"type": "status", "profile": ..., "state": "online"}` — mudança de estado
- `{"type": "pong"}` — resposta a heartbeat
- `bytes` — output raw do terminal do bot (PTY)

**Mensagens do cliente:**
- `{"type": "heartbeat"}` → recebe `pong`
- `{"type": "resize", "cols": 80, "rows": 24}` → redimensiona PTY
- `bytes` → input do teclado enviado ao bot

### 10.3 BotProcessManager

Gerencia o ciclo de vida do bot como subprocesso:
- `start()`: spawn via PTY (POSIX) ou winpty (Windows), broadcast de status
- `stop()`: terminate → wait 5s → kill → cleanup
- `_watch_process()`: polling a cada 0.75s, detecta crash e broadcast
- `_output_worker()`: thread que lê stdout do PTY e broadcast via WebSocket

### 10.4 Frozen Mode Detection

Quando executado como `.exe` (PyInstaller), `sys.frozen` é `True`. O `_build_bot_command()` se adapta:

```python
if getattr(sys, "frozen", False):
    return [sys.executable, "--run-bot", profile]   # re-invoca o .exe
else:
    return [sys.executable, "main.py", profile]      # dev normal
```

### 10.5 Perfis Múltiplos

O dashboard gerencia múltiplos perfis (arquivos `.ini` em `user_data/`):
- Cada perfil tem seu próprio `BotProcessManager`
- Stats e logs são segregados por perfil
- Import/export de perfis via API
- Token masking: `user_token`, `miner_token`, `telegram_bot_token` são exibidos como `********`

### 10.6 Segurança

- CORS: `allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"` — apenas localhost
- Erros: handlers globais para `HTTPException` e `Exception` com payload padronizado
- Shutdown: `on_event("shutdown")` para todos os bots em execução

---

## 11. Build System (build_windows.py)

Script de build em `build_windows.py` com 3 subcomandos:

| Flag | Ação |
|------|------|
| `--frontend` | `npm run build` no dashboard |
| `--package` | PyInstaller `--onedir --windowed` |
| `--installer` | Inno Setup (ISCC.exe) |
| *(sem flag)* | Executa todas as 3 etapas |

**Detecção de Python:** `find_build_python()` procura Python 3.12 com shared library (necessário para PyInstaller no Linux). Cria `.venv_build/` se necessário.

**Hidden imports** (adicionar aqui se PyInstaller não detectar):
```python
# TensorFlow
"tflite_runtime", "numpy", "PIL"
# Uvicorn (todos os submodulos de protocolos/loops)
"uvicorn", "uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.h11_impl", ...
# FastAPI / Starlette / Pydantic
"fastapi", "fastapi.responses", "starlette.routing", "pydantic", "pydantic_core"
# Discord / Textual / aiohttp
"discord", "textual", "textual.app", "aiohttp", "colorama"
```
