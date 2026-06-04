# 🔮 Oracle OS — Plano do Web Dashboard

## Visão Geral

Dashboard web premium com aba de terminal interativo embutido, servido por um backend FastAPI que controla o bot Oracle v3. O usuário interage com tudo pelo navegador — configuração, controle, logs em tempo real e terminal PTY completo. Suporte a múltiplos perfis (contas) simultâneos.

**Stack**: React 19 · Vite · Tailwind CSS v4 · Zustand · Axios · Framer Motion · GSAP · xterm.js

---

## 1. Arquitetura

```
NAVEGADOR (React + xterm.js)
    │
    ├── REST (Axios)  ──→  FastAPI  ──→  options_resolver.py (CRUD .ini)
    │                        │
    ├── WS /ws/terminal ──→  BotProcessManager[profile]  ──→  PTY ↔ python main.py <profile>.ini
    │                        │
    └── WS /ws/stats ─────→  Leitura periódica de stats_*.json por perfil
```

### Princípios

- **Bind `127.0.0.1` only** — nunca expor na rede. CORS restrito a `localhost`.
- **Single process owner** — cada perfil é gerenciado por uma instância exclusiva de `BotProcessManager`.
- **Sem autenticação** — app local single-user. Segurança é isolamento de rede.
- **Processos independentes** — cada `python main.py <perfil>.ini` é um processo separado com singletons próprios, zero conflito de estado.

---

## 2. BotProcessManager

Classe central do backend. Cada instância gerencia **um** perfil (um `.ini`, um processo, um PTY).

```python
class BotProcessManager:
    """Gerencia o ciclo de vida de uma instância do bot."""

    profile: str              # nome do .ini (ex: "options.ini")
    state: BotState           # offline | starting | online | stopping
    process: Popen | None
    pty_master_fd: int | None # file descriptor do PTY (Linux)
    pty_process: PtyProcess   # pywinpty (Windows)
    ws_clients: list[WebSocket]  # clientes conectados ao terminal deste perfil
```

O backend mantém um dicionário global:

```python
managers: dict[str, BotProcessManager] = {}
# ex: {"options.ini": BotProcessManager(...), "alt.ini": BotProcessManager(...)}
```

### State Machine do Bot

```
         start()              on_ready
OFFLINE ────────→ STARTING ────────────→ ONLINE
   ↑                                      │
   │               stop()                 │
   └──────────── STOPPING ←───────────────┘
                    │
                    └──→ OFFLINE (processo encerrou)
```

**Regras da UI baseadas no estado**:

| Estado | Botão Start | Botão Stop | Terminal |
|---|---|---|---|
| OFFLINE | ✅ Habilitado | 🚫 Desabilitado | Desconectado |
| STARTING | 🚫 (loading spinner) | 🚫 | Conectando... |
| ONLINE | 🚫 | ✅ Habilitado | Ativo |
| STOPPING | 🚫 | 🚫 (loading spinner) | Desconectando... |

### Fluxo de Lifecycle (unificado)

1. **Start**: `POST /api/bot/start` → `BotProcessManager.start()` cria o PTY e spawna o processo. Estado: `OFFLINE → STARTING → ONLINE`.
2. **Conectar terminal**: `WS /ws/terminal?profile=x` se **conecta** ao PTY já existente. Se o bot não estiver rodando, o WS fica em espera.
3. **Stop**: `POST /api/bot/stop` → `BotProcessManager.stop()` mata o processo. Estado: `ONLINE → STOPPING → OFFLINE`. Todos os WS clients recebem notificação de desconexão.
4. **Crash recovery**: Se o processo morrer sozinho, o manager detecta via poll, transita para `OFFLINE` e notifica os WS clients.

---

## 3. Protocolo WebSocket do Terminal

### Framing

O WebSocket `/ws/terminal` usa **dois tipos de mensagem**:

| Tipo | Formato | Direção | Conteúdo |
|---|---|---|---|
| **Binary** | bytes crus | Bidirecional | I/O do terminal (ANSI escapes, texto, input do teclado) |
| **Text** | JSON string | Client → Server | Mensagens de controle |

### Mensagens de Controle (JSON)

```json
{"type": "resize", "cols": 120, "rows": 40}
{"type": "heartbeat"}
```

O servidor responde heartbeat com `{"type": "pong"}`.

### Resize Flow

1. `xterm-addon-fit` detecta mudança de tamanho do container
2. Frontend envia `{"type": "resize", "cols": N, "rows": M}`
3. Backend chama `os.set_terminal_size(master_fd, (rows, cols))` (Linux) ou `pty_process.set_size(cols, rows)` (Windows via pywinpty)
4. O Textual re-renderiza automaticamente

