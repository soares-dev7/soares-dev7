# I.S.A. — Redesign criativo dos mapas (v0.8)

Direção de level design, composição ambiental e ritmo dos minérios nos 4
setores (floresta, caverna, copas, arena). Sprites, tilesets, backgrounds e a
arte de cenário **não foram alterados**: a mudança está em como os assets são
usados nas duas camadas CSV e no JSON de estruturas.

## Como instalar

Copie o conteúdo de `ISA_candidata_polida/` por cima da pasta do projeto
(mesmos caminhos). Os originais estão em `originais/` e a v0.7 está no
histórico do git deste repositório.

| Arquivo | Mudança |
|---|---|
| `assets/levels/setores/floresta.csv` | geometria nova, **404 colunas** (eram 374) |
| `assets/levels/setores/caverna.csv` | geometria nova (galeria de mina, poço de cristais, gruta inferior) |
| `assets/levels/setores/copas.csv` | geometria nova, **171 colunas** (eram 131) |
| `assets/levels/setores/arena.csv` | igual à v0.7 (geometria da luta intocada) |
| `assets/levels/decoracoes/*_decor.csv` (4) | composição nova |
| `assets/levels/estruturas_cenario.json` | árvores, arcos, suportes, conectores reassentados |
| `src/nivel_dados.py` | larguras de floresta e copas em `SETORES_GERADOS` (referência usada pelos validadores) |
| `MAPA-CSV.md` | só as tabelas de tamanho e de regiões |
| `ferramentas/auditar_ritmo_minerios.py` | **novo**: auditoria de espaçamento dos minérios por tempo de percurso |
| `ferramentas/auditar_level_design.py` | 1 linha (cria `docs/` antes de gravar o relatório) |
| `ferramentas/redesign_mapas/` | módulos de autoria por setor, renderizador e capturas no jogo |

---

## 1. O que acontece num minério (verificado no código)

- O minério é um **marcador `91` na camada física**, não na decorativa.
  `utils.extrair_marcadores` apaga o marcador da grade e `setores.criar_minerio`
  cria a entidade apoiada no bloco de baixo.
- `main._verificar_coletas`: **tocar no minério abre o quiz na hora**, desde que
  haja pergunta disponível. Se a fatia da fase acabou, o jogo remonta a lista
  antes.
- Respondendo, certo ou errado, o minério sai do mapa (`indice += 1`).
  ESC (`cancelar_quiz`) devolve o minério com 1,5 s de imunidade
  (`minerio_cobre.liberar`).
- Por isso, dois minérios próximos no percurso significam sair de uma pergunta e
  cair em outra. O espaçamento é parte do game design.
- A quantidade exigida pelo projeto (`teste_level_design_profissional`: ≥ 72) foi
  mantida: **72 minérios** (32 floresta + 25 caverna + 15 copas).

## 2. Auditoria de ritmo (nova) e diagnóstico

`ferramentas/auditar_ritmo_minerios.py` mede **tempo de percurso real**, não
distância em células. Ela usa o mesmo grafo de posições em pé do
`validar_fisica_real.py`: cada movimento é simulado com `Character.move`, o
custo é em quadros a 60 FPS e a penalidade artificial por pulo é descontada.
Para cada par de minérios, calcula o menor tempo do ponto em que se pega um
até tocar o outro, somando nas pontas a caminhada até o minério.

| Medida | Critério |
|---|---|
| vizinho mais próximo < 2,0 s | **ERRO**: pergunta colada na outra |
| vizinho < 3,5 s | aviso (meta) |
| mais de 4 minérios nos próximos 15 s de percurso | aviso (meta) |
| inimigo a < 3 tiles, decoração na célula do minério ou ao lado | aviso |

Mesma régua aplicada às três versões:

| Versão | Erros | Floresta (mediana / mín.) | Caverna | Copas |
|---|---|---|---|---|
| Original | **55** | 2,6 s / 0,8 s | 1,8 s / 1,1 s | 1,6 s / 0,7 s |
| v0.7 | **68** | 2,0 s / 1,0 s | 1,8 s / 0,8 s | 1,5 s / 0,9 s |
| **v0.8** | **0** | **3,3 s / 2,2 s** | **4,3 s / 2,0 s** | **3,6 s / 2,0 s** |

(intervalo entre minérios na ordem em que o jogador os encontra)

A v0.7 tinha **piorado** o ritmo: eu tinha distribuído os minérios pela
distância horizontal e muitos ficaram a 1 s um do outro. A auditoria nova
deixou isso visível.

**A conta que guiou a v0.8:** 72 minérios num percurso de ~190 s davam 2,6 s
por minério. Só reposicionar não bastava, e afrouxar a meta seria esconder o
problema. A solução foi **aumentar o percurso jogável com exploração**:
grutas, copas, galerias e desvios verticais, e duas regiões novas (+30 colunas
na floresta, +40 nas copas).

