<!-- MASCOTE VISUAL DO TERMINAL -->
<p align="center">
  <img src="banner.svg" alt="Banner do Olho Cibernético do Oracle v3" width="100%" style="border-radius: 8px; border: 1px solid rgba(168, 85, 247, 0.18);" />
</p>


🇺🇸 **For the English version of this document, see: [README.md](../README.md).**


```text
 ██████╗ ██████╗  █████╗  ██████╗██╗     ███████╗   ██╗   ██╗██████╗ 
██╔═══██╗██╔══██╗██╔══██╗██╔════╝██║     ██╔════╝   ██║   ██║╚════██╗
██║   ██║██████╔╝███████║██║     ██║     █████╗     ██║   ██║ █████╔╝
██║   ██║██╔══██╗██╔══██║██║     ██║     ██╔══╝     ╚██╗ ██╔╝ ╚═══██╗
╚██████╔╝██║  ██║██║  ██║╚██████╗███████╗███████╗    ╚████╔╝ ██████╔╝
 ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚══════╝     ╚═══╝  ╚═════╝
```


─────── ▪ ───────

## 📡 Diagnósticos do Sistema

O **Oracle v3** é um assistente de automação baseado em máquinas de estados de baixa latência construído sob medida para o Epic RPG. Otimizado para execução precisa de loops de jogo e segundo plano seguro, ele gerencia uma fila inteligente de comandos humanizados. O sistema utiliza inteligência artificial local (**Rede Neural Convolucional via TensorFlow Lite**) exclusivamente para a resolução de captchas e verificações de segurança, exibindo a telemetria do console via interface de terminal (**TUI**) e um **Web Dashboard** interativo.

─────── ▪ ───────

## 🧠 Arquitetura do Sistema e Fluxos de Dados

O diagrama abaixo detalha a estrutura de execução contínua, manipulando a transmissão de dados entre servidores Discord, nosso motor de filas de comando e o classificador de captchas local:

<p align="center">
  <img src="architecture.svg" alt="Pipeline de Fluxo de Dados Oracle v3" width="100%" style="border-radius: 8px; border: 1px solid rgba(168, 85, 247, 0.1);" />
</p>

### Fases de Execução da Automação
1. **Captura/Escuta**: O gateway de WebSocket de cliente do Discord captura as mensagens da guilda em tempo real através da biblioteca `discord.py-self`.
2. **Decomposição/Análise**: O analisador (Parser) extrai cooldowns de comandos, eventos ativos e argumentos solicitados pelas respostas de jogo.
3. **Resolução de Bloqueio**: Captchas disparam o recorte da imagem e processamento com OpenCV, resolvendo símbolos via **TensorFlow Lite** de forma local e assíncrona.
4. **Humanização**: As macros e ações passam pelo gerador de atraso que injeta desvios aleatórios de tempo, emulação de erros de digitação e pausa para ciclos de café e sono profundo.
5. **Telemetria**: Métricas de progresso de sessão são repassadas via sockets para atualizar a TUI do console e painéis web de forma simultânea.

─────── ▪ ───────

## ⚙️ Especificações Técnicas de Ambiente

```ini
[system-specification]
runtime      = Python 3.12 + Node.js v20
gateway_lib  = Discord.py-self v2.0 (Stealth Client)
ai_solver    = TensorFlow Lite 2.17 (Captcha CNN)
console_ui   = Textual TUI + Estilização Rich
web_backend  = FastAPI + Uvicorn + WebSockets
web_frontend = React 19 + Vite + Tailwind CSS v4 + Zustand
installers   = PyInstaller wrapper + Pacotes Inno Setup
```

| Módulo do Sistema | Tecnologias | Escopo de Operação |
| :--- | :--- | :--- |
| **Daemon de Automação** | Python, asyncio | Processamento de loops, gerenciamento de perfis e orquestração de filas. |
| **Resolvedor de Captcha** | TF Lite, OpenCV | Detecção de captchas, segmentação, limpeza e classificação de caracteres. |
| **Terminal de Console** | Textual, Temas TUI | Monitoramento de telemetria rápida, mascote animado e console de comandos. |
| **Backend de Controle** | FastAPI, WebSockets | Servidor web que alimenta o dashboard e persiste alterações nos dados de configuração. |
| **Web Dashboard** | React 19, Zustand | Painel visual de controle remoto, alteração de opções e acionamento de comandos de console. |
| **Empacotadores** | PyInstaller, Inno | Geração de pacotes executáveis de instalação autônoma e portabilidade. |

