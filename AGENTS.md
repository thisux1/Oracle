# Oracle v3 — Agent Guide

Guia de referência para agentes de código trabalhando neste repositório.

---

## 1. Arquitetura do Projeto

```
Oracle-V2/
├── bot/                    # Core do bot (Python)
│   ├── client.py           # WebSocket do Discord, filtro de canais, loop principal
│   ├── handlers.py         # Processamento de mensagens, machine states, sb commands
│   ├── parsers.py          # Detecção de eventos Epic RPG (drops, ready, duel, etc.)
│   ├── config.py           # Carregamento do options.ini, constantes, tipos
│   ├── state.py            # Estado global do bot (filas, flags, contadores)
│   ├── telegram.py         # Notificações via Telegram
│   ├── hud.py              # Output formatado (logs, display)
│   ├── tui.py              # Interface TUI (Textual)
│   ├── tui_input.py        # CLI com autocomplete da TUI
│   ├── tui_modals.py       # Modais de configuração da TUI
│   ├── tui_sidebar.py      # Sidebar de telemetria da TUI
│   ├── captcha.py          # Resolução de captchas com IA
│   ├── persistence.py      # Save/load de session data e stats
│   ├── typo.py             # Simulação de erros de digitação
│   └── utils.py            # Utilitários gerais
├── dashboard/              # Web Dashboard (React + FastAPI)
│   ├── src/
│   │   ├── tabs/           # OverviewTab, ConfigTab, StatsTab, TerminalTab
│   │   ├── components/     # Componentes React reutilizáveis
│   │   ├── stores/         # Zustand stores (useOracleStore)
│   │   └── lib/            # Utilitários do frontend
│   └── dist/               # Build de produção
├── dashboard_server.py     # Backend FastAPI do dashboard
├── launch_dashboard.py     # Launcher do dashboard (pywebview)
├── main.py                 # Entry point
├── options_resolver.py     # Parser do options.ini
└── options.ini             # Configuração do usuário
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
- [ ] Atualizar documentação se aplicável (README, `sb help`, TUI help)

### 8.3 Deploy

```bash
# Dashboard
cd dashboard && npm run build

# Bot
python main.py
```

- Verificar logs por erros após iniciar
- Confirmar que todas as interfaces (Discord, TUI, Dashboard) estão operacionais
