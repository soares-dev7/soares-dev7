"""FLORESTA — 374 x 44. Setor inicial (fase 1).

Progressão (colunas):
    0-37    Introdução   clareira plana, placa, 1ª passarela baixa (ensina o pulo)
   38-80    Exploração   colina suave com árvore no topo e passarela de raiz
   81-100   Ravina       vale raso com a boca da caverna (30), rochas e fungos
  101-160   Desenvolv.   planície em patamares, 1ª cobra, chegada da caverna (42)
  161-215   Desafio      colina da Árvore Guardiã: terraços, cobra no platô,
                         passarela alta opcional com minérios
  216-300   Respiro      baixada com lago raso, tucano, cobra, bosque
  301-373   Conclusão    subida final, vala com ponte de raiz, platô da
                         Árvore-Mãe com o cipó para as copas (31) e chegada (43)
"""
from kit import Grade, Compositor, perfil, checar_perfil, ruido, acaso, VAZIO

L, C = 44, 374

# IDs (constants.py)
GRAMA, GRAMA_FLOR, GRAMA_RAIZ = 1, 12, 13
TERRA, TERRA_FUNDA, TERRA_PEDRA = 2, 20, 22
PONTE, PASSARELA, ESCORA = 60, 64, 67
SPAWN, MINERIO, COBRA, TUCANO = 90, 91, 92, 93
P_CAVERNA, P_COPAS, CH_CAVERNA, CH_COPAS = 30, 31, 42, 43

# decorações (src/decoracoes_offline.ARTE)
FLOR, SAMAMB, COGU, ARBUSTO, PLACA, AGUA, FLOR_ROXA = 100, 101, 110, 112, 114, 115, 117
LIANA, FUNGO, RAMOS, RAIZ_ARCO, PEDRA, FOLHAGEM = 118, 119, 120, 121, 122, 123

PERFIL = [
    (0, 30), (18, 29), (25, 30),                          # clareira
    (38, 29), (40, 28), (45, 27), (52, 26), (61, 27),     # colina (patamares irregulares)
    (63, 28), (69, 29), (72, 30),
    (79, 31), (82, 32), (84, 33), (91, 32), (93, 31),     # ravina da caverna
    (95, 30),
    (111, 29), (119, 28), (127, 29),                      # planície em patamares
    (161, 28), (163, 27), (166, 26), (168, 24),           # colina da guardiã:
    (171, 23), (179, 21),                                 # face oeste íngreme,
    (197, 22), (200, 23), (202, 24), (206, 25),           # face leste longa
    (207, 26), (211, 27), (213, 28), (215, 29), (218, 30),
    (222, 31), (228, 32), (240, 31), (246, 30),           # baixada e lago
    (270, 29), (286, 28), (296, 27), (302, 26), (308, 25),
    (312, 26), (313, 27), (314, 28), (321, 27), (322, 26),  # vala
    (323, 25), (326, 24), (366, 23),                      # platô da Árvore-Mãe
]
LAGO = (228, 239)          # fundo do lago (linha 32)

# Passarelas: (c0, c1, linha, tile, colunas_de_escora)
PLATAFORMAS = [
    (28, 33, 28, PASSARELA, (28, 33)),     # 1º pulo
    (51, 57, 24, PASSARELA, (51, 57)),     # topo da colina
    (104, 109, 28, PASSARELA, (104, 109)),
    (111, 115, 26, PASSARELA, (115,)),     # degrau acima da anterior
    (121, 126, 26, PASSARELA, (121, 126)),
    (197, 206, 19, PASSARELA, (197, 202, 206)),  # rota alta da guardiã
    (248, 252, 28, PASSARELA, (248, 252)),
    (288, 293, 25, PASSARELA, (288, 293)),
    (314, 320, 25, PONTE, ()),             # ponte sobre a vala
    (360, 365, 22, PASSARELA, (360, 365)),
    (367, 372, 20, PASSARELA, (372,)),
]

# Árvores grandes (estruturas_cenario.json): (imagem, coluna_do_json)
# O tronco de arvore_antiga cai 1,2 tile à direita do centro -> coluna+1.
ARVORES = [("arvore_antiga.png", 19), ("arvore_antiga_alt.png", 56),
           ("arvore_antiga.png", 97), ("arvore_antiga_alt.png", 139),
           ("arvore_antiga_alt.png", 175), ("arvore_antiga.png", 223),
           ("arvore_antiga_alt.png", 252), ("arvore_antiga.png", 279),
           ("arvore_antiga_alt.png", 298), ("arvore_antiga.png", 329)]


