"""
gerar_sprites_npc.py — desenha os NPCs do I.S.A. em pixel art.

Cada NPC é montado em resolução NATIVA de 24x36 px (o jogo amplia 2x, sem
suavizar: 48x72 px na tela, um pouco mais alto que a Areninha) a partir de um
corpo-base e de acessórios. Depois de desenhado, recebe um CONTORNO escuro
automático (todo pixel transparente vizinho de um pintado), o mesmo
acabamento dos sprites de inimigos e da Areninha.

Quadros gravados em assets/images/npcs/:
    npc_<id>_0.png   parado
    npc_<id>_1.png   respirando (tronco e cabeça 1 px abaixo)
    npc_<id>_2.png   piscando

O NPC é desenhado olhando para a DIREITA; o jogo espelha quando precisa.

uso:  python ferramentas/gerar_sprites_npc.py [--previa saida.png]
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

L, A = 24, 36
CONTORNO = (28, 20, 24)

# ── paletas (claro, sombra) ───────────────────────────────────────────────────
PELE = {
    "clara": ((240, 196, 160), (206, 152, 118)),
    "media": ((205, 146, 100), (168, 110, 72)),
    "morena": ((150, 96, 62), (112, 68, 42)),
    "escura": ((112, 70, 46), (82, 50, 32)),
}


def ret(s, cor, x, y, w, h):
    pygame.draw.rect(s, cor, (x, y, w, h))


def px(s, cor, x, y):
    if 0 <= x < L and 0 <= y < A:
        s.set_at((x, y), cor)


def contornar(s):
    """Contorno de 1 px em volta de tudo que foi pintado."""
    out = s.copy()
    for y in range(A):
        for x in range(L):
            if s.get_at((x, y)).a:
                continue
            if any(0 <= x + dx < L and 0 <= y + dy < A and s.get_at((x + dx, y + dy)).a
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out.set_at((x, y), CONTORNO)
    return out


# ── corpo-base ────────────────────────────────────────────────────────────────
def corpo(s, p, dy=0, piscar=False):
    """
    p: dict de cores — pele, cabelo, camisa, calca, sapato (cada um (claro, sombra)).
    dy: deslocamento do tronco/cabeça (respiração). As pernas não se mexem.
    """
    pele, pele_s = p["pele"]
    cam, cam_s = p["camisa"]
    cal, cal_s = p["calca"]
    sap, sap_s = p["sapato"]
    cab, cab_s = p["cabelo"]

    # pernas (fixas)
    ret(s, cal, 8, 26, 3, 7); ret(s, cal_s, 10, 26, 1, 7)
    ret(s, cal, 13, 26, 3, 7); ret(s, cal_s, 15, 26, 1, 7)
    ret(s, sap, 8, 33, 4, 2); ret(s, sap_s, 8, 34, 4, 1)
    ret(s, sap, 13, 33, 4, 2); ret(s, sap_s, 13, 34, 4, 1)

    y = dy
    # braço de trás (mais escuro), tronco, braço da frente
    ret(s, cam_s, 6, 17 + y, 2, 8); ret(s, pele_s, 6, 25 + y, 2, 2)
    ret(s, cam, 8, 16 + y, 8, 11); ret(s, cam_s, 14, 16 + y, 2, 11)
    ret(s, cam_s, 8, 25 + y, 8, 2)          # barra da camisa
    ret(s, cam, 16, 17 + y, 2, 8); ret(s, cam_s, 17, 17 + y, 1, 8)
    ret(s, pele, 16, 25 + y, 2, 2); ret(s, pele_s, 17, 26 + y, 1, 1)
    # pescoço e cabeça
    ret(s, pele_s, 10, 14 + y, 4, 2)
    ret(s, pele, 7, 5 + y, 11, 10)
    ret(s, pele, 8, 4 + y, 9, 1)
    ret(s, pele_s, 7, 13 + y, 11, 2)       # queixo/sombra
    px(s, pele, 18, 9 + y); px(s, pele_s, 18, 10 + y)   # nariz
    # cabelo: topo e nuca (o lado direito é o rosto)
    ret(s, cab, 7, 3 + y, 10, 3); ret(s, cab, 6, 5 + y, 3, 7); ret(s, cab_s, 6, 9 + y, 2, 3)
    ret(s, cab_s, 7, 5 + y, 10, 1)
    # olho e boca
    if piscar:
        ret(s, CONTORNO, 14, 9 + y, 2, 1)
    else:
        px(s, (250, 250, 250), 14, 8 + y); px(s, CONTORNO, 15, 8 + y)
        px(s, (250, 250, 250), 14, 9 + y); px(s, CONTORNO, 15, 9 + y)
    ret(s, pele_s, 15, 12 + y, 2, 1)
    return y


# ── NPCs ──────────────────────────────────────────────────────────────────────
def guarda_taina(s, dy, piscar):
    """Guarda-florestal: chapéu de abas largas, camisa oliva, distintivo."""
    p = {"pele": PELE["morena"], "cabelo": ((40, 28, 24), (24, 16, 14)),
         "camisa": ((112, 128, 70), (82, 96, 50)), "calca": ((150, 126, 84), (118, 96, 62)),
         "sapato": ((86, 56, 36), (60, 38, 24))}
    y = corpo(s, p, dy, piscar)
    ret(s, p["cabelo"][0], 4, 9 + y, 3, 9); ret(s, p["cabelo"][1], 4, 14 + y, 2, 4)   # rabo de cavalo
    ret(s, (150, 126, 84), 4, 4 + y, 17, 2); ret(s, (118, 96, 62), 4, 5 + y, 17, 1)   # aba
    ret(s, (164, 140, 96), 8, 0 + y, 9, 4); ret(s, (118, 96, 62), 15, 0 + y, 2, 4)    # copa
    ret(s, (86, 56, 36), 8, 3 + y, 9, 1)                                              # fita
    ret(s, (232, 196, 60), 10, 18 + y, 2, 2); px(s, (255, 236, 140), 10, 18 + y)      # distintivo
    ret(s, (82, 96, 50), 8, 22 + y, 8, 1)                                             # cinto
    px(s, (232, 196, 60), 12, 22 + y)


def seu_benedito(s, dy, piscar):
    """Mineiro veterano: capacete amarelo com lanterna, bigode branco, macacão azul, picareta."""
    p = {"pele": PELE["media"], "cabelo": ((210, 210, 214), (160, 160, 168)),
         "camisa": ((62, 96, 156), (42, 68, 118)), "calca": ((62, 96, 156), (42, 68, 118)),
         "sapato": ((70, 46, 30), (48, 30, 20))}
    y = corpo(s, p, dy, piscar)
    # picareta na mão de trás (cabo diagonal atrás do corpo)
    for i in range(10):
        px(s, (120, 80, 44), 4 + i // 3, 14 + i + y)
    ret(s, (150, 150, 160), 1, 12 + y, 7, 2); ret(s, (110, 110, 122), 1, 13 + y, 7, 1)
    # capacete + lanterna
    ret(s, (238, 196, 40), 7, 1 + y, 10, 4); ret(s, (198, 156, 24), 15, 1 + y, 2, 4)
    ret(s, (238, 196, 40), 6, 4 + y, 13, 1); ret(s, (198, 156, 24), 6, 5 + y, 13, 1)
    ret(s, (90, 90, 100), 15, 1 + y, 4, 4)                                            # aro da lanterna
    ret(s, (255, 244, 170), 16, 2 + y, 2, 2); px(s, (255, 255, 255), 17, 2 + y)
    # bigode e sobrancelha brancos
    ret(s, (230, 230, 234), 14, 11 + y, 4, 1); px(s, (230, 230, 234), 13, 12 + y)
    ret(s, (230, 230, 234), 13, 7 + y, 3, 1)
    # alças do macacão
    ret(s, (42, 68, 118), 9, 16 + y, 1, 5); ret(s, (42, 68, 118), 13, 16 + y, 1, 5)
    ret(s, (232, 196, 60), 9, 20 + y, 1, 1); ret(s, (232, 196, 60), 13, 20 + y, 1, 1)


def engenheira_ana(s, dy, piscar):
    """Engenheira de minas: capacete branco, colete laranja refletivo, prancheta."""
    p = {"pele": PELE["escura"], "cabelo": ((34, 24, 22), (20, 14, 12)),
         "camisa": ((70, 110, 170), (50, 82, 132)), "calca": ((58, 62, 78), (40, 44, 56)),
         "sapato": ((60, 50, 44), (40, 32, 28))}
    y = corpo(s, p, dy, piscar)
    ret(s, p["cabelo"][0], 5, 6 + y, 3, 8); ret(s, p["cabelo"][1], 5, 11 + y, 2, 3)   # cabelo volumoso
    # capacete branco
    ret(s, (236, 236, 236), 7, 1 + y, 10, 4); ret(s, (196, 196, 204), 15, 1 + y, 2, 4)
    ret(s, (236, 236, 236), 6, 4 + y, 13, 1); ret(s, (196, 196, 204), 6, 5 + y, 13, 1)
    # colete laranja com faixas refletivas
    ret(s, (238, 120, 36), 8, 16 + y, 3, 9); ret(s, (238, 120, 36), 13, 16 + y, 3, 9)
    ret(s, (200, 92, 24), 15, 16 + y, 1, 9)
    ret(s, (240, 240, 210), 8, 21 + y, 3, 1); ret(s, (240, 240, 210), 13, 21 + y, 3, 1)
    # prancheta na mão da frente
    ret(s, (130, 90, 50), 17, 20 + y, 4, 6); ret(s, (248, 248, 240), 18, 21 + y, 2, 4)
    ret(s, (160, 160, 170), 18, 22 + y, 2, 1); ret(s, (160, 160, 170), 18, 24 + y, 2, 1)
    ret(s, (200, 200, 210), 18, 19 + y, 2, 1)


def pesquisadora_lia(s, dy, piscar):
    """Pesquisadora (bióloga): bandana verde, roupa cáqui, binóculo, mochila, trança ruiva."""
    p = {"pele": PELE["clara"], "cabelo": ((196, 92, 44), (150, 62, 30)),
         "camisa": ((206, 186, 136), (170, 150, 104)), "calca": ((120, 104, 72), (92, 78, 52)),
         "sapato": ((90, 60, 38), (64, 42, 26))}
    y = corpo(s, p, dy, piscar)
    # mochila nas costas
    ret(s, (130, 86, 48), 3, 16 + y, 4, 9); ret(s, (100, 64, 34), 3, 22 + y, 4, 3)
    ret(s, (100, 64, 34), 5, 16 + y, 1, 9)
    # trança
    ret(s, p["cabelo"][0], 5, 8 + y, 2, 9); px(s, (60, 140, 80), 5, 17 + y); px(s, (60, 140, 80), 6, 17 + y)
    # bandana verde
    ret(s, (60, 140, 80), 7, 3 + y, 10, 2); ret(s, (40, 104, 58), 7, 4 + y, 10, 1)
    ret(s, (60, 140, 80), 5, 4 + y, 2, 2)
    # binóculo no peito
    ret(s, (40, 40, 48), 10, 19 + y, 5, 3); ret(s, (90, 120, 160), 11, 20 + y, 1, 1)
    ret(s, (90, 120, 160), 13, 20 + y, 1, 1); ret(s, (40, 40, 48), 11, 16 + y, 1, 3)
    ret(s, (40, 40, 48), 14, 16 + y, 1, 3)
    # bolsos
    ret(s, (170, 150, 104), 9, 23 + y, 2, 2); ret(s, (170, 150, 104), 13, 23 + y, 2, 2)


NPCS = {
    "taina": guarda_taina,
    "benedito": seu_benedito,
    "ana": engenheira_ana,
    "lia": pesquisadora_lia,
}


def quadros(desenhar):
    out = []
    for dy, piscar in ((0, False), (1, False), (0, True)):
        s = pygame.Surface((L, A), pygame.SRCALPHA)
        desenhar(s, dy, piscar)
        out.append(contornar(s))
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    pygame.init()
    pygame.display.set_mode((1, 1))
    pasta = RAIZ / "assets" / "images" / "npcs"
    pasta.mkdir(parents=True, exist_ok=True)
    todos = {}
    for nome, f in NPCS.items():
        qs = quadros(f)
        todos[nome] = qs
        for i, q in enumerate(qs):
            pygame.image.save(q, str(pasta / f"npc_{nome}_{i}.png"))
    print(f"{len(NPCS)} NPCs x 3 quadros gravados em {pasta}")
    if "--previa" in argv:
        destino = argv[argv.index("--previa") + 1]
        k = 6
        prev = pygame.Surface((len(NPCS) * (L * k + 20) * 2, A * k + 20))
        prev.fill((90, 130, 110))
        x = 10
        for qs in todos.values():
            for q in (qs[0], qs[1]):
                prev.blit(pygame.transform.scale(q, (L * k, A * k)), (x, 10))
                x += L * k + 20
        pygame.image.save(prev, destino)


if __name__ == "__main__":
    main()