### Multi-cliente

Múltiplas abas do navegador podem conectar ao mesmo perfil. O backend faz **broadcast** da saída do PTY para todos os `ws_clients[]`. Input é aceito de qualquer cliente (último a digitar ganha — sem lock).

### Limites

- **Scrollback**: xterm.js configurado com `scrollback: 5000` linhas
- **Buffer de saída**: se nenhum WS client estiver conectado, o backend descarta a saída do PTY (não acumula em memória)

---

## 4. Gerenciamento de Perfis

### Endpoints

| Endpoint | Método | Função |
|---|---|---|
| `/api/profiles` | GET | Lista todos os `.ini` no diretório do projeto |
| `/api/profiles` | POST | Cria novo perfil (body: `{name, copyFrom?}`) |
| `/api/profiles` | DELETE | Remove perfil (`?name=alt.ini`). Não permite remover `options.ini`. |
| `/api/profiles/import` | POST | Upload de arquivo `.ini` (multipart) |
| `/api/profiles/export` | GET | Download do `.ini` (`?name=alt.ini`) |

### UX no Frontend

A sidebar esquerda (permanente, ~220px) lista os perfis disponíveis. Cada item mostra:
- Nome do perfil (sem extensão)
- Dot de status colorido (verde=online, cinza=offline, amarelo=coffee, roxo=starting)
- Botão de ações (⋮) → exportar, duplicar, remover

**Ações globais** (topo da sidebar):
- ➕ Novo perfil (modal: nome + opcionalmente clonar de perfil existente)
- 📥 Importar `.ini` (file upload dialog)

Clicar num perfil troca o **contexto** de todas as 4 abas (Overview, Terminal, Config, Stats) para aquele perfil. O Zustand store mantém `activeProfile` como chave.

---

## 5. API REST

### Endpoints Completos

Todos os endpoints de bot/config recebem `?profile=nome.ini` (default: `options.ini`).

| Endpoint | Método | Body/Params | Resposta |
|---|---|---|---|
| `/api/config` | GET | `?profile=` | `{config: {...}, masked: ["user_token"]}` |
| `/api/config` | POST | `{profile, settings: {...}}` | `{status: "ok"}` |
| `/api/status` | GET | `?profile=` | `{state, uptime, lastCommand, hpq, lpq}` |
| `/api/bot/start` | POST | `{profile}` | `{status: "started"}` |
| `/api/bot/stop` | POST | `{profile}` | `{status: "stopped"}` |

### Segurança Mínima

- `user_token` é retornado como `"••••••••"` no GET. O POST aceita o valor real.
- Backend bound a `127.0.0.1:8000` hardcoded.
- CORS: `allow_origins=["http://localhost:*", "http://127.0.0.1:*"]`

---

## 6. Design System

### Paleta de Cores

```
--bg-void:         #06060a       fundo principal
--bg-surface:      #0d0d14       cards e painéis
--bg-elevated:     #14141f       hover, inputs
--bg-glass:        rgba(20,20,31,0.6) + backdrop-blur-xl

--accent-primary:  #a78bfa       roxo Oracle (ações)
--accent-cyan:     #06b6d4       status online, indicadores
--accent-success:  #34d399       loot, sucesso
--accent-warning:  #fbbf24       alertas
--accent-danger:   #f87171       erro, parado

--text-primary:    #f0f0f5
--text-secondary:  #6b7280
--text-muted:      #374151
```

### Tipografia

- **UI**: `Inter` (400, 500, 600, 700)
- **Terminal/Código**: `JetBrains Mono` (400, 500)

### Efeitos Visuais

| Efeito | Onde |
|---|---|
| Glassmorphism | Cards, sidebar |
| Glow borders | Card ativo, status badge, botão primário hover |
| Gradiente sutil | Header (purple→transparent) |
| Framer Motion | Transição de abas (layoutId), entrada de cards, toggles spring |
| GSAP | Contadores numéricos animados (stats) |
| Pulse CSS | Dot de status "ONLINE" |

---

## 7. Layout e Abas

### Estrutura Global

```
Sidebar de Perfis (220px) │ Header (64px)
                          │ Tab Navigation
                          │ Conteúdo da Aba Ativa
```

### Header (fixo)

- Logo "ORACLE OS" com glow sutil + versão
- Badge de status com dot pulsante do perfil ativo
- Botão Start/Stop com transição animada de estado
- Uptime counter animado (GSAP)

### Tab Navigation

4 abas com ícones Lucide + label. Aba ativa tem underline gradiente animado (Framer `layoutId`).

### Aba 1: Overview

Grid responsivo (2 colunas desktop, 1 mobile):

