# I.S.A. v1.0 a v1.2: NPCs, nova luta contra o Gorila e arena em ruínas

Base: a v0.9 (mapas polidos; ver `../isa-redesign-mapas/`). Os mapas não
mudaram. Copie `ISA_candidata_polida/` por cima do projeto v0.9.

## Arquivos

| Arquivo | |
|---|---|
| `src/npcs.py` | **novo**: NPCs, falas por progresso, recompensa, validação de posição |
| `assets/levels/npcs.json` | **novo**: posições e falas (editável pela equipe) |
| `assets/images/npcs/` | **novo**: 4 NPCs em pixel art, 3 quadros cada |
| `ferramentas/gerar_sprites_npc.py` | **novo**: gera a pixel art dos NPCs |
| `src/enemies/boss.py` | salto de reposição, fase 3, anúncios, janela de punição, correção do `on_ground` |
| `src/setores.py` | NPCs por setor; zona da luta passada ao Gorila |
| `main.py` | conversa (tecla E), caixa de diálogo, HUD do boss (anúncio, contador, balão), avisos |
| `constants.py` | bloco "Boss v1.0" com os ajustes |
| `testes/teste_npcs.py`, `testes/teste_boss_v1.py` | **novos** |
| `testes/rodar_todos.py` | inclui os testes novos |
| `README.md`, `docs/NPCS_E_BOSS.md` | documentação |

## NPCs

| NPC | Onde | Papel |
|---|---|---|
| Guarda Tainá | floresta, perto do spawn | guia (minérios, pulo duplo, golpe); comenta o progresso |
| Seu Benedito | floresta, antes da ravina | narrativa (a fábrica parou sem cobre e zinco); fala muda depois da caverna |
| Engenheira Ana | caverna, nos andaimes | guia das galerias; **maçã** ao coletar 8 minérios da caverna |
| Pesquisadora Lia | copas, Árvore Espiral | ensina a luta contra o Gorila; **maçã** com 5 minérios das copas |
| Diretor | copas, antes do portal | o executivo das cutscenes (arte `S7.png` existente); fala com o total da partida |

A arte dos quatro primeiros é pixel art nova, feita no estilo dos sprites do
jogo (`imagens/npcs_pixel_art.png`). O Diretor usa a arte original da equipe.

## Gorila

- **Salta pela arena** entre arremessos: o pouso aparece marcado no chão
  antes, só em chão livre, nunca perto do jogador.
- **Fase 3** (2 de vida): **chuva de bananas** com o `cacho_banana.png`. As
  sombras com anel vermelho marcam o impacto cerca de 1 s antes, com 3 tiles
  de vão entre os cachos.
- **Feedback:**
  - faixa "FASE 2/3" na tela;
  - falas do Gorila em balão;
  - rugido sem ataque ao acordar depois da troca de fase;
  - estrelas no atordoamento;
  - **MINERIOS DEVOLVIDOS X/8** na HUD.
- **8 perguntas obrigatórias (v1.2):** cada minério devolvido com resposta certa
  tira 1 de vida e o Gorila tem 8. A janela de punição (minério caído que dá
  dano extra) ficou no código, mas **desligada** (`GORILA_DANO_BONUS = 0`).
  Atordoado, o Gorila não machuca por contato.
- **Correção encontrada pelos testes novos:** o `on_ground` do Gorila oscilava
  a cada frame parado no chão. Isso também atrasava o salto-pancada original.

Capturas do jogo rodando: `imagens/`.

## Testes executados

`testes_v1.0.txt`: **21/21 aprovados** na suíte completa, incluindo:
- `teste_boss_v1.py`: 40 saltos validados; chuva com 960 ms de aviso; luta
  completa vencida em 71 s de jogo;
- `teste_npcs.py`.

Também rodados com sucesso: `validar_dados.py` (0/0), validador de física real
(0 erros) e auditor de level design (72 minérios).

**Intermitente (não é regressão):** `teste_gamepad_falso.py` falhou uma vez
numa rodada da suíte. Ele aperta botões por relógio em tempo real. Rodado 6
vezes isolado, passou em todas, com e sem NPCs, e a rodada seguinte da suíte
inteira passou 21/21.

## Pendências

1. ~~Decisão pedagógica~~ **resolvida na v1.2**: a vitória exige as 8 perguntas
   (teste da luta completa confirma 8 respostas até a vitória).
2. **Sem partida manual.** Tudo foi validado por testes automáticos e capturas
   do loop real; vale jogar a luta e conversar com os NPCs.
3. A arte nova dos NPCs é minha: revisem se ela combina com o que a equipe quer.

---

# v1.1/v1.2: arena em ruínas

A arena do Gorila virou um **santuário em ruínas tomado pela floresta**:
colunas de pedra quebradas e cobertas de musgo, um arco partido, muralha
desmoronando, cipós e copas invadindo pelo alto, noite fria e enevoada com
lua pálida e vaga-lumes. **Sem vermelho**: paleta de azul-acinzentado e
verde-musgo. A geometria da luta não mudou.

**v1.2, pouca decoração** (pedido da equipe): o musgo fica na própria pedra.
De enfeite sobram duas colunas quebradas, o pórtico da saída e os dois
obeliscos com braseiro; a copa no alto virou só um beiral e há 6 vaga-lumes.
O arco partido continua sendo gerado, mas está fora da arena.

| Arquivo | |
|---|---|
| `assets/images/backgrounds/isa_arena_ruinas_fundo.png`, `isa_arena_ruinas_frente.png` | **novos**: fundo em 2 camadas de paralaxe |
| `assets/images/tiles/isa_ruina_*.png` (4) | **novos**: laje com musgo, blocos, bloco rachado, plataforma |
| `assets/images/cenarios/isa_ruina_*.png` (3) | **novos**: coluna alta, coluna quebrada, arco partido |
| `ferramentas/gerar_arte_arena_ruinas.py` | **novo**: gera toda essa arte (determinístico) |
| `constants.py` | tiles 68–71 (IDs novos; os do templo continuam válidos); ambiente da arena |
| `src/ambientes.py` | vaga-lumes (opção `vagalumes` do ambiente) |
| `assets/levels/setores/arena.csv`, `decoracoes/arena_decor.csv`, `estruturas_cenario.json` | arena com a pele nova |
| `ferramentas/redesign_mapas/arena.py` | gera a arena nova (também atualizado em `../isa-redesign-mapas/`) |

**Legibilidade:** o Gorila é quase preto. O fundo tem uma faixa de névoa mais
clara exatamente na altura da luta. Medido pelo gerador (`--medir`):
luminância média do Gorila 46 contra 75 na faixa da luta.

- O palco (colunas 16–32) fica sem decoração.
- As luzes quentes são só os dois braseiros nos obeliscos, que emolduram a luta.
- Para levar tudo ao repositório dos amigos: `../isa-integracao-amigos/`.
- O fundo antigo `pro_arena_fundo.png` continua na pasta. Para voltar, basta
  trocar `camadas` em `constants.AMBIENTES["arena"]`.

**Testes (`testes_v1.1.txt` e `testes_v1.2.txt`):** 21/21 aprovados nas duas versões. Também passaram
`validar_dados.py` (0/0), a física real da arena (0 erros) e o auditor. O
`build.py` da arena regenera os mesmos bytes.

Imagens: `imagens/arena_ruinas/` (antes/depois e capturas do jogo rodando).
