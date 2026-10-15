# I.S.A. — Redesign dos mapas CSV (v0.7)

Redesign das duas camadas CSV (física + decorativa) dos 4 setores do I.S.A.:
floresta, caverna, copas e arena. Nenhum sprite, tileset, background ou arte
de cenário foi alterado. A mudança está em **onde** e **como** os assets
existentes são usados.

## Como instalar

Copie o conteúdo de `ISA_candidata_polida/` por cima da pasta do projeto
(mesmos caminhos). São 10 arquivos de jogo e uma pasta nova de ferramentas:

| Arquivo | O que mudou |
|---|---|
| `assets/levels/setores/floresta.csv` | geometria nova |
| `assets/levels/setores/caverna.csv` | geometria nova |
| `assets/levels/setores/copas.csv` | geometria nova |
| `assets/levels/setores/arena.csv` | só o preenchimento do piso (a geometria da luta é idêntica) |
| `assets/levels/decoracoes/*_decor.csv` (4) | composição nova |
| `assets/levels/estruturas_cenario.json` | árvores, arcos e suportes reassentados no terreno novo |
| `ferramentas/auditar_level_design.py` | 1 linha: cria `docs/` antes de gravar o relatório |
| `ferramentas/redesign_mapas/` (novo) | kit de autoria, renderizador de camadas, capturas no jogo |

Os originais estão em `originais/assets/levels/` (backup recuperável).
Os CSVs mantêm o formato de cada arquivo original: separador `,`, sem BOM,
CRLF (copas: LF) e quebra de linha final.

---

## 1. Diagnóstico (antes)

Auditoria feita no código antes de mexer em qualquer arquivo: `src/world.py`,
`src/setores.py`, `src/decoracoes.py`, `src/estruturas_cenario.py`,
`src/passagens.py`, `utils.extrair_marcadores`, `constants.py` e a física em
`src/character.py`.

**Como o jogo lê as camadas**
- CSV físico: IDs de `constants.TILE_SPRITES`. Têm colisão só os IDs em
  `SOLID_TILES`. O `67` (escora de raiz) é desenhado, mas não tem colisão.
  Marcadores (30–45, 90–96) são apagados da grade ao carregar.
- CSV decorativo: IDs 100–123 (`src/decoracoes_offline.ARTE`), sem colisão.
  Precisa ter a mesma dimensão do CSV físico.
- Ordem de render (`main._desenhar_cena`): fundo → estruturas → **decoração →
  tiles** → passagens → entidades → atmosfera. Decoração é desenhada **atrás**
  dos tiles, então uma decoração numa célula sólida é invisível. Por isso o
  auditor já proíbe esse caso.
- Física real: tile = 48 px. Pulo simples = 1,5 tile, pulo duplo ≈ 3, alcance
  de 2,5 tiles. A regra do validador do projeto é degrau ≤ 2 e vão ≤ 2, e
  todo o redesign respeita isso.

**Problemas encontrados**

| Setor | Problema | Por que prejudica |
|---|---|---|
| Floresta | Subsolo com faixas verticais `DDDD`/`ssss` repetidas a cada 12 colunas, deslocadas na diagonal | padrão de algoritmo visível em toda a tela |
| Floresta | Duas "pirâmides" de degraus flutuando sobre uma laje de rocha (`66`), com o jogador passando por baixo | massa de terra sem apoio; lê como bloco colado, não como relevo |
| Floresta | 38 componentes sólidos, 18 deles com ≤ 4 tiles soltos no ar | "bloco no meio do nada" |
| Floresta | Uma faixa de grama enterrada no subsolo (linha 33, col 343–361) | erro visível |
| Floresta | Rochas decorativas (`122`) espalhadas uma a uma, sem grupo | ruído visual |
| Caverna | Corredor quase plano, tetos em escada | pouca variação espacial |
| Copas | Troncos sólidos em **escada diagonal** (`|!||||!`) do fundo do mapa até cada plataforma | parecem rampas de tijolo; escondem e brigam com as árvores desenhadas |
| Copas | Toquinhos (`106`) com folhas (`107`) dos dois lados formando "cruzes" repetidas; pares de cipó idênticos sob cada plataforma | repetição óbvia, poluição |
| Arena | Piso de templo com diagonal `tTTTT` repetida a cada 5 colunas | padrão artificial |
| Arena | 44 runas (`113`) em pilhas quebradas, com buracos, soltas no ar | 19 decorações sem apoio |

A linha de base passava nos validadores (0 erros de física). Ou seja, o
problema era de composição e leitura, não de um mapa quebrado.

## 2. O que foi feito em cada mapa

### Floresta (374 × 44): introdução → exploração → desenvolvimento → desafio → conclusão

Terreno descrito como um perfil de altura escolhido coluna a coluna (nada
aleatório na geometria):

