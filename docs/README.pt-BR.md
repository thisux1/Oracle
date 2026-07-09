<!-- BANNER ANIMADO -->
<p align="center">
  <img src="banner.svg" alt="Oracle v3 Banner" width="100%" style="border-radius: 8px; border: 1px solid rgba(168, 85, 247, 0.15);" />
</p>

<!-- TECH BADGES MINIMALISTAS -->
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-black?style=flat-square&logo=python&logoColor=3776AB&labelColor=050202" alt="Python" />
  <img src="https://img.shields.io/badge/TensorFlow_Lite-2.17-black?style=flat-square&logo=tensorflow&logoColor=FF6F00&labelColor=050202" alt="TensorFlow Lite" />
  <img src="https://img.shields.io/badge/Textual-TUI-black?style=flat-square&logo=terminal&logoColor=white&labelColor=050202" alt="Textual TUI" />
  <img src="https://img.shields.io/badge/FastAPI-0.111-black?style=flat-square&logo=fastapi&logoColor=009688&labelColor=050202" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-19-black?style=flat-square&logo=react&logoColor=61DAFB&labelColor=050202" alt="React" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-v4.0-black?style=flat-square&logo=tailwindcss&logoColor=38BDF8&labelColor=050202" alt="Tailwind CSS" />
  <img src="https://img.shields.io/badge/Discord.py--self-v2.0-black?style=flat-square&logo=discord&logoColor=5865F2&labelColor=050202" alt="Discord.py-self" />
</p>

---

> [!NOTE]
> 🇺🇸 **For the English version of this document, see: [README.md](../README.md).**

---

## Visão Geral

O **Oracle v3** é uma suíte de automação de última geração para o Epic RPG. Desenvolvido com foco em segurança, escalabilidade e facilidade de uso, o projeto integra uma rede neural convolucional (CNN) via TensorFlow Lite para resolver captchas de forma dinâmica, apresenta uma camada de anti-detecção que simula comportamentos humanos reais, e introduz um sistema de interface dupla composto por uma **Terminal User Interface (TUI)** de console interativo e um **Web Dashboard** de controle premium baseado em web.

---

## Arquitetura e Fluxo de Dados

O diagrama abaixo ilustra o loop de dados em tempo real e o fluxo de interação entre o gateway websocket do Discord, a máquina de estados de automação e o pipeline local de processamento de IA:

<p align="center">
  <img src="architecture.svg" alt="Arquitetura de Fluxo de Dados Oracle v3" width="100%" style="border-radius: 8px; border: 1px solid rgba(168, 85, 247, 0.08);" />
</p>

### Ciclo de Vida da Automação e IA

1. **Escuta do Gateway**: O bot estabelece uma conexão websocket segura com o Discord usando `discord.py-self` para interceptar mensagens e eventos de entrada.
2. **Monitoramento de Estado**: O Parser gerencia cooldowns e eventos. Quando um comando é disparado, ele enfileira ações em uma fila de prioridades.
3. **Resolução de Captchas por IA**: Caso o jogo exiba um captcha de verificação, o bot isola a imagem bruta, realiza o recorte dos caracteres e executa o processamento local via um modelo CNN em **TensorFlow Lite** para prever instantaneamente os símbolos e resolver o bloqueio.
4. **Transmissão de Telemetria**: O servidor FastAPI transmite estatísticas de execução, logs em tempo real e atualizações de estado para o Web Dashboard em React e para a TUI local em console.
5. **Camada Humanizadora (Escudo)**: Toda ação enviada é avaliada pelo motor de humanização, que adiciona micro-atrasos aleatórios, agenda coffee breaks orgânicos e força ciclos de sono noturnos para evitar marcações de segurança na plataforma.

---

## Detalhes Tecnológicos por Módulo

A tabela a seguir apresenta os detalhes técnicos e responsabilidades de cada módulo dentro do ecossistema:

