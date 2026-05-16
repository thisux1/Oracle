# 🔮 Oracle v2 — Epic RPG Automation

Este repositório contém o **Oracle v2**, um macro avançado para automação do Epic RPG com inteligência artificial para resolução de captchas e sistema de anti-detecção.

---

## 🛡️ Segurança e Diretrizes de Uso (MUITO IMPORTANTE)

Para garantir a longevidade da sua conta, siga estas diretrizes baseadas em heurísticas de anti-detecção:

### ⚠️ Não utilize em contas secundárias sem atividade orgânica
O Discord utiliza Machine Learning para analisar padrões comportamentais. Uma conta que **apenas** envia comandos de RPG e não tem outras atividades é facilmente detectada.
*   **POR QUÊ**: O endpoint `/science` do Discord rastreia movimentos do mouse, troca de canais e foco da tela. O bot não simula isso.
*   **MITIGAÇÃO**: Use a conta normalmente de vez em quando(converse com amigos, entre em canais de voz, navegue por servidores) enquanto o bot roda em segundo plano.

### 📋 Checklist de Sobrevivência
*   **🏠 IP Residencial**: Evite rodar em VPS ou Cloud (AWS, Google Cloud). Use o Wi-Fi de casa ou 4G do celular. IPs de data centers são marcados pelo Discord.
*   **☕ Coffee Breaks**: O Oracle v2 já possui pausas para "café" integradas (5-15min a cada 1-2h). Não as desative.
*   **🌙 Night Sleep (Modo Sono)**: Agora o bot pode se desconectar totalmente em horários específicos (ex: das 23:30 às 07:00) para simular que você foi dormir e está offline, desconectando-se completamente do websocket e fechando a conexão com o discord.
*   **📱 Notificações Telegram**: Mantenha o Telegram configurado. Se a IA falhar em um captcha, você precisa intervir manualmente rápido para evitar flag pelo EPIC RPG.

---

## 🚀 Como Começar

### 1. Requisitos
*   **Python 3.11** (Recomendado para compatibilidade com os modelos `.h5`)
*   Um token de conta do Discord (User Token)
*   Token do Bot do Telegram (opcional, para alertas e controle remoto)

### 2. Configuração do Ambiente (venv)
```bash
# No diretório do projeto:
python3.11 -m venv venv

# Ativar o ambiente virtual:
source venv/bin/activate  # Linux/macOS
 venv\Scripts\activate   # Windows

# Instalar as dependências:
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configurando o `options.ini`
Edite o arquivo `options.ini` com suas informações:

**Essenciais:**
*   `user_token`: Seu token do Discord.
*   `channel_id`: ID do canal de farm.
*   `guild_id`: ID do servidor.
*   `admin_ids`: Seu ID (para controle remoto).
*   `typo_chance`: Chance (ex: 0.05) de simular erros de digitação humanos.
*   `sleep_at` / `wake_up_at`: Horário (HH:MM) para o bot ficar offline (ex: 23:30 e 07:00).

**Comandos Togglable (opcional, default=true):**
*   `do_hunt`, `do_adv`, `do_farm`, `do_work`, `do_training`, `do_daily`, `do_weekly`, `do_quest`, `do_lootbox`, `do_dungeon`, `do_card_hand`: Habilita/desabilita comandos individuais sem precisar editar código.

**ULTR Training:**
*   `do_ultr=false`: Quando `true`, substitui `rpg training` pela sequência: `rpg ultr` → `double` → `attack` → `rpg use tc N`.

**Dungeon Automática:**
*   `is_eternal=false`: Ativa auto-enter em dungeon (`yes`) e bite loop automático no dragão eternal.

**Card Hand:**
*   `card_hand_action=auto`: `auto` (joga automaticamente via IA) ou `notify` (apenas notifica no Telegram para você jogar manualmente).

**Time Cookie:**
*   `tc_quantity=1`: Quantidade padrão de cookies por uso. Sobrescrito via comando `sb tc start Xc`.

**Adventure Optimization:**
*   `life_boost_before_adv=none`: Nível do life boost (a, b, c) para comprar antes de adventure.
*   `adventure_area=none`: Área para trocar antes do adventure (menos dano).
*   `current_area=none`: Área para voltar depois do adventure/eventos.

### 4. Executando o Bot
```bash
python main2.py
```

---

## 🛠️ Comandos de Controle (Discord)
Envie estes comandos no canal (apenas administradores):
*   `sb help` ou `sb ajuda`: Mostra a lista completa de comandos disponíveis no console.
*   `sb start` / `sb pause`: Inicia (descongela) ou pausa (congela) a execução automática do bot.
*   `sb reset`: Limpa filas de alta e baixa prioridade e reseta o estado de jogo.
*   `sb stats`: Exibe o relatório acumulado de XP, Coins e Loot da sessão inteira.
*   `sb stats [tempo]`: Mostra o relatório de estatísticas calculado para um período específico (ex: `sb stats 10h`, `sb stats 7d`, `sb stats 1m`). Os dados sobrevivem a reboots!
*   `sb tc start [Xc] [tempo]m`: Ativa o modo **Time Cookie**. Ex: `sb tc start 4c 60m` (4 cookies, 60 minutos). Ao ativar, enfileira automaticamente hunt, work, farm e rd.
*   `sb tc stop`: Desativa o modo Time Cookie.
*   `sb g start` / `sb g pause`: Inicia ou pausa o ciclo automático do cassino (Fibonacci Coinflip).
*   `sb say [texto]`: Envia uma mensagem no canal.
*   `rpg u`: Exibe o tempo de atividade do bot (uptime).

---

## 🧠 Inteligência Artificial (Oracle)
O bot utiliza dois modelos (`oracle_v2_color.h5` e `oracle_v2_gray.h5`) para resolver os captchas do Epic Guard. Se a confiança for baixa, ele enviará a foto para o seu Telegram para ajuda manual.
---

---

## 📋 Changelog (Oracle v2 — Donut Features Migration)

*   **Comandos Togglable**: 11 flags `do_*` no `options.ini` para desabilitar comandos individualmente.
*   **ULTR Training**: `do_ultr=true` substitui training pela sequência ultr → double → attack → rpg use tc.
*   **TC Startup Queue**: Ao ativar TC mode, hunt, work, farm e rd são enfileirados automaticamente.
*   **TC Quantity**: `sb tc start 4c` usa 4 cookies por vez. Configurável via `tc_quantity` no `.ini`.
*   **Dungeon State Machine**: Auto-enter em dungeon + bite loop no dragão eternal (gated por `is_eternal`).
*   **Card Hand Toggle**: `card_hand_action=notify` só avisa no Telegram sem jogar automaticamente.
*   **Adventure Optimization**: Compra life boost e troca de área antes de adventure.
*   **HUD Melhorado**: Métodos especializados `dungeon()`, `tc()`, `cardhand()`, `separator()`, `navi()`.
*   **Eventos Globais**: Handlers de zombie horde, mysterious man, seed event e god drop movidos para antes do filtro `is_for_user` — agora funcionam mesmo sem o nome do usuário no embed.

---

## ⚠️ Aviso Legal
O uso de self-bots viola os Termos de Serviço do Discord. Este software é fornecido para fins educacionais. O Oracle v2 inclui sistemas de anti-detecção, mas o risco de banimento nunca é zero. Use com inteligência e sem ganância.
