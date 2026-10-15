"""CAVERNA — 251 x 44 (fase 2).

Piso e teto são dois perfis desenhados à mão; tudo entre eles é ar, o resto é
rocha. Seções:
    0-24    Galeria de entrada   chegada (40), teto médio, primeiros cristais
   25-57    Corredor descendente aranha no teto baixo, 1ª cobra num patamar largo
   58-99    Câmara principal     teto alto, rocha pendente, andaimes de mina
                                 em escada (61) com minérios e aranha
  100-124   Passagem espremida   piso subindo, teto baixo constante (3 tiles)
  125-159   Galeria dos cristais teto alto, veios de cristal (26), tucano
  160-199   Salão de combate     piso largo e plano, 2 cobras, andaimes laterais
  200-217   Corredor fundo       poça d'água, musgo e cogumelos
  218-250   Câmara de saída      subida final até a saída (32), tochas
"""
from kit import Grade, Compositor, perfil, checar_perfil, ruido, acaso, VAZIO

L, C = 44, 251
ROCHA, ROCHA_VAR, ROCHA_CRISTAL, VIGA = 24, 25, 26, 61
MINERIO, COBRA, TUCANO, ARANHA = 91, 92, 93, 94
P_SAIDA, CH_ENTRADA = 32, 40
CRIST_AZUL, CRIST_ROXO, TOCHA, COGU, ESTALACT, ARBUSTO, AGUA, FUNGO = 102, 103, 104, 110, 111, 112, 115, 119

PISO = [
    (0, 30), (16, 29), (21, 30), (25, 31), (28, 32), (33, 33), (38, 32),
    (42, 33), (53, 34), (56, 35),                                   # patamar da cobra 42-52
    (58, 35), (64, 36), (72, 35), (76, 34), (80, 35), (86, 36), (94, 35), (98, 34),
    (104, 33), (108, 32), (113, 31), (118, 30),                     # espremida
    (125, 30), (129, 31), (134, 32), (140, 31), (146, 30), (155, 31), (160, 32),
    (164, 33), (197, 34), (200, 34), (203, 35), (212, 34), (215, 33),
    (218, 32), (222, 31), (226, 30), (232, 29), (245, 30),
]
TETO = [  # linha da ÚLTIMA rocha do teto (ar começa na linha seguinte)
    (0, 21), (4, 20), (9, 22), (13, 21), (17, 23), (21, 24),
    (25, 26), (29, 27), (34, 27), (38, 28), (47, 27), (52, 26), (56, 24),
    (58, 22), (61, 20), (66, 19), (72, 21), (76, 26), (80, 20), (86, 19), (92, 21), (97, 24),
    (100, 30), (104, 29), (108, 28), (113, 27), (118, 26), (122, 24),
    (125, 21), (129, 19), (134, 18), (139, 19), (150, 20), (155, 21), (158, 23),
    (160, 24), (164, 22), (170, 21), (178, 20), (186, 21), (194, 22), (198, 25),
    (200, 28), (205, 29), (212, 29), (216, 28),
    (218, 26), (222, 25), (227, 24), (232, 22), (240, 21), (246, 23),
]
POCA = (203, 211)

# Andaimes de mina: (c0, c1, linha)
VIGAS = [(66, 71, 34), (74, 79, 32), (82, 86, 30), (169, 174, 31), (186, 191, 31)]


def construir():
    piso, teto = perfil(PISO, C), perfil(TETO, C)
    checar_perfil(piso, 2, "caverna piso")
    for c in range(C):
        assert piso[c] - teto[c] - 1 >= 3, ("pouco espaco", c, teto[c], piso[c])
    t = Grade(L, C, ROCHA)

    # teto irregular: algumas colunas sobem 1 linha (nunca descem: não rouba altura)
    teto_v = [teto[c] - (1 if ruido(c, 0, 61, 2.5) > 0.62 else 0) for c in range(C)]
    for c in range(C):
        for r in range(teto_v[c] + 1, piso[c]):
            t.set(c, r, VAZIO)

    def perto_do_ar(c, r, d=2):
        return any(t.get(c + dx, r + dy, ROCHA) == VAZIO
                   for dx in range(-d, d + 1) for dy in range(-d, d + 1))

    for r in range(L):
        for c in range(C):
            if t.g[r][c] != ROCHA:
                continue
            if ruido(c, r, 5, 4.5) > 0.63:
                t.g[r][c] = ROCHA_VAR
            galeria = 122 <= c <= 162
            if perto_do_ar(c, r) and ruido(c, r, 9, 2.2) > (0.70 if galeria else 0.90):
                t.g[r][c] = ROCHA_CRISTAL

    for c0, c1, r in VIGAS:
        for c in range(c0, c1 + 1):
            assert t.g[r][c] == VAZIO, ("viga em rocha", c, r)
            t.set(c, r, VIGA)

    def chao(c, v):
        t.set(c, piso[c] - 1, v)

    chao(7, CH_ENTRADA)
    chao(238, P_SAIDA)
    for c in (47, 90, 178, 195):
        chao(c, COBRA)
    t.set(147, 26, TUCANO)
    t.set(31, teto_v[31] + 1, ARANHA)
    t.set(77, teto_v[77] + 1, ARANHA)
    t.set(229, teto_v[229] + 1, ARANHA)
    for c in (13, 20, 27, 36, 41, 51, 60, 96, 103, 110, 116, 122, 128, 134, 139,
              144, 152, 158, 166, 181, 198, 201, 216, 222, 233):
        chao(c, MINERIO)
    for c, r in [(68, 34), (77, 32), (84, 30), (171, 31), (189, 31)]:
        t.set(c, r - 1, MINERIO)

    return t, decorar(t, piso, teto), estruturas(piso)


