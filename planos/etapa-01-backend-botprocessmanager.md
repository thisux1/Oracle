# Etapa 01 - Backend e BotProcessManager

## Objetivo

Implementar a base do backend FastAPI com controle de processo por perfil, endpoints REST essenciais e WebSocket de terminal com framing binario/JSON.

## Arquivos alvo

- `dashboard_server.py`
- `options_resolver.py` (integracao de leitura/escrita de config)
- `requirements.txt`

## Escopo funcional

- Estruturar `BotProcessManager` por perfil (`dict[str, BotProcessManager]`).
- Implementar state machine (`offline`, `starting`, `online`, `stopping`).
- Implementar lifecycle (`start`, `stop`, deteccao de crash).
- Expor endpoints REST iniciais:
  - `GET /api/config`
  - `POST /api/config`
  - `GET /api/status`
  - `POST /api/bot/start`
  - `POST /api/bot/stop`
- Expor `WS /ws/terminal?profile=` com:
  - binary para I/O PTY
  - text(JSON) para `resize` e `heartbeat`

## Checklist tecnico

- [ ] FastAPI bindado em `127.0.0.1:8000`.
- [ ] CORS restrito a localhost/127.0.0.1.
- [ ] Gerenciador global por perfil implementado.
- [ ] `start()` cria PTY e processo `python main.py <profile>.ini`.
- [ ] `stop()` encerra processo e limpa recursos PTY.
- [ ] Poll de processo detecta crash e atualiza estado.
- [ ] `GET /api/status` retorna estado e dados minimos (uptime, filas se disponivel).
- [ ] `GET /api/config` mascara `user_token`.
- [ ] `POST /api/config` persiste alteracoes no `.ini` correto.
- [ ] WS terminal aceita multiplos clientes por perfil.
- [ ] Broadcast de saida do PTY para todos clientes conectados.
- [ ] Mensagem `{"type":"heartbeat"}` responde `{"type":"pong"}`.
- [ ] Mensagem `resize` aplica `cols/rows` no PTY (Linux/Windows).
- [ ] Sem buffer infinito de saida quando sem clientes (descartar).
- [ ] Tratamento de erro padronizado (HTTPException + payload claro).

## Criterios de pronto

- [ ] Conseguir iniciar e parar bot via API em `options.ini`.
- [ ] Conseguir conectar terminal via WS e enviar comandos.
- [ ] Reconhecer encerramento inesperado e refletir `offline` sem travar WS.
