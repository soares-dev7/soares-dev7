"""COPAS — 131 x 44 (fase 3). Percurso aéreo entre as árvores.

Antes: troncos sólidos em escada diagonal (|!||||!) do chão do mapa até cada
plataforma — liam como rampas de tijolo, não como árvores. Agora as árvores
são a ARTE (estruturas_cenario.json, que fica onde estava) e a geometria
física são decks e galhos finos que cruzam essa arte na altura certa:

     0-16   deck de chegada (34) sob o pórtico, cruzando o tronco de fundo (col 10)
    17-28   dois galhos subindo, apoiados num ramo conector diagonal
    29-43   deck da Árvore Ancestral (29), na bifurcação; galho alto na copa (27)
    45-66   galho com conector -> deck do ninho (26), minério dentro do ninho
    68-84   subida com conector até o tronco de fundo da col 83
    86-97   deck da Árvore Espiral (20); tucano na copa
    99-130  último galho e deck final (17) com a chegada (45) e o portal da arena (34)
"""
from kit import Grade, Compositor, ruido, acaso, VAZIO

L, C = 44, 131
COPA, COPA_VAR, GALHO = 14, 15, 62
MINERIO, COBRA, TUCANO = 91, 92, 93
P_FLORESTA, P_ARENA, CH_COPAS, CH_ARENA = 33, 34, 41, 45
FLOR, SAMAMB, CIPO, LANTERNA, ARBUSTO, PLACA, LIANA, RAMOS, FOLHAGEM = 100, 101, 105, 109, 112, 114, 118, 120, 123

# (c0, c1, linha, tipo) — "deck" = tábua com folhagem (14/15), "galho" = 62
PLATAFORMAS = [
    (0, 16, 34, "deck"),
    (17, 21, 32, "galho"), (23, 27, 30, "galho"),
    (29, 43, 29, "deck"), (32, 38, 27, "galho"),          # copa da ancestral
    (45, 51, 27, "galho"),
    (53, 66, 26, "deck"),                                 # ninho pousado no deck
    (68, 73, 24, "galho"), (75, 84, 22, "galho"),
    (86, 97, 20, "deck"),                                 # árvore espiral
    (99, 104, 19, "galho"),
    (106, 130, 17, "deck"), (112, 117, 15, "galho"),      # deck final
]


def construir():
    t = Grade(L, C)
    for c0, c1, r, tipo in PLATAFORMAS:
        for c in range(c0, c1 + 1):
            assert t.g[r][c] == VAZIO, ("sobreposicao", c, r)
            if tipo == "galho":
                v = GALHO
            else:
                v = COPA_VAR if ruido(c, r, 13, 3.0) > 0.62 else COPA
            t.set(c, r, v)

    def sobre(c, r, v):
        assert t.g[r][c] in (COPA, COPA_VAR, GALHO), ("sem apoio", c, r)
        t.set(c, r - 1, v)

    sobre(5, 34, CH_COPAS)
    sobre(11, 34, P_FLORESTA)
    sobre(118, 17, CH_ARENA)
    sobre(126, 17, P_ARENA)
    sobre(40, 29, COBRA)
    sobre(57, 26, COBRA)
    t.set(91, 17, TUCANO)
    for c, r in [(15, 34), (19, 32), (25, 30), (31, 29), (42, 29), (35, 27), (49, 27),
                 (55, 26), (65, 26), (61, 26), (70, 24), (79, 22), (88, 20), (95, 20),
                 (101, 19), (109, 17), (114, 15), (122, 17)]:
        sobre(c, r, MINERIO)
    return t, decorar(t), estruturas()


