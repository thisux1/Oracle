# 🔮 Oracle v2 — Epic RPG Automation

Este repositório contém a versão isolada do **Oracle v2**, um macro avançado para automação do Epic RPG com inteligência artificial para resolução de captchas e sistema de anti-detecção.

---

## 🛡️ Segurança e Diretrizes de Uso (MUITO IMPORTANTE)

O uso de automação no Discord é um jogo de "gato e rato". Para garantir a longevidade da sua conta, siga estas diretrizes baseadas em heurísticas de anti-detecção:

### ⚠️ Use em sua conta principal com atividade orgânica
O Discord utiliza Machine Learning para analisar padrões comportamentais. Uma conta que **apenas** envia comandos de RPG e não tem outras atividades é facilmente detectada.
*   **POR QUÊ**: O endpoint `/science` do Discord rastreia movimentos do mouse, troca de canais e foco da tela. O bot não simula isso.
*   **MITIGAÇÃO**: Use a conta normalmente (conversa com amigos, entra em canais de voz, navega por servidores) enquanto o bot roda em segundo plano.

### 📋 Checklist de Sobrevivência
*   **🚫 NUNCA rode 24/7**: O padrão de atividade ininterrupta é um sinal claro de bot. Utilize pausas manuais ou scripts de agendamento.
*   **🏠 IP Residencial**: Evite rodar em VPS ou Cloud (AWS, Google Cloud). Use o Wi-Fi de casa ou 4G do celular. IPs de data centers são marcados pelo Discord.
*   **☕ Coffee Breaks**: O Oracle v2 já possui pausas para "café" integradas (5-15min a cada 1-2h). Não as desative.
*   **📱 Notificações Telegram**: Mantenha o Telegram configurado. Se a IA falhar em um captcha, você precisa intervir manualmente rápido para evitar o "Jail".

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
# venv\Scripts\activate   # Windows

# Instalar as dependências:
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configurando o `options.ini`
Edite o arquivo `options.ini` com suas informações:
*   `user_token`: Seu token do Discord.
*   `channel_id`: ID do canal de farm.
*   `guild_id`: ID do servidor.
*   `admin_ids`: Seu ID (para controle remoto).
*   `typo_chance`: Chance (ex: 0.05) de simular erros de digitação humanos.

### 4. Executando o Bot
```bash
python main2.py
```

---

## 🛠️ Comandos de Controle (Discord)
Envie estes comandos no canal (apenas administradores):
*   `sb start` / `sb pause`: Inicia ou pausa o farm.
*   `sb stats`: Relatório de XP, Coins e Loot da sessão.
*   `sb tc start [tempo]m`: Modo **Time Cookie** (ex: `sb tc start 60m`).
*   `sb reset`: Limpa filas e estados.

---

## 🧠 Inteligência Artificial (Oracle)
O bot utiliza dois modelos (`oracle_v2_color.h5` e `oracle_v2_gray.h5`) para resolver os captchas do Epic Guard. Se a confiança for baixa, ele enviará a foto para o seu Telegram para ajuda manual.

---

## ⚠️ Aviso Legal
O uso de self-bots viola os Termos de Serviço do Discord. Este software é fornecido para fins educacionais. O Oracle v2 inclui sistemas de anti-detecção, mas o risco de banimento nunca é zero. Use com inteligência.