def construir():
    alt = perfil(PERFIL, C)
    checar_perfil(alt, 2, "floresta")
    t = Grade(L, C)
    troncos = [col + 1 for _, col in ARVORES] + [190, 353]

    for c in range(C):
        topo = alt[c]
        perto_tronco = any(abs(c - tc) <= 3 for tc in troncos)
        no_lago = LAGO[0] <= c <= LAGO[1]
        for r in range(topo, L):
            prof = r - topo
            if prof == 0:
                if no_lago:
                    v = TERRA
                elif perto_tronco:
                    v = GRAMA_RAIZ
                elif ruido(c, 0, 11, 5.0) > 0.70:
                    v = GRAMA_FLOR
                else:
                    v = GRAMA
            elif prof <= 2:
                v = TERRA
            else:
                v = TERRA_FUNDA if ruido(c, r, 3, 6.0) + prof * 0.035 > 0.82 else TERRA
                if prof >= 3 and ruido(c, r, 7, 2.6) > 0.80:
                    v = TERRA_PEDRA
            t.set(c, r, v)

    for c0, c1, r, tile, escoras in PLATAFORMAS:
        for c in range(c0, c1 + 1):
            assert t.get(c, r) == VAZIO, ("plataforma sobre terreno", c, r)
            t.set(c, r, tile)
        for c in escoras:
            for rr in range(r + 1, alt[c]):
                t.set(c, rr, ESCORA)

    # ── marcadores ──────────────────────────────────────────────────────────
    def chao(c, v):
        t.set(c, alt[c] - 1, v)

    def sobre(c, linha_plat, v):
        t.set(c, linha_plat - 1, v)

    chao(8, SPAWN)
    chao(87, P_CAVERNA)
    chao(150, CH_CAVERNA)
    chao(337, CH_COPAS)
    chao(344, P_COPAS)
    for c in (134, 189, 276):
        chao(c, COBRA)
    t.set(263, 25, TUCANO)

    minerios_chao = [15, 40, 66, 76, 81, 92, 99, 118, 145, 157, 162, 173, 181,
                     194, 212, 220, 244, 256, 268, 282, 297, 309, 317, 350, 357]
    for c in minerios_chao:
        chao(c, MINERIO)
    for c, r in [(31, 28), (54, 24), (106, 28), (113, 26), (123, 26),
                 (201, 19), (205, 19), (250, 28), (290, 25), (363, 22), (370, 20)]:
        sobre(c, r, MINERIO)

    decor = decorar(t, alt, troncos)
    estruturas = estruturas_floresta(alt)
    return t, decor, estruturas