## 3. Decisões criativas por setor

### Floresta: ambiente vivo (404 × 44)

| Colunas | Região | Decisão |
|---|---|---|
| 0–37 | Clareira | Spawn plano e seguro; morrinho; placa; 1º pulo numa passarela com minério |
| 38–76 | Colina | Patamares irregulares e árvore no topo. **Desvio vertical:** passarela + galho preso ao tronco, com minério no alto |
| 77–96 | Ravina | Vale de 4 degraus, boca da caverna emoldurada por rochas e fungos, vão central limpo |
| 97–127 | **Clareira afundada** (nova) | Bacia com minério no fundo. Um tronco caído cruza por cima: atalho que pula o minério, escolha do jogador |
| 128–160 | Planície | Patamar da árvore, 1ª cobra, chegada da caverna |
| 161–216 | **Árvore Guardiã** | Face oeste íngreme, platô com cobra e passarela alta. **Gruta escondida** sob a árvore: porta pequena num paredão, túnel curto, salão com fungos luminosos e raízes penduradas, minério dentro. Placa avisa "há algo no paredão" |
| 217–245 | Lago | Lâmina d'água contínua, juncos nas margens |
| 246–275 | **Outeiro do mirante** (novo) | Quebra a planura da baixada: rochas agrupadas, flores no topo, mirante com minério |
| 276–330 | Baixada | Campo do tucano, tronco caído, **toca** que desce para um túnel curto sob a cobra (minério) |
| 331–403 | **Árvore-Mãe** | Vala com ponte, platô com o cipó das copas e **escalada pela copa** em 5 passarelas até o cume, dentro das folhas (minério). O clímax vertical do setor |

### Caverna: exploração e descoberta (251 × 44)

- **Galeria de mina superior** (rota alternativa à passagem espremida): andaimes
  em escada na câmara principal, patamar de madeira com corda de corrimão,
  túnel escorado (postes de mina do chão ao teto), tochas, aranha de guarda.
  Ela sai por cima da galeria de cristais.
- **Poço dos cristais**: depressão com lâmina d'água no fundo e cristais nas bordas.
- **Gruta inferior** sob o salão de combate: poço de descida com andaimes em
  ziguezague a cada 2 linhas (desce e sobe), cristais, poça, estalactites,
  5 minérios a ~2,2 s um do outro.
- Mantidos: galeria de entrada, câmara alta com rocha pendente, salão de
  combate, corredor com poça e câmara de saída com tochas.
- Mantidos de propósito para os testes: chegada `40` perto de (12,27) e as
  células (136,14) e (147,18) como casos ruins do tucano.

### Copas: verticalidade e natureza (171 × 44)

A v0.7 tinha ficado vazia (25 decorações, uma linha de decks). Medi na arte a
posição dos galhos de cada árvore:

- árvores de fundo: galho esquerdo nas linhas 20–21, direito nas 25–27,
  esquerdo baixo nas 29–31;
- Ancestral: copa nas linhas 21–28;
- Espiral: copa nas linhas 11–18.

**Toda plataforma se apoia num elemento da arte** (galho, bifurcação, copa,
raiz, conector ou toquinho), registrado ao lado de cada plataforma em
`copas.py`. Nenhum tronco artificial em escada.

- **Árvore Ancestral**: deck baixo; **subida pela copa até o cume**; rota alta
  pelo galho esquerdo da árvore de fundo, caindo no ninho; **rota baixa pelas
  raízes**.
- **Ninho**: pousado no deck, com o minério dentro.
- **Galho baixo da árvore de fundo** e **raízes da Espiral**: desvio inferior com minérios.
- **Árvore Espiral**: deck na bifurcação, cume na copa, tucano voando na copa
  (faixa de voo limpa).
- **Árvore Vigia** (nova, +40 colunas): ponte de galhos, galho esquerdo da
  árvore, deck no galho direito preso por um toquinho, subida pela copa até o
  deck final.
- Vegetação densa nos decks, folhas brotando na ponta dos galhos, lianas de
  comprimentos variados e ramos sob todas as plataformas, lanternas no caminho
  do portal. São 130 decorações; na v0.7 eram 25.

### Arena: clareza e impacto

A geometria da luta não muda. A composição virou uma **moldura**: dois
obeliscos de runas iguais marcam as bordas do palco (colunas 14 e 34), cada um
com uma tocha do lado de fora. Os estandartes e as lanternas ficam pendurados
nas plataformas altas. O **centro (16–32) fica limpo**, para ler o Gorila e os
projéteis.

### Decorações (regras gerais)

- **Âncora por sprite**, medida na área opaca de cada PNG: as de chão só entram
  com bloco embaixo e as penduradas só com bloco em cima.
