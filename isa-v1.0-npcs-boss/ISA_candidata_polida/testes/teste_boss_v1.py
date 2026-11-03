"""
Teste headless das melhorias da luta contra o Gorila (boss v1.0).

Mesmo esquema de testes/teste_boss.py: código real do jogo (main.passo_da_partida)
com relógio falso de 16 ms por frame.

Cobre:
  * fases: 1 (vida > 4), 2 (<= 4), 3 (<= 2);
  * troca de fase: faixa de anúncio + fala; ao acordar, rugido sem ataque;
  * SALTO DE REPOSIÇÃO: aviso antes de sair do chão; pouso no chão livre da
    arena (nunca em plataforma, nunca fora da área de luta), longe do
    jogador; 40 saltos com o jogador em posições sorteadas;
  * CHUVA DE BANANAS (fase 3): aviso, cachos espaçados (sempre há vão),
    sombra no ponto real de impacto com antecedência, dano uma vez só;
  * JANELA DE PUNIÇÃO: minério cai do lado do jogador; atordoado não fere
    por contato; pegar o minério tira vida extra; some se não for pego;
  * HUD: contador de minérios, anúncio e balão desenhados sem erro;
  * luta completa com um bot que aproveita a janela de punição.

Uso (na raiz do projeto):  python testes/teste_boss_v1.py
"""
import os
import random
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
PASTA_TMP = tempfile.mkdtemp(prefix="isa_teste_boss_v1_")
os.environ["ISA_DB"] = os.path.join(PASTA_TMP, "estatisticas.db")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import pygame  # noqa: E402

_agora = [10_000]
pygame.time.get_ticks = lambda: _agora[0]

import constants  # noqa: E402
import main as M  # noqa: E402
from src.enemies.boss import CachoCaindo, ProjetilGorila  # noqa: E402
from src.joystick import GerenciadorJoystick  # noqa: E402

T = constants.TILE_SIZE
DT = 16
random.seed(7)


def ok(msg):
    print("ok:", msg)


def frame(n=1):
    for _ in range(n):
        _agora[0] += DT
        M.passo_da_partida(DT)
        if M.estado_jogo in ("JOGANDO", "PAUSADO"):
            M.desenhar_jogo((0, 0))


def esperar(cond, limite=2000):
    for _ in range(limite):
        if cond():
            return True
        frame()
    return False


def preparar():
    pygame.init()
    M.configurar_janela()
    M.clock = pygame.time.Clock()
    M.gamepad = GerenciadorJoystick()
    M.recriar_ui()
    M.iniciar_jogo()
    M.estado_jogo = "JOGANDO"
    M.ativar_setor("arena")


def colocar_player(x_px):
    p = M.player
    p.rect.centerx = int(x_px)
    p.rect.bottom = M.boss.chao_y or M.boss.rect.bottom
    p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y)
    p.vel_y = 0
    M.reiniciar_movimento()


def luta_ativa():
    """Entra na área, espera a aparição e deixa o boss em COMBATE."""
    colocar_player(M.area_boss["rect"].left + T)
    frame()
    assert esperar(lambda: M.boss.estado == "COMBATE", 300)


def manter_vivo():
    if M.player:
        M.player.player_health = constants.PLAYER_HEALTH
        M.player.alive = True


def teste_fases():
    b = M.boss
    for vida, fase in ((8, 1), (5, 1), (4, 2), (3, 2), (2, 3), (1, 3)):
        b.vida = vida
        assert b.fase == fase, (vida, b.fase)
    b.vida = b.VIDA_MAX
    ok("fases: 1 (vida 5-8), 2 (3-4), 3 (1-2)")