def decorar(t):
    import constants
    comp = Compositor(t, constants.SOLID_TILES, constants.TILES_MARCADORES)
    comp.reservar(4, 6, 32, 33)          # chegada 41
    comp.reservar(9, 13, 31, 33)         # descida para a floresta (sob o pórtico)
    comp.reservar(116, 120, 15, 16)      # chegada 45
    comp.reservar(124, 128, 14, 16)      # portal da arena
    comp.reservar(86, 96, 15, 19)        # faixa de voo do tucano: leitura limpa
    for r in range(L):
        for c in range(C):
            if t.g[r][c] == MINERIO:
                comp.reservar(c - 1, c + 1, r, r)

    comp.grupo_chao(8, 33, [PLACA])

    # Vegetação sobre os decks (não sobre galhos finos: ficam limpos para o pulo).
    VINHETAS = [[SAMAMB], [FLOR, SAMAMB], [ARBUSTO], [FOLHAGEM, ARBUSTO], [SAMAMB, VAZIO, FLOR]]
    for c0, c1, r, tipo in PLATAFORMAS:
        if tipo != "deck":
            continue
        c = c0
        while c <= c1:
            if ruido(c, r, 17, 4.0) > 0.50:
                v = VINHETAS[int(acaso(c, r, 19) * len(VINHETAS)) % len(VINHETAS)]
                if c + len(v) - 1 <= c1 and comp.grupo_chao(c, r - 1, v):
                    c += len(v) + 2 + int(acaso(c, r, 23) * 3)
                    continue
            c += 1

    # Pendurados sob decks e galhos: comprimentos variados, espaçados.
    for i, (c0, c1, r, tipo) in enumerate(PLATAFORMAS):
        c = c0 + 1 + int(acaso(c0, r, 29) * 2)
        while c < c1:
            if acaso(c, r, 31) > 0.45:
                tam = 1 + int(acaso(c, r, 37) * 2)
                sorte = acaso(c, r, 41)
                peca = RAMOS if sorte < 0.30 else (CIPO if sorte > 0.85 else LIANA)
                ids = [RAMOS] if peca == RAMOS else [peca] * (1 if peca == CIPO else tam)
                comp.pendurar(c, r + 1, ids)
            c += 3 + int(acaso(c, r, 43) * 4)

    # Lanternas sob o deck final: o caminho para a clareira do Gorila.
    for c in (108, 113, 121):
        comp.d.set(c, 18, VAZIO)
        comp.por(c, 18, LANTERNA)
    return comp.d


def estruturas():
    """Arte mantida no lugar (as árvores ditam a geometria). Conectores e
    toquinhos foram reposicionados para ligar os galhos novos."""
    return [
        {"imagem": "arvore_copas.png", "coluna": 10, "base": 44},
        {"imagem": "arvore_copas_alt.png", "coluna": 33, "base": 44},
        {"imagem": "arvore_copas.png", "coluna": 53, "base": 44},
        {"imagem": "arvore_copas_alt.png", "coluna": 83, "base": 44},
        {"imagem": "arvore_copas.png", "coluna": 116, "base": 44},
        {"imagem": "isa_copas_portico_subida.png", "coluna": 9, "base": 37},
        {"imagem": "isa_copas_arvore_ancestral.png", "coluna": 37, "base": 39},
        {"imagem": "isa_copas_ninho_raizes.png", "coluna": 60, "base": 27},
        {"imagem": "isa_copas_arvore_espiral.png", "coluna": 89, "base": 30},
        {"imagem": "isa_copas_portal_ancestral.png", "coluna": 125, "base": 19},
        {"imagem": "isa_final_ramo_conector_copas_A.png", "coluna": 20, "base": 35},
        {"imagem": "isa_final_ramo_conector_copas_B.png", "coluna": 47.5, "base": 31},
        {"imagem": "isa_final_ramo_conector_copas_A.png", "coluna": 71, "base": 27},
        {"imagem": "isa_final_ramo_conector_copas_B.png", "coluna": 101.5, "base": 24},
        {"imagem": "isa_v05_tronco_copas_16px.png", "coluna": 34.5, "base": 29},
        {"imagem": "isa_v05_tronco_copas_16px.png", "coluna": 114.5, "base": 17},
    ]
