# 🔮 Oracle v3 — Epic RPG Automation

Este repositório contém o **Oracle v3**, um macro para automação do Epic RPG com inteligência artificial para resolução de captchas, sistema de anti-detecção e uma **Terminal User Interface (TUI)** interativa.

---

## Recursos da Versão 3.0 (TUI)

A v3.0 introduz uma interface de terminal construída sobre **Textual** + **Rich**, permitindo o controle e monitoramento do bot em tempo real.

### Inicialização (Splash Screen)
Arte do Olho do Oracle com barra de progresso de carregamento (pode ser pulada pressionando qualquer tecla).

### Mascote Animado
Exibe uma animação que alterna entre o Olho do Oracle (ativo) e um gatinho dormindo (pausas/hibernação), adaptando-se ao estado do bot.

### Painel de Telemetria e Estatísticas
Aba lateral (sidebar) com contadores de comandos executados (Hunts, Adventures, Farms, Lootboxes), saldo de moedas e experiência obtida na sessão.

### Suporte a Temas Visuais
10 esquemas de cores pré-configurados (Cathedral, Dracula, Nord, Monokai Pro, Gruvbox, Catppuccin, Tokyo Night, Rosé Pine, Solarized e Cyberpunk), selecionáveis na interface com persistência.

### CLI Integrada com Histórico e Autocomplete
Linha de comandos no rodapé com suporte a histórico (`↑`/`↓`) e sugestões automáticas ao digitar `/`.

### Visualizador de Logs
Log centralizado com formatação colorida e categorização por tags (`LOOT`, `ORACLE`, `ALERTA`, `SYSTEM`, etc.).

---

## Segurança e Diretrizes de Uso

Para reduzir o risco de detecção e banimento, siga as diretrizes abaixo:

### Uso em contas principais e secundárias
O Discord monitora padrões de atividade. Uma conta que apenas envia comandos de RPG sem interações orgânicas é facilmente identificada como bot.
*   **Recomendação**: Interaja na conta manualmente de tempos em tempos (converse em servidores, acesse canais, use outros recursos do Discord).

### Boas Práticas
*   **IP Residencial**: Evite rodar em servidores em nuvem ou VPS (AWS, GCP, etc.). Use conexão de internet residencial ou dados móveis.
*   **Coffee Breaks**: O bot possui pausas programadas automatizadas (5 a 15 minutos a cada 1 ou 2 horas). Não as desative.
*   **Modo Sono (Night Sleep)**: O bot se desconecta totalmente do websocket do Discord em horários específicos (ex: das 23:30 às 07:00) para simular o período de sono.
*   **Notificações Telegram**: Configure os alertas do Telegram para receber imagens de captchas em caso de falha de resolução pela IA.

---

## Instalação e Execução

### 1. Requisitos
*   Python 3.11
*   Token da conta do Discord
*   Token do Bot do Telegram (opcional, para receber alertas)

### 2. Configuração do Ambiente Virtual (venv)
```bash
# Criar o ambiente virtual:
python3.11 -m venv venv

# Ativar o ambiente virtual:
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Instalar dependências:
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configuração do `options.ini`
Crie ou edite o arquivo `options.ini` na raiz do projeto com suas credenciais:
*   `user_token`: Token da conta do Discord.
*   `channel_id`: ID do canal de texto para os comandos.
*   `guild_id`: ID do servidor Discord.
*   `admin_ids`: Seu ID de usuário (para comandos remotos).

### 4. Executando o Bot
```bash
python main.py
```

### 5. Configuração de Atalho Global (Opcional)
Você pode configurar o comando `oracle` globalmente executando o instalador de atalhos:
```bash
chmod +x setup.sh && ./setup.sh
source ~/.bashrc  # ou ~/.zshrc
```
Depois disso, execute o bot de qualquer local apenas digitando:
```bash
oracle
```

---

## Comandos da CLI e Discord

Os comandos listados abaixo podem ser enviados pela CLI da TUI ou pelo chat do Discord (apenas por administradores configurados):

| Comando | Descrição |
| :--- | :--- |
| **`help`** / **`/help`** | Abre o modal de atalhos e lista de comandos. |
| **`start`** / **`resume`** | Inicia ou retoma o bot. |
| **`pause`** / **`stop`** | Pausa o bot. |
| **`reset`** | Reseta as filas de comandos, cooldowns e estados. |
| **`stats [período]`** | Exibe estatísticas da sessão (ex: `stats 1h`, `stats 30m`). |
| **`queue`** | Exibe o tamanho e itens das filas de prioridade. |
| **`say <mensagem>`** | Envia uma mensagem ou comando diretamente para o canal. |
| **`tc start [Xc] [Xm]`** | Ativa o modo Time Cookie (ex: `tc start 4c 60m`). |
| **`tc stop`** | Desativa o modo Time Cookie. |
| **`g start`** | Inicia o modo gambling/coinflip com estratégia Fibonacci. |
| **`g pause`** / **`g stop`** | Pausa o modo gambling/coinflip. |
| **`cfg <chave> <valor>`** | Modifica dinamicamente uma configuração em tempo real e a salva no `options.ini` (ex: `cfg do_hunt false`). |
| **`theme`** | Abre a tela de escolha de temas visuais (TUI). |
| **`exit`** / **`quit`** | Encerra com segurança o bot e a interface. |

### Atalhos Rápidos (Discord Self-bot)
Se você estiver digitando diretamente da sua conta no canal do Discord, o bot também responderá a comandos que se passam por mensagens de RPG normais:
* **`rpg s`**: Imprime as estatísticas da sessão nos logs locais.
* **`rpg s t`**: Envia as estatísticas completas formatadas em texto no canal do Discord.
* **`rpg s p`**: Imprime as estatísticas do parceiro de casamento nos logs (se aplicável).
* **`rpg u`**: Imprime o tempo de atividade (uptime) do bot nos logs locais.
* **`rpg u t`**: Envia o tempo de atividade (uptime) do bot em formato de mensagem no Discord.

---

## Aviso Legal
O uso de self-bots viola os Termos de Serviço do Discord. Este software foi desenvolvido para fins de estudo e aprendizado. O uso do bot acarreta riscos de suspensão ou banimento da conta. Use com moderação.
