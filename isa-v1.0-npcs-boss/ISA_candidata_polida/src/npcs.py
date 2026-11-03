"""
NPCs: personagens que conversam com a Areninha.

Os dados (posição, falas, recompensa) vêm de assets/levels/npcs.json — a
equipe edita as falas sem tocar em código. A arte vem de assets/images/npcs/
(pixel art gerada por ferramentas/gerar_sprites_npc.py) ou de uma imagem já
existente em assets/images/personagens/.

Papel no jogo:
  * GUIA       — explicam mecânicas e apontam caminhos;
  * NARRATIVA  — ligam a fase à história das cutscenes (a fábrica sem
                 minério); as falas mudam com o progresso;
  * RECOMPENSA — alguns entregam uma maçã (cura) uma vez por partida, quando
                 o jogador já coletou minérios suficientes no setor.

NPC não tem colisão, não é inimigo e não abre pergunta. O jogador conversa
apertando E (ou X no controle) perto dele; a conversa não pausa o jogo e se
fecha sozinha se ele se afastar. Uma passagem ao alcance tem prioridade
sobre a conversa (os NPCs são posicionados longe delas — ver validar_npcs).
"""
import json

import pygame

import constants
from utils import ASSETS_PATH, carregar_imagem

ESCALA_NPC = 2                 # 24x36 nativo -> 48x72 na tela (SCALE 3)
ALTURA_ARTE_EXISTENTE = 72     # px na tela para artes de personagens/
ALCANCE_X_TILES = 1.6          # distância horizontal para conversar
AFASTAR_TILES = 4.0            # longe disso a conversa fecha
QUADRO_MS = 650                # respiração
PISCAR_CADA_MS = 3200
PISCAR_DURA_MS = 140

_cache_frames = {}


def _carregar_frames(sprite):
    if sprite in _cache_frames:
        return _cache_frames[sprite]
    frames = []
    if sprite.startswith("personagens:"):
        arquivo = sprite.split(":", 1)[1]
        img = carregar_imagem("personagens", arquivo)
        rects = pygame.mask.from_surface(img).get_bounding_rects()
        if rects:
            img = img.subsurface(rects[0].unionall(rects[1:])).copy()
        h = ALTURA_ARTE_EXISTENTE
        w = max(1, round(img.get_width() * h / img.get_height()))
        img = pygame.transform.smoothscale(img, (w, h))
        frames = [img, img, img]
    else:
        for i in range(3):
            img = carregar_imagem("npcs", f"npc_{sprite}_{i}.png")
            frames.append(pygame.transform.scale(
                img, (img.get_width() * ESCALA_NPC, img.get_height() * ESCALA_NPC)))
    _cache_frames[sprite] = frames
    return frames


def _condicoes_ok(bloco, ctx):
    if ctx["coletados_setor"] < bloco.get("min_coletados_setor", 0):
        return False
    if "max_coletados_setor" in bloco and ctx["coletados_setor"] > bloco["max_coletados_setor"]:
        return False
    if ctx["coletados_total"] < bloco.get("min_coletados_total", 0):
        return False
    if "max_coletados_total" in bloco and ctx["coletados_total"] > bloco["max_coletados_total"]:
        return False
    if "visitou" in bloco and bloco["visitou"] not in ctx.get("visitados", ()):
        return False
    return True


