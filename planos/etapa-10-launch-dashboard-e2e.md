# Etapa 10 - Launch Dashboard e E2E local

## Objetivo

Criar entrypoint desktop/local que sobe backend, serve frontend buildado e abre interface em janela nativa (ou browser como fallback).

## Arquivos alvo

- `launch_dashboard.py`
- `dashboard_server.py`

## Escopo funcional

- Subir Uvicorn em thread daemon local.
- Montar `dashboard/dist` como static files.
- Tentar abrir app via `pywebview`; fallback para `webbrowser`.
- Validar fluxo ponta-a-ponta local.

## Checklist tecnico

- [ ] `launch_dashboard.py` inicializa sem dependencia circular.
- [ ] Servidor sobe em `127.0.0.1:8000`.
- [ ] Frontend buildado servido corretamente em rota raiz.
- [ ] Fallback para browser ocorre se `pywebview` nao estiver instalado.
- [ ] Encerramento da janela encerra processo de forma limpa.
- [ ] Logs de inicializacao claros para diagnostico.
- [ ] Teste E2E manual executado (start, terminal, config save, stats, troca de perfil).

## Criterios de pronto

- [ ] Usuario roda um comando e abre dashboard funcional localmente.
- [ ] Sem depender de `npm run dev` para uso final.