| Módulo / Componente | Tecnologias Utilizadas | Papel no Sistema |
| :--- | :--- | :--- |
| **Núcleo de Automação (Bot)** | Python 3.12, discord.py-self, asyncio, Textual | Gerencia os estados do bot, listeners do websocket, enfileiramento de comandos prioritários e recarregamento de configurações em tempo real. |
| **Engine de Captcha com IA** | TensorFlow Lite, OpenCV, NumPy | Automatiza o pré-processamento de imagens, segmentação de cortes e classificação CNN para resolver o captcha do Epic Guard. |
| **Console de Terminal (TUI)** | Textual, Rich | Interface baseada em console que exibe telemetria dinâmica, animações de mascote, seletores de temas e uma CLI com autocomplete. |
| **Backend do Dashboard** | FastAPI, Uvicorn, WebSockets | Expõe endpoints de API e transmissões via websockets para enviar estatísticas, gerenciar o arquivo `options.ini` e alternar perfis. |
| **Frontend do Dashboard** | React 19, Vite, Tailwind CSS v4, Zustand | Web app premium com design glassmorphic que serve como sala de controle remoto com mini-terminal integrado. |
| **Utilitários de Compilação** | PyInstaller, Inno Setup, Bash Shell | Empacota dependências do sistema, gera instaladores autônomos `.exe` para Windows e instala atalhos globais no terminal. |

---

## Como Iniciar

### Pré-requisitos
* **Python 3.11 ou 3.12**
* **Node.js v20+** (necessário apenas para compilar ou modificar o frontend do Dashboard)
* **Token da conta do Discord**
* **Token do Bot do Telegram** (opcional, para notificações remotas)

<details>
<summary><b>1. Criar e Ativar Ambiente Virtual (venv)</b></summary>
<br />

Crie um ambiente virtual para isolar os pacotes python:

```bash
# Criar o ambiente virtual:
python3 -m venv venv

# Ativar no Linux/macOS:
source venv/bin/activate

# Ativar no Windows:
venv\Scripts\activate
```
</details>

<details>
<summary><b>2. Instalar Dependências</b></summary>
<br />

