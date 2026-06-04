# Etapa 11 - Build Windows e instalador

## Objetivo

Preparar pipeline de distribuicao Windows com build do frontend, empacotamento PyInstaller e instalador Inno Setup.

## Arquivos alvo

- `build_windows.py` (ou script equivalente)
- `setup.iss`
- `requirements.txt`

## Escopo funcional

- Automatizar build do frontend.
- Gerar pacote `--onedir` com assets e dependencias do bot/dashboard.
- Gerar instalador final `.exe`.

## Checklist tecnico

- [ ] Script executa `npm run build` dentro de `dashboard/`.
- [ ] PyInstaller inclui `dashboard/dist` e arquivos necessarios (`.ini`, modelos, classes).
- [ ] Hidden imports criticos adicionados (`tensorflow`, `uvicorn`, `fastapi`).
- [ ] Executavel inicia `launch_dashboard.py` corretamente.
- [ ] `setup.iss` instala em diretorio padrao e cria atalhos.
- [ ] Instalador desinstala sem deixar lixo relevante.
- [ ] Teste smoke no Windows limpo (abrir app, start bot, fechar app).

## Criterios de pronto

- [ ] Artefato `OracleOS_Setup.exe` gerado com sucesso.
- [ ] Instalacao reproduzivel com instrucoes minimas para usuario final.
