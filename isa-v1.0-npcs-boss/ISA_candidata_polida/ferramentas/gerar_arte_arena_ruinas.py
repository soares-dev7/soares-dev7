"""
gerar_arte_arena_ruinas.py — arte da ARENA EM RUÍNAS (pixel art).

"Ruínas de pedra tomadas pela floresta, clima sombrio": um santuário antigo
onde a mata entrou — colunas quebradas cobertas de musgo, muralha
desmoronando, cipós e copas invadindo pelo alto, noite fria e enevoada com
lua pálida (sem vermelho: paleta de azul-acinzentado e verde-musgo).

Gera (resolução nativa, o jogo amplia sem suavizar):
  assets/images/backgrounds/isa_arena_ruinas_fundo.png   400x200 (x3 = 1200x600, opaco)
  assets/images/backgrounds/isa_arena_ruinas_frente.png  400x200 (transparente, paralaxe)
  assets/images/tiles/isa_ruina_laje_musgo.png           16x16  chão (topo)
  assets/images/tiles/isa_ruina_bloco.png                16x16  preenchimento
  assets/images/tiles/isa_ruina_bloco_rachado.png        16x16  preenchimento (variação)
  assets/images/tiles/isa_ruina_plataforma.png           16x16  plataforma
  assets/images/cenarios/isa_ruina_coluna_alta.png       coluna quebrada alta
  assets/images/cenarios/isa_ruina_coluna_quebrada.png   coluna quebrada baixa
  assets/images/cenarios/isa_ruina_arco.png              arco em ruína

LEGIBILIDADE: o Gorila é quase preto. O fundo tem uma faixa de NÉVOA mais
clara exatamente na altura em que a luta acontece (linhas nativas ~85-150),
e as ruínas próximas ficam em tom médio — nada escuro atrás dos lutadores.
`--medir` imprime o contraste de luminância entre o Gorila e essa faixa.

Tudo é determinístico (ruído por hash): rodar de novo dá os mesmos PNGs.
uso:  python ferramentas/gerar_arte_arena_ruinas.py [--previa saida.png] [--medir]
"""
import math
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

LB, AB = 400, 200          # fundo nativo

# ── paleta ────────────────────────────────────────────────────────────────────
CEU_TOPO = (8, 12, 18)
CEU_MEIO = (20, 30, 40)
HORIZONTE = (58, 76, 84)       # luar frio no horizonte
NEVOA = (98, 112, 116)         # névoa clara atrás dos lutadores
LUA = (226, 214, 196)
MURO_LONGE = (58, 66, 76)
MATA_LONGE = (30, 48, 44)
PEDRA = ((112, 116, 122), (86, 90, 98), (62, 64, 74), (138, 142, 144))  # base, sombra, escura, luz
MUSGO = ((70, 108, 56), (96, 140, 70), (46, 74, 42))
FOLHA = ((26, 54, 38), (40, 78, 50), (18, 38, 28))
CIPO = (52, 96, 50)
CONTORNO = (20, 18, 26)


def h(x, y, s=0):
    v = (x * 374761393 + y * 668265263 + s * 2147483647) & 0xFFFFFFFF
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((v ^ (v >> 16)) & 0xFFFF) / 65535.0


def ruido1(x, s=0, esc=8.0):
    x0 = math.floor(x / esc)
    t = x / esc - x0
    t = t * t * (3 - 2 * t)
    return h(x0, 0, s) * (1 - t) + h(x0 + 1, 0, s) * t


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def px(s, x, y, c):
    w, hh = s.get_size()
    if 0 <= y < hh:
        s.set_at((x % w, y), c)   # x embrulha: camadas emendam sem costura


def ret(s, x, y, w, hh, c):
    for yy in range(y, y + hh):
        for xx in range(x, x + w):
            px(s, xx, yy, c)