| Colunas | Trecho | Decisões |
|---|---|---|
| 0–37 | Clareira | Plana para aprender os controles. Placa no início. Primeira passarela baixa (2 tiles) com minério, que ensina o pulo |
| 38–80 | Colina | Patamares de larguras irregulares, árvore no topo, passarela de raiz cruzando o tronco |
| 79–95 | Ravina | Vale de 3 degraus com a boca da caverna (`30`) no fundo. Rochas e fungos emolduram a entrada, e o vão central fica limpo |
| 95–160 | Planície | Patamares, passarelas em escada (28 → 26), 1ª cobra numa área plana larga, chegada da caverna (`42`) |
| 161–217 | Colina da Árvore Guardiã | Face oeste íngreme, platô com cobra, face leste longa. A colina agora é uma massa de terra apoiada no chão, não uma pirâmide flutuante. Rota alta opcional (passarela na linha 19) com 2 minérios |
| 218–300 | Baixada | Respiro: lago raso (água `115` sobre o fundo, juncos nas margens), tucano em campo aberto, bosque |
| 301–373 | Final | Subida, vala com ponte de raiz (dá para atravessar por cima ou descer pela vala), platô da Árvore-Mãe com o cipó das copas (`31`) ao pé dela e passarelas de recompensa |

- Subsolo: terra com variação por manchas suaves e pedras em pequenos grupos
  orgânicos, em vez de faixas. Grama com raízes (`13`) só perto dos troncos das
  árvores grandes; grama com flores (`12`) em manchas.
- Árvores grandes (`arvore_antiga*`) reposicionadas sobre trechos planos, com
  a base calculada a partir do terreno real (o mesmo afundamento de 1 tile do
  original).

### Caverna (251 × 44)

Piso e teto viraram dois perfis desenhados: tudo entre eles é ar, o resto é
rocha.

| Colunas | Seção |
|---|---|
| 0–24 | Galeria de entrada (chegada `40`) |
| 25–57 | Corredor descendente: aranha num teto baixo, cobra num patamar de 11 tiles |
| 58–99 | Câmara principal alta, com rocha pendente e andaimes de mina (`61`) em escada (34 → 32 → 30), cada um com minério; suporte de mina sob o andaime alto |
| 100–124 | Passagem espremida: teto constante de 3 tiles, piso subindo |
| 125–159 | Galeria dos cristais: veios de cristal (`26`) na rocha perto do ar, cristais no chão junto aos veios, tucano no espaço alto |
| 160–199 | Salão de combate: piso largo, 2 cobras, andaimes laterais |
| 200–217 | Corredor fundo com poça d'água, musgo e cogumelos |
| 218–250 | Câmara de saída: subida até a saída (`32`), com tochas dos dois lados |

- Estalactites só sob rocha (nunca sob madeira) e no máximo 2 lado a lado.
- Tochas marcam onde houve trabalho humano (andaimes e saída).
- Arcos, colunas e cristais grandes assentados no piso novo (afundados 2 tiles,
  como no original). Suportes de mina com altura escolhida pelo vão real
  (`isa_mine_support_<altura>.png`).
- Mantidos de propósito para os testes: chegada `40` perto de (12,27) e as
  células (136,14) e (147,18) em posições "ruins" para o tucano (casos
  negativos do `teste_voadores.py`).

### Copas (131 × 44)

As árvores da arte (`estruturas_cenario.json`) **não mudaram de lugar**: elas
ditam a geometria. A camada física virou decks finos (`14`/`15`) e galhos
(`62`) que cruzam essa arte na altura certa:

- deck de chegada sob o pórtico, cruzando o tronco de fundo;
- galhos subindo apoiados num ramo conector diagonal (reposicionado);
- deck da Árvore Ancestral na altura da bifurcação, com um galho opcional na
  copa (apoiado num toquinho de tronco);
- deck do ninho: o ninho foi baixado 1 tile para pousar no deck, e há um minério
  dentro dele;
- deck da Árvore Espiral, com o tucano voando na copa (faixa de voo limpa);
- deck final com lanternas penduradas, levando ao portal ancestral da arena.

Todos os vãos são de 1 tile e todos os degraus de até 2.

### Arena (41 × 44)

Geometria da luta intocada (piso, plataformas `63`, marcadores e
`AREA_BOSS`). O piso perdeu o padrão diagonal. As runas soltas viraram dois
obeliscos apoiados no chão (3 e 2 de altura, sem espelhar). Estandartes e
lanternas ficam pendurados nas plataformas altas e as tochas ficam no chão e
nas pontas das plataformas. O centro da luta ficou limpo.

## 3. Lógica de composição das decorações

Implementada em `ferramentas/redesign_mapas/kit.py` (`Compositor`). A
decoração é posicionada **depois** da geometria e lendo a geometria:

1. **Âncora por tipo de sprite**, medida pela área opaca de cada PNG:
   - de chão: flor, samambaia, arbusto, cogumelo, fungo, cristais, pedra,
     placa, tocha, raiz, água e runas. Só entram em célula livre com bloco
     sólido logo abaixo;
   - pendurados: estalactite, liana, cipó, ramos, lanterna e bandeira. Só
     entram com bloco sólido logo acima.
2. **Peças narrativas à mão**: placas (início, ravina, rumo às copas), moldura
   da boca da caverna, tochas da saída, lanternas do caminho da arena.
