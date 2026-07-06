# 🔮 Oracle v3 — Epic RPG Automation

Este repositório contém o **Oracle v3**, um macro para automação do Epic RPG com inteligência artificial para resolução de captchas, sistema de anti-detecção, uma **Terminal User Interface (TUI)** interativa e um **Web Dashboard** moderno para controle de desktop.

---

## Interfaces e Recursos da Versão 3.0

A v3.0 introduz duas interfaces completas de controle e monitoramento em tempo real:

### 1. Terminal User Interface (TUI)
Uma interface rica construída sobre **Textual** + **Rich**, perfeita para uso local no console em Linux/macOS.
*   **Inicialização (Splash Screen):** Arte do Olho do Oracle com barra de progresso (pressione qualquer tecla para pular).
*   **Mascote Animado:** Exibe uma animação que alterna entre o Olho do Oracle (ativo) e um gatinho dormindo (pausas/hibernação), adaptando-se ao estado do bot.
*   **Painel de Telemetria:** Aba lateral (sidebar) com contadores de comandos executados, moedas e experiência.
*   **Suporte a Temas Visuais:** 10 esquemas de cores pré-configurados (Cathedral, Dracula, Nord, Monokai Pro, Gruvbox, Catppuccin, Tokyo Night, Rosé Pine, Solarized e Cyberpunk).
*   **Visualizador de Logs:** Log centralizado com formatação colorida e categorização por tags.
*   **CLI com Autocomplete:** Linha de comandos no rodapé com histórico (`↑`/`↓`) e sugestões automáticas.

### 2. Web Dashboard & Desktop App
Uma interface desktop moderna com design premium glassmorphism, construída em **React (Vite) + Tailwind CSS** no frontend e **FastAPI (Uvicorn)** no backend.
*   **Visão Geral (Overview):** Telemetria em tempo real com contadores animados, gráficos de atividade e status dinâmico do processo do bot.
*   **Console Integrado:** Mini-terminal web responsivo para monitorar logs em tempo real e interagir com o bot.
*   **Configuração Simplificada:** Painel interativo para ajustar todos os parâmetros do `options.ini` sem abrir arquivos de texto.
*   **Gerenciador de Perfis:** Salve, importe, exporte e alterne facilmente entre múltiplos perfis de configuração.
*   **Modo Desktop Nativo:** Janela dedicada sem barra de navegação no Windows utilizando `pywebview` (com fallback automático para o navegador padrão).

### 3. Recursos Avançados de Automação
*   **Auto-Enchant Inteligente:** Loops automáticos de `rpg enchant`, `rpg refine`, `rpg transmute` ou `rpg transcend` até obter um encantamento desejado ou superior, com proteção financeira integrada (cancela se faltar gold).
*   **Automação de Duelos:** Sistema inteligente com máquina de estados para duelar cooperativamente com uma conta parceira configurada (`duel_partner_id`).
*   **Sleepet Mode:** Loop contínuo otimizado para envio e resgate de aventuras de pets.
*   **Suporte a Eternal Player:** Entrada automática em dungeons Eternal e loop automático do comando `rpg bite` até a conclusão.
*   **Ciclo de Sono (Sleep & Wake):** Desconexão do websocket e pausas durante a noite simulando horários reais de sono humana.
*   **Recarregamento Dinâmico (Config Reload):** Monitora o arquivo de configuração e aplica alterações do `options.ini` dinamicamente sem necessidade de reiniciar o bot.

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
*   Python 3.12 (ou 3.11)
*   Node.js v20+ (apenas se for compilar/modificar o frontend do Dashboard)
*   Token da conta do Discord
*   Token do Bot do Telegram (opcional, para receber alertas)

### 2. Configuração do Ambiente Virtual (venv)
```bash
# Criar o ambiente virtual:
python3 -m venv venv

# Ativar o ambiente virtual:
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Instalar dependências do bot:
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Executando o Bot (TUI)
Para rodar a interface clássica no terminal:
```bash
python main.py
```

### 4. Executando o Web Dashboard (Desktop App)
Para iniciar o launcher que abre a janela de controle do Dashboard:
```bash
python launch_dashboard.py
```
*(Nota: Certifique-se de que a build do frontend existe na pasta `dashboard/dist`. Caso contrário, siga as instruções de compilação abaixo).*

### 5. Compilação do Frontend e Geração do Executável (.exe)
Se você modificou o Dashboard ou deseja gerar o instalador autônomo para Windows:

**Gerar build do React:**
```bash
cd dashboard
npm install
npm run build
cd ..
```

**Gerar executável do Windows (.exe) e instalador Inno Setup:**
Execute o script de build integrado (irá rodar o PyInstaller e compilar o arquivo `.iss` gerando o instalador na pasta `Output/`):
```bash
python build_windows.py
```

### 6. Configuração de Atalho Global (Linux/macOS - Opcional)
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
| **`sleepet start`** | Inicia o loop automático de Sleepet Mode (limpa LPQ, foca em aventuras de pets). |
| **`sleepet stop`** | Para o loop de Sleepet Mode e restabelece a fila normal. |
| **`<enchant/refine/transmute/transcend> <a/s> <enchant_name>`** | Auto-encanta espada (`s`) ou armadura (`a`) até atingir ou superar o nível desejado (ex: `refine s godly`). |
| **`<enchant/refine/transmute/transcend> stop`** | Cancela o processo de encantamento automático. |
| **`export [ini/txt]`** / **`/export [ini/txt]`** | Exporta o arquivo de configuração atual como anexo (formato `.ini` ou `.txt`). |
| **`log`** | Envia o arquivo .log da sessão atual (ou os últimos 5MB dele). |
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
