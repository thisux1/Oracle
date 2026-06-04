# Etapa 09 - Perfis (CRUD, import, export)

## Objetivo

Adicionar gerenciamento completo de perfis `.ini` com criacao, duplicacao, remocao protegida e fluxo de import/export.

## Arquivos alvo

- `dashboard_server.py`
- `options_resolver.py`
- `dashboard/src/components/ProfileSidebar.jsx`
- `dashboard/src/lib/api.js`

## Escopo funcional

- Implementar endpoints:
  - `GET /api/profiles`
  - `POST /api/profiles`
  - `DELETE /api/profiles?name=`
  - `POST /api/profiles/import`
  - `GET /api/profiles/export?name=`
- Integrar a UI da sidebar para operacoes de perfil.

## Checklist tecnico

- [ ] Listagem retorna apenas `.ini` validos no diretorio alvo.
- [ ] Criacao valida nome e evita path traversal.
- [ ] Duplicacao (`copyFrom`) preserva conteudo do perfil base.
- [ ] Remocao bloqueia `options.ini`.
- [ ] Remocao impede apagar perfil com bot online (ou para antes com seguranca).
- [ ] Import valida extensao e conteudo minimo do `.ini`.
- [ ] Export devolve arquivo com headers corretos de download.
- [ ] Sidebar mostra menu de acoes por perfil.
- [ ] Troca de perfil recarrega config/status/stats automaticamente.

## Criterios de pronto

- [ ] Usuario consegue fazer ciclo completo: criar -> selecionar -> editar -> exportar -> remover (quando permitido).
- [ ] Nenhuma operacao de perfil derruba gerenciamento dos outros perfis.