3. **Zonas limpas**: vão das passagens, chegadas, spawn, fio das aranhas,
   faixa de voo do tucano, 1 célula de cada lado dos minérios e centro da luta.
4. **Densidade por zona e manchas**: ruído suave decide *onde* há manchas de
   vegetação; vinhetas pequenas e variadas (1–3 peças) preenchem cada mancha,
   com vazio entre elas. Nunca "toda célula vazia".
5. **Contexto**: raízes e cogumelos ao pé das árvores, cristais junto aos
   veios de cristal, musgo nas partes úmidas, nada pendurado sob madeira e
   galhos finos sem vegetação em cima (leitura do pulo).

## 4. Resultados dos testes (executados)

Todos rodados nesta sessão, sobre os mapas finais:

| Verificação | Resultado |
|---|---|
| `python testes/rodar_todos.py` | **19/19 aprovados** |
| `python ferramentas/validar_fisica_real.py` (BFS com o `Character.move` real, pulo duplo) | **0 erros, 0 avisos**. Todas as superfícies pisáveis, todos os minérios/maçãs alcançáveis, nenhuma posição sem saída |
| `python validar_dados.py` | 0 erros, 0 avisos |
| `testes/teste_level_design_profissional.py` (auditor) | aprovado: 84 minérios (mínimo 72), marcadores apoiados, decoração fora de colisão |
| `testes/teste_voadores.py` | 3 tucanos reais aprovados e 3 casos negativos reprovados como esperado |
| Reconstrução pelas ferramentas | idempotente (rodar de novo gera arquivos byte a byte iguais) |

Métricas antes → depois (calculadas sobre os CSVs):

| Setor | Pedaços sólidos de ≤ 4 tiles soltos | Decorações sem apoio | Decorações |
|---|---|---|---|
| Floresta | 18 → **0** | 0 → 0 | 112 → 121 |
| Caverna | 2 → **0** | 0 → 0 | 57 → 112 |
| Copas | 3 → **0** | 2 → **0** | 172 → 25 |
| Arena | 0 → 0 | 19 → **0** | 51 → 13 |

**Validação visual.** `imagens/mapas/` tem as três visões pedidas para cada
setor, antes e depois: `*_1_fisica`, `*_2_decor` e `*_3_combinada` (com o
background original). `imagens/jogo_antes/` e `imagens/jogo_depois/` são
capturas do **loop real do jogo** (`main.py`, câmera do jogador, HUD e
atmosfera) em 17 pontos-chave. Os ajustes foram iterados sobre essas imagens:
pirâmide da colina, ravina rasa, lago cortado por minério, estalactites sob
madeira, ninho escondido por um galho e obelisco caindo sobre a plataforma
foram todos corrigidos a partir dos renders.

## 5. Pendências e observações

- **Não houve playtest humano.** A jogabilidade foi provada pela física real
  simulada, pelos testes automatizados e pelas capturas do loop real. Vale uma
  passada jogando, principalmente nas copas.
- **Copas: queda no vazio continua dando game over** (já era assim no
  original). Os vãos agora são todos de 1 tile, mas não há "rede" embaixo.
  Se quiserem queda sem morte, a solução é uma camada de galhos baixa com
  caminho de volta, e isso muda o design da fase.
- **Copas ficou intencionalmente mais limpa** (172 → 25 decorações): o céu e as
  árvores grandes já carregam a cena. Dá para adensar em `copas.py`, na lista
  `VINHETAS`.
- Floresta: as 6 peças `isa_polimento_raiz_ancorada_*` do JSON foram removidas,
  porque ancoravam plataformas que deixaram de existir. As escoras `67` fazem
  esse papel agora. Os PNGs continuam na pasta.
- Documentação do projeto não foi editada: `MAPA-CSV.md` ainda descreve as
  seções antigas da caverna e repete 3 vezes o parágrafo da camada de
  decorações; `assets/levels/decoracoes/README.md` cita IDs 100–117, mas já
  existem 118–123.
- Ambiente: `teste_estatisticas.py` e `teste_boss.py` precisam do pacote
  `fpdf2` (já está no `requirements.txt`). O zip recebido não trazia a pasta
  `docs/`, e por isso o auditor falhava ao gravar o relatório (corrigido).

## Ferramentas (`ISA_candidata_polida/ferramentas/redesign_mapas/`)

```
python ferramentas/redesign_mapas/build.py . floresta,caverna,copas,arena                  # só confere
python ferramentas/redesign_mapas/build.py . floresta,caverna,copas,arena --sobrescrever   # grava
python ferramentas/redesign_mapas/renderizar_camadas.py . all renders 0.5 --grid           # 3 visões
python ferramentas/redesign_mapas/capturas_no_jogo.py . capturas                           # loop real
```

Cada setor é um módulo legível (`floresta.py`, `caverna.py`, `copas.py`,
`arena.py`) com o perfil do terreno, as plataformas, os marcadores e as
regras de decoração escritos explicitamente. Ajustar o mapa = editar essas
listas, gravar com `--sobrescrever` e rodar os validadores. O `build.py`
sobrescreve edições à mão feitas depois nos CSVs: use com consciência, como o
`gerar_mundo.py`.