# ── fundo (camada 0, opaca) ───────────────────────────────────────────────────
def fundo():
    s = pygame.Surface((LB, AB))
    for y in range(AB):
        if y < 70:
            c = mix(CEU_TOPO, CEU_MEIO, y / 70)
        elif y < 118:
            c = mix(CEU_MEIO, HORIZONTE, (y - 70) / 48)
        else:
            c = mix(HORIZONTE, NEVOA, (y - 118) / 22)
        for x in range(LB):
            s.set_at((x, y), c)
    # lua com halo
    cx, cy, r = 292, 42, 13
    for y in range(cy - 30, cy + 31):
        for x in range(cx - 30, cx + 31):
            d = math.hypot(x - cx, y - cy)
            if d <= r:
                c = LUA if h(x, y, 3) > 0.12 or d < r - 3 else (196, 186, 170)
                px(s, x, y, c)
            elif d < 30:
                px(s, x, y, mix(s.get_at((x, y))[:3], (96, 112, 120), 0.35 * (1 - (d - r) / (30 - r))))
    # faixas de nuvem escura (embrulham)
    for banda, (y0, esp) in enumerate(((30, 4), (48, 3), (62, 5), (86, 3))):
        for x in range(LB):
            alt = int(esp * ruido1(x, 10 + banda, 22))
            if ruido1(x, 20 + banda, 40) > 0.45:
                for y in range(y0, y0 + alt):
                    px(s, x, y, mix(s.get_at((x % LB, y))[:3], (12, 18, 24), 0.7))
    # muralha distante com torres quebradas (silhueta enevoada)
    for x in range(LB):
        seg = x // 14                           # trechos retos de muralha
        topo = 114 + int(4 * h(seg, 0, 30))
        torre = h(x // 26, 0, 31) > 0.66 and (x % 26) < 16
        if torre:
            topo = 82 + int(18 * h(x // 26, 1, 33))
            if (x % 26) > 10 and h(x // 26, 2, 34) > 0.5:
                topo += 3 + (x % 26 - 10) * 2   # canto desmoronado
            elif (x % 4) < 2:
                topo -= 2                       # ameias da torre
        elif (x // 4) % 2 == 0:
            topo -= 2                           # ameias
        for y in range(topo, 150):
            c = mix(MURO_LONGE, NEVOA, (y - topo) / 60 + 0.1)
            if torre and 92 < y < 100 and (x % 26) in (6, 7):
                c = mix(HORIZONTE, LUA, 0.2)    # janelas com o céu atrás
            px(s, x, y, c)
    # mata distante na frente da muralha
    for x in range(LB):
        topo = 128 + int(10 * ruido1(x, 40, 9)) + int(4 * ruido1(x, 41, 3))
        for y in range(topo, AB):
            px(s, x, y, mix(MATA_LONGE, NEVOA, 0.25 + 0.4 * max(0, (y - topo)) / 40))
    # névoa: véu claro na faixa da luta
    for y in range(84, 152):
        a = 0.22 * math.sin(math.pi * (y - 84) / 68)
        for x in range(LB):
            px(s, x, y, mix(s.get_at((x, y))[:3], NEVOA, a))
    return s


# ── frente (camada 1, transparente) ───────────────────────────────────────────
def pedra_tex(s, x0, y0, w, hh, seed, enevoar=0.0, tijolo=(8, 5), origem=None):
    """Bloco de pedra com juntas, variação por tijolo, rachaduras e borda.
    `origem`: (x, y) da grade de tijolos — permite pintar coluna a coluna
    mantendo os tijolos alinhados."""
    bw, bh = tijolo
    ox, oy = origem if origem is not None else (x0, y0)
    for y in range(y0, y0 + hh):
        fila = (y - oy) // bh
        off = (bw // 2) * (fila % 2)
        for x in range(x0, x0 + w):
            bx = (x - ox + off) // bw
            junta = (y - oy) % bh == 0 or (x - ox + off) % bw == 0
            var = h(bx, fila, seed)
            c = PEDRA[2] if junta else (PEDRA[1] if var < 0.35 else PEDRA[0])
            if not junta and (y - oy) % bh == 1 and var > 0.5:
                c = PEDRA[3]                    # luz na aresta superior
            if not junta and h(x, y, seed + 5) > 0.985:
                c = PEDRA[2]                    # pontinhos/rachaduras
            px(s, x, y, mix(c, NEVOA, enevoar))


def musgo(s, x0, y0, w, seed, prof=3, enevoar=0.0):
    for x in range(x0, x0 + w):
        n = int(prof * ruido1(x, seed, 3) + 1)
        for k in range(n):
            c = MUSGO[1] if k == 0 else (MUSGO[0] if k < n - 1 else MUSGO[2])
            px(s, x, y0 + k, mix(c, NEVOA, enevoar))
        if h(x, 0, seed + 1) > 0.8:             # gotas de musgo escorrendo
            for k in range(n, n + 2 + int(4 * h(x, 1, seed))):
                px(s, x, y0 + k, mix(MUSGO[2], NEVOA, enevoar))


def cipo(s, x, y0, comp, seed, enevoar=0.0):
    for k in range(comp):
        xx = x + int(1.5 * math.sin((k + seed) / 4))
        px(s, xx, y0 + k, mix(CIPO, NEVOA, enevoar))
        if k % 5 == 2:
            px(s, xx + 1, y0 + k, mix(MUSGO[1], NEVOA, enevoar))
            px(s, xx - 1, y0 + k + 1, mix(MUSGO[0], NEVOA, enevoar))


def coluna_quebrada(s, x, base, larg, alt, seed, enevoar=0.0):
    topo = base - alt
    # base e capitel tombado
    ret(s, x - 2, base - 6, larg + 4, 6, mix(PEDRA[1], NEVOA, enevoar))
    ret(s, x - 2, base - 6, larg + 4, 1, mix(PEDRA[3], NEVOA, enevoar))
    for xx in range(x, x + larg):
        quebra = topo + int(7 * h(xx // 2, 0, seed))          # topo irregular
        for y in range(quebra, base - 6):
            lado = (xx - x) / max(1, larg - 1)
            c = PEDRA[3] if lado < 0.18 else (PEDRA[1] if lado > 0.72 else PEDRA[0])
            if (base - 6 - y) % 14 == 0:
                c = PEDRA[2]                                   # tambores da coluna
            elif (base - 6 - y) % 14 == 1 and lado < 0.72:
                c = PEDRA[3]
            if h(xx // 2, y // 3, seed + 9) > 0.985:
                c = PEDRA[1]                                   # manchas de desgaste
            px(s, xx, y, mix(c, NEVOA, enevoar))
        musgo(s, xx, quebra, 1, seed + 2, prof=3, enevoar=enevoar)
    # rachadura diagonal
    cx = x + larg // 2
    for k in range(alt // 2):
        px(s, cx + int(2 * math.sin(k / 3)), topo + 10 + k, mix(PEDRA[2], NEVOA, enevoar))
    # cipós descendo
    for i in range(2):
        cipo(s, x + 2 + i * (larg - 4), topo + 4, alt // 2 + int(10 * h(i, 3, seed)), seed + i, enevoar)


def frente():
    s = pygame.Surface((LB, AB), pygame.SRCALPHA)
    nev = 0.28
    # muro baixo desmoronando ao longo da base (embrulha)
    for x in range(LB):
        topo = 132 + int(8 * ruido1(x, 50, 11)) + (4 if h(x // 6, 0, 51) > 0.8 else 0)
        pedra_tex(s, x, topo, 1, AB - topo, 52, nev, origem=(0, 120))
        musgo(s, x, topo, 1, 53, prof=2, enevoar=nev)
    # colunas quebradas em alturas variadas
    for i, (x, larg, alt) in enumerate(((18, 18, 88), (112, 16, 58), (196, 20, 104), (300, 16, 70), (366, 18, 46))):
        coluna_quebrada(s, x, 140, larg, alt, 60 + i, nev)
    # copa invadindo pelo alto: folhagem pendente + cipós
    for x in range(LB):
        fundo_folha = 10 + int(14 * ruido1(x, 70, 7)) + int(6 * ruido1(x, 71, 2.5))
        for y in range(0, fundo_folha):
            c = FOLHA[1] if h(x, y, 72) > 0.7 else (FOLHA[0] if y < fundo_folha - 2 else FOLHA[2])
            px(s, x, y, c)
        if h(x, 0, 73) > 0.94:
            cipo(s, x, fundo_folha - 1, 20 + int(40 * h(x, 1, 74)), x, 0.1)
    return s


# ── tiles 16x16 ───────────────────────────────────────────────────────────────
def tile_bloco(rachado=False, seed=0):
    s = pygame.Surface((16, 16))
    pedra_tex(s, 0, 0, 16, 16, 80 + seed, 0.18, tijolo=(8, 8))
    # mais escuro que a laje do topo: o piso jogável se destaca da massa abaixo
    for y in range(16):
        for x in range(16):
            c = s.get_at((x, y))[:3]
            s.set_at((x, y), (int(c[0] * 0.56), int(c[1] * 0.58), int(c[2] * 0.62)))
    if rachado:
        for k in range(10):
            s.set_at((4 + k // 2 + (k % 3 == 0), 3 + k), (30, 30, 38))
        for x in (10, 11, 12):
            s.set_at((x, 14), MUSGO[2])
        s.set_at((11, 13), MUSGO[0])
    return s


def tile_laje():
    s = pygame.Surface((16, 16))
    pedra_tex(s, 0, 0, 16, 16, 90, 0.1, tijolo=(16, 16))
    for x in range(16):
        s.set_at((x, 15), PEDRA[2])
        s.set_at((x, 4), PEDRA[2])
    s.set_at((7, 9), PEDRA[2]); s.set_at((8, 10), PEDRA[2])
    musgo(s, 0, 0, 16, 91, prof=3)
    return s


def tile_plataforma():
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    pedra_tex(s, 0, 2, 16, 11, 95, 0.1, tijolo=(8, 11))
    for x in range(16):
        s.set_at((x, 12), PEDRA[2])
    musgo(s, 0, 1, 16, 96, prof=2)
    for x in (3, 9, 13):                         # musgo pendurado
        for k in range(13, 13 + 1 + int(2 * h(x, 0, 97))):
            s.set_at((x, k), MUSGO[2])
    return s


# ── estruturas (nativo; o jogo amplia x SCALE) ────────────────────────────────
def estrutura_coluna(larg, alt, seed):
    s = pygame.Surface((larg + 12, alt + 8), pygame.SRCALPHA)
    coluna_quebrada(s, 6, alt + 8, larg, alt, seed, 0.0)
    return _contornar(s)


def estrutura_arco():
    W, H = 240, 176
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    coluna_quebrada(s, 14, H, 26, 150, 201, 0.0)
    coluna_quebrada(s, W - 40, H, 26, 96, 202, 0.0)
    # arco partido: só a metade esquerda sobrevive
    cx, cy, r_ext, r_int = W // 2, 112, 104, 86     # topo do arco em y=8
    for y in range(cy - r_ext, cy + 4):
        for x in range(14, cx + 18):
            d = math.hypot(x - cx, y - cy)
            if r_int <= d <= r_ext and y <= cy:
                ang = math.degrees(math.atan2(cy - y, x - cx))
                if ang < 70 or ang > 182:
                    continue
                lado = (d - r_int) / (r_ext - r_int)
                c = PEDRA[3] if lado > 0.85 else (PEDRA[1] if lado < 0.2 else PEDRA[0])
                if int(ang) % 12 == 0:
                    c = PEDRA[2]                 # aduelas
                px(s, x, y, c)
    # ponta quebrada com musgo e raízes caindo
    for x in range(cx - 6, cx + 18):
        for k in range(3):
            y = cy - r_ext + 2 + k + int(3 * h(x, 0, 205))
            if s.get_at((x, y)).a:
                px(s, x, y, MUSGO[k % 3])
    for i, x in enumerate((44, 70, 96, 118)):
        cipo(s, x, cy - int(math.sqrt(max(0, r_ext ** 2 - (x - cx) ** 2))) + 6, 30 + 12 * i, 210 + i)
    return _contornar(s)


def _contornar(s):
    out = s.copy()
    w, hh = s.get_size()
    for y in range(hh):
        for x in range(w):
            if s.get_at((x, y)).a:
                continue
            if any(0 <= x + dx < w and 0 <= y + dy < hh and s.get_at((x + dx, y + dy)).a
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out.set_at((x, y), CONTORNO)
    return out


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    pygame.init()
    pygame.display.set_mode((1, 1))
    A = RAIZ / "assets" / "images"
    saida = {
        A / "backgrounds" / "isa_arena_ruinas_fundo.png": fundo(),
        A / "backgrounds" / "isa_arena_ruinas_frente.png": frente(),
        A / "tiles" / "isa_ruina_laje_musgo.png": tile_laje(),
        A / "tiles" / "isa_ruina_bloco.png": tile_bloco(False, 0),
        A / "tiles" / "isa_ruina_bloco_rachado.png": tile_bloco(True, 1),
        A / "tiles" / "isa_ruina_plataforma.png": tile_plataforma(),
        A / "cenarios" / "isa_ruina_coluna_alta.png": estrutura_coluna(22, 190, 301),
        A / "cenarios" / "isa_ruina_coluna_quebrada.png": estrutura_coluna(22, 120, 302),
        A / "cenarios" / "isa_ruina_arco.png": estrutura_arco(),
    }
    for caminho, surf in saida.items():
        pygame.image.save(surf, str(caminho))
    print(f"{len(saida)} imagens gravadas")
    if "--medir" in argv:
        f = saida[A / "backgrounds" / "isa_arena_ruinas_fundo.png"]
        faixa = [lum(f.get_at((x, y))) for y in range(90, 148) for x in range(0, LB, 3)]
        g = pygame.image.load(str(A / "inimigos" / "gorila_01.png"))
        pix = [g.get_at((x, y)) for x in range(0, g.get_width(), 2) for y in range(0, g.get_height(), 2)]
        lg = sum(lum(p) for p in pix if p.a > 200) / max(1, sum(1 for p in pix if p.a > 200))
        lf = sum(faixa) / len(faixa)
        print(f"luminancia media: gorila {lg:.0f} | faixa da luta no fundo {lf:.0f} "
              f"(min {min(faixa):.0f}) | diferenca {lf - lg:.0f}")
    if "--previa" in argv:
        destino = argv[argv.index("--previa") + 1]
        prev = pygame.Surface((LB * 2, AB * 2))
        prev.blit(pygame.transform.scale(saida[A / "backgrounds" / "isa_arena_ruinas_fundo.png"], (LB * 2, AB * 2)), (0, 0))
        prev.blit(pygame.transform.scale(saida[A / "backgrounds" / "isa_arena_ruinas_frente.png"], (LB * 2, AB * 2)), (0, 0))
        pygame.image.save(prev, destino)


if __name__ == "__main__":
    main()
