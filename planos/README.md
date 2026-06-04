# Oracle OS Dashboard - Plano dividido por etapas

Este diretorio separa o `DASHBOARD_PLAN.md` em etapas executaveis, com checklist tecnico por fase.

## Ordem sugerida

1. `planos/etapa-01-backend-botprocessmanager.md`
2. `planos/etapa-02-scaffold-react.md`
3. `planos/etapa-03-design-system.md`
4. `planos/etapa-04-shell-ui-sidebar-header-tabs.md`
5. `planos/etapa-05-overview-tab.md`
6. `planos/etapa-06-terminal-tab.md`
7. `planos/etapa-07-config-tab.md`
8. `planos/etapa-08-stats-tab.md`
9. `planos/etapa-09-perfis-crud-import-export.md`
10. `planos/etapa-10-launch-dashboard-e2e.md`
11. `planos/etapa-11-build-windows-setup.md`

## Convencoes de execucao

- Cada etapa tem objetivo, escopo, arquivos e checklist tecnico.
- So iniciar a etapa seguinte quando os criterios de pronto da atual estiverem completos.
- Quando uma etapa tocar backend e frontend ao mesmo tempo, validar primeiro contrato de API (backend) e depois UI.
- Use `options.ini` como perfil padrao em todos os fluxos de teste.
