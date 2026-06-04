# Etapa 07 - Config Tab

## Objetivo

Criar formulario completo de configuracao por perfil, com secoes colapsaveis, validacao, save e indicacao de hot reload vs restart.

## Arquivos alvo

- `dashboard/src/tabs/ConfigTab.jsx`
- `dashboard/src/components/ConfigSection.jsx`
- `dashboard/src/components/ToggleSwitch.jsx`

## Escopo funcional

- Montar secoes funcionais (Credenciais, Geral, Adventure, Economy, Telegram, Features, Advanced, Schedule).
- Implementar componentes de input/select/toggle reutilizaveis.
- Persistir alteracoes via `POST /api/config`.
- Exibir badges por campo (`runtime` vs `reinicio`).

## Checklist tecnico

- [ ] `fetchConfig` carrega dados do perfil ativo.
- [ ] Campos sensiveis (ex.: `user_token`) com mascara e toggle de visibilidade.
- [ ] Validacao minima de campos obrigatorios.
- [ ] Toggles booleanos funcionando sem dessync visual.
- [ ] Selects com valores validos e fallback seguro.
- [ ] `configDirty` acionado ao editar.
- [ ] Botao salvar fixo no rodape da aba.
- [ ] Feedback de sucesso e erro ao salvar.
- [ ] Badge visual para campos que exigem reinicio.
- [ ] Mapeamento de hot reload alinhado a matriz do plano.

## Criterios de pronto

- [ ] Alteracoes persistem no `.ini` correto por perfil.
- [ ] Usuario entende claramente o que aplica em runtime e o que requer restart.
