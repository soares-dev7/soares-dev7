"""ARENA v1.1 — 41 x 44. Santuário em ruínas tomado pela floresta.

A geometria da luta NÃO muda: piso na linha 24, plataformas nas mesmas
células (validadas por gerar_mundo.validar_area_boss e teste_boss),
marcadores nas mesmas células. Muda a PELE:

  * tiles: pedra antiga com musgo (IDs 68-71, ferramentas/gerar_arte_arena_ruinas.py)
    no lugar do templo limpo (27-29, 63);
  * estruturas: duas colunas quebradas no lugar das colunas e estandartes
    do santuário; o pórtico da saída fica (marca a saída);
  * decoração MÍNIMA (pedido da equipe: "não precisa de muita decoração"):
    só os dois obeliscos de runas com braseiro, que emolduram e iluminam o
    palco. O musgo fica na própria pedra (tiles e fundo), não em enfeites.
"""
import os
from kit import Grade, Compositor, ler_csv, ruido, VAZIO

TOPO, BLOCO, RACHADO, PLATAFORMA = 68, 69, 70, 71
ANTIGOS_TOPO, ANTIGOS_BLOCO, ANTIGOS_PLAT = {29, 68}, {27, 28, 69, 70}, {63, 71}
TOCHA, RUNAS = 104, 113


def construir():
    # Geometria lida do próprio arena.csv do jogo (aceita os IDs antigos e os
    # novos), então rodar de novo dá o mesmo resultado.
    base = ler_csv(os.path.join(os.environ["ISA_JOGO"], "assets", "levels", "setores", "arena.csv"))
    L, C = len(base), len(base[0])
    t = Grade(L, C)
    for r in range(L):
        for c in range(C):
            v = base[r][c]
            if v in ANTIGOS_TOPO:
                v = TOPO
            elif v in ANTIGOS_BLOCO:
                v = RACHADO if ruido(c, r, 81, 2.6) > 0.70 else BLOCO
            elif v in ANTIGOS_PLAT:
                v = PLATAFORMA
            t.g[r][c] = v
    return t, decorar(t), estruturas()


def decorar(t):
    import constants
    comp = Compositor(t, constants.SOLID_TILES, constants.TILES_MARCADORES)
    comp.reservar(0, 2, 22, 23)            # saída
    comp.reservar(4, 6, 22, 23)            # chegada
    comp.reservar(16, 32, 10, 23)          # palco da luta: limpo
    comp.reservar(5, 7, 20, 20)            # maçãs das plataformas
    comp.reservar(35, 37, 20, 20)

    # Obeliscos de runas (ruínas do santuário) com braseiro no topo: as únicas
    # luzes quentes da arena, emoldurando o palco.
    for c in (14, 34):
        for i in range(3):
            comp.por(c, 23 - i, RUNAS)
        comp.por(c, 20, TOCHA)
    return comp.d


def estruturas():
    """Duas colunas quebradas no fundo; o pórtico continua marcando a saída."""
    return [
        {"imagem": "isa_ruina_coluna_alta.png", "coluna": 11.5, "base": 24.15},
        {"imagem": "isa_ruina_coluna_quebrada.png", "coluna": 39.5, "base": 24.15},
        {"imagem": "isa_arena_portico_retorno.png", "coluna": 5, "base": 25},
    ]
