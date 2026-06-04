# Etapa 06 - Terminal Tab

## Objetivo

Implementar terminal completo com xterm.js ligado ao PTY do backend por WebSocket, com resize, reconexao e acoes utilitarias.

## Arquivos alvo

- `dashboard/src/tabs/TerminalTab.jsx`
- `dashboard/src/lib/terminal.js`

## Escopo funcional

- Renderizar xterm em tela cheia da aba.
- Integrar addons de fit e links clicaveis.
- Ligar I/O binario bidirecional com backend.
- Enviar controle JSON (`resize`, `heartbeat`).

## Checklist tecnico

- [ ] Terminal inicializa sem vazamento ao trocar de aba/perfil.
- [ ] `@xterm/addon-fit` ajusta colunas/linhas ao resize.
- [ ] Frontend envia `resize` apos fit.
- [ ] Input do teclado enviado como frame binario.
- [ ] Output do backend renderizado com ANSI corretamente.
- [ ] Botao fullscreen funcional.
- [ ] Botao clear limpa apenas viewport local.
- [ ] Reconexao automatica quando WS cai.
- [ ] Indicador visual de conectado/desconectado.
- [ ] Scrollback configurado para 5000 linhas.

## Criterios de pronto

- [ ] Fluxo completo start -> conecta terminal -> comando -> output funciona.
- [ ] Resize da janela nao quebra o layout textual do bot.
