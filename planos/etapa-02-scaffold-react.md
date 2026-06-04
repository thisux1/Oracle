# Etapa 02 - Scaffold React

## Objetivo

Criar estrutura inicial do dashboard React com Vite, Tailwind v4, Zustand e camada de API/terminal pronta para integrar com backend.

## Arquivos alvo

- `dashboard/package.json`
- `dashboard/vite.config.js`
- `dashboard/index.html`
- `dashboard/src/main.jsx`
- `dashboard/src/App.jsx`
- `dashboard/src/stores/useOracleStore.js`
- `dashboard/src/lib/api.js`
- `dashboard/src/lib/terminal.js`

## Escopo funcional

- Inicializar app React 19 com Vite.
- Configurar Tailwind v4 no pipeline do Vite.
- Criar store global Zustand com shape inicial.
- Criar cliente Axios e funcoes de API basicas.
- Criar utilitario de conexao WS terminal por perfil.

## Checklist tecnico

- [ ] Projeto `dashboard/` criado e buildando.
- [ ] Dependencias alinhadas ao plano (React, Zustand, Axios, Framer, GSAP, xterm).
- [ ] Tailwind v4 integrado ao Vite sem erros.
- [ ] Estrutura de pastas criada (`components`, `tabs`, `stores`, `lib`).
- [ ] `useOracleStore` com estado inicial de perfis, bot, config, stats e terminal.
- [ ] Actions da store declaradas (`fetchProfiles`, `fetchConfig`, `saveConfig`, `startBot`, `stopBot`).
- [ ] `api.js` com baseURL local e tratamento de erro consistente.
- [ ] `terminal.js` com funcao de conectar/desconectar WS por perfil.
- [ ] App renderiza layout base sem quebrar em mobile.

## Criterios de pronto

- [ ] `npm run dev` sobe frontend sem warnings criticos.
- [ ] `npm run build` conclui com sucesso.
- [ ] Tela inicial abre e carrega estado default sem erro de runtime.