Instale as dependências principais e atualize o gerenciador de pacotes pip:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```
</details>

<details>
<summary><b>3. Configurar Parâmetros</b></summary>
<br />

Copie o arquivo de exemplo de opções para `options.ini` e edite-o com seu token do Discord, configurações de notificação do Telegram e macros desejadas:

```bash
cp options_example.ini options.ini
```
*Abra o arquivo `options.ini` em qualquer editor para customizar suas credenciais e variáveis de cooldown.*
</details>

<details>
<summary><b>4. Executar o Bot (TUI no Console)</b></summary>
<br />

Inicie a interface clássica no terminal baseada em Textual:

```bash
python main.py
```
</details>

<details>
<summary><b>5. Executar o Web Dashboard (Desktop App)</b></summary>
<br />

Inicie o servidor de backend em FastAPI e abra a aplicação de controle:

```bash
python launch_dashboard.py
```
*(Nota: Certifique-se de que a build do frontend existe na pasta `dashboard/dist`. Caso contrário, execute os comandos de compilação abaixo).*
</details>

<details>
<summary><b>6. Compilar o Frontend e Gerar Executáveis (Opcional)</b></summary>
<br />

Se você modificou o Dashboard ou deseja gerar o instalador autônomo para Windows:

**Gerar build do React:**
```bash
cd dashboard
npm install
npm run build
cd ..
```

**Gerar executável do Windows (.exe) e instalador:**
```bash
python build_windows.py
```
</details>

<details>
<summary><b>7. Configurar Atalho Global CLI (Linux/macOS - Opcional)</b></summary>
<br />

Configure o comando `oracle` globalmente no sistema:

```bash
chmod +x setup.sh && ./setup.sh
source ~/.bashrc  # ou ~/.zshrc
```
Após a configuração, você pode rodar o bot de qualquer pasta apenas digitando:
```bash
oracle
```
</details>

---

## Estrutura do Repositório

```path
Oracle-V2/
├── bot/              # Núcleo de automação em Python, handlers e TUI
├── dashboard/        # Código do Web Dashboard em React (Vite, Tailwind, CSS)
├── docs/             # Recursos de documentação visual e diagramas
│   ├── banner.svg    # Banner animado de alta tecnologia do projeto
│   └── architecture.svg # Diagrama de arquitetura e fluxo de dados
├── requirements.txt  # Dependências de pacotes Python
├── main.py           # Ponto de entrada do app (inicializador TUI)
├── launch_dashboard.py # Inicializador do servidor web do Dashboard
├── build_windows.py  # Script de automação para empacotar o executável EXE
└── setup.sh          # Script de instalação do atalho global no terminal
```

---

## Comandos da CLI e Discord

Você pode interagir com o Oracle através do terminal da TUI, do mini-terminal no Dashboard ou diretamente pelo chat do Discord (apenas por administradores configurados):

| Comando | Descrição |
| :--- | :--- |
| **`help`** / **`/help`** | Exibe o modal de atalhos de teclado e lista todos os comandos. |
| **`start`** / **`resume`** | Inicia ou retoma os loops de automação. |
| **`pause`** / **`stop`** | Pausa todas as tarefas ativas de automação. |
| **`reset`** | Limpa as filas de comandos, cooldowns e estados internos. |
| **`stats [período]`** | Exibe as estatísticas de telemetria da sessão (ex: `stats 1h`, `stats 30m`). |
| **`queue`** | Exibe a quantidade e itens presentes na fila de prioridades. |
| **`say <mensagem>`** | Envia uma mensagem personalizada ou comando bruto no canal atual. |
| **`tc start [c] [m]`** | Ativa o modo Time Cookie (ex: `tc start 4c 60m`). |
| **`tc stop`** | Desativa o modo Time Cookie. |
| **`g start`** | Ativa a macro de gambling/coinflip com estratégia de Fibonacci. |
| **`g pause`** / **`g stop`** | Pausa ou para as tarefas de gambling. |
| **`sleepet start`** | Ativa os loops de Sleepet Mode (foca em resgate de aventuras de pets). |
| **`sleepet stop`** | Desativa o Sleepet Mode e restaura o ciclo de filas normal. |
| **`<enchant/refine/transmute/transcend> <a/s> <enchant_name>`** | Roda encantamentos automáticos em armas (`s`) ou armaduras (`a`) até atingir ou superar o nível alvo (ex: `refine s godly`). |
| **`<enchant/refine/transmute/transcend> stop`** | Interrompe o loop de encantamento automático ativo. |
| **`export [ini/txt]`** | Exporta seu perfil atual do `options.ini` como anexo no chat do Discord. |
| **`log`** | Faz upload do arquivo de logs da sessão ativa (até 5MB). |
| **`cfg <chave> <valor>`** | Altera qualquer variável de configuração dinamicamente e salva no `options.ini` (ex: `cfg do_hunt false`). |
| **`theme`** | Abre o painel seletor de temas visuais na TUI. |
| **`exit`** / **`quit`** | Encerra de forma segura o processo do bot e a interface. |

### Atalhos no Chat do Discord
Se estiver digitando no canal do bot a partir da conta principal autorizada:
* **`rpg s`**: Imprime as métricas da sessão atual localmente nos logs.
* **`rpg s t`**: Envia as métricas da sessão formatadas diretamente no chat do Discord.
* **`rpg s p`**: Imprime as métricas do parceiro de casamento localmente nos logs.
* **`rpg u`**: Imprime o tempo de atividade (uptime) do bot localmente nos logs.
* **`rpg u t`**: Envia o tempo de atividade (uptime) diretamente no chat do Discord.

---

## Segurança e Boas Práticas

Para proteger sua conta contra análises automáticas da plataforma:
* **Interação Orgânica**: Não deixe a conta unicamente automatizada. Converse com amigos, acesse canais e use o cliente oficial do Discord de tempos em tempos.
* **IP Residencial**: Evite rodar o bot em VPS de grandes provedores (AWS, Google Cloud, DigitalOcean). Utilize conexões residenciais ou pontos de acesso móveis.
* **Coffee Breaks**: Não desative as pausas periódicas automáticas integradas (5 a 15 minutos de inatividade aleatória a cada 1 ou 2 horas).
* **Ciclos de Sono**: Configure a janela de Night Sleep (`night_sleep`) no arquivo de configuração para desconectar o bot durante o período da noite.
* **Alertas no Telegram**: Mantenha os alertas do Telegram ativos para responder rapidamente a captchas manuais caso o resolvedor de IA precise de ajuda.

---

## Aviso Legal
O uso de self-bots viola os Termos de Serviço do Discord. Este software foi desenvolvido estritamente para fins educacionais e de estudo. Os criadores não assumem qualquer responsabilidade por suspensões ou banimentos de contas ocorridos. Use por sua própria conta e risco.

---

## Licença

Este projeto é de código aberto e está licenciado sob os termos da [Licença MIT](LICENSE). Sinta-se livre para estudar, adaptar e modificar o código.