def decorar(t, alt, troncos):
    import constants
    comp = Compositor(t, constants.SOLID_TILES, constants.TILES_MARCADORES | {ESCORA})

    # 1. Peças narrativas, colocadas à mão.
    comp.grupo_chao(12, alt[12] - 1, [PLACA])                 # placa do começo
    comp.grupo_chao(79, alt[79] - 1, [PLACA])                 # aviso da ravina
    comp.grupo_chao(340, alt[340] - 1, [PLACA])               # rumo às copas
    # boca da caverna: rochas e fungos emoldurando, vão central limpo
    comp.grupo_chao(84, 32, [PEDRA, FUNGO])
    comp.grupo_chao(89, 32, [FUNGO, PEDRA])
    comp.grupo_chao(82, 31, [SAMAMB, COGU])
    comp.grupo_chao(91, 31, [COGU])
    comp.grupo_chao(93, 30, [PEDRA])
    comp.reservar(85, 89, 30, 32)
    # cipó das copas ao pé da Árvore-Mãe: deixa a subida legível
    comp.reservar(342, 346, 21, 23)
    comp.reservar(335, 339, 22, 23)                           # chegada 43
    comp.reservar(148, 152, 27, 28)                           # chegada 42
    comp.reservar(6, 10, 27, 29)                              # spawn
    # lago raso: água em toda a lâmina, juncos nas margens
    for c in range(LAGO[0] + 1, LAGO[1]):
        comp.por(c, 31, AGUA)
    comp.grupo_chao(LAGO[0], 31, [SAMAMB])
    comp.grupo_chao(LAGO[1], 31, [SAMAMB])
    comp.grupo_chao(LAGO[1] + 1, alt[LAGO[1] + 1] - 1, [FLOR_ROXA])

    # 2. Pé das árvores: raízes rasteiras e sombra (cogumelos / samambaia).
    for i, tc in enumerate(troncos):
        r = alt[tc] - 1
        if tc in (190, 353):   # guardiã e mãe: base larga, mais densa
            comp.grupo_chao(tc - 5, r, [SAMAMB, RAIZ_ARCO])
            comp.grupo_chao(tc + 4, r, [RAIZ_ARCO, COGU, FUNGO])
            continue
        comp.grupo_chao(tc - 2, r, [RAIZ_ARCO])
        comp.grupo_chao(tc + 2, r, [RAIZ_ARCO])
        if i % 3 == 0:
            comp.grupo_chao(tc + 3, r, [COGU])
        elif i % 3 == 1:
            comp.grupo_chao(tc - 4, r, [SAMAMB, COGU])
        else:
            comp.grupo_chao(tc + 3, r, [SAMAMB])

    # 3. Pendurados sob as passarelas — nem todas, nem no mesmo ponto.
    for i, (c0, c1, r, tile, escoras) in enumerate(PLATAFORMAS):
        larg = c1 - c0 + 1
        if larg < 5 or i % 2 == 1 and tile != PONTE:
            continue
        a = c0 + 1 + int(acaso(c0, r, 5) * (larg - 3))
        if a in escoras:
            a += 1
        comp.pendurar(a, r + 1, [LIANA, LIANA][: 1 + (i % 2 == 0)])
        b = a + 2 + (i % 2)
        if b < c1 and b not in escoras:
            comp.pendurar(b, r + 1, [RAMOS])

    # Minério no chão: 1 célula livre de cada lado (leitura do item).
    for r in range(L):
        for c in range(C):
            if t.g[r][c] == MINERIO:
                comp.reservar(c - 1, c + 1, r, r)

    # 3b. Barranco do lago e da vala: rochas onde o terreno quebra.
    for c in (313, 321):
        comp.grupo_chao(c, alt[c] - 1, [PEDRA])

    # 4. Vegetação por zona: manchas agrupadas, com vazios entre elas.
    ZONAS = [  # (c0, c1, densidade, vinhetas)
        (0, 37, 0.55, "clareira"), (38, 80, 0.40, "colina"),
        (95, 160, 0.45, "planicie"), (161, 215, 0.35, "guardia"),
        (216, 300, 0.65, "baixada"), (301, 373, 0.50, "final"),
    ]
    VINHETAS = {
        "clareira": [[FLOR], [FLOR, VAZIO, FLOR_ROXA], [SAMAMB, FLOR], [ARBUSTO], [FLOR_ROXA, FLOR]],
        "colina": [[SAMAMB], [ARBUSTO, SAMAMB], [FLOR], [ARBUSTO]],
        "planicie": [[ARBUSTO, ARBUSTO], [FLOR], [SAMAMB, FLOR, VAZIO, FLOR_ROXA], [FOLHAGEM, ARBUSTO], [SAMAMB]],
        "guardia": [[SAMAMB], [COGU], [ARBUSTO], [PEDRA, SAMAMB]],
        "baixada": [[FOLHAGEM, ARBUSTO], [SAMAMB, SAMAMB], [FLOR_ROXA], [ARBUSTO, VAZIO, FLOR],
                    [FOLHAGEM, FOLHAGEM, ARBUSTO], [SAMAMB, COGU]],
        "final": [[FLOR_ROXA], [SAMAMB, FLOR_ROXA], [ARBUSTO], [FUNGO], [FLOR, VAZIO, SAMAMB]],
    }
    for z0, z1, dens, nome in ZONAS:
        c = z0
        while c <= z1:
            r = alt[c] - 1
            mancha = ruido(c, 0, 21, 9.0) * dens
            if mancha > 0.16:
                opcoes = VINHETAS[nome]
                vinheta = opcoes[int(acaso(c, r, 31) * len(opcoes)) % len(opcoes)]
                fim = c + len(vinheta) - 1
                if fim <= z1 and all(alt[x] == alt[c] for x in range(c, fim + 1)):
                    if comp.grupo_chao(c, r, vinheta):
                        c = fim + 2 + int(acaso(c, 7, 41) * 5)
                        continue
            c += 1
    return comp.d


def estruturas_floresta(alt):
    out = []
    for img, col in ARVORES:
        tc = col + 1
        assert len({alt[x] for x in range(tc - 2, tc + 3)}) == 1, ("arvore em desnivel", img, col)
        out.append({"imagem": img, "coluna": col, "base": alt[tc] + 1})
    out.append({"imagem": "isa_v06_arvore_guardia_visivel.png", "coluna": 190, "base": alt[190] + 1})
    out.append({"imagem": "isa_v06_arvore_mae_visivel.png", "coluna": 353, "base": alt[353]})
    return out