**Esquerda**:
- Bot State Card (estado, uptime, último comando)
- Queue Card (HPQ/LPQ com barras visuais)
- Quick Actions (start, pause, reset, tc start)

**Direita**:
- Counters Grid 2×3 (Hunts, Adventures, Farms, Lootboxes, Coins, XP) com GSAP
- Recent Drops (últimos 10, coloridos por categoria)

**Rodapé**: Mini-terminal (5 linhas de log, clicável para ir à aba Terminal)

### Aba 2: Terminal

- **xterm.js** ocupando 100% do espaço disponível
- Tema sincronizado com paleta do dashboard
- Botão fullscreen (⛶) e clear (🗑)
- `xterm-addon-fit` para auto-resize
- `xterm-addon-web-links` para links clicáveis
- Reconexão automática com indicador visual
- Scrollback: 5000 linhas

### Aba 3: Config

Formulário em seções colapsáveis (Framer Motion):

| Seção | Campos |
|---|---|
| 🔑 Credenciais | `user_token`★, `user_mention_text`★, `channel_id`★, `guild_id`★ |
| ⚙️ Geral | `random_interval`, `typo_chance` |
| ⚔️ Adventure | `life_boost_before_adv`, `adventure_area`, `current_area`, `zombie_horde_event_response` |
| 🌾 Economy | `lootbox_type`, `seed`, `work_command`, `bankroll`, `max_losses`, `initial_step` |
| 📱 Telegram | `telegram_bot_token`★, `telegram_chat_id` |
| ✅ Features | `do_hunt` .. `do_card_hand` (toggles animados) |
| 🧪 Advanced | `do_ultr`, `card_hand_action`, `tc_quantity`, `is_eternal`, `is_married`, `partner_name`, `is_ascended`, `admin_ids`, `tc_stop_on` |
| 🕐 Schedule | `sleep_at`, `wake_up_at`, `theme` |

★ = Requer reinício (badge visual na UI)

**Componentes**: Toggle switches com spring animation, selects estilizados, inputs com label flutuante, password com toggle de visibilidade.

Botão "Salvar" fixo no rodapé com feedback (shake on error, pulse on success).

### Aba 4: Stats

- Summary Cards (coins, XP, tempo) com GSAP
- Loot Breakdown por categoria (tabela com barras relativas)
- Cards Grid (common→eternal com cores por raridade)
- Misc Stats (coolness, arena cookies, guard events)

---

## 8. Matriz de Hot Reload

Ao salvar configurações, o frontend exibe badges indicando quais mudanças tomam efeito imediato vs quais precisam de reinício.

### ⚡ Runtime (efeito imediato via `cfg` command)

| Chave | Motivo |
|---|---|
| `do_hunt`, `do_adv`, `do_farm`, `do_work`, `do_training` | Flags lidas a cada ciclo |
| `do_daily`, `do_weekly`, `do_quest`, `do_lootbox`, `do_dungeon` | Idem |
| `do_card_hand`, `do_ultr`, `card_hand_action` | Idem |
| `random_interval` | Lida antes de cada delay |
| `sleep_at`, `wake_up_at` | Verificado a cada tick |
| `theme` | CSS swap, sem restart |

### 🔄 Requer Reinício

| Chave | Motivo |
|---|---|
| `user_token` | Autenticação Discord no startup |
| `user_mention_text`, `user_id` | Parsados uma vez em `config.py` |
| `channel_id`, `guild_id` | Usados como int no startup |
| `telegram_bot_token`, `telegram_chat_id` | Inicializados uma vez |
| `bankroll`, `max_losses`, `initial_step` | Constroem `CoinFlipFibonacci` no startup |
| `seed`, `work_command`, `lootbox_type` | Lidos uma vez em `config.py` |
| `is_married`, `partner_name`, `is_ascended` | Afetam estrutura de dados da sessão |

---

## 9. Estado Global (Zustand)

```javascript
// stores/useOracleStore.js
{
  // Perfis
  profiles: ["options.ini", "alt.ini"],
  activeProfile: "options.ini",

  // Bot (por perfil ativo)
  botState: "offline",  // offline | starting | online | stopping
  uptime: 0,
  lastCommand: "",
  hpqSize: 0,
  lpqSize: 0,

  // Config
  config: {},
  configDirty: false,

  // Stats
  sessionStats: {
    commands: { hunt: 0, adventure: 0, farm: 0, training: 0, work: 0,
                quest: 0, daily: 0, weekly: 0, lootbox: 0 },
    progress: { coins: 0, xp: 0, levels: 0 },
    loot: { mob_drops: {}, lootbox_drops: {}, work_drops: {}, farm_drops: {} },
    misc: { cards: {}, coolness: 0, arena_cookies: 0 }
  },

  // Terminal
  terminalConnected: false,

  // Actions
  setActiveProfile: (name) => ...,
  fetchProfiles: () => ...,
  fetchConfig: () => ...,
  saveConfig: (updates) => ...,
  startBot: () => ...,
  stopBot: () => ...,
}
```

