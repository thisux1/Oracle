# Etapa 05 - Overview Tab

## Objetivo

Implementar aba de visao geral com cards de estado, filas, contadores de sessao, acoes rapidas e mini-terminal.

## Arquivos alvo

- `dashboard/src/tabs/OverviewTab.jsx`
- `dashboard/src/components/AnimatedCounter.jsx`
- `dashboard/src/components/MiniTerminal.jsx`

## Escopo funcional

- Exibir estado do bot, uptime e ultimo comando.
- Exibir HPQ/LPQ com barras visuais.
- Exibir contadores principais com animacao GSAP.
- Exibir drops recentes e mini log terminal.

## Checklist tecnico

- [ ] Card de estado consome `botState`, `uptime`, `lastCommand`.
- [ ] Queue card consome `hpqSize` e `lpqSize`.
- [ ] Quick actions conectadas a API/store (start, pause, reset, tc start quando existir).
- [ ] Counters 2x3 com animacao numerica sem flicker.
- [ ] Lista de drops recentes limitada (ex.: ultimos 10).
- [ ] Mini-terminal mostra ultimas linhas de log em tempo real.
- [ ] Clique no mini-terminal navega para aba Terminal.
- [ ] Layout responsivo (2 colunas desktop, 1 coluna mobile).

## Criterios de pronto

- [ ] Overview atualiza em tempo quase real sem travar render.
- [ ] Todos os cards permanecem legiveis em largura mobile.
