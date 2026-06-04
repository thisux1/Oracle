# Etapa 08 - Stats Tab

## Objetivo

Entregar aba de estatisticas com visao consolidada de progresso, loot e metricas auxiliares por perfil.

## Arquivos alvo

- `dashboard/src/tabs/StatsTab.jsx`

## Escopo funcional

- Exibir cards de resumo (coins, XP, tempo).
- Exibir breakdown de loot por categoria com barras relativas.
- Exibir grid de cartas por raridade.
- Exibir estatisticas misc (coolness, arena cookies, guard events).

## Checklist tecnico

- [ ] Fonte de dados por perfil conectada (`stats_*.json` via backend/WS).
- [ ] Summary cards com animacao de numero (GSAP) sem reanimar a cada render trivial.
- [ ] Tabela de loot com ordenacao clara e percentuais.
- [ ] Grid de raridades com cores consistentes.
- [ ] Bloco misc com campos ausentes tratados (fallback em zero).
- [ ] Atualizacao periodica sem bloquear interacao da UI.
- [ ] Layout legivel em mobile (cards empilhados).

## Criterios de pronto

- [ ] Stats refletem dados reais do perfil ativo.
- [ ] Interface permanece fluida com volumes maiores de dados.
