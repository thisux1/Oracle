# Etapa 04 - Shell UI (Sidebar, Header, Tabs)

## Objetivo

Construir casca principal da aplicacao com navegacao por perfis e abas, incluindo feedback de estado do perfil ativo.

## Arquivos alvo

- `dashboard/src/App.jsx`
- `dashboard/src/components/ProfileSidebar.jsx`
- `dashboard/src/components/Header.jsx`
- `dashboard/src/components/TabNav.jsx`

## Escopo funcional

- Sidebar fixa com lista de perfis e acoes globais.
- Header com status ativo, start/stop e uptime.
- Tab navigation com 4 abas (Overview, Terminal, Config, Stats).
- Transicoes de layout usando Framer Motion.

## Checklist tecnico

- [ ] Sidebar com largura fixa e boa usabilidade em desktop.
- [ ] Modo mobile com colapso/overlay funcional.
- [ ] Lista de perfis refletindo `profiles` da store.
- [ ] Selecao de perfil atualiza `activeProfile` global.
- [ ] Header exibe nome do perfil ativo e estado atual.
- [ ] Botao Start/Stop respeita state machine.
- [ ] Uptime exibido com atualizacao periodica.
- [ ] Tabs trocam conteudo sem perder contexto de perfil.
- [ ] Indicador visual de aba ativa com animacao suave.

## Criterios de pronto

- [ ] Troca de perfil atualiza shell inteiro corretamente.
- [ ] Start/Stop disparados do header funcionam via store/API.