─────── ▪ ───────

## 🚀 Linha de Implantação

<details>
<summary><b>[1] Inicializar Workspace Virtual</b></summary>
<br />

Isole o ambiente do interpretador Python e ative os binários da sessão:

```bash
# Criar diretório virtual:
python3 -m venv venv

# Ativar (Linux/macOS):
source venv/bin/activate

# Ativar (Windows CMD):
venv\Scripts\activate.bat
```
</details>

<details>
<summary><b>[2] Instalar Pacotes de Execução</b></summary>
<br />

Baixe e atualize os requisitos da aplicação:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```
</details>

<details>
<summary><b>[3] Configurar Credenciais de Perfil</b></summary>
<br />

Inicie os dados de configuração local copiando o template de exemplo:

```bash
cp options_example.ini options.ini
```

Abra o arquivo `options.ini` e defina suas credenciais:
```ini
language=pt
user_token=seu_token_de_usuario_do_discord
channel_id=id_do_canal_de_mensagens
guild_id=id_da_guilda_do_servidor
do_hunt=true
do_adv=true
```
</details>

<details>
<summary><b>[4] Boot do Console Oracle (TUI Mode)</b></summary>
<br />

Inicie o painel interativo no terminal:

```bash
python main.py
```
</details>

<details>
<summary><b>[5] Deploy do Dashboard de Controle Web</b></summary>
<br />

Rode o servidor local FastAPI e visualize métricas e relatórios gráficos:

```bash
python launch_dashboard.py
```
*Monitore dados e acesse o mini-terminal em tempo real no navegador.*
</details>

<details>
<summary><b>[6] Compilar Artefatos e Empacotar Executáveis</b></summary>
<br />

Gere builds consolidadas e empacote as dependências em um único `.exe`:

```bash
# Compilar build do Dashboard React:
cd dashboard
npm install
npm run build
cd ..

# Build do Executável Windows:
python build_windows.py
```
</details>

<details>
<summary><b>[7] Registrar Atalho Global no Terminal (Linux)</b></summary>
<br />

Gere o Wrapper global do script CLI:

```bash
chmod +x setup.sh && ./setup.sh
source ~/.bashrc
```
Com isso, você pode rodar o bot de qualquer pasta digitando apenas:
```bash
oracle
```
</details>

─────── ▪ ───────

## 📂 Organização das Pastas

```path
Oracle-V2/
├── bot/                # Daemon em Python, handlers e regras da TUI
│   ├── tui.py          # Aplicação principal Textual
│   ├── tui_eye.py      # Definição do olho e do gato animado
│   └── tui_splash_art.py # Splash art gigante em Braille do terminal
├── dashboard/          # Web Dashboard escrito em React (Vite, CSS)
├── docs/               # Documentação gráfica e localização de README
│   ├── banner.svg      # Imagem vetorial do olho do terminal (sem texto)
│   └── architecture.svg # Pipeline do sistema
├── options_example.ini # Arquivo base de configurações
├── requirements.txt    # Dependências do ecossistema Python
├── main.py             # Arquivo inicializador
├── launch_dashboard.py # Inicializador do backend FastAPI
└── setup.sh            # Script de registro CLI global
```

─────── ▪ ───────

## ⌨️ Comandos da CLI & Discord

Controle o andamento das tarefas e gerencie filas utilizando o terminal da TUI, a aba de comandos do dashboard ou enviando mensagens diretas no chat do Discord (restrito a admins configurados):

```text
  COMANDO             DESCRIÇÃO
  -----------------------------------------------------------------------------
  help                Exibe atalhos do teclado, menu de comandos e manual.
  start / resume      Ativa os loops de automação e retoma filas.
  pause / stop        Suspende envio de comandos e threads em background.
  reset               Limpa estados do bot, filas e cooldowns.
  stats [período]     Retorna dados da sessão de progresso (ex. stats 1h, stats 45m).
  queue               Mostra o tamanho da fila e comandos agendados.
  say <msg>           Envia uma string customizada no canal configurado.
  tc start [c] [m]    Ativa o modo Time Cookie (ex. tc start 5c 60m).
  tc stop             Para o modo Time Cookie ativo.
  g start             Inicia rotina de gambling/apostas Fibonacci.
  g pause             Interrompe rotinas de gambling.
  sleepet start       Redireciona escopo para resgate de Pet Adventures.
  sleepet stop        Desativa busca de pets e retorna rotinas normais.
  theme               Carrega a tela de seleção de paleta visual da TUI.
  exit                Encerra processos e persiste arquivos de log.