- Nada pendurado sob madeira, nem no teto liso dos túneis escavados.
- Zonas limpas em volta dos portais, chegadas, spawn, faixas de voo, fio das
  aranhas e minérios (nenhuma decoração na célula do minério ou ao lado).
- Densidades diferentes por região; vegetação em manchas com vazios entre elas.

## 4. Validação (executada nesta sessão, sobre os arquivos finais)

| Verificação | Resultado |
|---|---|
| `python testes/rodar_todos.py` | **19/19 aprovados** |
| `python ferramentas/validar_fisica_real.py` | **0 erros, 0 avisos**. Todas as superfícies pisadas nos 4 setores; todos os minérios alcançáveis; nenhuma posição sem saída |
| `python ferramentas/auditar_ritmo_minerios.py` | **0 erros**. 83 avisos de meta: 58 vizinhos entre 2,0 e 3,5 s e 25 janelas com mais de 4 minérios em 15 s |
| `python validar_dados.py` | 0 erros, 0 avisos |
| Auditor do projeto (`teste_level_design_profissional`) | aprovado, 72 minérios |
| Instalação limpa | a cópia instalada a partir desta pasta é idêntica à versão validada; o `build.py` regenera os mesmos bytes |

Problemas que os validadores pegaram durante o trabalho e que foram corrigidos
no mapa (nenhum validador foi afrouxado):

- O tronco caído fechava a clareira afundada por cima (só a física real viu).
- O paredão da gruta deixaria a metade leste da floresta sem volta (resolvido
  com um degrau de raiz).
- Minérios sob plataformas, sem espaço livre.
- Cobras sob galhos e andaimes.
- Um morrinho ocupava a célula que `teste_csv_edicao` usa ao lado do spawn.
- 13 pares de minérios colados.

**Validação visual.**

- `imagens/mapas_v08/`: as três visões de cada setor (física, decorativa e
  combinada com o background original).
- `imagens/comparacao/`: original × v0.7 × v0.8 na visão combinada.
- `imagens/jogo_v08/`: 22 capturas do **loop real do jogo** (câmera, HUD,
  atmosfera, inimigos).
- `imagens/jogo_original/` e `imagens/jogo_v07/`: capturas das versões anteriores.

Ajustes feitos a partir das imagens:

- A primeira gruta ficou grande demais e virou uma "janela" sob uma laje.
  Reduzida para um abrigo.
- A toca foi encurtada pelo mesmo motivo.
- Estalactites saíram do teto dos túneis.
- Um galho escondia o ninho na v0.7.

`auditoria/` traz os relatórios de ritmo (original, v0.7 e v0.8) e a saída dos testes.

## 5. Pendências e limites honestos

- **Não houve playtest humano.** A jogabilidade foi provada por simulação com a
  física real, testes automáticos e capturas do loop real.
- **Os 72 minérios são o limite do ritmo.** Com a meta de 2 s não há erro, mas
  58 minérios têm um vizinho entre 2 e 3,5 s. Se o projeto puder baixar o
  mínimo (por exemplo, para 60), dá para chegar a ~4 s entre perguntas sem
  mexer na geometria. Essa decisão é da equipe.
- **Floresta e copas ficaram mais largas.** O jogo lê a largura do CSV; só
  `nivel_dados.py` e a tabela do `MAPA-CSV.md` foram atualizados. O
  `gerar_mundo.py` continua gerando o mundo antigo, mas não sobrescreve CSVs
  editados.
- **Grutas e tocas na floresta mostram o fundo da floresta** por dentro, porque
  o jogo não tem tile de parede de fundo. Por isso foram mantidas pequenas,
  com porta estreita.
- **Copas: queda no vazio continua dando game over** (como no original). Todos
  os vãos são de no máximo 2 tiles.
- Documentação antiga não revisada: a seção de encontros do `MAPA-CSV.md` e o
  README das decorações, que ainda cita os IDs 100–117.

## Ferramentas

```
python ferramentas/redesign_mapas/build.py . floresta,caverna,copas,arena                  # só confere
python ferramentas/redesign_mapas/build.py . floresta,caverna,copas,arena --sobrescrever   # grava
python ferramentas/auditar_ritmo_minerios.py --processos 4 --lista                         # ritmo
python ferramentas/redesign_mapas/renderizar_camadas.py . all renders 0.5 --grid           # 3 visões
python ferramentas/redesign_mapas/capturas_no_jogo.py . capturas                           # loop real
```

Cada setor é um módulo legível com o perfil do terreno, as cavidades, as
plataformas (e no que cada uma se apoia), os marcadores e as regras de
decoração escritos explicitamente. O `build.py` sobrescreve edições à mão
feitas depois nos CSVs: use com consciência.
