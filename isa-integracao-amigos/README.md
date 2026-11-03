# Como levar as melhorias para o repositório `GuiLought/I.S.A`

Melhorias incluídas, como uma série de **3 commits** sobre o pacote original
`ISA_candidata_polida` (a base comum do projeto):

| Patch | Conteúdo |
|---|---|
| `0001` | **v0.9**: redesign dos 4 mapas (CSV físico + decorativo), estruturas, auditoria de ritmo dos minérios, ferramentas de autoria. 72 minérios |
| `0002` | **v1.0**: 5 NPCs (`src/npcs.py`, `assets/levels/npcs.json`, pixel art) e nova luta contra o Gorila (salto, fase 3 com chuva de bananas, anúncios, falas) |
| `0003` | **v1.2**: arena em ruínas com pouca decoração (noite fria, sem vermelho); Gorila exige as **8 perguntas** |

Testado aqui: a série aplica limpa sobre o pacote original e reproduz a v1.2
byte a byte. Na v1.2: `python testes/rodar_todos.py` dá 21/21, e passam também
`validar_dados.py` e o validador de física.

## Opção A: dar acesso ao Claude (mais simples)

O dono do repositório instala o app do Claude no `GuiLought/I.S.A`
(https://github.com/apps/claude/installations/select_target). Depois eu
aplico tudo num **branch novo** e abro um **Pull Request** para vocês
revisarem; nada vai direto para o `main`.

## Opção B: aplicar os patches vocês mesmos

Na pasta do repositório de vocês:

```bash
git checkout -b melhorias-isa
git am --keep-cr --3way caminho/para/patches/000*.patch
python testes/rodar_todos.py
```

- `--keep-cr` é **obrigatório**: os CSVs de mapa usam quebra de linha CRLF.
- Se a versão de vocês já mudou os mesmos arquivos, o `git am` para no patch
  com conflito. Resolvam (`git status` mostra quais), `git add` e
  `git am --continue`. Para desistir: `git am --abort`.
- Arquivos com mais chance de conflito: `main.py`, `constants.py`,
  `src/setores.py`, `src/enemies/boss.py`, `src/ambientes.py` e os CSVs de
  `assets/levels/`.
- **Conflito em CSV de mapa:** não misturem linhas à mão. Escolham uma versão
  inteira do arquivo (`git checkout --theirs` ou `--ours`). Para recriar os
  mapas da v1.2 a partir das ferramentas, use
  `python ferramentas/redesign_mapas/build.py . floresta,caverna,copas,arena --sobrescrever`.

## Opção C: copiar a pasta

Se a versão de vocês **não mudou** os arquivos acima, basta copiar o jogo
completo v1.2 por cima. Isso sobrescreve sem perguntar, então só use se tiver
certeza.