def teste_troca_de_fase_anuncio_e_rugido():
    b = M.boss
    b.vida = 5
    b.levar_minerio()                   # 5 -> 4: fase 2
    assert b.fase == 2 and b.estado == "ATORDOADO"
    assert b.anuncio and "FASE 2" in b.anuncio[0], b.anuncio
    assert b.fala and "irritou" in b.fala[0]
    M.desenhar_jogo((0, 0))             # HUD com anúncio, contador e balão
    assert esperar(lambda: b.estado == "COMBATE", constants.GORILA_ATORDOADO_MS // DT + 20)
    inicio = _agora[0]
    # durante o rugido: nada de arremesso, pancada ou salto
    while _agora[0] - inicio < constants.GORILA_RUGIDO_FASE_MS - 3 * DT:
        frame()
        manter_vivo()
        assert not b.preparando and not b.pancada and not b.salto, "atacou durante o rugido"
    ok("troca de fase: faixa 'FASE 2', fala, e rugido sem ataque ao acordar")


def _valida_pouso(b):
    T_ = T
    zona = b.zona_luta
    assert b.on_ground and b.rect.bottom == b.chao_y, ("pousou fora do chao", b.rect, b.chao_y)
    assert zona.left <= b.rect.left and b.rect.right <= zona.right, ("fora da area", b.rect, zona)
    batendo = [o for o in b.obstaculos_proximos(b.rect) if o.colliderect(b.rect)]
    assert not batendo, ("dentro de bloco", batendo)
    return b.rect.centerx


def teste_salto_de_reposicao():
    b = M.boss
    b.vida = b.VIDA_MAX
    b.estado, b.pancada, b.chuva, b.preparando = "COMBATE", None, None, None
    zona = b.zona_luta
    pousos = set()
    for _ in range(40):
        manter_vivo()
        px_ = random.randrange(zona.left + T, zona.right - T)
        colocar_player(px_)
        b._arremessos_desde_salto = 99
        b.proximo_ataque = _agora[0] + 10_000      # só o salto interessa
        b.preparando = None
        if not esperar(lambda: b.salto is not None, 60):
            # nenhum ponto a >= 4 tiles do jogador: o boss segue sem saltar
            continue
        alvo = b.salto["alvo_x"]
        inicio = _agora[0]
        assert b.salto["etapa"] == "aviso" and b.on_ground
        assert abs(alvo - M.player.rect.centerx) >= constants.GORILA_SALTO_DIST_PLAYER * T
        assert esperar(lambda: b.rect.bottom < b.chao_y, 120), "nao saiu do chao"
        assert _agora[0] - inicio >= constants.GORILA_SALTO_AVISO_MS - DT, "saltou sem aviso"
        assert esperar(lambda: b.salto is None, 200), "nao pousou"
        x = _valida_pouso(b)
        assert abs(x - alvo) <= 2, (x, alvo)
        pousos.add(x // T)
    assert len(pousos) >= 4, f"saltos pouco variados: {sorted(pousos)}"
    ok(f"salto de reposicao: aviso antes, pouso no chao livre, longe do jogador "
       f"({len(pousos)} pontos de pouso diferentes em 40 saltos)")


def teste_chuva_de_bananas():
    b = M.boss
    b.vida = 2
    assert b.fase == 3
    b.estado, b.pancada, b.salto, b.preparando = "COMBATE", None, None, None
    b.proxima_pancada = _agora[0] + 60_000
    b.proxima_chuva = _agora[0]
    b._arremessos_desde_salto = 0
    colocar_player(b.zona_luta.left + 2 * T)
    manter_vivo()
    assert esperar(lambda: b.chuva is not None, 60), "fase 3 sem chuva"
    inicio = _agora[0]
    assert esperar(lambda: b.cachos, 200), "chuva sem cachos"
    assert _agora[0] - inicio >= constants.GORILA_CHUVA_AVISO_MS - DT, "chuva sem aviso"
    criados = _agora[0]
    xs = sorted(c.rect.centerx for c in b.cachos)
    assert len(xs) >= 6
    gaps = [b_ - a for a, b_ in zip(xs, xs[1:])]
    assert min(gaps) >= constants.GORILA_CHUVA_ESPACO_TILES * T - 1, gaps
    for c in b.cachos:
        col = c.rect.centerx // T
        assert M.world._solidos[c.y_chao // T][col] is not None, "sombra fora do chao"
    # antecedência: tempo entre a sombra aparecer e o primeiro impacto
    impactos = {}
    restantes = list(b.cachos)
    for _ in range(300):
        frame()
        manter_vivo()
        for c in list(restantes):
            if c not in b.cachos:
                impactos[id(c)] = _agora[0]
                restantes.remove(c)
        if not restantes:
            break
    antecedencia = min(impactos.values()) - criados
    assert antecedencia >= 900, f"sombra com pouca antecedencia ({antecedencia} ms)"
    # dano uma vez só
    cacho = CachoCaindo(M.player.rect.centerx, M.player.rect.top + 12, b.chao_y, 0)
    M.player.invulnerable = False
    vida = M.player.player_health
    cacho.update(M.player, _agora[0])
    cacho.update(M.player, _agora[0])
    assert M.player.player_health == vida - constants.GORILA_CHUVA_DANO
    M.player.invulnerable = False
    ok(f"chuva de bananas: aviso, {len(xs)} cachos com >= {constants.GORILA_CHUVA_ESPACO_TILES} "
       f"tiles de vao, sombra no chao real {antecedencia} ms antes do impacto, dano unico")


def _minerio_no_player():
    b = M.boss
    p = ProjetilGorila(b, M.player.rect.centerx + 60, M.player.rect.centery, -8, 0, "cobre")
    b.projeteis.append(p)
    assert esperar(lambda: M.estado_jogo == "QUIZ", 60)
    M.processar_resposta(M.pergunta_em_jogo()["resposta"])
    assert esperar(lambda: b.estado == "ATORDOADO", 600), "nao atordoou"


def teste_janela_de_punicao():
    b = M.boss
    b.vida = b.VIDA_MAX
    b.anuncio = None
    b.estado, b.pancada, b.salto, b.chuva, b.preparando = "COMBATE", None, None, None, None
    b.cachos = []
    colocar_player(b.rect.centerx - 6 * T)
    vida_boss = b.vida
    _minerio_no_player()
    assert b.vida == vida_boss - 1
    caido = b.minerio_caido
    assert caido is not None and caido.estado == "no_chao"
    assert caido.rect.bottom == b.chao_y, "minerio nao caiu no chao"
    assert caido.rect.centerx < b.rect.centerx, "minerio caiu do lado oposto ao jogador"
    frame(2)
    assert "PEGUE" in M.aviso_jogo[0], M.aviso_jogo
    # atordoado não fere por contato
    M.player.invulnerable = False
    vida = M.player.player_health
    M.player.rect.center = b.rect.center
    assert not b.check_player_collision(M.player) and M.player.player_health == vida
    # pega o minério -> dano extra
    M.player.rect.midbottom = caido.rect.midbottom
    M.player.pos_x, M.player.pos_y = float(M.player.rect.x), float(M.player.rect.y)
    assert esperar(lambda: b.vida == vida_boss - 2, 120), "minerio caido nao causou dano extra"
    assert b.minerio_caido is None and "extra" in M.aviso_jogo[0].lower()
    assert esperar(lambda: b.estado == "COMBATE", constants.GORILA_ATORDOADO_MS // DT + 20)
    # não pego: some ao acordar
    colocar_player(b.rect.centerx - 7 * T)
    _minerio_no_player()
    assert b.minerio_caido is not None
    assert esperar(lambda: b.estado == "COMBATE", constants.GORILA_ATORDOADO_MS // DT + 20)
    assert b.minerio_caido is None, "minerio caido nao sumiu ao acordar"
    ok("janela de punicao: minerio cai do lado do jogador, atordoado nao fere, "
       "pegar tira 1 vida extra, some se nao for pego")


def teste_luta_completa_com_punicao():
    """Bot: responde certo, pega o minério caído, mantém a vida; mede o ritmo."""
    from src.enemies.boss import Gorila
    bonus = [0]
    original = Gorila.levar_minerio_bonus

    def contar(self):
        bonus[0] += 1
        original(self)
    Gorila.levar_minerio_bonus = contar
    try:
        M.reiniciar_luta_boss()
        luta_ativa()
        inicio = _agora[0]
        perguntas = 0
        fases_vistas = set()
        for _ in range(60 * 60 * 6):
            if M.estado_jogo == "VITORIA":
                break
            b = M.boss
            if M.estado_jogo == "QUIZ" and M.quiz_boss:
                M.processar_resposta(M.pergunta_em_jogo()["resposta"])
                perguntas += 1
            elif b is not None and b.minerio_caido is not None and b.minerio_caido.estado == "no_chao":
                M.player.rect.midbottom = b.minerio_caido.rect.midbottom
                M.player.pos_x, M.player.pos_y = float(M.player.rect.x), float(M.player.rect.y)
            if b is not None:
                fases_vistas.add(b.fase)
            manter_vivo()
            frame()
    finally:
        Gorila.levar_minerio_bonus = original
    assert M.estado_jogo == "VITORIA", "luta nao terminou"
    duracao = (_agora[0] - inicio) / 1000
    assert fases_vistas >= {1, 2, 3}, fases_vistas
    assert perguntas + bonus[0] * constants.GORILA_DANO_BONUS == Gorila.VIDA_MAX, (perguntas, bonus[0])
    assert perguntas >= Gorila.VIDA_MAX // 2, "vitoria sem perguntas suficientes"
    ok(f"luta completa com punicao: VITORIA em {duracao:.0f} s de jogo; {perguntas} perguntas "
       f"+ {bonus[0]} minerios caidos devolvidos; fases {sorted(fases_vistas)}")


if __name__ == "__main__":
    preparar()
    luta_ativa()
    teste_fases()
    teste_troca_de_fase_anuncio_e_rugido()
    teste_salto_de_reposicao()
    teste_chuva_de_bananas()
    teste_janela_de_punicao()
    teste_luta_completa_com_punicao()
    M.banco_estatisticas.fechar()
    print("TODOS OS TESTES DO BOSS v1.0 PASSARAM")