class NPC:
    def __init__(self, dados):
        self.id = dados["id"]
        self.nome = dados["nome"]
        self.coluna = dados["coluna"]
        self.base = dados["base"]
        self.falas = dados["falas"]
        self.recompensa = dados.get("recompensa")
        self.recompensa_entregue = False
        self.frames = _carregar_frames(dados["sprite"])
        self.frames_esq = [pygame.transform.flip(f, True, False) for f in self.frames]
        T = constants.TILE_SIZE
        self.rect = self.frames[0].get_rect(midbottom=(self.coluna * T + T // 2, self.base * T))
        self.olhando_esquerda = False
        self._ultimo_bloco_visto = None
        self._fase_anim = (self.coluna * 137) % QUADRO_MS   # NPCs não respiram em sincronia

    # ── conteúdo ─────────────────────────────────────────────────────────
    def _bloco(self, ctx):
        for i, bloco in enumerate(self.falas):
            if _condicoes_ok(bloco, ctx):
                return i, bloco
        return None, None

    def recompensa_pronta(self, ctx):
        return (self.recompensa is not None and not self.recompensa_entregue
                and _condicoes_ok(self.recompensa, ctx))

    def tem_novidade(self, ctx):
        """Algo que o jogador ainda não ouviu (mostra o '!' sobre a cabeça)."""
        i, _ = self._bloco(ctx)
        return i != self._ultimo_bloco_visto or self.recompensa_pronta(ctx)

    def conversar(self, ctx):
        """
        Linhas desta conversa. Se a recompensa estiver pronta, ela é marcada
        como entregue e as falas dela vêm primeiro; devolve (linhas, item|None).
        """
        i, bloco = self._bloco(ctx)
        self._ultimo_bloco_visto = i
        linhas = []
        item = None
        if self.recompensa_pronta(ctx):
            self.recompensa_entregue = True
            item = self.recompensa.get("item")
            linhas += self.recompensa.get("linhas", [])
        if bloco:
            linhas += bloco["linhas"]
        return [l.format(**ctx) for l in linhas], item

    # ── jogo ─────────────────────────────────────────────────────────────
    def perto(self, rect_player, alcance_tiles=ALCANCE_X_TILES):
        T = constants.TILE_SIZE
        return (abs(rect_player.centerx - self.rect.centerx) <= alcance_tiles * T
                and abs(rect_player.bottom - self.rect.bottom) <= 1.5 * T)

    def olhar_para(self, rect_player):
        if abs(rect_player.centerx - self.rect.centerx) <= 6 * constants.TILE_SIZE:
            self.olhando_esquerda = rect_player.centerx < self.rect.centerx

    def ponto_de_entrega(self, world):
        """Célula (coluna, linha_do_apoio) ao lado do NPC onde a maçã cai."""
        T = constants.TILE_SIZE
        for dc in ((-1, 1) if self.olhando_esquerda else (1, -1)) + (-2, 2):
            c = self.coluna + dc
            if 0 <= c < world.colunas and world._solidos[self.base][c] is not None \
                    and world._solidos[self.base - 1][c] is None:
                return c, self.base
        return self.coluna, self.base

    def desenhar(self, surface, camera_x, camera_y, agora, novidade=False, falando=False):
        frames = self.frames_esq if self.olhando_esquerda else self.frames
        t = agora + self._fase_anim
        quadro = 1 if (t // QUADRO_MS) % 2 else 0
        if t % PISCAR_CADA_MS < PISCAR_DURA_MS:
            quadro = 2
        img = frames[quadro]
        pos = self.rect.move(-camera_x, -camera_y)
        surface.blit(img, pos)
        if falando or novidade:
            _balao(surface, pos.centerx, pos.top - 6, "..." if falando else "!", agora)


def _balao(surface, cx, base_y, simbolo, agora):
    """Balãozinho em pixel art sobre a cabeça: '!' (novidade) ou '...' (falando)."""
    s = 3
    sobe = 2 if (agora // 300) % 2 and simbolo == "!" else 0
    w, h = (7 * s, 8 * s) if simbolo == "!" else (11 * s, 7 * s)
    x, y = cx - w // 2, base_y - h - sobe
    pygame.draw.rect(surface, (28, 20, 24), (x - s, y - s, w + 2 * s, h + 2 * s))
    pygame.draw.rect(surface, (250, 246, 230), (x, y, w, h))
    pygame.draw.polygon(surface, (28, 20, 24), [(cx - 2 * s, y + h), (cx + 2 * s, y + h), (cx, y + h + 3 * s)])
    pygame.draw.polygon(surface, (250, 246, 230), [(cx - s, y + h), (cx + s, y + h), (cx, y + h + 2 * s)])
    cor = (220, 60, 40)
    if simbolo == "!":
        pygame.draw.rect(surface, cor, (cx - s // 2 - 1, y + s, s + 1, 4 * s))
        pygame.draw.rect(surface, cor, (cx - s // 2 - 1, y + 6 * s, s + 1, s))
    else:
        for i in range(3):
            pygame.draw.rect(surface, (60, 60, 70), (x + 2 * s + i * 3 * s, y + 3 * s, s, s))


class GerenciadorNPCs:
    """Os NPCs de um setor. Estado (recompensa entregue) dura a partida."""

    def __init__(self, nome_setor, caminho=None):
        caminho = caminho or (ASSETS_PATH / "levels" / "npcs.json")
        self.itens = []
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"Aviso: NPCs nao carregados ({e})")
            return
        for d in dados.get(nome_setor, []):
            try:
                self.itens.append(NPC(d))
            except (KeyError, FileNotFoundError, pygame.error) as e:
                print(f"Aviso: NPC {d.get('id', '?')} ignorado ({e})")

    def __len__(self):
        return len(self.itens)

    def ao_alcance(self, rect_player):
        perto = [n for n in self.itens if n.perto(rect_player)]
        return min(perto, key=lambda n: abs(n.rect.centerx - rect_player.centerx)) if perto else None

    def atualizar(self, rect_player):
        for n in self.itens:
            n.olhar_para(rect_player)

    def desenhar(self, surface, camera_x, camera_y, area, ctx, falando_com=None):
        agora = pygame.time.get_ticks()
        for n in self.itens:
            if area.colliderect(n.rect):
                n.desenhar(surface, camera_x, camera_y, agora,
                           novidade=n.tem_novidade(ctx), falando=n is falando_com)


def validar_npcs(nome_setor, grade, npcs):
    """
    Regras de posicionamento (usadas pelos testes):
      * pisa num bloco sólido e tem 2 células livres acima;
      * a >= 4 colunas de passagens e chegadas (a passagem tem prioridade na tecla E);
      * a >= 2 colunas de minérios e inimigos de chão no mesmo nível.
    Devolve lista de problemas (vazia = ok).
    """
    S = constants.SOLID_TILES
    problemas = []
    marcas = [(c, r, v) for r, linha in enumerate(grade) for c, v in enumerate(linha)
              if v in constants.TILES_MARCADORES]
    for n in npcs:
        c, b = n.coluna, n.base
        if not (0 < b < len(grade) and 0 <= c < len(grade[0])) or grade[b][c] not in S:
            problemas.append(f"{nome_setor}/{n.id}: sem chao em (col {c}, linha {b})")
            continue
        if any(grade[b - k][c] in S for k in (1, 2)):
            problemas.append(f"{nome_setor}/{n.id}: sem espaco livre acima")
        for mc, mr, v in marcas:
            if abs(mr - (b - 1)) > 3:
                continue
            d = abs(mc - c)
            if (v in constants.TILES_PASSAGEM or v in constants.TILES_CHEGADA) and d < 4:
                problemas.append(f"{nome_setor}/{n.id}: a {d} col da passagem/chegada {v}")
            elif v in (constants.TILE_MINERIO, constants.TILE_MOB_COBRA) and d < 2:
                problemas.append(f"{nome_setor}/{n.id}: colado no marcador {v} (col {mc})")
    return problemas
