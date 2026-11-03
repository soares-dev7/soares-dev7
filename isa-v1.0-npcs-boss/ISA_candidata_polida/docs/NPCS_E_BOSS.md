# NPCs e luta contra o Gorila (v1.0)

## NPCs

Cinco personagens que conversam com a Areninha (tecla **E**, ou **X** no controle).
Eles não têm colisão, não são inimigos e não abrem pergunta. A conversa não
pausa o jogo e fecha sozinha se o jogador se afastar. Quando há uma passagem
ao alcance, a tecla E vai para a passagem.

| NPC | Setor (coluna) | Papel | Arte |
|---|---|---|---|
| Guarda Tainá | floresta (20), perto do spawn | guia: minérios, perguntas, pulo duplo, golpe | pixel art nova |
| Seu Benedito | floresta (74), antes da ravina | narrativa: a fábrica sem cobre e zinco; muda a fala depois da caverna | pixel art nova |
| Engenheira Ana | caverna (61), nos andaimes | guia das galerias + **recompensa** (maçã com 8 minérios da caverna) | pixel art nova |
| Pesquisadora Lia | copas (92), Árvore Espiral | aviso sobre o Gorila + **recompensa** (maçã com 5 minérios das copas) | pixel art nova |
| Diretor | copas (148), antes do portal da arena | narrativa: o executivo das cutscenes, fala com o total da partida | `S7.png` (arte existente) |

- **"!"** sobre a cabeça: o NPC tem algo novo a dizer (fala nova liberada ou
  recompensa pronta). **"..."**: está falando.
- Recompensa: a maçã cai no chão ao lado do NPC, uma vez por partida. Ela
  só é consumida se o jogador estiver ferido (regra da maçã do jogo).

### Editar falas e posições: `assets/levels/npcs.json`

Cada NPC tem `coluna` e `base` (a linha do **bloco sólido** onde pisa, como nos
marcadores do CSV). `falas` é uma lista de blocos: vale o **primeiro** cuja
condição é verdadeira, então os mais específicos vêm antes.

Condições: `min_coletados_setor`, `max_coletados_setor`, `min_coletados_total`,
`max_coletados_total`, `visitou` (nome de setor). Textos aceitam
`{coletados_setor}`, `{total_setor}` e `{coletados_total}`.

Use texto **sem acento**: a fonte de pixel (`upheavtt`) não tem acentos, como
no resto da HUD. Cada linha cabe em até 3 linhas da caixa.

`testes/teste_npcs.py` valida o posicionamento: chão sob os pés, 2 células
livres acima, ≥ 4 colunas de passagens e chegadas, ≥ 2 de minérios e cobras.

### Arte

`python ferramentas/gerar_sprites_npc.py --previa previa.png` redesenha os
quatro NPCs em pixel art (24×36 px, ampliados 2× no jogo, contorno escuro
automático; 3 quadros: parado, respirando, piscando). Para usar outra arte,
coloque o PNG em `assets/images/npcs/npc_<nome>_0..2.png` ou use
`"sprite": "personagens:<arquivo>.png"` no JSON.

## Gorila Guardião: o que mudou

| | Antes | Agora |
|---|---|---|
| Posição | parado no centro | **salta para outro ponto** a cada 3 arremessos (2 nas fases 2–3); pouso marcado no chão 0,55 s antes; só em chão livre, nunca a menos de 4 tiles do jogador |
| Fases | 2 | **3**: com 1/4 da vida, **chuva de bananas** (`cacho_banana.png`) e arremessos a cada 0,8 s |
| Troca de fase | só o número na HUD | **faixa na tela**, fala do Gorila, tremor e **rugido sem ataque** ao acordar |
| Atordoado | 3 s de espera; encostar machucava | não fere por contato; estrelas sobre a cabeça. A **janela de punição** (minério caído = dano extra) existe, mas fica **desligada**: a vitória exige as **8 perguntas** |
| HUD | barra + "FASE" | + **MINÉRIOS DEVOLVIDOS X/8** e balão de fala |

Justiça (verificada em `testes/teste_boss_v1.py`):

- todo ataque novo tem aviso;
- os cachos da chuva caem com 3 tiles de vão entre si, e a sombra marca o
  ponto real de impacto (chão ou plataforma) cerca de 1 s antes;
- o salto nunca pousa em plataforma, fora da arena ou perto do jogador.

**Correção encontrada pelos testes:** o `on_ground` do Gorila alternava a
cada frame parado no chão (gravidade < 1 px por frame + `int()`), e o
salto-pancada da fase 2 só podia começar em frames alternados. Agora uma
sonda de 1 px sob os pés mantém o estado estável.

### Ajustes (`constants.py`, bloco "Boss v1.0")

`GORILA_SALTO_A_CADA`, `GORILA_SALTO_AVISO_MS`, `GORILA_CHUVA_INTERVALO`,
`GORILA_CHUVA_ESPACO_TILES`, `GORILA_CHUVA_DANO`, `GORILA_INTERVALO_ATAQUE_F3`,
`GORILA_RUGIDO_FASE_MS`, `GORILA_ANUNCIO_MS`, `GORILA_DANO_BONUS`.

**8 perguntas obrigatórias (decisão da equipe):** `GORILA_DANO_BONUS = 0`.
Cada minério devolvido com resposta certa tira 1 de vida e o Gorila tem 8, então
a vitória exige 8 respostas certas (verificado no teste da luta completa). A
janela de punição continua no código e testada; para ligá-la, use um valor
> 0. Com ela ligada, quem aproveita todas as janelas vence com 4 perguntas.

## Arena em ruínas (v1.1/v1.2)

Santuário de pedra em ruínas, noite fria e enevoada, sem vermelho. **Pouca
decoração** (pedido da equipe): o musgo está na própria pedra (tiles e
fundo); de enfeite, só os dois obeliscos com braseiro que emolduram a luta,
duas colunas quebradas e o pórtico da saída. A copa no alto é só um beiral,
com poucos cipós, e há 6 vaga-lumes.

A arte é gerada por `ferramentas/gerar_arte_arena_ruinas.py`: fundo em 2
camadas, tiles 68–71 e estruturas. O arco partido continua sendo gerado,
mas está fora da arena. A geometria da luta é a mesma.

**Legibilidade:** a faixa de névoa clara fica atrás dos lutadores. `--medir`
mostra o contraste: Gorila 46 contra fundo 75. Para voltar ao templo antigo,
use `pro_arena_fundo.png` em `camadas`.