```

### Comandos de Controle Remoto no Discord (Prefixo `sb `)
Contas administradoras autorizadas podem controlar o daemon enviando comandos diretamente no canal configurado:

* `sb help` / `sb ajuda`: Exibe a ajuda dos comandos administrativos.
* `sb status`: Envia uma mensagem de status em tempo real para o Discord e Telegram (com atualização automática a cada 30 segundos).
* `sb config`: Exibe o painel de configurações dinâmicas e os valores atuais dos parâmetros.
* `sb config <parametro> <valor>`: Altera dinamicamente um parâmetro do arquivo `options.ini` (ex: `sb config typo_chance 0.08`).
* `sb toggle <parametro>`: Alterna rapidamente o valor de um parâmetro booleano (ex: `sb toggle hunt`, `sb toggle delay`).
* `sb log`: Envia o arquivo de log da sessão atual diretamente no chat.
* `sb export [txt/ini]`: Exporta o arquivo de configurações atual.
* `sb pause` / `sb stop`: Pausa a execução dos loops de automação.
* `sb start` / `sb resume`: Retoma o envio de comandos e loops de automação.
* `sb reset`: Limpa as filas de comandos, timers de cooldown e reseta o estado geral do bot.
* `sb sleepet start` / `sb sleepet stop`: Ativa ou desativa o modo sleepet (automação focada em Pet Adventures).
* `sb tc start [c] [m]`: Inicia o modo Time Cookie (ex: `sb tc start 5c 60m`).
* `sb tc stop` / `sb tc pause`: Encerra o modo Time Cookie ativo.
* `sb g start` / `sb g stop` / `sb g pause`: Ativa ou desativa as rotinas do módulo de gambling/apostas Fibonacci.
* `sb say <mensagem>`: Envia uma mensagem personalizada no canal ativo.

─────── ▪ ───────

## 🛡️ Protocolos de Segurança e Anti-Detecção

```text
  [!] USE CONEXÃO RESIDENCIAL: Evite hostings comerciais (AWS, GCP, DigitalOcean).
  [!] ERROS DE DIGITAÇÃO: Emula falhas humanas de digitação de comando (typo_chance=0.05).
  [!] PAUSAS DO CAFÉ: Pausas dinâmicas automatizadas (5 a 15 min) a cada 1.5 horas.
  [!] CICLOS DE SONO: Períodos off configuráveis para dormir à noite (sleep_at, wake_up_at).
  [!] NOTIFICAÇÃO TELEGRAM: Alertas imediatos em captchas duvidosos.
```

─────── ▪ ───────

## ⚠️ Aviso Legal

```text
  [AVISO]
  Esta aplicação interage com o Discord através de chamadas à APIs não-oficiais.
  Isso viola as diretrizes de termos de uso do Discord. O pacote foi criado
  unicamente para fins de estudos acadêmicos e testes. Os autores não assumem
  qualquer responsabilidade por suspensões de contas ou bans. Use por sua conta.
```

─────── ▪ ───────

## 📄 Termos de Licenciamento

Sob os termos da licença de código aberto **[MIT License](LICENSE)**. Permissivo para modificação, estudo acadêmico e redistribuição.

```text
  Copyright (c) 2026 Oracle Devs
  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files...
```
