"""
Boss final: o GORILA da arena (setor "arena", no alto da copa).

Origem: protótipo do fork "isa_boss (em andamento)" — sprites, arremesso de
bananas, minério que abre pergunta e é devolvido ao boss, atordoamento e
8 minérios para vencer. Na unificação ele foi:

  * integrado ao sistema de inimigos da v12 (herda Enemy, usa VIDA_MAX /
    receber_dano / derrotado / SEMPRE_ATIVO, é criado pelo setor da arena a
    partir do marcador 95 e atualizado pelo mesmo laço dos outros inimigos);
  * ampliado com aparição, duas fases, salto-pancada com onda de choque,
    animação de derrota e reinício limpo.

COMO A LUTA FUNCIONA (o que o jogador vê)
-----------------------------------------
  APARIÇÃO  — quando o jogador cruza a borda da área de luta, o Gorila ruge
              (GORILA_INTRO_MS) sem atacar; a barra de vida aparece.
  ARREMESSO — pose de aviso (GORILA_POSE_ARREMESSO) e depois o projétil,
              mirado onde o jogador ESTAVA:
                * BANANA: desvie (andar ou pular basta). Dano 10.
                * MINÉRIO (cobre/zinco), 1 por ciclo de 5 arremessos, e a
                  pose mostra o gorila segurando a pedra: deixe ACERTAR.
                  Abre uma pergunta com tempo; acertou -> o minério volta e
                  acerta o boss; errou/tempo esgotado -> dano.
  ATORDOADO — ao levar o minério de volta: GORILA_ATORDOADO_MS sem atacar
              (janela de recuperação; as maçãs das plataformas curam).
  FASE 2    — com metade da vida: arremessos mais rápidos e o SALTO-PANCADA
              (tremor + faixa vermelha no chão como aviso -> salto -> duas
              ondas de choque correm pelo chão). Pule a onda.
  FASE 3    — com 1/4 da vida: CHUVA DE BANANAS (cachos caem do alto; a
              sombra marca o ponto de impacto antes) e arremessos ainda mais
              rápidos.
  REPOSIÇÃO — entre arremessos o Gorila SALTA para outro ponto da arena (o
              pouso aparece marcado no chão; nunca perto do jogador).
  PUNIÇÃO   — atordoado, ele derruba um minério do lado do jogador: pegue-o
              e ele volta voando na cabeça do Gorila (dano extra). Atordoado,
              o Gorila não machuca por contato.
  TROCA DE FASE — faixa de anúncio na tela; ao acordar, um rugido (sem
              ataque) antes de voltar ao combate.
  DERROTA   — com 0 de vida: animação de queda; ao terminar o boss fica
              `derrotado` e o main abre a tela de vitória.

Justiça do combate: todo ataque tem aviso visual antes; nenhum dano se
repete por frame (a invencibilidade do jogador vale para tudo); sempre há
pelo menos um minério por ciclo, então a vitória é sempre possível.
"""

import math
import random

import pygame

import constants
from src import sons
from src.enemies.enemy import Enemy
from utils import carregar_imagem

ARQUIVOS_MINERIO = {
    "cobre": "gorila_minerio_cobre_cenario_01.png",
    "zinco": "gorila_minerio_zinco_cenario_01.png",
}
POSE_PREPARO = {"cobre": "gorila_55_cenario_01.png",
                "zinco": "gorila_63_cenario_01.png",
                None: "gorila_53_cenario_01.png"}
SPRITE_ATORDOADO = "gorila_estunado_cenario_01.png"


def _recortar(surf):
    rects = pygame.mask.from_surface(surf).get_bounding_rects()
    if not rects:
        return surf
    return surf.subsurface(rects[0].unionall(rects[1:])).copy()


_cache_poses = {}


def _pose(arquivo, altura, inverter):
    """Pose recortada e escalada pela ALTURA (as artes têm resoluções diferentes)."""
    chave = (arquivo, altura, inverter)
    if chave not in _cache_poses:
        img = _recortar(carregar_imagem("inimigos", arquivo))
        largura = max(1, round(img.get_width() * altura / img.get_height()))
        img = pygame.transform.smoothscale(img, (largura, altura))
        _cache_poses[chave] = pygame.transform.flip(img, True, False) if inverter else img
    return _cache_poses[chave]