def decorar(t, piso, teto):
    import constants
    comp = Compositor(t, constants.SOLID_TILES, constants.TILES_MARCADORES)
    comp.reservar(236, 240, 27, 28)            # boca da saída
    comp.reservar(5, 9, 28, 29)                # chegada
    for r in range(L):
        for c in range(C):
            v = t.g[r][c]
            if v == MINERIO:
                comp.reservar(c - 1, c + 1, r, r)
            elif v == ARANHA:
                comp.reservar(c - 1, c + 1, r, r + 1)   # fio da aranha livre

    # Tochas: marcam o trecho "trabalhado" (andaimes) e a saída.
    comp.grupo_chao(235, piso[235] - 1, [TOCHA])
    comp.grupo_chao(241, piso[241] - 1, [TOCHA])
    for c0, c1, r in VIGAS:
        for c in (c0 - 1, c1 + 1):
            if piso[c] - 1 > r:
                comp.grupo_chao(c, piso[c] - 1, [TOCHA])
                break

    # Poça no corredor fundo, com musgo e fungos na margem.
    for c in range(POCA[0], POCA[1] + 1):
        if piso[c] == 35:
            comp.por(c, 34, AGUA)
    comp.grupo_chao(POCA[0] - 2, piso[POCA[0] - 2] - 1, [ARBUSTO, COGU])
    comp.grupo_chao(213, piso[213] - 1, [FUNGO, COGU])

    # Estalactites: em grupos onde o teto forma bolsões, nunca contínuas.
    seguidas = 0
    ultimo = None
    for c, r in comp.tetos():
        if r < 15 or r > 33 or t.get(c, r - 1) == VIGA:
            continue                      # nada pendurado sob madeira
        junto = ultimo == (c - 1, r)
        seguidas = seguidas + 1 if junto else 0
        if seguidas >= 2:                 # no máximo 2 lado a lado
            ultimo = None
            continue
        if ruido(c, 0, 51, 5.0) > 0.52 and acaso(c, r, 52) > 0.40 and comp.por(c, r, ESTALACT):
            ultimo = (c, r)
        else:
            ultimo, seguidas = None, 0

    # Piso: cristais perto dos veios; cogumelos/musgo nas partes úmidas.
    for c in range(1, C - 1):
        r = piso[c] - 1
        if not comp.apoio(c, r):
            continue
        veio = any(t.get(c + dx, piso[c] + dy) == ROCHA_CRISTAL for dx in (-1, 0, 1) for dy in (0, 1))
        umido = 56 <= c <= 99 or 200 <= c <= 217
        galeria = 125 <= c <= 160
        sorte = acaso(c, r, 71)
        mancha = ruido(c, 0, 73, 6.0)
        if (veio and sorte > 0.35) or (galeria and mancha > 0.55 and sorte > 0.55):
            comp.por(c, r, CRIST_AZUL if ruido(c, 3, 77, 4.0) > 0.5 else CRIST_ROXO)
        elif umido and mancha > 0.58 and sorte > 0.5:
            comp.por(c, r, (COGU, ARBUSTO, FUNGO)[int(acaso(c, r, 79) * 3) % 3])
        elif mancha > 0.78 and sorte > 0.7:
            comp.por(c, r, COGU)
    return comp.d


def estruturas(piso):
    """Arcos, colunas e cristais assentados no piso novo (afundados 2 tiles,
    como no original); suportes de mina sob os andaimes (base = piso + 1)."""
    fundo = [("arco_rochoso.png", 8), ("isa_rock_column.png", 17), ("isa_cave_arc_mass.png", 44),
             ("arco_rochoso_alt.png", 63), ("isa_cave_arc_mass.png", 89), ("arco_rochoso.png", 100),
             ("isa_cave_arc_cracked.png", 112), ("isa_rock_column.png", 126),
             ("isa_crystal_cluster_purple.png", 133), ("arco_rochoso_alt.png", 145),
             ("isa_crystal_cluster_blue.png", 153), ("arco_rochoso.png", 165),
             ("isa_rock_column_alt.png", 180), ("isa_cave_arc_cracked.png", 196),
             ("isa_cave_arc_mass.png", 208), ("isa_rock_column_alt.png", 224),
             ("isa_crystal_cluster_blue.png", 243), ("isa_rock_column.png", 248)]
    out = [{"imagem": img, "coluna": col, "base": piso[col] + 2} for img, col in fundo]
    for c0, c1, r in VIGAS:
        meio = (c0 + c1) // 2
        vao = piso[meio] - r - 1
        if vao >= 2:
            out.append({"imagem": f"isa_mine_support_{(vao + 1) * 16}.png",
                        "coluna": meio + 0.5, "base": piso[meio] + 1})
    for c in (31, 229):   # vigas verticais de escoramento perto das aranhas
        out.append({"imagem": "isa_v05_viga_mina_48px.png", "coluna": c - 2.5, "base": piso[c - 3] + 1})
    return out
