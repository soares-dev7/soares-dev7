"""Capturas de tela do loop REAL do jogo (main.py), com a câmera do jogador,
em pontos-chave de cada setor. Diferente de renderizar_camadas.py, aqui passa
HUD, câmera, atmosfera e inimigos de verdade.

uso (na raiz do projeto):
    python ferramentas/redesign_mapas/capturas_no_jogo.py . pasta_saida
"""
import os, sys, tempfile
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("ISA_DB", os.path.join(tempfile.mkdtemp(prefix="isa_shot_"), "e.db"))
GAME, OUT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
sys.path.insert(0, GAME); os.chdir(GAME)
import pygame, constants, main as M
from src.joystick import GerenciadorJoystick
T = constants.TILE_SIZE
pygame.init(); M.configurar_janela(); M.clock = pygame.time.Clock()
M.gamepad = GerenciadorJoystick(); M.recriar_ui(); M.iniciar_jogo(); M.estado_jogo = "JOGANDO"
PONTOS = [("floresta", 10, "inicio"), ("floresta", 88, "boca_caverna"), ("floresta", 186, "colina_guardia"),
          ("floresta", 234, "lago"), ("floresta", 318, "vala_ponte"), ("floresta", 348, "arvore_mae"),
          ("caverna", 10, "entrada"), ("caverna", 80, "camara_andaimes"), ("caverna", 147, "galeria_cristais"),
          ("caverna", 207, "poca"), ("caverna", 236, "saida"),
          ("copas", 8, "chegada"), ("copas", 36, "ancestral"), ("copas", 60, "ninho"),
          ("copas", 90, "espiral"), ("copas", 120, "portal_arena"), ("arena", 12, "arena")]
for setor, col, nome in PONTOS:
    M.ativar_setor(setor)
    M.ambientes.forcar(M.setor_atual.ambiente)
    M.player.health = constants.PLAYER_HEALTH
    g = M.setor_atual.world
    topo = next(r for r in range(1, g.linhas) if g._solidos[r][col] is not None and g._solidos[r-1][col] is None)
    p = M.player
    p.rect.centerx = col * T + T // 2; p.rect.bottom = topo * T
    p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y); p.vel_y = 0.0
    M.moving_left = M.moving_right = False
    for _ in range(40):
        M.atualizar_jogando(16)
    M.atualizar_camera(instantaneo=True)
    M.desenhar_jogo((0, 0))
    pygame.image.save(M.screen, os.path.join(OUT, f"{setor}_{nome}.jpg"))
    print("ok", setor, nome)