class ProjetilGorila:
    """Banana (dano) ou minério (abre pergunta quando acerta o jogador)."""

    def __init__(self, dono, x, y, vx, vy, tipo_minerio=None, gravidade=0.0, alvo_x=None):
        self.dono = dono
        self.gravidade = gravidade    # banana: arco; minério: linha reta
        self.alvo_x = alvo_x          # onde a banana vai cair (sombra no chão)
        self.tipo_minerio = tipo_minerio
        self.estado = "voando"           # voando | aguardando_resposta | retornando
        tam = constants.GORILA_PROJETIL_SIZE
        if tipo_minerio is None:
            self.image = carregar_imagem("inimigos", constants.GORILA_PROJETIL, (tam, tam))
        else:
            self.image = carregar_imagem("itens", ARQUIVOS_MINERIO[tipo_minerio],
                                         (int(tam * 1.15), int(tam * 1.15)))
        self.rect = self.image.get_rect(center=(int(x), int(y)))
        self.pos_x, self.pos_y = float(self.rect.x), float(self.rect.y)
        self.vx, self.vy = vx, vy
        self.angulo = 0.0

    @property
    def eh_minerio(self):
        return self.tipo_minerio is not None

    def update(self, player):
        """Devolve False quando o projétil deve sumir."""
        if self.estado == "aguardando_resposta":
            return True
        if self.estado == "retornando":
            dx = self.dono.rect.centerx - self.rect.centerx
            dy = self.dono.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy) or 1.0
            v = constants.GORILA_PROJETIL_SPEED_F2 * 1.4
            self.pos_x += dx / dist * v
            self.pos_y += dy / dist * v
            self.rect.topleft = (round(self.pos_x), round(self.pos_y))
            if self.rect.colliderect(self.dono.rect) or dist < v:
                self.dono.levar_minerio()
                return False
            return True

        self.vy += self.gravidade
        self.pos_x += self.vx
        self.pos_y += self.vy
        self.angulo = (self.angulo + 12) % 360
        self.rect.topleft = (round(self.pos_x), round(self.pos_y))

        # Jogador ANTES do cenário: o projétil mira o centro do jogador, e
        # perto do chão ele encostaria no bloco um frame antes de acertá-lo.
        if player is not None and player.alive and self.rect.colliderect(player.rect):
            if self.eh_minerio:
                # Pausa no ar e avisa o boss: o main abre a pergunta.
                self.estado = "aguardando_resposta"
                self.dono.minerio_atingiu_player = self
                return True
            self.causar_dano(player)
            return False
        # Só o CHÃO da arena para o projétil. As plataformas não servem de
        # escudo: debaixo delas o minério nunca chegaria ao jogador e a luta
        # travaria (achado no teste da luta completa). Elas continuam úteis
        # para mudar de altura e fugir das bananas.
        chao = self.dono.chao_y
        miolo = self.rect.inflate(-self.rect.width // 2, -self.rect.height // 2)
        for o in self.dono.obstaculos_proximos(self.rect):
            if (chao is None or o.top >= chao) and miolo.colliderect(o):
                return False
        return self.dono.limites.colliderect(self.rect)

    def causar_dano(self, player):
        _aplicar_dano(player, constants.GORILA_PROJETIL_DAMAGE)

    def refletir(self):
        self.estado = "retornando"

    def draw(self, surface, camera_x, camera_y):
        img = self.image
        if self.alvo_x is not None and self.estado == "voando" and self.dono.chao_y:
            # Sombra no ponto de queda: mostra para onde NÃO ficar.
            larg = self.rect.width
            sombra = pygame.Rect(0, 0, larg, max(4, larg // 4))
            sombra.midbottom = (int(self.alvo_x) - camera_x, self.dono.chao_y - camera_y)
            pygame.draw.ellipse(surface, (40, 20, 10), sombra)
        if not self.eh_minerio and self.estado == "voando":
            img = pygame.transform.rotate(self.image, self.angulo)
        surface.blit(img, img.get_rect(center=self.rect.center).move(-camera_x, -camera_y))


def _aplicar_dano(player, dano):
    """Dano no jogador respeitando a invencibilidade (nunca repete por frame)."""
    if player is None or not player.alive or player.invulnerable:
        return False
    player.player_health = max(0, player.player_health - dano)
    player.invulnerable = True
    player.last_stunned_time = pygame.time.get_ticks()
    sons.tocar("dano")
    if player.player_health <= 0:
        player.alive = False
    return True


class OndaDeChoque:
    """Onda que corre pelo chão depois do salto-pancada. Pule para desviar."""

    def __init__(self, x, chao_y, direcao, limites):
        self.direcao = direcao
        self.limites = limites
        alt = constants.GORILA_ONDA_ALTURA
        self.rect = pygame.Rect(0, 0, int(alt * 1.4), alt)
        self.rect.midbottom = (int(x), chao_y)
        self.pos_x = float(self.rect.x)
        self.ativa = True

    def update(self, player):
        self.pos_x += constants.GORILA_ONDA_VELOCIDADE * self.direcao
        self.rect.x = int(self.pos_x)
        if player is not None and self.rect.colliderect(player.rect):
            _aplicar_dano(player, constants.GORILA_ONDA_DANO)
        return self.limites.contains(self.rect)

    def draw(self, surface, camera_x, camera_y):
        r = self.rect.move(-camera_x, -camera_y)
        t = pygame.time.get_ticks() / 60.0
        pontos = [(r.left, r.bottom)]
        for i in range(9):
            px = r.left + r.width * i / 8
            py = r.top + r.height * (0.35 + 0.35 * math.sin(t + i))
            pontos.append((px, py))
        pontos.append((r.right, r.bottom))
        pygame.draw.polygon(surface, (235, 205, 120), pontos)
        pygame.draw.lines(surface, (120, 80, 30), False, pontos, 2)


class CachoCaindo:
    """Cacho de bananas da chuva (fase 3): sombra primeiro, queda depois."""

    def __init__(self, x, y_inicio, y_chao, inicio_ms):
        larg = int(constants.TILE_SIZE * 1.15)
        self.image = carregar_imagem("itens", "cacho_banana.png",
                                     (larg, int(larg * 539 / 670)))
        self.rect = self.image.get_rect(midbottom=(int(x), int(y_inicio)))
        self.pos_y = float(self.rect.y)
        self.vy = 2.0
        self.y_chao = y_chao              # topo do bloco onde ele cai
        self.inicio_ms = inicio_ms        # antes disso só a sombra aparece

    def update(self, player, agora):
        """Devolve False quando o cacho deve sumir."""
        if agora < self.inicio_ms:
            return True
        self.vy = min(self.vy + 0.5, constants.VEL_TERMINAL)
        self.pos_y += self.vy
        self.rect.y = int(self.pos_y)
        if player is not None and player.alive and self.rect.colliderect(player.rect):
            _aplicar_dano(player, constants.GORILA_CHUVA_DANO)
            return False
        return self.rect.bottom < self.y_chao

    def draw(self, surface, camera_x, camera_y, agora):
        # Sombra no ponto de impacto desde o primeiro frame: cresce conforme
        # o cacho se aproxima, com um anel vermelho pulsante de aviso.
        dist = max(0, self.y_chao - self.rect.bottom)
        larg = int(self.rect.width * (1.0 - min(0.35, dist / 1200)) * 1.2)
        sombra = pygame.Rect(0, 0, max(10, larg), max(6, larg // 3))
        sombra.midbottom = (self.rect.centerx - camera_x, self.y_chao - camera_y + 2)
        pygame.draw.ellipse(surface, (40, 20, 10), sombra)
        anel = sombra.inflate(10, 6)
        alpha = 120 + int(100 * (0.5 + 0.5 * math.sin(agora / 70)))
        camada = pygame.Surface(anel.size, pygame.SRCALPHA)
        pygame.draw.ellipse(camada, (230, 60, 40, alpha), camada.get_rect(), 3)
        surface.blit(camada, anel)
        if agora >= self.inicio_ms:
            surface.blit(self.image, self.rect.move(-camera_x, -camera_y))


class MinerioCaido:
    """
    Janela de punição: minério que o Gorila atordoado derruba no chão. O
    jogador encosta -> ele voa até o Gorila e causa dano extra.
    """

    def __init__(self, dono, x, chao_y, tipo):
        self.dono = dono
        tam = int(constants.GORILA_PROJETIL_SIZE * 1.15)
        self.image = carregar_imagem("itens", ARQUIVOS_MINERIO[tipo], (tam, tam))
        self.rect = self.image.get_rect(midbottom=(int(x), int(chao_y)))
        self.pos_x, self.pos_y = float(self.rect.x), float(self.rect.y)
        self.estado = "no_chao"           # no_chao | voando

    def update(self, player):
        """Devolve False quando some (acertou o Gorila)."""
        if self.estado == "no_chao":
            if player is not None and player.alive and self.rect.colliderect(player.rect):
                self.estado = "voando"
                sons.tocar("acerto")
            return True
        dx = self.dono.rect.centerx - self.rect.centerx
        dy = self.dono.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy) or 1.0
        v = constants.GORILA_PROJETIL_SPEED_F2 * 1.6
        self.pos_x += dx / dist * v
        self.pos_y += dy / dist * v
        self.rect.topleft = (round(self.pos_x), round(self.pos_y))
        if self.rect.colliderect(self.dono.rect) or dist < v:
            self.dono.levar_minerio_bonus()
            return False
        return True

    def draw(self, surface, camera_x, camera_y, agora):
        dy = 0
        if self.estado == "no_chao":
            dy = int(4 * math.sin(agora / 120))
            # brilho pulsante: "pegue-me"
            r = self.rect.width // 2 + 6 + int(3 * math.sin(agora / 90))
            halo = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(halo, (255, 230, 120, 90), (r, r), r)
            surface.blit(halo, (self.rect.centerx - r - camera_x, self.rect.centery - r - camera_y + dy))
        surface.blit(self.image, self.rect.move(-camera_x, -camera_y + dy))


FALAS = {
    "intro": "UUUH! Quem ousa subir na minha copa?",
    "fase2": "GRRR! Agora voce me irritou!",
    "fase3": "MINHAS BANANAS! TODAS ELAS!",
    "atordoado": "Ugh... minha cabeca...",
    "derrota": "Uhh... a jazida... e sua...",
}
ANUNCIOS = {2: "FASE 2 - O GORILA ESTA FURIOSO!", 3: "FASE 3 - CHUVA DE BANANAS!"}


class Gorila(Enemy):
    PASTA_SPRITES = "inimigos"
    SPRITE_FACES_LEFT = False
    ARQUIVOS_FRAMES = [f"gorila_0{i}.png" for i in range(1, 7)]
    LARGURA_ALVO = max(1, int(190 * constants.SCALE / 5))
    COR_PROVISORIA = (40, 40, 60)
    NOME = "GORILA GUARDIÃO"

    VIDA_MAX = constants.GORILA_VIDA
    DANO = constants.GORILA_DANO_CONTATO
    INVENCIVEL = False
    RECOMPENSA_PONTOS = 10
    SEMPRE_ATIVO = True          # age mesmo com a câmera longe (arena larga)
    # O golpe de asa da Areninha não fere o Gorila: ele tem a mecânica
    # própria (devolver minérios respondendo perguntas). Ver src/combate.py.
    IMUNE_A_GOLPE = True
    VELOCIDADE_PATRULHA = 0
    VELOCIDADE_PERSEGUICAO = 0
    VEL_ANIM_PATRULHA = 180
    DURACAO_DERROTA_MS = 1600

    def __init__(self, x, y):
        super().__init__(x, y)
        self.estado = "AGUARDANDO"   # AGUARDANDO|INTRO|COMBATE|ATORDOADO|DERROTA
        self.ativo = False
        self.projeteis = []
        self.ondas = []
        self.lancamentos = 0
        self._pos_minerio_ciclo = 0
        self._tipo_minerio_ciclo = "cobre"
        self.preparando = None        # None ou (tipo_minerio|None, fim_ms)
        self.pancada = None           # None ou dict com fase/tempos
        self.proximo_ataque = 0
        self.proxima_pancada = 0
        self.atordoado_ate = 0
        self.intro_ate = 0
        self.derrota_ate = 0
        self.flash_ate = 0
        self.minerio_atingiu_player = None
        self.tremor = 0               # px de tremor de câmera pedido ao main
        self.obstaculos_proximos = lambda rect: []
        self.limites = pygame.Rect(0, 0, 10 ** 6, 10 ** 6)
        self.chao_y = None
        # v1.0 — movimento, fase 3, feedback, janela de punição
        self.zona_luta = None         # Rect da área de luta (setores.criar_boss)
        self._world = None
        self._faixa_x = None          # (min, max) do centro nos saltos: chão livre
        self.pos_x = float(self.rect.x)
        self.salto = None             # None ou {etapa, ate, alvo_x, vx}
        self._arremessos_desde_salto = 0
        self.chuva = None             # None ou {etapa, ate}
        self.cachos = []
        self.proxima_chuva = 0
        self.minerio_caido = None
        self.anuncio = None           # (texto, ate_ms) — faixa na tela (main)
        self.fala = None              # (texto, ate_ms) — balão sobre o Gorila (main)
        self._rugir_ao_acordar = False
        self._ja_atordoado = False
        self.eventos = []             # avisos para o main: "minerio_caido", "bonus"

    # ── ligação com o setor/main ──────────────────────────────────────────
    def conectar(self, world, limites_px):
        """Chamado pelo setor: de onde vêm os obstáculos e até onde ir."""
        self.obstaculos_proximos = world.obstaculos_proximos
        self.limites = pygame.Rect(limites_px)
        self._world = world

    @property
    def fase(self):
        if self.vida <= self.VIDA_MAX // 4:
            return 3
        return 2 if self.vida <= self.VIDA_MAX // 2 else 1

    # ── avisos para o main (tolerante a instâncias montadas sem __init__) ──
    def _evento(self, nome):
        if not hasattr(self, "eventos"):
            self.eventos = []
        self.eventos.append(nome)

    def _falar(self, chave, ms=2600):
        self.fala = (FALAS[chave], pygame.time.get_ticks() + ms)

    @property
    def em_luta(self):
        return self.ativo and self.estado != "DERROTA" and not self.derrotado

    def ativar(self):
        if self.ativo:
            return
        agora = pygame.time.get_ticks()
        self.ativo = True
        self.estado = "INTRO"
        self.intro_ate = agora + constants.GORILA_INTRO_MS
        self.proximo_ataque = self.intro_ate + 300
        self.proxima_pancada = self.intro_ate + constants.GORILA_PANCADA_INTERVALO
        self.proxima_chuva = self.intro_ate + constants.GORILA_CHUVA_INTERVALO
        self.tremor = 8
        sons.tocar("rugido")
        self._falar("intro", constants.GORILA_INTRO_MS + 900)

    # ── combate (pontos de extensão do Enemy) ─────────────────────────────
    def receber_dano(self, quantidade):
        """Sobrescreve o Enemy: a derrota tem animação antes do `derrotado`."""
        if self.estado == "DERROTA" or self.derrotado:
            return False
        fase_antes = self.fase
        self.vida = max(0, self.vida - quantidade)
        agora = pygame.time.get_ticks()
        self.flash_ate = agora + 250
        sons.tocar("boss_dano")
        if self.vida == 0:
            self.estado = "DERROTA"
            self.derrota_ate = agora + self.DURACAO_DERROTA_MS
            self.projeteis = [p for p in self.projeteis if p.estado == "aguardando_resposta"]
            self.ondas = []
            self.preparando = self.pancada = None
            self.salto = self.chuva = self.minerio_caido = None
            self.cachos = []
            self._falar("derrota", self.DURACAO_DERROTA_MS + 400)
            return True
        if self.fase > fase_antes:
            # Troca de fase: faixa na tela agora, rugido quando acordar.
            self.anuncio = (ANUNCIOS[self.fase], agora + constants.GORILA_ANUNCIO_MS)
            self._falar(f"fase{self.fase}", constants.GORILA_ANUNCIO_MS)
            self._rugir_ao_acordar = True
            self.tremor = 14
        return False

    def levar_minerio(self):
        """O minério devolvido pelo jogador acertou o boss."""
        derrotou = self.receber_dano(1)
        if not derrotou:
            self.estado = "ATORDOADO"
            self.atordoado_ate = pygame.time.get_ticks() + constants.GORILA_ATORDOADO_MS
            self.preparando = None
            self.pancada = None
            self.salto = None
            self.chuva = None
            self.tremor = max(self.tremor, 5)
            if not getattr(self, "_ja_atordoado", True) and not getattr(self, "anuncio", None):
                self._falar("atordoado")
            self._ja_atordoado = True
            self._derrubar_minerio()

    def _derrubar_minerio(self):
        """Janela de punição: um minério cai do lado do jogador (se houver chão ali)."""
        rect = getattr(self, "rect", None)
        chao = getattr(self, "chao_y", None)
        if rect is None or chao is None:
            return
        T = constants.TILE_SIZE
        lado = getattr(self, "direcao", 1) or 1
        x = rect.centerx + lado * (rect.width // 2 + int(1.5 * T))
        faixa = getattr(self, "_faixa_x", None)
        if faixa:
            # o minério também precisa cair no chão livre (não em plataforma)
            x = max(faixa[0] - rect.width // 2, min(faixa[1] + rect.width // 2, x))
        tipo = getattr(self, "_tipo_minerio_ciclo", "cobre")
        self.minerio_caido = MinerioCaido(self, x, chao, tipo)
        self._evento("minerio_caido")

    def levar_minerio_bonus(self):
        """O minério caído, pego pelo jogador, acertou o Gorila: dano extra."""
        self.receber_dano(constants.GORILA_DANO_BONUS)
        self.tremor = max(self.tremor, 6)
        self._evento("bonus")

    def check_player_collision(self, player):
        if not self.ativo or self.estado == "DERROTA" or not self.rect.colliderect(player.rect):
            return False
        if self.estado == "ATORDOADO":
            return False     # atordoado não machuca: a janela de punição é segura
        if player.rect.centerx < self.rect.centerx:
            player.pos_x -= constants.KNOCKBACK_X
        else:
            player.pos_x += constants.KNOCKBACK_X
        if player.vel_y >= 0 and player.rect.bottom <= self.rect.top + self.rect.height // 4:
            player.vel_y = -constants.QUIQUE_Y   # pular na cabeça só quica
            return False
        _aplicar_dano(player, self.DANO)
        return True

    # ── ciclo de arremessos ───────────────────────────────────────────────
    def _proximo_tipo_projetil(self):
        """1 minério em posição aleatória a cada ciclo; o resto são bananas."""
        n = constants.GORILA_ARREMESSOS_POR_CICLO
        no_ciclo = self.lancamentos % n
        if no_ciclo == 0:
            self._pos_minerio_ciclo = random.randrange(n)
            self._tipo_minerio_ciclo = random.choice(tuple(ARQUIVOS_MINERIO))
        self.lancamentos += 1
        return self._tipo_minerio_ciclo if no_ciclo == self._pos_minerio_ciclo else None

    def _lancar(self, player, tipo):
        """
        BANANA: arco (parábola) que cai onde o jogador ESTAVA, com sombra no
        chão — desvia-se saindo do lugar. Uma linha reta mirada no centro do
        jogador era praticamente indesviável (o teste com bot apanhava de
        todas). MINÉRIO: linha reta e mais lenta, para ser "pego".
        """
        mao_x = self.rect.centerx + self.direcao * self.rect.width * 0.4
        mao_y = self.rect.top + self.rect.height * 0.35
        v = (constants.GORILA_PROJETIL_SPEED if self.fase == 1
             else constants.GORILA_PROJETIL_SPEED_F2)
        if tipo is not None:
            dx = player.rect.centerx - mao_x
            dy = player.rect.centery - mao_y
            dist = math.hypot(dx, dy) or 1.0
            v *= 0.8
            proj = ProjetilGorila(self, mao_x, mao_y, dx / dist * v, dy / dist * v, tipo)
        else:
            alvo_x = player.rect.centerx
            alvo_y = (self.chao_y or player.rect.bottom) - constants.GORILA_PROJETIL_SIZE // 2
            dx = alvo_x - mao_x
            dy = alvo_y - mao_y
            # tempo de voo em frames: proporcional à distância, com piso (dá
            # tempo de reagir) e teto (não fica pendurado no ar).
            t = max(50.0, min(80.0, abs(dx) / v))
            g = constants.GRAVITY * 0.9
            vx = dx / t
            vy = (dy - 0.5 * g * t * t) / t
            proj = ProjetilGorila(self, mao_x, mao_y, vx, vy, None, gravidade=g, alvo_x=alvo_x)
        self.projeteis.append(proj)
        sons.tocar("arremesso")

    # ── física mínima (o boss não anda; só cai/assenta e salta) ───────────
    def _assentar(self):
        self.vel_y = min(self.vel_y + constants.GRAVITY, constants.VEL_TERMINAL)
        self.pos_y += self.vel_y
        self.rect.y = int(self.pos_y)
        self.on_ground = False
        for obs in self.obstaculos_proximos(self.rect):
            if self.rect.colliderect(obs):
                if self.vel_y > 0:
                    self.rect.bottom = obs.top
                    self.on_ground = True
                    if self.chao_y is None:
                        self.chao_y = obs.top
                elif self.vel_y < 0:
                    self.rect.top = obs.bottom
                self.vel_y = 0.0
                self.pos_y = float(self.rect.y)
        if not self.on_ground and self.vel_y >= 0:
            # Parado no chão a gravidade soma menos de 1 px e o int() esconde
            # o movimento: sem esta sonda o on_ground alternava a cada frame
            # (e o salto-pancada só podia começar em frames alternados).
            pe = self.rect.move(0, 1)
            if any(pe.colliderect(o) for o in self.obstaculos_proximos(pe)):
                self.on_ground = True
                self.vel_y = 0.0
                self.pos_y = float(self.rect.y)
                if self.chao_y is None:
                    self.chao_y = self.rect.bottom   # nasce já apoiado no chão

    # ── atualização ───────────────────────────────────────────────────────
    def update(self, obstacles, player=None):
        agora = pygame.time.get_ticks()
        self._assentar()
        self.tremor = max(0, self.tremor - 1) if self.tremor else 0
        if player is not None and self.estado not in ("DERROTA",):
            self.direcao = 1 if player.rect.centerx >= self.rect.centerx else -1

        if self.estado == "DERROTA":
            if agora >= self.derrota_ate:
                self.derrotado = True    # o main remove e chama ao_inimigo_derrotado
            self._atualizar_projeteis(player)
            return

        if not self.ativo:
            self._atualizar_animacao()
            return

        if self.estado == "INTRO":
            if agora >= self.intro_ate:
                self.estado = "COMBATE"
            self._atualizar_animacao()
            return

        if self.estado == "ATORDOADO":
            if agora >= self.atordoado_ate:
                self.estado = "COMBATE"
                self.proximo_ataque = agora + 600
                if self.minerio_caido is not None and self.minerio_caido.estado == "no_chao":
                    self.minerio_caido = None      # não pegou a tempo: some
                if self._rugir_ao_acordar:
                    self._rugir_ao_acordar = False
                    self.proximo_ataque = agora + constants.GORILA_RUGIDO_FASE_MS
                    self.proxima_pancada = max(self.proxima_pancada, self.proximo_ataque + 1500)
                    self.proxima_chuva = max(self.proxima_chuva, self.proximo_ataque + 800)
                    self.tremor = 10
                    sons.tocar("rugido")
            self._atualizar_projeteis(player)
            return

        # COMBATE
        if self.pancada:
            self._atualizar_pancada(agora)
        elif self.salto:
            self._atualizar_salto(agora)
        elif self.chuva:
            self._atualizar_chuva(agora)
        elif self.preparando:
            tipo, fim = self.preparando
            if agora >= fim:
                self.preparando = None
                if player is not None and player.alive:
                    self._lancar(player, tipo)
                    self._arremessos_desde_salto += 1
                intervalo = (constants.GORILA_INTERVALO_ATAQUE, constants.GORILA_INTERVALO_ATAQUE_F2,
                             constants.GORILA_INTERVALO_ATAQUE_F3)[self.fase - 1]
                self.proximo_ataque = agora + intervalo
        elif self.fase >= 2 and agora >= self.proxima_pancada and self.on_ground:
            self.pancada = {"etapa": "aviso", "ate": agora + constants.GORILA_PANCADA_AVISO_MS}
        elif self.fase == 3 and agora >= self.proxima_chuva and self.on_ground:
            self.chuva = {"etapa": "aviso", "ate": agora + constants.GORILA_CHUVA_AVISO_MS}
            self.tremor = 6
            sons.tocar("rugido")
        elif (self._arremessos_desde_salto >= constants.GORILA_SALTO_A_CADA[self.fase - 1]
              and self.on_ground and player is not None and self._iniciar_salto(player, agora)):
            pass
        elif agora >= self.proximo_ataque and player is not None and player.alive:
            tipo = self._proximo_tipo_projetil()
            self.preparando = (tipo, agora + constants.GORILA_POSE_ARREMESSO)

        self._atualizar_projeteis(player)
        self._atualizar_animacao()

    # ── salto de reposição ────────────────────────────────────────────────
    def _calcular_faixa_x(self):
        """
        Faixa de x (centro do Gorila) onde ele pode pousar: o chão livre em
        volta da posição inicial, sem bloco na linha logo acima do chão (as
        plataformas baixas da arena ficam de fora) — lida da grade real.
        """
        w = self._world
        if w is None or self.chao_y is None:
            return None
        T = constants.TILE_SIZE
        linha = self.chao_y // T - 1
        col = self.rect.centerx // T
        livre = lambda c: (0 <= c < w.colunas and w._solidos[linha][c] is None
                           and w._solidos[linha + 1][c] is not None)
        c0 = c1 = col
        while livre(c0 - 1):
            c0 -= 1
        while livre(c1 + 1):
            c1 += 1
        meia = self.rect.width // 2
        x_min, x_max = c0 * T + meia + T // 4, (c1 + 1) * T - meia - T // 4
        if self.zona_luta is not None:
            x_min = max(x_min, self.zona_luta.left + meia + T)
            x_max = min(x_max, self.zona_luta.right - meia - T)
        return (x_min, x_max) if x_max > x_min else None

    def _iniciar_salto(self, player, agora):
        if self._faixa_x is None:
            self._faixa_x = self._calcular_faixa_x()
        if not self._faixa_x:
            return False
        T = constants.TILE_SIZE
        x_min, x_max = self._faixa_x
        candidatos = [x for x in range(int(x_min), int(x_max) + 1, T // 2)
                      if abs(x - player.rect.centerx) >= constants.GORILA_SALTO_DIST_PLAYER * T
                      and abs(x - self.rect.centerx) >= 3 * T]
        if not candidatos:
            self._arremessos_desde_salto = 0
            return False
        candidatos.sort(key=lambda x: -abs(x - player.rect.centerx))
        alvo = random.choice(candidatos[:max(1, len(candidatos) // 3)])
        self.salto = {"etapa": "aviso", "ate": agora + constants.GORILA_SALTO_AVISO_MS, "alvo_x": alvo}
        self._arremessos_desde_salto = 0
        return True

    def _atualizar_salto(self, agora):
        sl = self.salto
        if sl["etapa"] == "aviso" and agora >= sl["ate"]:
            v0 = constants.SPEED_JUMP * 1.45
            quadros = 2 * v0 / constants.GRAVITY
            sl["vx"] = (sl["alvo_x"] - self.rect.centerx) / quadros
            sl["etapa"] = "voo"
            self.pos_x = float(self.rect.x)
            self.vel_y = -v0
            self.on_ground = False
            sons.tocar("arremesso")
        elif sl["etapa"] == "voo":
            restante = sl["alvo_x"] - self.rect.centerx
            passo = sl["vx"] if abs(restante) > abs(sl["vx"]) else restante
            self.pos_x += passo
            self.rect.x = int(round(self.pos_x))
            if self.on_ground and self.vel_y == 0 and abs(restante) <= abs(sl["vx"]) + 1:
                self.rect.centerx = int(sl["alvo_x"])
                self.pos_x = float(self.rect.x)
                self.salto = None
                self.tremor = 5
                sons.tocar("pancada")
                self.proximo_ataque = max(self.proximo_ataque, agora + 450)

    # ── chuva de bananas (fase 3) ─────────────────────────────────────────
    def _chao_em(self, x):
        """Topo do primeiro bloco sólido abaixo do teto da arena na coluna de x."""
        w = self._world
        T = constants.TILE_SIZE
        if w is None:
            return self.chao_y
        c = int(x) // T
        topo = (self.zona_luta.top // T) if self.zona_luta is not None else 0
        for r in range(max(0, topo), w.linhas):
            if w._solidos[r][c] is not None:
                return r * T
        return self.chao_y

    def _atualizar_chuva(self, agora):
        ch = self.chuva
        if ch["etapa"] == "aviso" and agora >= ch["ate"]:
            T = constants.TILE_SIZE
            zona = self.zona_luta or self.limites
            esp = constants.GORILA_CHUVA_ESPACO_TILES * T
            inicio = zona.left + T + random.randrange(0, esp, T // 2)
            xs = list(range(inicio, zona.right - T, esp))
            random.shuffle(xs)
            # nasce 9 tiles acima do chão: a queda inteira fica dentro da câmera
            y0 = max(zona.top - T, (self.chao_y or zona.bottom) - 9 * T)
            for i, x in enumerate(xs):
                self.cachos.append(CachoCaindo(x, y0, self._chao_em(x),
                                               agora + 450 + i * constants.GORILA_CHUVA_ATRASO_MS))
            ch["etapa"] = "queda"
            ch["ate"] = agora + 450 + len(xs) * constants.GORILA_CHUVA_ATRASO_MS + 900
            self.tremor = 8
        elif ch["etapa"] == "queda" and agora >= ch["ate"]:
            self.chuva = None
            self.proxima_chuva = agora + constants.GORILA_CHUVA_INTERVALO
            self.proximo_ataque = max(self.proximo_ataque, agora + 400)

    def _atualizar_pancada(self, agora):
        p = self.pancada
        if p["etapa"] == "aviso" and agora >= p["ate"]:
            p["etapa"] = "salto"
            self.vel_y = -constants.SPEED_JUMP * 1.3
            self.on_ground = False
        elif p["etapa"] == "salto" and self.on_ground and self.vel_y == 0:
            chao = self.rect.bottom
            for d in (-1, 1):
                self.ondas.append(OndaDeChoque(self.rect.centerx + d * self.rect.width * 0.4,
                                               chao, d, self.limites))
            self.tremor = 12
            sons.tocar("pancada")
            p["etapa"] = "recuperacao"
            p["ate"] = agora + 900       # janela: o boss fica parado
        elif p["etapa"] == "recuperacao" and agora >= p["ate"]:
            self.pancada = None
            self.proxima_pancada = agora + constants.GORILA_PANCADA_INTERVALO
            self.proximo_ataque = agora + 500

    def _atualizar_projeteis(self, player):
        self.projeteis = [p for p in self.projeteis if p.update(player)]
        self.ondas = [o for o in self.ondas if o.update(player)]
        agora = pygame.time.get_ticks()
        if getattr(self, "cachos", None):
            self.cachos = [c for c in self.cachos if c.update(player, agora)]
        caido = getattr(self, "minerio_caido", None)
        if caido is not None and not caido.update(player):
            self.minerio_caido = None

    def limpar_ataques(self):
        """Some com bananas/ondas em voo (usado ao reiniciar a luta)."""
        self.projeteis = []
        self.ondas = []
        self.cachos = []
        self.minerio_caido = None
        self.minerio_atingiu_player = None

    def area_desenho(self):
        return self.rect.inflate(self.rect.width * 2, self.rect.height)

    def desenhar_feedback(self, surface, camera_x, camera_y):
        """O boss tem flash e barra de vida próprios (HUD); nada aqui."""

    # ── desenho ───────────────────────────────────────────────────────────
    def draw(self, surface, camera_x, camera_y):
        agora = pygame.time.get_ticks()
        h = self.rect.height
        inverter = self.direcao < 0
        imagem = None
        dy = 0
        if self.estado == "DERROTA":
            prog = 1 - max(0, self.derrota_ate - agora) / self.DURACAO_DERROTA_MS
            imagem = _pose(SPRITE_ATORDOADO, int(h * 1.15), inverter).copy()
            imagem.set_alpha(int(255 * (1 - prog * 0.85)))
            dy = int(prog * h * 0.15)
        elif self.estado == "ATORDOADO":
            imagem = _pose(SPRITE_ATORDOADO, int(h * 1.15), inverter)
        elif self.pancada and self.pancada["etapa"] == "aviso":
            imagem = _pose(POSE_PREPARO[None], h, inverter)
            dy = 0
            # aviso: faixa vermelha pulsando no chão dos dois lados
            alcance = self.rect.width * 3
            alpha = 90 + int(80 * (0.5 + 0.5 * math.sin(agora / 70)))
            faixa = pygame.Surface((alcance * 2 + self.rect.width, 8), pygame.SRCALPHA)
            faixa.fill((230, 40, 40, alpha))
            surface.blit(faixa, (self.rect.centerx - faixa.get_width() // 2 - camera_x,
                                 self.rect.bottom - 8 - camera_y))
        elif self.salto and self.salto["etapa"] == "aviso":
            # agachado (pose achatada) + marca do pouso no chão
            base = _pose(POSE_PREPARO[None], h, inverter)
            imagem = pygame.transform.scale(base, (int(base.get_width() * 1.08), int(h * 0.86)))
            alvo = pygame.Rect(0, 0, self.rect.width + 16, 14)
            alvo.midbottom = (int(self.salto["alvo_x"]) - camera_x, self.rect.bottom - camera_y + 4)
            alpha = 110 + int(90 * (0.5 + 0.5 * math.sin(agora / 60)))
            marca = pygame.Surface(alvo.size, pygame.SRCALPHA)
            pygame.draw.ellipse(marca, (255, 140, 40, alpha), marca.get_rect(), 3)
            surface.blit(marca, alvo)
        elif self.salto:
            imagem = _pose(POSE_PREPARO[None], h, inverter)
        elif self.chuva and self.chuva["etapa"] == "aviso":
            imagem = _pose(POSE_PREPARO[None], h, inverter)
        elif self.preparando:
            imagem = _pose(POSE_PREPARO[self.preparando[0]], h, inverter)

        if imagem is None:
            super().draw(surface, camera_x, camera_y)
            quadros = self.frames_direita if self.direcao > 0 else self.frames_esquerda
            desenhada = quadros[min(self.frame_atual, len(quadros) - 1)]
            pos = (self.rect.x - camera_x, self.rect.y - camera_y)
        else:
            tremendo = ((self.pancada and self.pancada["etapa"] == "aviso")
                        or (self.chuva and self.chuva["etapa"] == "aviso"))
            tremor = (agora // 40) % 3 - 1 if tremendo else 0
            x = self.rect.centerx - imagem.get_width() // 2 - camera_x + tremor * 2
            y = self.rect.bottom - imagem.get_height() - camera_y + dy
            surface.blit(imagem, (x, y))
            desenhada, pos = imagem, (x, y)

        if agora < self.flash_ate:
            # Brilho com a FORMA do sprite desenhado (antes era um retângulo do
            # tamanho da hitbox, mais estreito que a arte: aparecia uma "caixa").
            brilho = pygame.mask.from_surface(desenhada).to_surface(
                setcolor=(255, 255, 255, 110), unsetcolor=(0, 0, 0, 0))
            surface.blit(brilho, pos)
        if self.estado == "ATORDOADO":
            _estrelas(surface, self.rect.centerx - camera_x, pos[1] + 6, agora)
        for o in self.ondas:
            o.draw(surface, camera_x, camera_y)
        if self.minerio_caido is not None:
            self.minerio_caido.draw(surface, camera_x, camera_y, agora)
        for c in self.cachos:
            c.draw(surface, camera_x, camera_y, agora)
        for p in self.projeteis:
            p.draw(surface, camera_x, camera_y)


def _estrelas(surface, cx, y, agora):
    """Três estrelas girando sobre a cabeça: o Gorila está atordoado."""
    for i in range(3):
        ang = agora / 260 + i * 2 * math.pi / 3
        x = cx + math.cos(ang) * 34
        yy = y + math.sin(ang) * 9
        r = 8 if math.sin(ang) > 0 else 6
        pts = []
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5
            rr = r if k % 2 == 0 else r * 0.45
            pts.append((x + math.cos(a) * rr, yy + math.sin(a) * rr))
        pygame.draw.polygon(surface, (255, 226, 90), pts)
        pygame.draw.polygon(surface, (120, 80, 20), pts, 1)