---

## 10. Estrutura de Arquivos

```
Oracle-V2/
├── dashboard/                      ← Frontend React
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx                 ← Layout global + sidebar + tabs
│   │   ├── index.css               ← Tailwind + custom props
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── TabNav.jsx
│   │   │   ├── ProfileSidebar.jsx
│   │   │   ├── StatusBadge.jsx
│   │   │   ├── AnimatedCounter.jsx
│   │   │   ├── ToggleSwitch.jsx
│   │   │   ├── GlassCard.jsx
│   │   │   ├── ConfigSection.jsx
│   │   │   └── MiniTerminal.jsx
│   │   ├── tabs/
│   │   │   ├── OverviewTab.jsx
│   │   │   ├── TerminalTab.jsx
│   │   │   ├── ConfigTab.jsx
│   │   │   └── StatsTab.jsx
│   │   ├── stores/
│   │   │   └── useOracleStore.js
│   │   └── lib/
│   │       ├── api.js
│   │       └── terminal.js
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── dashboard_server.py             ← Backend FastAPI
├── launch_dashboard.py             ← Entry point do executável
├── main.py                         ← Bot (existente, sem alterações)
├── bot/                            ← Código do bot (sem alterações)
└── requirements.txt                ← + fastapi, uvicorn, pywinpty
```

---

## 11. Dependências

### Python (adicionar ao requirements.txt)
```
fastapi
uvicorn[standard]
python-multipart
pywinpty; sys_platform == "win32"
```

### Node.js (dashboard/package.json)
```json
{
  "dependencies": {
    "react": "^19",
    "react-dom": "^19",
    "@xterm/xterm": "^5",
    "@xterm/addon-fit": "^0.10",
    "@xterm/addon-web-links": "^0.11",
    "zustand": "^5",
    "axios": "^1",
    "framer-motion": "^12",
    "gsap": "^3",
    "lucide-react": "^0.400"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4",
    "tailwindcss": "^4",
    "vite": "^6",
    "@vitejs/plugin-react": "^4"
  }
}
```

---

## 12. Empacotamento Windows

### Build Pipeline

```bash
# 1. Compilar frontend
cd dashboard && npm run build && cd ..

# 2. PyInstaller (--onedir para TF pesado)
pyinstaller --name=OracleOS --onedir --windowed \
  --add-data="dashboard/dist:dashboard/dist" \
  --add-data="options_example.ini:." \
  --add-data="classes.txt:." \
  --add-data="oracle_v2_color.h5:." \
  --add-data="oracle_v2_gray.h5:." \
  --hidden-import=tensorflow --hidden-import=uvicorn --hidden-import=fastapi \
  launch_dashboard.py

# 3. Instalador (Inno Setup)
iscc setup.iss  # → Output/OracleOS_Setup.exe
```

### launch_dashboard.py

1. Inicia uvicorn em thread daemon (`127.0.0.1:8000`)
2. Tenta `pywebview` (janela nativa) → fallback `webbrowser.open()`
3. FastAPI monta `dashboard/dist/` como static files

**Dependência opcional**: `pywebview` para janela nativa desktop. Se não instalado, abre no browser padrão.

---

## 13. Ordem de Implementação

| Fase | Tarefa |
|---|---|
| **1** | `dashboard_server.py`: `BotProcessManager` + endpoints REST + WebSocket PTY com framing binário/JSON |
| **2** | Scaffold React: Vite + Tailwind + estrutura de pastas + Zustand store |
| **3** | Design system: `index.css` com paleta, glass cards, tipografia (Inter + JetBrains Mono) |
| **4** | `ProfileSidebar.jsx` + `Header.jsx` + `TabNav.jsx` com Framer Motion |
| **5** | `OverviewTab.jsx` com status cards, GSAP counters, quick actions |
| **6** | `TerminalTab.jsx` com xterm.js + WS PTY bidirecional + resize + reconnect |
| **7** | `ConfigTab.jsx` com seções colapsáveis, toggles, selects, badges runtime/restart |
| **8** | `StatsTab.jsx` com loot breakdown e misc stats |
| **9** | Endpoints de perfis (CRUD, import/export) + UI da sidebar |
| **10** | `launch_dashboard.py` + teste end-to-end local |
| **11** | `build_windows.py` + `setup.iss` para empacotamento final |
