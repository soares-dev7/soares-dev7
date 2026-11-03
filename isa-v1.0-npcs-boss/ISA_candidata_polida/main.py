import os
import random
import sys
import unicodedata

import pygame
from pygame import mixer

import constants
from src import nivel_dados, sons
from src.ambientes import GerenciadorAmbientes
from src.buttons import Botao, BotaoConfig, BotaoSair
from src.character import Character
from src.creditos import TelaCreditos
from src.combate import EfeitosCombate, GolpeAsa
from src.cutscene import Cutscene
from src.enemies.boss import Gorila
from src import npcs as npcs_mod
from src.estatisticas import Banco as BancoEstatisticas
from src.estatisticas import TelaEstatisticas
from src.quiz_tela import TelaQuiz
from src.joystick import (
    GerenciadorJoystick,
    acionar,
    centro_do_botao,
    navegar,
)
from src.setores import carregar_setores
from src.telas import TelaConfiguracoes, TelaLogin
from src.transicao import Transicao
from utils import (
    carregar_fonte,
    carregar_fundo,
    carregar_imagem,
    carregar_musica,
    carregar_perguntas_csv,
    carregar_perguntas_professores,
    carregar_tiles,
    obter_alternativas_pergunta,
)

# ── Inicialização ─────────────────────────────────────────────────────────────
# O jogo inteiro é desenhado numa superfície virtual de altura fixa (600) e,
# no fim de cada frame, essa superfície é esticada para caber na janela real.
#
# A ALTURA é travada em 600: é ela que define o zoom do mundo e o tamanho de
# toda a interface. A LARGURA acompanha o formato do monitor, para que não
# sobrem barras pretas nas laterais em telas widescreen. Num monitor 16:9 a
# virtual fica 1067x600; num 4:3, 800x600.
#
# Antes havia dois sistemas de escala que não conversavam: a interface crescia
# junto com a resolução enquanto o mundo ficava travado em TILE_SIZE. Em tela
# cheia a UI inchava e a câmera mostrava muito mais mapa — daí a desproporção.
BASE_H = 600
BASE_W_MIN = 800  # nunca mais estreito que 4:3
ASPECTO_MAX = 2.0  # trava monitores ultrawide, senão a UI fica perdida no meio

BASE_W = BASE_W_MIN  # recalculado em configurar_janela()

janela = None  # superfície real da janela/monitor — só recebe o blit final
screen = None  # superfície virtual — TUDO é desenhado aqui
clock = None

_escala = 1.0  # fator de ampliação da virtual para a janela
_offset_x = 0  # margem lateral (letterbox) em pixels de janela
_offset_y = 0  # margem superior (letterbox) em pixels de janela
_fullscreen = False

constants.SCREEN_WIDTH = BASE_W
constants.SCREEN_HEIGHT = BASE_H


def _largura_virtual_para_monitor():
    """Escolhe a largura da virtual a partir do formato do monitor."""
    info = pygame.display.Info()
    if info.current_h <= 0:
        return BASE_W_MIN
    aspecto = info.current_w / info.current_h
    aspecto = max(BASE_W_MIN / BASE_H, min(aspecto, ASPECTO_MAX))
    largura = int(round(BASE_H * aspecto / 2)) * 2  # arredonda para número par
    return max(BASE_W_MIN, largura)


def _recalcular_escala():
    """Recalcula ampliação e margens para centralizar a virtual na janela."""
    global _escala, _offset_x, _offset_y
    jw, jh = janela.get_size()
    # min() preserva a proporção; com a largura casando com o monitor,
    # na prática não sobra barra nenhuma em tela cheia
    _escala = min(jw / BASE_W, jh / BASE_H)
    _offset_x = (jw - int(BASE_W * _escala)) // 2
    _offset_y = (jh - int(BASE_H * _escala)) // 2


def configurar_janela(fullscreen=False):
    """Cria ou recria a janela real. A superfície virtual é preservada."""
    global janela, screen, _fullscreen, BASE_W
    _fullscreen = fullscreen

    if screen is None:
        # A largura virtual é decidida uma única vez, na primeira chamada,
        # para que alternar F11 não mude o enquadramento do jogo.
        BASE_W = _largura_virtual_para_monitor()
        constants.SCREEN_WIDTH = BASE_W
        constants.SCREEN_HEIGHT = BASE_H

    if fullscreen:
        janela = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        janela = pygame.display.set_mode((BASE_W, BASE_H))

    if screen is None:
        screen = pygame.Surface((BASE_W, BASE_H)).convert()
    _recalcular_escala()


def alternar_fullscreen():
    """
    Alterna janela/tela cheia. Note como isto ficou trivial: não é mais
    preciso recriar interface, fontes, botões ou telas, porque nada disso
    depende da resolução real da janela.
    """
    configurar_janela(not _fullscreen)


def apresentar():
    """Escala a superfície virtual para a janela e atualiza o vídeo."""
    destino = (int(BASE_W * _escala), int(BASE_H * _escala))
    if destino == janela.get_size():
        janela.blit(screen, (0, 0))
    else:
        janela.fill((0, 0, 0))  # barras do letterbox
        janela.blit(pygame.transform.scale(screen, destino), (_offset_x, _offset_y))
    pygame.display.flip()


def pos_virtual(pos):
    """Converte coordenada da janela real para coordenada da virtual 800x600."""
    x = (pos[0] - _offset_x) / _escala
    y = (pos[1] - _offset_y) / _escala
    return (int(x), int(y))


def mouse_virtual():
    return pos_virtual(pygame.mouse.get_pos())


_EVENTOS_COM_POS = (
    pygame.MOUSEBUTTONDOWN,
    pygame.MOUSEBUTTONUP,
    pygame.MOUSEMOTION,
)


def converter_evento(evento):
    """
    Reescreve as coordenadas de eventos de mouse para o espaço virtual.
    Sem isso, um clique em tela cheia chegaria aos botões com a coordenada
    do monitor (ex: 1600, 900) em vez da coordenada do jogo.
    """
    if evento.type not in _EVENTOS_COM_POS:
        return evento
    dados = dict(evento.__dict__)
    dados["pos"] = pos_virtual(dados["pos"])
    if "rel" in dados:
        rx, ry = dados["rel"]
        dados["rel"] = (int(rx / _escala), int(ry / _escala))
    return pygame.event.Event(evento.type, dados)

# ── Estados possíveis ─────────────────────────────────────────────────────────
# MENU, LOGIN, CUTSCENE, JOGANDO, QUIZ, QUIZ_FEEDBACK, PAUSADO, GAME_OVER,
# VITORIA (boss derrotado), CONFIGURACOES, CREDITOS e ESTATISTICAS (tela de
# desempenho + relatório PDF).
estado_jogo = "MENU"

# ── Controle de música ─────────────────────────────────────────────────────────
musica_atual = None  # guarda o nome do arquivo tocando, evita recarregar à toa
VOLUME_NORMAL = 0.5
VOLUME_QUIZ = 0.15
VOLUME_MUSICA_CONFIG = 0.7
VOLUME_EFEITOS_CONFIG = 0.7


NOME_MUSICA = "8-bit Game Music Loop.wav"  # arquivo dentro de assets/songs/


def aplicar_volume_musica(valor):
    global VOLUME_MUSICA_CONFIG
    VOLUME_MUSICA_CONFIG = max(0.0, min(1.0, float(valor)))
    if not mixer.get_init():
        return
    volume_ativo = VOLUME_NORMAL * VOLUME_MUSICA_CONFIG
    if estado_jogo == "QUIZ":
        volume_ativo = VOLUME_QUIZ * VOLUME_MUSICA_CONFIG
    mixer.music.set_volume(volume_ativo)


def aplicar_volume_efeitos(valor):
    global VOLUME_EFEITOS_CONFIG
    VOLUME_EFEITOS_CONFIG = max(0.0, min(1.0, float(valor)))
    sons.definir_volume(VOLUME_EFEITOS_CONFIG)


def abaixar_volume_quiz():
    """Abaixa a música ao entrar no quiz."""
    if mixer.get_init():
        mixer.music.set_volume(VOLUME_QUIZ * VOLUME_MUSICA_CONFIG)


def restaurar_volume_jogo():
    """
    Devolve a música ao volume normal.
    Precisa ser chamada em TODA saída do estado QUIZ — inclusive nas saídas
    de exceção — senão a trilha fica presa no volume baixo pelo resto da
    partida.
    """
    if mixer.get_init():
        mixer.music.set_volume(VOLUME_NORMAL * VOLUME_MUSICA_CONFIG)


def tocar_musica(nome_arquivo, pasta_interna="songs", volume=VOLUME_NORMAL, fade_ms=800):
    """Troca a música de fundo em loop, evitando recarregar se já for a mesma faixa."""
    global musica_atual
    if nome_arquivo == musica_atual:
        return
    try:
        caminho = carregar_musica(nome_arquivo, pasta_interna)
        mixer.music.load(caminho)
        mixer.music.set_volume(max(0.0, min(1.0, volume * VOLUME_MUSICA_CONFIG)))
        mixer.music.play(-1, fade_ms=fade_ms)
        musica_atual = nome_arquivo
    except Exception as e:  # noqa: BLE001
        print(f"Erro ao tocar música '{nome_arquivo}': {e}")


# ── Escala proporcional ───────────────────────────────────────────────────────
# Estas funções são IDENTIDADE: sx(50) == 50. Antes multiplicavam pela razão
# entre a tela e 800x600, o que esticava a interface em telas maiores.
#
# Agora a altura virtual é sempre 600, então não há nada a escalar. Foram
# mantidas para não ter que alterar as centenas de chamadas espalhadas pelo
# arquivo — mas atenção: como a LARGURA virtual varia, qualquer posição
# ancorada à direita precisa usar constants.SCREEN_WIDTH, não sx().
def sx(v):
    return int(v)


def sy(v):
    return int(v)


def sf(v):
    return max(8, int(v))


# ── TELA DE CARREGAMENTO ──────────────────────────────────────────────────────
def tela_carregamento(screen, progresso=0, mensagem="Carregando..."):
    W = constants.SCREEN_WIDTH
    H = constants.SCREEN_HEIGHT
    screen.fill((20, 20, 40))
    try:
        fonte_titulo = carregar_fonte("upheavtt.ttf", sf(48))
        titulo = fonte_titulo.render("I.S.A", True, (241, 187, 52))
        screen.blit(titulo, titulo.get_rect(center=(W // 2, H // 2 - 80)))
        fonte_msg = carregar_fonte("upheavtt.ttf", sf(20))
        texto = fonte_msg.render(mensagem, True, (200, 200, 200))
        screen.blit(texto, texto.get_rect(center=(W // 2, H // 2 - 20)))
    except Exception as e:
        print(f"Erro ao desenhar tela de carregamento: {e}")
    barra_w = 400
    barra_h = 20
    barra_x = (W - barra_w) // 2
    barra_y = H // 2 + 20
    pygame.draw.rect(
        screen, (60, 60, 80), (barra_x, barra_y, barra_w, barra_h), border_radius=10
    )
    pygame.draw.rect(
        screen,
        (76, 175, 80),
        (barra_x, barra_y, int(barra_w * progresso), barra_h),
        border_radius=10,
    )
    pygame.draw.rect(
        screen,
        (241, 187, 52),
        (barra_x, barra_y, barra_w, barra_h),
        2,
        border_radius=10,
    )
    apresentar()  # antes: pygame.display.flip() — agora escala a virtual


# ── Recursos reescaláveis ─────────────────────────────────────────────────────
background_img = None
# Gerenciador dos backgrounds da fase (floresta/caverna/copas + crossfade).
# Substituiu as duas Surfaces soltas paralaxe_c1/paralaxe_c2: agora quem sabe
# quais camadas existem, em que trecho do mapa cada uma vale e como
# misturá-las é o GerenciadorAmbientes (importado do ISA Kauan).
ambientes = None
# Fade Out -> reposicionamento -> Fade In ao usar uma passagem entre regiões
# (ver src/transicao.py e src/setores.py). Não depende de nada carregado em
# recriar_ui, mas fica junto por consistência de ciclo de vida.
transicao = None
fonte_ui = None
fonte_titulo = None
fonte_logo = None
botoes_menu = []
botoes_pausa = []
botoes_game_over = []
botoes_game_over_boss = []   # game over DENTRO da arena: inclui "tentar o boss"
botoes_vitoria = []
botao_voltar = None
tela_creditos = None
tela_login = None
tela_configuracoes = None
cutscene = None  # abertura em 6 imagens, exibida entre o login e a partida


def recriar_ui():
    global background_img, ambientes, transicao, fonte_ui, fonte_titulo, fonte_logo
    global botoes_game_over_boss, botoes_vitoria
    global \
        botoes_menu, \
        botoes_pausa, \
        botoes_game_over, \
        tela_login, \
        tela_creditos, \
        tela_configuracoes, \
        botao_voltar  # noqa: PLW0602
    tela_carregamento(screen, 0.1, "Carregando interface...")
    W, H = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
    # carregar_fundo cobre sem distorcer (a largura virtual agora varia)
    background_img = carregar_fundo("tela_menu", "Tela_Menu_Principal.jpg", (W, H))
    tela_carregamento(screen, 0.3, "Carregando ambientes...")
    # Um único objeto carrega TODOS os ambientes da fase de uma vez. Fica aqui
    # (e não em carregar_recursos_jogo) porque as camadas são escaladas pela
    # altura da virtual — a mesma razão que já trazia o paralaxe para cá — e
    # porque assim reiniciar a fase não recarrega imagem nenhuma.
    ambientes = GerenciadorAmbientes(W, H)
    # Modo discreto: sem isso o ambiente ficaria no default interno
    # (zonas[0], "copas") até a primeira passagem ser usada.
    ambientes.forcar(constants.SETORES[constants.SETOR_INICIAL]["ambiente"])
    transicao = Transicao()
    tela_carregamento(screen, 0.5, "Carregando fontes...")
    fonte_ui = carregar_fonte("upheavtt.ttf", sf(28))
    fonte_titulo = carregar_fonte("upheavtt.ttf", sf(18))
    # O titulo do menu usava fonte_titulo (18px) e ficava perdido no fundo.
    fonte_logo = carregar_fonte("upheavtt.ttf", sf(64))
    btn_w = max(180, sx(200))
    btn_h = max(50, sy(60))
    x_c = W // 2 - btn_w // 2
    tela_carregamento(screen, 0.7, "Carregando botões...")
    # Com a largura virtual variável, posições fixas deixariam os botões
    # descentralizados. JOGAR centraliza em W; sair e configurações
    # ancoram na borda direita. JOGAR abre a tela de registro do nome
    # (TelaLogin) antes de começar a partida — o nome vai para o PDF.
    botoes_menu = [
        Botao("JOGAR", x_c, sy(500), btn_w, btn_h, abrir_login),
        BotaoSair(cx=W - sx(100), cy=sy(38), raio=max(25, sx(30)), acao=encerrar_jogo),
        BotaoConfig(
            cx=W - sx(38), cy=sy(38), raio=max(25, sx(30)), acao=configurar_jogo
        ),
    ]
    # O botão "MENU" (tanto da pausa quanto do game over) representa o jogador
    # ENCERRANDO a partida — normalmente (GAME_OVER) ou no meio dela (PAUSADO) —
    # então os dois abrem a tela de estatísticas da sessão atual antes de voltar
    # ao menu (voltar_menu é chamado pela própria tela de estatísticas quando o
    # jogador clica em "VOLTAR AO MENU").
    botoes_pausa = [
        Botao("RETOMAR", x_c, sy(220), btn_w, btn_h, retomar_jogo),
        Botao("MENU", x_c, sy(310), btn_w, btn_h, abrir_estatisticas),
    ]
    botoes_game_over = [
        Botao("REINICIAR", x_c, sy(280), btn_w, btn_h, iniciar_jogo),
        Botao("MENU", x_c, sy(360), btn_w, btn_h, abrir_estatisticas),
    ]
    # Morreu lutando contra o boss: dá para recomeçar SÓ a luta, sem refazer
    # o mapa inteiro (minérios, perguntas e pontuação ficam como estavam).
    largo = max(btn_w, sx(300))
    x_l = W // 2 - largo // 2
    botoes_game_over_boss = [
        Botao("TENTAR DE NOVO", x_l, sy(270), largo, btn_h, reiniciar_luta_boss),
        Botao("REINICIAR", x_l, sy(345), largo, btn_h, iniciar_jogo),
        Botao("MENU", x_l, sy(420), largo, btn_h, abrir_estatisticas),
    ]
    botoes_vitoria = [
        Botao("RELATORIO", x_l, sy(345), largo, btn_h, abrir_estatisticas),
        Botao("JOGAR DE NOVO", x_l, sy(420), largo, btn_h, iniciar_jogo),
        Botao("MENU", x_l, sy(495), largo, btn_h, voltar_menu),
    ]

    tela_creditos = TelaCreditos(screen, W, H, callback_voltar=voltar_menu)
    tela_carregamento(screen, 1.0, "Pronto!")
    # Idem: 500 ms de espera artificial na montagem da UI.


# ── Paralaxe / ambientes ──────────────────────────────────────────────────────
def desenhar_paralaxe(camera_x=0, referencia=None, camera_y=0):
    """
    Desenha o fundo do frame. O nome ficou por retrocompatibilidade, mas o
    trabalho agora é do GerenciadorAmbientes: além do paralaxe, ele escolhe o
    ambiente pela ALTURA do jogador e dissolve um no outro nas fronteiras.

    `referencia` é a posição do jogador no eixo configurado em
    constants.EIXO_AMBIENTE — com "y", player.rect.centery. Usar o jogador e
    não a câmera importa nas bordas do mapa, onde a câmera trava e a transição
    congelaria pela metade.
    """
    if ambientes is None:
        screen.fill((0, 0, 0))
        return
    ambientes.desenhar(screen, camera_x, referencia, camera_y)


# ── TELA DE PERGUNTA COM LAYOUT MELHORADO (SCROLL + CLIQUE NAS ALTERNATIVAS) ──


# ── Intro do personagem ─────────────────────────────────────────────────────
intro_personagem_img = None
intro_personagem_rect = None
intro_personagem_x = -200
intro_personagem_y = 0
intro_velocidade = 3
intro_animacao_finalizada = False
intro_frames = []
intro_frame_index = 0
intro_frame_counter = 0
intro_frame_delay = 12

# Balão de fala: índice da fala atual (-1 = nenhuma)
intro_indice_fala = -1

texto_historia = [
    "Bem-vindo ao I.S.A!",
    "Ajude a personagem a coletar os minerios",
    "e responder as perguntas.",
    "Clique em qualquer lugar para continuar.",
]


#Função para retirar o fundo(Mesmo que a img já esteja sem) para após escalar
#os frames que vão alternar para o mesmo tamanho
def recortar_transparencia(sprite):
    """Remove a margem transparente ao redor do personagem, devolvendo só o conteúdo visível."""
    mask = pygame.mask.from_surface(sprite)
    rects = mask.get_bounding_rects()
    if not rects:
        return sprite
    r = rects[0]
    for rr in rects[1:]:
        r = r.union(rr)
    return sprite.subsurface(r).copy()


def escalar_mantendo_proporcao(sprite, altura_alvo):
    sprite = recortar_transparencia(sprite)  # ← linha nova
    razao = sprite.get_width() / sprite.get_height()
    largura_alvo = int(altura_alvo * razao)
    return pygame.transform.scale(sprite, (largura_alvo, altura_alvo))


def inicializar_intro():
    global intro_personagem_img, intro_personagem_rect
    global intro_personagem_x, intro_personagem_y
    global intro_animacao_finalizada, intro_frames
    global intro_frame_index, intro_frame_counter
    global intro_indice_fala

    frame_names = [
        "S4.png",
        "S5.png",
    ]

    intro_frames = []
    for nome in frame_names:
        try:
            sprite = carregar_imagem("personagens", nome)
            intro_frames.append(escalar_mantendo_proporcao(sprite, sy(220)))
        except Exception as e:
            print(f"Erro ao carregar frame de intro '{nome}': {e}")
            continue
    if not intro_frames:
        try:
            fallback = carregar_imagem("personagens", "Areninha4 2.png")
            intro_frames = [pygame.transform.scale(fallback, (220, 220))]
        except Exception as e:
            print(f"Erro ao carregar frame de fallback de intro: {e}")
            intro_frames = []

    intro_frame_index = 0
    intro_frame_counter = 0
    intro_indice_fala = -1  # nenhum balão ainda
    intro_personagem_img = intro_frames[0] if intro_frames else None
    intro_personagem_x = -sx(140)
    intro_personagem_y = constants.SCREEN_HEIGHT - sy(250)
    intro_personagem_rect = (
        intro_personagem_img.get_rect(topleft=(intro_personagem_x, intro_personagem_y))
        if intro_personagem_img
        else None
    )
    intro_animacao_finalizada = False


def atualizar_intro():
    """Avança a animação de corrida. Chamar apenas quando estado == 'INTRO'."""
    global intro_personagem_x, intro_personagem_rect
    global intro_frame_index, intro_frame_counter
    global intro_personagem_img, intro_animacao_finalizada, intro_indice_fala

    destino_x = sx(50)
    if intro_personagem_x < destino_x:
        intro_personagem_x += intro_velocidade
        if intro_personagem_rect:
            intro_personagem_rect.x = intro_personagem_x
        intro_frame_counter += 1
        if intro_frame_counter >= intro_frame_delay:
            intro_frame_counter = 0
            if intro_frames:
                intro_frame_index = (intro_frame_index + 1) % len(intro_frames)
                intro_personagem_img = intro_frames[intro_frame_index]
    else:
        if not intro_animacao_finalizada:
            intro_animacao_finalizada = True
            intro_indice_fala = 0
            try:
                sprite_parado = carregar_imagem("personagens", "S7.png")
                intro_personagem_img = escalar_mantendo_proporcao(sprite_parado, sy(220))
            except Exception as e:
                print(f"Erro ao carregar sprite parado da intro 'S7.png': {e}")


def processar_clique_intro(pos_mouse):
    global intro_indice_fala

    if not intro_animacao_finalizada:
        return
    if not intro_personagem_rect:
        return

    if not intro_personagem_rect.collidepoint(pos_mouse):
        return

    intro_indice_fala = (intro_indice_fala + 1) % len(texto_historia)


def desenhar_intro(mouse_pos):
    W = constants.SCREEN_WIDTH

    # Personagem
    if intro_personagem_img and intro_personagem_rect:
        screen.blit(intro_personagem_img, intro_personagem_rect)

        # ── Balão de fala ───────────────────────────────────────────
        if intro_animacao_finalizada and 0 <= intro_indice_fala < len(texto_historia):
            fala = texto_historia[intro_indice_fala]
            fonte_b = carregar_fonte("upheavtt.ttf", sf(18))
            surf_txt = fonte_b.render(fala, True, (20, 20, 20))
            pad = 12
            bal_w = surf_txt.get_width() + pad * 2
            bal_h = surf_txt.get_height() + pad * 2 + 22
            bal_x = intro_personagem_rect.right + sx(14)
            bal_y = intro_personagem_rect.top

            # Garante que não sai da tela pela direita
            if bal_x + bal_w > W - 10:
                bal_x = intro_personagem_rect.left - bal_w - sx(14)

            # NOVO: garante que o balão nunca sobreponha os botões do menu
            balloon_rect = pygame.Rect(bal_x, bal_y, bal_w, bal_h)
            for botao in botoes_menu:
                botao_rect = getattr(botao, "rect", None)
                if botao_rect and balloon_rect.colliderect(botao_rect):
                    bal_y = botao_rect.top - bal_h - sy(10)
                    balloon_rect.topleft = (bal_x, bal_y)
            
            # Fundo branco do balão
            pygame.draw.rect(
                screen, (255, 255, 240), (bal_x, bal_y, bal_w, bal_h), border_radius=12
            )
            pygame.draw.rect(
                screen, (80, 60, 20), (bal_x, bal_y, bal_w, bal_h), 2, border_radius=12
            )

            # Rabinho do balão (triângulo apontando para o personagem)
            cx = bal_x  # borda esquerda do balão
            cy = bal_y + bal_h // 2
            pygame.draw.polygon(
                screen,
                (255, 255, 240),
                [
                    (cx, cy - 8),
                    (cx, cy + 8),
                    (cx - sx(12), cy),
                ],
            )
            pygame.draw.lines(
                screen,
                (80, 60, 20),
                False,
                [
                    (cx, cy - 8),
                    (cx - sx(12), cy),
                    (cx, cy + 8),
                ],
                2,
            )

            screen.blit(surf_txt, (bal_x + pad, bal_y + pad))
            # instrução de continuar
            fonte_inst = carregar_fonte("upheavtt.ttf", sf(13))
            inst = fonte_inst.render("[ clique em mim! ]", True, (120, 100, 40))
            screen.blit(inst, (bal_x + pad, bal_y + bal_h - inst.get_height() - 4))

            # Contador de falas (ex: 1/4)
            prog = fonte_titulo.render(
                f"{intro_indice_fala + 1}/{len(texto_historia)}", True, constants.YELLOW
            )
            screen.blit(
                prog,
                (
                    bal_x + bal_w - prog.get_width() - 6,
                    bal_y + bal_h - prog.get_height() - 4,
                ),
            )


# ── Variáveis de jogo ─────────────────────────────────────────────────────────
player = None
# Setores do mapa (src/setores.py): todos montados no início da partida.
# As variáveis abaixo apontam para os objetos do SETOR ATIVO e são trocadas
# juntas por ativar_setor() — o resto do main continua usando `world`,
# `enemies`, `itens`... sem saber que existem vários setores.
setores = {}
setor_atual = None
world = None
passagens_cenario = None   # GerenciadorPassagens do setor ativo
area_boss = None           # só no setor da arena (ver setores.montar_area_boss)
passagem_ao_alcance = None # passagem que o player pode usar AGORA (ou None)
interagir_pressionado = False  # borda da tecla/botao de interacao
# NPCs (src/npcs.py): quem está ao alcance da tecla E e a conversa aberta
# ({"npc", "linhas", "i"} ou None). Setores já visitados nesta partida
# mudam algumas falas.
npc_ao_alcance = None
dialogo = None
setores_visitados = set()
enemies = []
itens = []
curas = []                 # itens de cura (maçãs) do setor ativo
# Combate contra inimigos comuns (src/combate.py): um golpe e uma lista de
# efeitos para o jogo todo.
golpe = GolpeAsa()
efeitos = EfeitosCombate()
inimigos_derrotados = 0    # só informativo (tela de vitória); não vale ponto
TECLAS_GOLPE = (pygame.K_j, pygame.K_f)
boss = None                # Gorila do setor ativo (só na arena)
camera_x = 0
camera_y = 0
moving_left = moving_right = False
jump_pressed = False

perguntas = []
pontuacao = 0
indice = 0
quiz_mensagem = ""
quiz_timer = 0
item_para_remover = None
# Pergunta aberta pelo MINÉRIO DO BOSS (None fora dela): dict com a pergunta,
# o projétil e o prazo. Fica separada de `perguntas`/`indice` para não
# bagunçar a fila do quiz normal.
quiz_boss = None
morreu_na_arena = False
selecao_vitoria = 0
# Aviso curto no rodapé do jogo (texto, até quando).
aviso_jogo = ("", 0)
# Toda a tela de pergunta (scroll, alternativas, seleção) mora aqui dentro.
# Eram cinco globais tocadas em sete pontos do arquivo; ver src/quiz_tela.py.
quiz_tela = TelaQuiz(sf, mouse_virtual)

# ── Foco de navegação ────────────────────────────────────────────────────────
# Os botões só conhecem "hover do mouse". Para o controle destacar o item
# selecionado, o jogo finge uma posição de mouse sobre ele. Esta flag decide
# quem manda no destaque: liga ao usar o controle, desliga ao mexer o mouse.
foco_no_controle = False
selecao_menu = 0
selecao_pausa = 0
selecao_game_over = 0

# ── Estatísticas / relatório ─────────────────────────────────────────────────
# O banco (SQLite) vive a execução inteira; cada partida nova ganha uma
# sessao_atual_id, e cada resposta do quiz é gravada nessa sessão na hora —
# assim a tela de desempenho funciona mesmo se o jogador sair no meio.
aluno_atual = "Aluno"  # nome digitado na tela de registro (TelaLogin)
ordem_resposta = 0
banco_estatisticas = BancoEstatisticas()
sessao_atual_id = None
tela_estatisticas = None
pdf_estatisticas_atual = None  # caminho do último PDF gerado (apagado ao reiniciar/voltar ao menu)

# ── Dificuldade progressiva ──────────────────────────────────────────────────
# `todas_perguntas` é o banco inteiro; `perguntas` é a fatia da fase atual.
# `_ids_respondidas` guarda a identidade (id()) das perguntas já usadas nesta
# partida, para que trocar de fase (ou voltar para uma região anterior) nunca
# repita pergunta.
todas_perguntas = []
fase_atual = 1
_ids_respondidas = set()


def posicao_de_foco(botoes, selecao, mouse_pos):
    """Onde desenhar o destaque: sobre o item selecionado ou sob o mouse."""
    if foco_no_controle and 0 <= selecao < len(botoes):
        return centro_do_botao(botoes[selecao])
    return mouse_pos


def navegar_menu(botoes, selecao, gamepad):
    """Aplica a navegação do d-pad/analógico a uma lista de botões."""
    passo = gamepad.nav_y or gamepad.nav_x
    if passo:
        return navegar(botoes, selecao, passo)
    return selecao


def reiniciar_movimento():
    global moving_left, moving_right, jump_pressed
    moving_left = moving_right = jump_pressed = False


def carregar_perguntas():
    lista_padrao = []
    try:
        lista_padrao = carregar_perguntas_csv("perguntas.csv")
        if lista_padrao:
            print(f" {len(lista_padrao)} perguntas carregadas")
    except Exception as e:
        print(f"Erro ao carregar perguntas: {e}")

    # Perguntas cadastradas pelos professores (CSV opcional, merge Pedro)
    lista_professores = carregar_perguntas_professores()

    lista_final = lista_padrao + lista_professores
    if lista_final:
        return lista_final

    # Fallback
    print(" Usando perguntas padrão")

    return [
        {
            "disciplina": "Teste",
            "dificuldade": "Fácil",
            "pergunta": "Quanto é 2+2?",
            "opcao_a": "3",
            "opcao_b": "4",
            "opcao_c": "5",
            "opcao_d": "6",
            "opcao_e": "",
            "resposta": "b",
        },
        {
            "disciplina": "Teste",
            "dificuldade": "Fácil",
            "pergunta": "Qual a cor do céu?",
            "opcao_a": "Verde",
            "opcao_b": "Azul",
            "opcao_c": "Vermelho",
            "opcao_d": "Amarelo",
            "opcao_e": "",
            "resposta": "b",
        },
    ]


def _normalizar_texto(texto):
    """Remove acentos e caixa, pra 'Fácil'/'FACIL'/'fácil' baterem igual.
    Serve tanto para dificuldade quanto para disciplina."""
    texto = (
        unicodedata.normalize("NFKD", str(texto or ""))
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return texto.strip().lower()


def filtrar_perguntas_por_fase(lista_perguntas, fase, disciplinas=None, embaralhar=False):
    """Retorna as perguntas permitidas na fase, na ordem em que devem sair.

    1. Perguntas já respondidas NESTA partida ficam de fora, para que
       atravessar uma passagem (ou voltar para uma região anterior) não
       repita conteúdo.
    2. Dificuldade: só as de constants.DIFICULDADES_POR_FASE[fase].
    3. Disciplina (veio do main_4): as de constants.DISCIPLINAS_POR_FASE[fase]
       — ou do parâmetro `disciplinas`, se passado — saem PRIMEIRO.
       Com DISCIPLINA_ESTRITA = True, só elas saem.

    Por que prioridade e não corte: o banco atual tem poucas perguntas por
    disciplina. Se o filtro cortasse, a floresta ficaria com 1 pergunta e
    os outros minérios sumiriam sem quiz (ver a coleta no loop principal).

    Nenhum filtro trava o quiz: se um passo zerar a lista, ele é ignorado.
    `embaralhar` embaralha DENTRO de cada grupo, sem desfazer a prioridade.
    """
    disponiveis = [p for p in lista_perguntas if id(p) not in _ids_respondidas]
    if not disponiveis:
        disponiveis = list(lista_perguntas)

    permitidas = constants.DIFICULDADES_POR_FASE.get(fase)
    if permitidas:
        por_dificuldade = [
            p
            for p in disponiveis
            if _normalizar_texto(p.get("dificuldade", p.get("nivel", ""))) in permitidas
        ]
        if por_dificuldade:
            disponiveis = por_dificuldade

    if disciplinas is None:
        disciplinas = constants.DISCIPLINAS_POR_FASE.get(fase)
    alvos = {_normalizar_texto(d) for d in (disciplinas or ())}

    if not alvos:
        if embaralhar:
            random.shuffle(disponiveis)
        return disponiveis

    da_disciplina = [
        p for p in disponiveis if _normalizar_texto(p.get("disciplina", "")) in alvos
    ]
    outras = [p for p in disponiveis if p not in da_disciplina]
    if embaralhar:
        random.shuffle(da_disciplina)
        random.shuffle(outras)

    if constants.DISCIPLINA_ESTRITA and da_disciplina:
        return da_disciplina
    return da_disciplina + outras


def aplicar_fase(nova_fase, embaralhar=True):
    """Troca a fase ativa e remonta a lista de perguntas do quiz.

    O `indice` volta a zero de propósito: ele caminha dentro da fatia da fase,
    não dentro do banco inteiro. A pontuação é global e não é afetada.
    """
    global fase_atual, perguntas, indice
    fase_atual = nova_fase
    perguntas = filtrar_perguntas_por_fase(
        todas_perguntas, fase_atual, embaralhar=embaralhar
    )
    indice = 0
    if constants.DEBUG:
        print(f"[fase] {fase_atual} -> {len(perguntas)} perguntas disponíveis")


def avancar_fase(nova_fase):
    """Chamada quando o player entra numa região nova (ver _resolver_passagem)."""
    if nova_fase != fase_atual:
        aplicar_fase(nova_fase)


todas_perguntas = carregar_perguntas()
perguntas = filtrar_perguntas_por_fase(todas_perguntas, fase_atual)


def pergunta_em_jogo():
    """A pergunta mostrada agora: a do minério do boss ou a da fila normal."""
    if quiz_boss is not None:
        return quiz_boss["pergunta"]
    if indice < len(perguntas):
        return perguntas[indice]
    return None


def avisar(texto, ms=2500):
    global aviso_jogo
    aviso_jogo = (texto, pygame.time.get_ticks() + ms)


# ── Processa uma resposta (chamada tanto pelo teclado quanto pelo clique) ─────
def processar_resposta(resposta):
    """
    Aplica a resposta da pergunta em jogo. `resposta` é "a".."e"; "" (vazio)
    significa TEMPO ESGOTADO na pergunta do boss e conta como erro.

    Quiz normal : acertou +20 de vida; errou -DAMAGE. O minério é consumido.
    Quiz do boss: acertou -> o minério volta e acerta o Gorila; errou -> o
                  minério acerta o jogador (dano do projétil).
    Em ambos a resposta é gravada no SQLite e a pontuação conta acertos.
    """
    global pontuacao, quiz_mensagem, quiz_timer, indice
    global item_para_remover, estado_jogo, ordem_resposta, quiz_boss

    pergunta_atual = pergunta_em_jogo()
    if pergunta_atual is None or resposta is None:
        return
    if not resposta and quiz_boss is None:
        return

    gabarito = pergunta_atual.get("resposta", "").strip().lower()
    acertou = bool(resposta) and resposta == gabarito
    evento = quiz_boss

    if acertou:
        pontuacao += 1
        sons.tocar("acerto")
        if evento:
            quiz_mensagem = "ACERTOU! O MINERIO VOLTOU PARA O GORILA!"
            evento["projetil"].refletir()
        else:
            quiz_mensagem = "VOCE ACERTOU! +20 de vida"
            if player and player.alive:
                player.player_health = min(
                    player.player_health + 20, constants.PLAYER_HEALTH
                )
    else:
        sons.tocar("erro")
        if evento:
            quiz_mensagem = ("TEMPO ESGOTADO! O MINERIO TE ACERTOU!" if not resposta
                             else "ERROU! O MINERIO TE ACERTOU!")
            projetil = evento["projetil"]
            if player and player.alive:
                player.invulnerable = False   # o acerto do minério sempre conta
                projetil.causar_dano(player)
            if projetil in evento["boss"].projeteis:
                evento["boss"].projeteis.remove(projetil)
        else:
            quiz_mensagem = "VOCE ERROU!"
            if player and player.alive:
                player.player_health -= constants.DAMAGE
                if player.player_health <= 0:
                    player.player_health = 0
                    player.alive = False

    # Registra a resposta no SQLite para a tela de estatísticas, mesmo que
    # o jogador saia no meio da partida (cada resposta é salva na hora).
    if sessao_atual_id is not None:
        ordem_resposta += 1
        try:
            banco_estatisticas.registrar_resposta(
                sessao_atual_id,
                ordem_resposta,
                pergunta_atual.get("disciplina", "Geral"),
                pergunta_atual.get("dificuldade", pergunta_atual.get("nivel", "Médio")),
                pergunta_atual.get("pergunta", ""),
                obter_alternativas_pergunta(pergunta_atual),
                gabarito,
                resposta,
            )
        except Exception as e:  # noqa: BLE001 - nunca derruba o quiz por causa disso
            print(f"Erro ao salvar resposta nas estatísticas: {e}")

    # Marca como usada para o filtro de fase não sortear de novo.
    _ids_respondidas.add(id(pergunta_atual))

    quiz_timer = 90
    if evento:
        quiz_boss = None
        if player:
            # Volta do quiz com um respiro: nenhuma banana em voo acerta o
            # jogador no primeiro frame de controle.
            player.invulnerable = True
            player.last_stunned_time = (pygame.time.get_ticks()
                                        - player.invulnerable_duration
                                        + constants.GRACA_POS_QUIZ_MS)
    else:
        indice += 1
        if item_para_remover and item_para_remover in itens:
            itens.remove(item_para_remover)
        item_para_remover = None
    quiz_tela.reiniciar()  # próxima pergunta começa do topo
    reiniciar_movimento()
    estado_jogo = "QUIZ_FEEDBACK"
    restaurar_volume_jogo()


def cancelar_quiz():
    """
    ESC / botão voltar no quiz NORMAL: fecha a pergunta SEM consumir o
    minério (ele volta a aparecer e pode ser coletado de novo). O quiz do
    boss não pode ser cancelado — o minério já está no ar.
    """
    global estado_jogo, item_para_remover
    if quiz_boss is not None:
        return
    if item_para_remover is not None:
        item_para_remover.liberar()
    item_para_remover = None
    quiz_tela.reiniciar()
    reiniciar_movimento()
    estado_jogo = "JOGANDO"
    restaurar_volume_jogo()


def _prazo_quiz_boss(pergunta):
    """Tempo justo para ler e responder: mínimo + tamanho do texto."""
    texto = pergunta.get("pergunta", "") + " ".join(
        t for _, t in obter_alternativas_pergunta(pergunta))
    segundos = constants.QUIZ_BOSS_MIN_S + len(texto) / constants.QUIZ_BOSS_CHARS_POR_S
    return int(min(constants.QUIZ_BOSS_MAX_S, segundos) * 1000)


def iniciar_quiz_boss(gorila, projetil):
    """
    O minério arremessado pelo Gorila acertou o jogador: abre uma pergunta
    com tempo. Cobre = Fácil, zinco = Médio (como no fork do boss); prefere
    perguntas curtas e ainda não respondidas. Sem pergunta elegível o
    minério simplesmente causa dano — o jogo nunca fica preso.
    """
    global quiz_boss, estado_jogo
    alvo = "facil" if projetil.tipo_minerio == "cobre" else "medio"
    elegiveis = [p for p in todas_perguntas
                 if _normalizar_texto(p.get("dificuldade", "")) == alvo] or list(todas_perguntas)
    nao_usadas = [p for p in elegiveis if id(p) not in _ids_respondidas] or elegiveis
    curtas = [p for p in nao_usadas if len(p.get("pergunta", "")) <= 220] or nao_usadas
    if not curtas:
        projetil.causar_dano(player)
        if projetil in gorila.projeteis:
            gorila.projeteis.remove(projetil)
        return
    pergunta = random.choice(curtas)
    quiz_boss = {
        "boss": gorila,
        "projetil": projetil,
        "pergunta": pergunta,
        "prazo": pygame.time.get_ticks() + _prazo_quiz_boss(pergunta),
    }
    estado_jogo = "QUIZ"
    quiz_tela.reiniciar()
    reiniciar_movimento()
    abaixar_volume_quiz()


def segundos_restantes_boss():
    if quiz_boss is None:
        return None
    return max(0, (quiz_boss["prazo"] - pygame.time.get_ticks() + 999) // 1000)


# ── Carregamento do nível ─────────────────────────────────────────────────────
def _assentar(entidade, col, row_superficie, altura_tiles=0):
    """Apoia o rect da entidade EM CIMA do tile sólido (col, row_superficie)."""
    T = constants.TILE_SIZE
    entidade.rect.centerx = col * T + T // 2
    entidade.rect.bottom = row_superficie * T - altura_tiles * T
    entidade.pos_x = float(entidade.rect.x)
    entidade.pos_y = float(entidade.rect.y)
    return entidade


def ativar_setor(nome):
    """Troca o setor ativo: mundo, inimigos, minérios e passagens juntos."""
    global setor_atual, world, enemies, itens, passagens_cenario, area_boss
    global curas, boss, dialogo, npc_ao_alcance
    setor_atual = setores[nome]
    setores_visitados.add(nome)
    dialogo = None
    npc_ao_alcance = None
    world = setor_atual.world
    enemies = setor_atual.inimigos
    itens = setor_atual.itens
    curas = setor_atual.curas
    boss = setor_atual.boss
    efeitos.limpar()
    golpe.reiniciar()
    passagens_cenario = setor_atual.passagens
    area_boss = setor_atual.area_boss
    if constants.DEBUG:
        print(f"[setor] {setor_atual}")
        _validar_setor(setor_atual)


def _validar_setor(setor):
    """
    Só com DEBUG: confere com os rects REAIS se alguma entidade ficou dentro
    de bloco, sobreposta a outra ou fora do setor, e se todo trecho do setor
    é alcançável a partir da entrada.
    """
    from src import validacao_mapa

    entidades = [(f"{type(e).__name__}#{i}", e.rect) for i, e in enumerate(setor.inimigos)]
    entidades += [(f"minerio#{i}", it.rect) for i, it in enumerate(setor.itens)]
    entidades += [(f"cura#{i}", c.rect) for i, c in enumerate(setor.curas)]
    problemas = validacao_mapa.validar_csv(setor.grade)
    problemas += validacao_mapa.validar_entidades(
        setor.grade, setor.world.obstacles, entidades
    )
    info = nivel_dados.SETORES_GERADOS.get(setor.nome)
    if info:
        problemas += validacao_mapa.validar_regiao(
            setor.grade, setor.nome, 0, setor.world.colunas - 1,
            info["entrada_col"], info["entrada_row"]
        )
    validacao_mapa.relatorio(problemas, f"VALIDACAO DO SETOR {setor.nome.upper()}")


def carregar_recursos_jogo():
    global player, setores, quiz_boss, morreu_na_arena
    global pontuacao, indice, quiz_mensagem, quiz_timer, item_para_remover
    tela_carregamento(screen, 0.2, "Carregando tiles...")
    tiles, tile_fallback = carregar_tiles(
        constants.TILE_SPRITES,
        constants.TILE_SIZE,
        constants.TILE_FALLBACK_ID,
    )

    # Todos os setores de uma vez: montar a grade leva poucos ms, e assim o
    # estado de cada setor (minério coletado etc.) sobrevive às idas e voltas.
    tela_carregamento(screen, 0.4, "Construindo setores...")
    setores = carregar_setores(tiles, tile_fallback)
    setores_visitados.clear()
    ativar_setor(constants.SETOR_INICIAL)

    tela_carregamento(screen, 0.7, "Carregando personagem...")
    # A animação (andando/pulo) é carregada pelo próprio Character; esta
    # imagem é só o último recurso se faltarem os sprites.
    player_image = carregar_imagem("personagens", "areninha_ISA.png")
    player = Character(
        constants.PLAYER_START_X,
        constants.PLAYER_START_Y,
        constants.PLAYER_SIZE,
        constants.PLAYER_SPEED,
        player_image,
        constants.PLAYER_HEALTH,
    )
    # Assenta o player na célula do marcador 90 usando a ALTURA REAL do rect
    # (o sprite é escalado mantendo a proporção: o rect é 30x45, não 45x45).
    _assentar(player, *setor_atual.player_spawn)

    # Enquadra o spawn de imediato: sem isso o primeiro frame mostrava o
    # canto do mapa.
    global _cam_foco_y, _cam_iniciada
    _cam_foco_y, _cam_iniciada = None, False
    atualizar_camera(instantaneo=True)
    if ambientes:
        # Força o ambiente inicial (o player pode ter morrido na caverna na
        # partida anterior).
        ambientes.forcar(setor_atual.ambiente)
    if transicao:
        # Defensivo: uma transição presa (morte no meio do fade) não passa
        # para a próxima partida.
        transicao.ativa = False
        transicao.alpha = 0.0
    reiniciar_movimento()
    pontuacao = 0
    indice = 0
    quiz_mensagem = ""
    quiz_timer = 0
    item_para_remover = None
    quiz_boss = None
    morreu_na_arena = False
    tela_carregamento(screen, 1.0, "Pronto!")


# ── Câmera ────────────────────────────────────────────────────────────────────
# A câmera antiga travava o centro da tela no centro do player, sem folga
# nenhuma: o jogador via a mesma distância para os dois lados, para cima e
# para baixo, sempre. Num mapa que agora tem 44 linhas de altura isso é
# desconfortável — quem sobe não enxerga o galho seguinte, quem desce não vê
# onde vai cair, e quem anda para a direita enxerga tanto do que já passou
# quanto do que vem pela frente.
#
# Três correções, nesta ordem de importância:
#
# 1. LOOK-AHEAD HORIZONTAL — a câmera se desloca para o lado que o player
#    está olhando, mostrando mais caminho à frente do que atrás.
# 2. ANTECIPAÇÃO VERTICAL — a velocidade vertical desloca o alvo: subindo,
#    revela o que está acima; caindo, revela o chão que vem.
# 3. ZONA MORTA VERTICAL — pulinhos não sacodem a câmera. Ela só passa a
#    seguir o eixo Y quando o player realmente sai da faixa.
#
# Tudo é seguido com suavização (interpolação), então a câmera acompanha em
# vez de grudar. `instantaneo=True` pula a suavização — é o que a transição
# entre regiões usa para já reaparecer enquadrada.
_cam_foco_y = None       # linha de referência vertical que a câmera persegue
_cam_iniciada = False


def atualizar_camera(instantaneo=False):
    global camera_x, camera_y, _cam_foco_y, _cam_iniciada
    if player is None:
        return

    W, H = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
    map_w = setor_atual.largura_px
    map_h = setor_atual.altura_px

    # 1. Horizontal: empurra o enquadramento para o lado que o player encara.
    direcao = -1 if getattr(player, "flip", False) else 1
    alvo_x = player.rect.centerx + direcao * constants.CAM_AVANCO_X - W // 2

    # 3. Zona morta: o foco vertical só se move quando o player sai da faixa.
    if _cam_foco_y is None or instantaneo:
        _cam_foco_y = float(player.rect.centery)
    else:
        desvio = player.rect.centery - _cam_foco_y
        if abs(desvio) > constants.CAM_ZONA_MORTA_Y:
            _cam_foco_y += desvio - constants.CAM_ZONA_MORTA_Y * (1 if desvio > 0 else -1)
        if getattr(player, "on_ground", False):
            # Pisou no chão: reancora de vez, senão a zona morta acumula erro
            # e a câmera fica permanentemente torta depois de uma queda longa.
            _cam_foco_y = float(player.rect.centery)

    # 2. Antecipação vertical proporcional à velocidade de queda/subida.
    antecipacao = player.vel_y * constants.CAM_ANTECIPACAO_Y
    antecipacao = max(-constants.CAM_AVANCO_SUBIDA,
                      min(constants.CAM_AVANCO_QUEDA, antecipacao))
    alvo_y = _cam_foco_y + antecipacao - H // 2

    if luta_em_andamento():
        # Luta contra o boss: enquadra jogador E boss (ponto médio, sem
        # perder o jogador de vista) e sobe o horizonte para mostrar o espaço
        # dos arremessos em vez da terra embaixo do chão.
        meio = (player.rect.centerx + boss.rect.centerx) / 2
        folga = W // 2 - constants.TILE_SIZE * 2
        alvo_x = max(player.rect.centerx - W // 2 - folga,
                     min(meio - W // 2, player.rect.centerx - W // 2 + folga))
        alvo_y = boss.rect.bottom - int(H * 0.74)

    # Limites do mapa: é o que impede a câmera de revelar vazio fora do mundo.
    alvo_x = max(0, min(alvo_x, map_w - W))
    alvo_y = max(0, min(alvo_y, map_h - H))

    if instantaneo or not _cam_iniciada:
        camera_x, camera_y = int(alvo_x), int(alvo_y)
        _cam_iniciada = True
        return

    k = constants.CAM_SUAVIZACAO
    camera_x += (alvo_x - camera_x) * k
    camera_y += (alvo_y - camera_y) * k
    camera_x = int(max(0, min(camera_x, map_w - W)))
    camera_y = int(max(0, min(camera_y, map_h - H)))


# ── Passagens entre regiões (Fade Out -> reposicionamento -> Fade In) ───────
def _resolver_passagem(destino):
    """
    Devolve o callback que a Transicao roda no instante 100% preto: repõe o
    player no spawn do destino, troca o ambiente ativo e resincroniza a
    câmera. Isolado numa função por causa do late binding de closures em
    laço — sem isso, todo callback acabaria usando o último `destino` do
    dicionário em vez do seu próprio.
    """
    def _callback():
        # Onde o player reaparece vem do MARCADOR DE CHEGADA desenhado no CSV
        # do setor de destino (constants.PASSAGENS_CSV amarra cada entrada ao
        # seu setor e ao ID da chegada). A célula é a posição.
        destino_setor = setores.get(destino.get("setor"))
        chegada = destino_setor.chegadas.get(destino.get("chegada")) if destino_setor else None
        if chegada is None:
            print(f"Passagem sem destino valido, ignorada: {destino}")
            return
        ativar_setor(destino_setor.nome)
        col, linha = chegada
        # A base do rect encosta na base da célula da chegada, seja qual for
        # a altura real do sprite.
        player.rect.centerx = col * constants.TILE_SIZE + constants.TILE_SIZE // 2
        player.rect.bottom = (linha + 1) * constants.TILE_SIZE
        player.pos_x, player.pos_y = float(player.rect.x), float(player.rect.y)
        # Zera o momentum: sem isso o player podia chegar na nova região já
        # "caindo" com a velocidade que tinha antes de entrar na passagem.
        player.vel_y = 0.0
        player.on_ground = False
        player.jumps_left = player.MAX_JUMPS
        if ambientes:
            ambientes.forcar(setor_atual.ambiente)
        # O setor é a "fase" do quiz: entrar na caverna endurece as perguntas.
        # Ver constants.FASE_POR_REGIAO / DIFICULDADES_POR_FASE.
        avancar_fase(constants.FASE_POR_REGIAO.get(setor_atual.nome, fase_atual))
        # instantaneo=True: o reposicionamento acontece com a tela 100% preta,
        # entao a camera tem que SALTAR para o novo enquadramento. Com a
        # suavizacao ligada ela comecaria o Fade In ainda mostrando a regiao
        # antiga e deslizaria ate a nova na frente do jogador.
        atualizar_camera(instantaneo=True)

    return _callback


def _checar_passagens():
    """
    Chamada uma vez por frame enquanto o player está jogando (e nenhuma
    transição já está em andamento).

    Mudou de "encostou, teleportou" para "encostou, aparece o aviso; apertou,
    entra". A especificação pede que o jogador UTILIZE a passagem (§10), e o
    teleporte automático tinha um efeito colateral chato: passar correndo pela
    boca da caverna arrastava o jogador para dentro sem querer.

    Um estilo pode voltar ao comportamento antigo declarando
    `"interacao": "toque"` em src/passagens.py — a mecânica aceita os dois.
    """
    global passagem_ao_alcance
    passagem_ao_alcance = None
    if passagens_cenario is None:
        return

    perto = passagens_cenario.ao_alcance(player.rect)
    if perto is None:
        return
    if luta_em_andamento():
        # A arena fecha durante a luta: a saída só reabre com o boss vencido.
        if interagir_pressionado:
            avisar("A saida esta bloqueada! Derrote o Gorila primeiro.")
        return

    if not perto.exige_tecla:
        transicao.iniciar(_resolver_passagem(perto.destino))
        return

    passagem_ao_alcance = perto
    if interagir_pressionado:
        reiniciar_movimento()
        transicao.iniciar(_resolver_passagem(perto.destino))


def contexto_npcs():
    """Progresso que as falas dos NPCs consultam (ver assets/levels/npcs.json)."""
    total = sum(s.minerios_iniciais - len(s.itens) for s in setores.values())
    s = setor_atual
    return {"coletados_setor": s.minerios_iniciais - len(s.itens),
            "total_setor": s.minerios_iniciais,
            "coletados_total": total,
            "visitados": frozenset(setores_visitados)}


def _checar_npcs():
    """
    Conversa com NPCs pela mesma tecla das passagens (E / X). A passagem ao
    alcance tem prioridade; a conversa não pausa o jogo, avança a cada E e
    fecha no fim ou quando o jogador se afasta.
    """
    global npc_ao_alcance, dialogo
    npc_ao_alcance = None
    if setor_atual is None or not setor_atual.npcs.itens:
        return
    setor_atual.npcs.atualizar(player.rect)
    if dialogo is not None:
        if not dialogo["npc"].perto(player.rect, npcs_mod.AFASTAR_TILES):
            dialogo = None
        elif interagir_pressionado:
            dialogo["i"] += 1
            if dialogo["i"] >= len(dialogo["linhas"]):
                dialogo = None
        return
    if passagem_ao_alcance is not None:
        return
    npc = setor_atual.npcs.ao_alcance(player.rect)
    npc_ao_alcance = npc
    if npc is not None and interagir_pressionado:
        linhas, item = npc.conversar(contexto_npcs())
        if item == "maca":
            col, base = npc.ponto_de_entrega(world)
            from src.setores import criar_cura
            nova = criar_cura({"col": col, "row": base})
            setor_atual.curas.append(nova)
            sons.tocar("cura")
        if linhas:
            dialogo = {"npc": npc, "linhas": linhas, "i": 0}


# ── Ações dos botões ──────────────────────────────────────────────────────────
def luta_em_andamento():
    return boss is not None and boss.em_luta


def _checar_inicio_da_luta():
    """A luta começa quando o jogador cruza a borda da área do boss."""
    if boss is None or boss.ativo or area_boss is None:
        return
    if player.rect.left >= area_boss["rect"].left:
        boss.ativar()
        avisar("Desvie das BANANAS! Deixe o MINERIO te acertar e responda!", 5000)


def _avisos_do_boss():
    """Eventos que o Gorila sinaliza viram avisos na tela."""
    if boss is None or not getattr(boss, "eventos", None):
        return
    for ev in boss.eventos:
        if ev == "minerio_caido":
            avisar("O Gorila esta tonto! PEGUE o minerio caido para dano extra!", 3000)
        elif ev == "bonus":
            avisar("Na cabeca! Dano extra no Gorila!", 1800)
    boss.eventos.clear()


def reiniciar_luta_boss():
    """
    TENTAR DE NOVO (game over na arena): recomeça SÓ a luta. O setor da arena
    troca o boss por uma instância nova (nada duplicado, nada herdado) e
    devolve as maçãs; o jogador volta inteiro para a entrada da arena. Mapa,
    minérios já coletados, perguntas e pontuação ficam como estavam.
    """
    global estado_jogo, quiz_boss, morreu_na_arena, quiz_mensagem
    arena = setores.get(nivel_dados.AREA_BOSS["setor"])
    if arena is None or player is None:
        iniciar_jogo()
        return
    arena.reiniciar_boss()
    ativar_setor(arena.nome)
    chegada = arena.chegadas.get(constants.TILE_CHEGADA_ARENA)
    col, linha = chegada if chegada else (3, arena.world.linhas // 2)
    player.rect.centerx = col * constants.TILE_SIZE + constants.TILE_SIZE // 2
    player.rect.bottom = (linha + 1) * constants.TILE_SIZE
    player.pos_x, player.pos_y = float(player.rect.x), float(player.rect.y)
    player.player_health = constants.PLAYER_HEALTH
    player.alive = True
    player.vel_y = 0.0
    player.invulnerable = False
    player.preso = False
    player.jumps_left = player.MAX_JUMPS
    quiz_boss = None
    quiz_mensagem = ""
    morreu_na_arena = False
    reiniciar_movimento()
    if transicao:
        transicao.ativa = False
        transicao.alpha = 0.0
    atualizar_camera(instantaneo=True)
    estado_jogo = "JOGANDO"
    restaurar_volume_jogo()


def iniciar_jogo():
    global estado_jogo, sessao_atual_id, ordem_resposta, todas_perguntas
    global inimigos_derrotados
    apagar_pdf_estatisticas()
    inimigos_derrotados = 0
    # Relê os CSVs de perguntas a cada partida: quem editou o banco (Excel,
    # LibreOffice, Bloco de Notas) vê a mudança ao clicar em JOGAR/REINICIAR,
    # sem fechar o jogo. Os mapas já eram relidos em carregar_recursos_jogo.
    todas_perguntas = carregar_perguntas()
    # Partida nova: zera o histórico de perguntas usadas e volta pra fase 1
    # (a região inicial), remontando e embaralhando a lista do quiz.
    _ids_respondidas.clear()
    ordem_resposta = 0
    quiz_tela.reiniciar()
    aplicar_fase(constants.FASE_POR_REGIAO.get(constants.SETOR_INICIAL, 1))
    # Nova partida = nova sessão de estatísticas (o ID é o que a tela de
    # estatísticas usa pra buscar só as respostas DESTA partida, nunca a
    # última do banco inteiro).
    sessao_atual_id = banco_estatisticas.nova_sessao(aluno_atual)
    carregar_recursos_jogo()
    estado_jogo = "JOGANDO"
    tocar_musica(NOME_MUSICA)


def encerrar_jogo():
    banco_estatisticas.fechar()
    pygame.quit()
    sys.exit()


def abrir_login():
    """Abre a tela de registro do nome (clique em JOGAR no menu)."""
    global estado_jogo
    if tela_login:
        tela_login.resetar()
    estado_jogo = "LOGIN"


def sair_do_login():
    """Volta do registro do nome para o menu, desligando a digitação."""
    global estado_jogo
    pygame.key.stop_text_input()
    estado_jogo = "MENU"


def confirmar_login(nome):
    """Guarda o nome digitado (usado no relatório em PDF) e começa a partida."""
    global aluno_atual
    aluno_atual = (nome or "").strip() or "Aluno"
    iniciar_cutscene()


def iniciar_cutscene():
    """Abertura em imagens: roda logo depois do nome e termina em iniciar_jogo().

    REINICIAR (game over) chama iniciar_jogo() direto, então a cutscene só
    aparece uma vez por vez que o jogador clica em JOGAR e registra o nome.
    """
    global estado_jogo
    reiniciar_movimento()
    cutscene.iniciar()
    estado_jogo = "CUTSCENE"


def registrar_pdf_gerado(caminho):
    """Chamado pela TelaEstatisticas assim que um PDF é gerado com sucesso,
    pra sabermos qual arquivo apagar depois (reiniciar / voltar ao menu)."""
    global pdf_estatisticas_atual
    pdf_estatisticas_atual = caminho


def apagar_pdf_estatisticas():
    """Apaga o PDF de estatísticas gerado na sessão que está sendo encerrada.
    Chamado ao reiniciar o jogo e ao voltar pro menu, pra não ficar acumulando
    relatório no disco. Nunca derruba o jogo se falhar (ex.: arquivo ainda
    aberto no leitor de PDF do sistema)."""
    global pdf_estatisticas_atual
    if pdf_estatisticas_atual:
        try:
            if os.path.exists(pdf_estatisticas_atual):
                os.remove(pdf_estatisticas_atual)
        except OSError as e:
            print(f"Aviso: não foi possível apagar o PDF de estatísticas: {e}")
        pdf_estatisticas_atual = None


def abrir_estatisticas():
    """
    Abre a tela de estatísticas com o resultado da sessão ATUAL (nunca a
    última sessão do banco). É chamada tanto quando o jogo termina normalmente
    (GAME_OVER) quanto quando o jogador sai no meio (PAUSADO). Funciona mesmo
    com 0 perguntas respondidas.
    """
    global estado_jogo, tela_estatisticas
    try:
        resultado = banco_estatisticas.buscar_resultado(sessao_atual_id)
    except Exception as e:  # noqa: BLE001 - a tela não pode quebrar o jogo
        print(f"Erro ao carregar estatísticas: {e}")
        resultado = banco_estatisticas.resultado_vazio(aluno_atual)
    tela_estatisticas = TelaEstatisticas(
        screen,
        constants.SCREEN_WIDTH,
        constants.SCREEN_HEIGHT,
        resultado,
        callback_voltar=voltar_menu,
        callback_pdf_gerado=registrar_pdf_gerado,
    )
    estado_jogo = "ESTATISTICAS"


def configurar_jogo():
    global estado_jogo
    estado_jogo = "CONFIGURACOES"


def retomar_jogo():
    global estado_jogo
    estado_jogo = "JOGANDO"


def voltar_menu():
    global estado_jogo, player, world, enemies, itens, curas, boss, quiz_boss
    apagar_pdf_estatisticas()
    player = world = None
    enemies = []
    itens = []
    curas = []
    boss = None
    quiz_boss = None
    estado_jogo = "MENU"
    tocar_musica(NOME_MUSICA)
    restaurar_volume_jogo()


def abrir_creditos():
    global estado_jogo
    estado_jogo = "CREDITOS"


# ── Partida: atualização por frame ───────────────────────────────────────────
# O que antes era um bloco de ~60 linhas dentro do while do __main__ virou
# funções pequenas. Além de ler melhor, isso permite testar/medir a partida
# sem abrir janela (ver testes/teste_benchmark.py). O boss se encaixa aqui
# como mais um inimigo em `enemies` (ver src/setores.py).
def area_ativa():
    """
    Retângulo (no mundo) onde inimigos são atualizados e desenhados: a tela
    da câmera mais uma folga. Fora dele, nada roda — com 21 inimigos
    espalhados por 756 colunas, quase todos estão sempre fora.
    """
    folga = constants.MARGEM_ATIVACAO_TILES * constants.TILE_SIZE
    return pygame.Rect(
        camera_x - folga,
        camera_y - folga,
        constants.SCREEN_WIDTH + 2 * folga,
        constants.SCREEN_HEIGHT + 2 * folga,
    )


def _movimento_do_player():
    """Lê a entrada (teclado + analógico) e devolve o dx deste frame."""
    global jump_pressed
    if player.preso and pygame.time.get_ticks() >= player.preso_ate:
        player.preso = False
    if player.preso:
        # Preso pela Aranha: não anda nem pula até o tempo da prisão acabar.
        jump_pressed = False
        return 0
    if jump_pressed and player.jump():
        jump_pressed = False
    # O teclado produz -1/0/1; o analógico soma um valor contínuo, o que
    # permite andar devagar inclinando pouco o direcional.
    eixo = moving_right - moving_left
    if gamepad.conectado:
        eixo += gamepad.eixo_x
    eixo = max(-1.0, min(1.0, eixo))
    return eixo * constants.PLAYER_SPEED


def _atualizar_inimigos(area):
    """Atualiza só os inimigos ativos e trata os que foram derrotados.

    Inimigo atordoado por um golpe não roda a IA (só desliza o empurrão); o
    golpe de asa é aplicado depois do movimento, sobre os inimigos ativos."""
    for enemy in enemies:
        if not enemy.precisa_atualizar(area):
            continue
        obstaculos = world.obstaculos_proximos(enemy.rect)
        if getattr(enemy, "atordoado_por_golpe", False):
            enemy.atualizar_atordoado(obstaculos)
        else:
            enemy.update(obstaculos, player)
        enemy.check_player_collision(player)
    ativos = [e for e in enemies if e.precisa_atualizar(area)]
    for inimigo, resultado in golpe.atualizar(pygame.time.get_ticks(), player, ativos, efeitos):
        if resultado == "imune" and isinstance(inimigo, Gorila):
            avisar("O golpe nao fere o Gorila: devolva os MINERIOS respondendo!", 2500)
    if any(e.derrotado for e in enemies):
        for enemy in [e for e in enemies if e.derrotado]:
            enemies.remove(enemy)
            ao_inimigo_derrotado(enemy)


def ao_inimigo_derrotado(inimigo):
    """
    Evento de derrota de inimigo. Comum (golpe de asa ou pisão): some com um
    "puf" e fica derrotado só neste setor e nesta partida. Boss: encerra a
    campanha (VITORIA).
    """
    global estado_jogo, boss, selecao_vitoria, inimigos_derrotados
    if constants.DEBUG:
        print(f"[inimigo] {type(inimigo).__name__} derrotado "
              f"(recompensa {inimigo.RECOMPENSA_PONTOS})")
    if not isinstance(inimigo, Gorila):
        efeitos.puf(inimigo.rect)
        inimigos_derrotados += 1
        sons.tocar("pisao")
        return
    if isinstance(inimigo, Gorila):
        if setor_atual is not None and setor_atual.boss is inimigo:
            setor_atual.boss = None
        boss = None
        reiniciar_movimento()
        selecao_vitoria = 0
        try:
            banco_estatisticas.marcar_resultado(sessao_atual_id, "vitoria")
        except Exception as e:  # noqa: BLE001
            print(f"Aviso: não foi possível gravar o resultado da sessão: {e}")
        sons.tocar("vitoria")
        estado_jogo = "VITORIA"


def _verificar_coletas():
    """Minério tocado abre o quiz. Devolve True se o estado mudou."""
    global estado_jogo, item_para_remover
    for cura in curas:
        if cura.verificar_coleta(player):
            avisar(f"+{cura.cura} de vida!", 1200)
    curas[:] = [c for c in curas if not c.coletado]

    for item in itens:
        if not item.verificar_coleta(player):
            continue
        if indice >= len(perguntas):
            # A fatia da fase acabou: remonta com o que ainda não foi
            # respondido (o filtro cai para outras dificuldades e, no limite,
            # para o banco inteiro). Antes o minério sumia sem pergunta.
            aplicar_fase(fase_atual)
        if indice < len(perguntas):
            estado_jogo = "QUIZ"
            quiz_tela.reiniciar()
            reiniciar_movimento()
            item_para_remover = item
            abaixar_volume_quiz()
            return True
        # Banco vazio (CSV ilegível e sem fallback): o minério fica no mapa.
        item.liberar()
        avisar("Nenhuma pergunta disponivel - confira os CSVs (validar_dados.py)")
        return False
    return False


def _limitar_player_ao_setor():
    """
    Parede invisível nas bordas laterais do setor.

    O redesign tirou as colunas de rocha das bordas da floresta, das copas e
    da arena; sem elas, segurar para a esquerda no spawn levava a Areninha
    para fora do mapa (x < 0), onde não há chão, e o jogo dava GAME OVER.
    Limitar aqui protege todos os CSVs sem mexer na geometria nem na arte.
    """
    largura = setor_atual.largura_px if setor_atual else None
    if not largura:
        return
    if player.rect.left < 0:
        player.rect.left = 0
        player.pos_x = float(player.rect.x)
    elif player.rect.right > largura:
        player.rect.right = largura
        player.pos_x = float(player.rect.x)


def atualizar_jogando(dt_ms):
    """Um frame de partida: player, câmera, inimigos, coleta e passagens."""
    global estado_jogo
    if transicao.ativa:
        # Fade em andamento: nada de física, inimigo ou item. O callback
        # (reposicionar + trocar ambiente) roda dentro de transicao.atualizar().
        transicao.atualizar(dt_ms)
        return

    player.move(_movimento_do_player(), world.obstaculos_proximos(player.rect))
    _limitar_player_ao_setor()
    atualizar_camera()
    player.update_invulnerable()
    _checar_inicio_da_luta()
    _atualizar_inimigos(area_ativa())
    _avisos_do_boss()
    if estado_jogo != "JOGANDO":       # boss derrotado -> VITORIA
        return
    if boss is not None and boss.minerio_atingiu_player is not None:
        projetil = boss.minerio_atingiu_player
        boss.minerio_atingiu_player = None
        if player.alive:
            iniciar_quiz_boss(boss, projetil)
            if estado_jogo == "QUIZ":
                return
    if _verificar_coletas():
        return

    if not player.alive or player.rect.top > setor_atual.altura_px:
        _fim_de_jogo()
    else:
        _checar_passagens()
        _checar_npcs()


def passo_da_partida(dt_ms):
    """
    Lógica por frame dos estados da partida (JOGANDO, QUIZ, QUIZ_FEEDBACK).
    Saiu do while do __main__ para que os testes rodem EXATAMENTE o mesmo
    código do jogo (ver testes/teste_boss.py).
    """
    global quiz_timer, quiz_mensagem, estado_jogo
    if quiz_timer > 0:
        quiz_timer -= 1
        if quiz_timer == 0 and estado_jogo not in ("QUIZ_FEEDBACK", "QUIZ"):
            quiz_mensagem = ""

    if estado_jogo == "JOGANDO" and player:
        atualizar_jogando(dt_ms)

    # Prazo da pergunta do minério do boss.
    if (estado_jogo == "QUIZ" and quiz_boss is not None
            and pygame.time.get_ticks() >= quiz_boss["prazo"]):
        processar_resposta("")

    if estado_jogo == "QUIZ_FEEDBACK" and quiz_timer == 0:
        quiz_mensagem = ""
        if player and not player.alive:
            _fim_de_jogo()
        else:
            estado_jogo = "JOGANDO"


def _fim_de_jogo():
    global estado_jogo, morreu_na_arena, selecao_game_over
    morreu_na_arena = luta_em_andamento()
    selecao_game_over = 0
    reiniciar_movimento()
    if sessao_atual_id is not None:
        try:
            banco_estatisticas.marcar_resultado(
                sessao_atual_id, "derrota no boss" if morreu_na_arena else "derrota")
        except Exception as e:  # noqa: BLE001
            print(f"Aviso: não foi possível gravar o resultado da sessão: {e}")
    estado_jogo = "GAME_OVER"


# ── Partida: desenho ─────────────────────────────────────────────────────────
_cache_overlays = {}
_cache_textos = {}


def overlay(cor_rgba):
    """Véu translúcido do tamanho da tela, criado uma vez por cor."""
    chave = (cor_rgba, constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
    surf = _cache_overlays.get(chave)
    if surf is None:
        surf = pygame.Surface(chave[1:], pygame.SRCALPHA)
        surf.fill(cor_rgba)
        _cache_overlays[chave] = surf
    return surf


def texto(fonte, conteudo, cor):
    """
    font.render com cache. HUD e avisos redesenham o MESMO texto a cada
    frame; renderizar fonte é das operações mais caras do pygame.
    """
    chave = (id(fonte), conteudo, cor)
    surf = _cache_textos.get(chave)
    if surf is None:
        if len(_cache_textos) > 256:
            _cache_textos.clear()
        surf = fonte.render(conteudo, True, cor)
        _cache_textos[chave] = surf
    return surf


def desenhar_barra_vida(surface, x, y, largura, altura, proporcao,
                        cor_cheia=constants.GREEN, cor_vazia=constants.RED):
    """Barra de vida genérica (jogador e boss)."""
    proporcao = max(0.0, min(1.0, proporcao))
    pygame.draw.rect(surface, cor_vazia, (x, y, largura, altura), border_radius=4)
    pygame.draw.rect(surface, cor_cheia, (x, y, int(largura * proporcao), altura),
                     border_radius=4)
    pygame.draw.rect(surface, constants.WHITE, (x, y, largura, altura), 2,
                     border_radius=4)


def _desenhar_cena(area):
    """Mundo e entidades, com culling pela área visível."""
    desenhar_paralaxe(camera_x, player.rect.centery if player else None, camera_y)
    if setor_atual and hasattr(setor_atual, "estruturas"):
        setor_atual.estruturas.render(screen, camera_x, camera_y)
    if setor_atual and hasattr(setor_atual, "decoracoes"):
        setor_atual.decoracoes.render(screen, camera_x, camera_y)
    if world:
        world.render(screen, camera_x, camera_y)
    if passagens_cenario:
        # Depois do mundo e antes das entidades: o player passa NA FRENTE da
        # entrada, e a entrada na frente do terreno.
        passagens_cenario.desenhar(
            screen, camera_x, camera_y, pygame.time.get_ticks() / 1000.0
        )
    if setor_atual is not None and setor_atual.npcs.itens and player:
        setor_atual.npcs.desenhar(screen, camera_x, camera_y, area, contexto_npcs(),
                                  falando_com=dialogo["npc"] if dialogo else None)
    for enemy in enemies:
        if area.colliderect(enemy.area_desenho()):
            enemy.draw(screen, camera_x, camera_y)
            enemy.desenhar_feedback(screen, camera_x, camera_y)
    for item in itens:
        if area.colliderect(item.rect):
            item.draw(screen, camera_x, camera_y)
    for cura in curas:
        if area.colliderect(cura.rect):
            cura.draw(screen, camera_x, camera_y)
    if player and player.alive:
        player.draw(screen, camera_x, camera_y)
        golpe.desenhar(screen, camera_x, camera_y, player)
    efeitos.desenhar(screen, camera_x, camera_y)
    if ambientes:
        # Tonalidade, luz e partículas: depois da cena e antes da HUD, porque
        # escurecer a caverna faz sentido, escurecer a barra de vida não.
        ambientes.desenhar_atmosfera(screen, camera_x, camera_y)
    if constants.DEBUG and area_boss:
        pygame.draw.rect(screen, (255, 60, 60),
                         area_boss["rect"].move(-camera_x, -camera_y), 2)


def _desenhar_aviso_passagem():
    W, H = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
    botao = "X" if gamepad.conectado else "E"
    aviso = texto(fonte_titulo, f"{botao} - {passagem_ao_alcance.rotulo}",
                  constants.YELLOW)
    caixa = aviso.get_rect(center=(W // 2, H - sy(70)))
    fundo = pygame.Surface((caixa.width + sx(28), caixa.height + sy(16)),
                           pygame.SRCALPHA)
    fundo.fill((0, 0, 0, 170))
    screen.blit(fundo, fundo.get_rect(center=caixa.center))
    screen.blit(aviso, caixa)


def _desenhar_aviso_npc():
    W, H = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
    botao = "X" if gamepad.conectado else "E"
    aviso = texto(fonte_titulo, f"{botao} - Conversar com {npc_ao_alcance.nome}",
                  constants.YELLOW)
    caixa = aviso.get_rect(center=(W // 2, H - sy(70)))
    fundo = pygame.Surface((caixa.width + sx(28), caixa.height + sy(16)), pygame.SRCALPHA)
    fundo.fill((0, 0, 0, 170))
    screen.blit(fundo, fundo.get_rect(center=caixa.center))
    screen.blit(aviso, caixa)


def _quebrar_linhas(fonte, conteudo, largura):
    palavras, linhas, atual = conteudo.split(), [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if fonte.size(teste)[0] <= largura or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def _desenhar_dialogo():
    """Caixa de fala na base da tela: retrato, nome e a linha atual."""
    W, H = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
    npc = dialogo["npc"]
    larg, alt = min(W - sx(40), sx(720)), sy(132)
    caixa = pygame.Rect((W - larg) // 2, H - alt - sy(18), larg, alt)
    fundo = pygame.Surface(caixa.size, pygame.SRCALPHA)
    fundo.fill((14, 12, 20, 225))
    screen.blit(fundo, caixa)
    pygame.draw.rect(screen, (241, 187, 52), caixa, 3)
    # retrato: o quadro parado do NPC, ampliado
    retrato = npc.frames[0]
    escala = (alt - sy(24)) / retrato.get_height()
    retrato = pygame.transform.scale(
        retrato, (max(1, int(retrato.get_width() * escala)), max(1, int(retrato.get_height() * escala))))
    ret_r = retrato.get_rect(midleft=(caixa.left + sx(14), caixa.centery))
    pygame.draw.rect(screen, (40, 52, 44), ret_r.inflate(sx(8), sy(8)))
    screen.blit(retrato, ret_r)
    x0 = ret_r.right + sx(18)
    screen.blit(texto(fonte_titulo, npc.nome, constants.YELLOW), (x0, caixa.top + sy(12)))
    y = caixa.top + sy(40)
    for linha in _quebrar_linhas(fonte_titulo, dialogo["linhas"][dialogo["i"]], caixa.right - x0 - sx(16))[:3]:
        screen.blit(texto(fonte_titulo, linha, constants.WHITE), (x0, y))
        y += fonte_titulo.get_linesize()
    botao = "X" if gamepad.conectado else "E"
    fim = dialogo["i"] + 1 >= len(dialogo["linhas"])
    dica = texto(fonte_titulo, f"{botao} - {'fechar' if fim else 'continuar'}  "
                 f"({dialogo['i'] + 1}/{len(dialogo['linhas'])})", (200, 200, 200))
    screen.blit(dica, dica.get_rect(bottomright=(caixa.right - sx(12), caixa.bottom - sy(8))))


def desenhar_hud_boss():
    """Nome + barra de vida do boss (sincronizada com boss.vida) no topo."""
    if boss is None or not boss.ativo:
        return
    W = constants.SCREEN_WIDTH
    larg = min(sx(420), W - sx(460))
    x = (W - larg) // 2
    y = sy(14)
    nome = texto(fonte_titulo, f"{boss.NOME}  -  FASE {boss.fase}", constants.YELLOW)
    screen.blit(nome, nome.get_rect(midbottom=(W // 2, y + sy(16))))
    desenhar_barra_vida(screen, x, y + sy(20), larg, sy(16), boss.proporcao_vida,
                        cor_cheia=(200, 60, 40), cor_vazia=(50, 20, 20))
    # Marcas de cada ponto de vida: mostram quantos minérios faltam.
    for i in range(1, boss.VIDA_MAX):
        mx = x + larg * i // boss.VIDA_MAX
        pygame.draw.line(screen, (20, 10, 10), (mx, y + sy(21)), (mx, y + sy(34)), 1)
    devolvidos = boss.VIDA_MAX - boss.vida
    cont = texto(fonte_titulo, f"MINERIOS DEVOLVIDOS {devolvidos}/{boss.VIDA_MAX}", (230, 210, 170))
    screen.blit(cont, cont.get_rect(midtop=(W // 2, y + sy(40))))
    if boss.estado == "ATORDOADO":
        st = texto(fonte_titulo, "ATORDOADO!", (255, 230, 120))
        screen.blit(st, st.get_rect(midtop=(W // 2, y + sy(62))))
    agora = pygame.time.get_ticks()
    # Faixa de troca de fase
    anuncio = getattr(boss, "anuncio", None)
    if anuncio and agora < anuncio[1]:
        restante = anuncio[1] - agora
        alpha = 255 if restante > 400 else int(255 * restante / 400)
        faixa = pygame.Surface((W, sy(64)), pygame.SRCALPHA)
        faixa.fill((90, 10, 10, min(200, alpha)))
        yf = constants.SCREEN_HEIGHT // 2 - sy(120)
        screen.blit(faixa, (0, yf))
        msg = fonte_ui.render(anuncio[0], True, (255, 220, 90))
        sombra = fonte_ui.render(anuncio[0], True, (40, 0, 0))
        msg.set_alpha(alpha)
        sombra.set_alpha(alpha)
        r = msg.get_rect(center=(W // 2, yf + sy(32)))
        screen.blit(sombra, r.move(3, 3))
        screen.blit(msg, r)
    # Balão de fala sobre o Gorila (posição no mundo -> tela)
    fala = getattr(boss, "fala", None)
    if fala and agora < fala[1]:
        surf = texto(fonte_titulo, fala[0], (30, 20, 20))
        cx = boss.rect.centerx - camera_x
        topo = boss.rect.top - camera_y - sy(16)
        caixa = surf.get_rect(midbottom=(cx, topo)).inflate(sx(18), sy(12))
        caixa.clamp_ip(pygame.Rect(sx(6), sy(90), W - sx(12), constants.SCREEN_HEIGHT))
        pygame.draw.rect(screen, (28, 20, 24), caixa.inflate(6, 6))
        pygame.draw.rect(screen, (250, 246, 230), caixa)
        bico_x = max(caixa.left + 12, min(caixa.right - 12, cx))
        pygame.draw.polygon(screen, (250, 246, 230),
                            [(bico_x - 7, caixa.bottom), (bico_x + 7, caixa.bottom), (bico_x, caixa.bottom + 10)])
        screen.blit(surf, surf.get_rect(center=caixa.center))


def _desenhar_aviso_jogo():
    msg, ate = aviso_jogo
    if not msg or pygame.time.get_ticks() >= ate:
        return
    W, H = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
    surf = texto(fonte_titulo, msg, constants.WHITE)
    if surf.get_width() > W - sx(40):
        surf = pygame.transform.smoothscale(
            surf, (W - sx(40), max(1, int(surf.get_height() * (W - sx(40)) / surf.get_width()))))
    caixa = surf.get_rect(center=(W // 2, H - sy(110)))
    fundo = pygame.Surface((caixa.width + sx(24), caixa.height + sy(12)), pygame.SRCALPHA)
    fundo.fill((0, 0, 0, 180))
    screen.blit(fundo, fundo.get_rect(center=caixa.center))
    screen.blit(surf, caixa)


def desenhar_hud():
    W = constants.SCREEN_WIDTH
    if constants.DEBUG and ambientes:
        dbg = fonte_titulo.render(
            f"{ambientes.nome_atual}  {ambientes.mistura:.0%}", True, constants.YELLOW
        )
        screen.blit(dbg, (sx(10), sy(70)))
    dica = ("Start = Pausa   B = Golpe" if gamepad.conectado
            else "ESC = Pausa   J = Golpe")
    screen.blit(texto(fonte_titulo, dica, constants.WHITE), (sx(10), sy(10)))
    if passagem_ao_alcance and estado_jogo == "JOGANDO" and not transicao.ativa:
        _desenhar_aviso_passagem()
    elif npc_ao_alcance and not dialogo and estado_jogo == "JOGANDO" and not transicao.ativa:
        _desenhar_aviso_npc()
    if dialogo and not transicao.ativa:
        _desenhar_dialogo()
    if player and player.alive:
        desenhar_barra_vida(
            screen, sx(10), sy(35), sx(200), sy(18),
            player.player_health / constants.PLAYER_HEALTH,
        )
        pontos = texto(fonte_ui, f"Pontos: {pontuacao}", constants.WHITE)
        screen.blit(pontos, (W - pontos.get_width() - sx(14), sy(10)))
    desenhar_hud_boss()
    _desenhar_aviso_jogo()


def desenhar_jogo(mouse_pos):
    """Frame dos estados JOGANDO e PAUSADO."""
    global camera_x, camera_y
    W = constants.SCREEN_WIDTH
    # Tremor de câmera pedido pelo boss (rugido, pancada) — só no desenho,
    # a posição real da câmera não muda.
    tremor = boss.tremor if (boss is not None and estado_jogo == "JOGANDO") else 0
    if tremor:
        dx = random.randint(-tremor, tremor)
        dy = random.randint(-tremor, tremor)
        camera_x += dx
        camera_y += dy
        _desenhar_cena(area_ativa())
        camera_x -= dx
        camera_y -= dy
    else:
        _desenhar_cena(area_ativa())
    desenhar_hud()
    if estado_jogo == "PAUSADO":
        screen.blit(overlay((0, 0, 0, 160)), (0, 0))
        surf = texto(fonte_ui, "PAUSADO", constants.YELLOW)
        screen.blit(surf, surf.get_rect(center=(W // 2, sy(150))))
        for botao in botoes_pausa:
            botao.desenhar(screen, posicao_de_foco(botoes_pausa, selecao_pausa, mouse_pos))
    if transicao:
        # Última camada: o fade precisa esconder a cena inteira, HUD incluída.
        transicao.desenhar(screen)


def desenhar_vitoria(mouse_pos):
    W, H = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
    screen.blit(background_img, (0, 0))
    screen.blit(overlay((10, 20, 0, 175)), (0, 0))
    titulo = fonte_logo.render("VITORIA!", True, constants.YELLOW)
    sombra = fonte_logo.render("VITORIA!", True, (60, 40, 0))
    screen.blit(sombra, sombra.get_rect(center=(W // 2 + 4, sy(110) + 4)))
    screen.blit(titulo, titulo.get_rect(center=(W // 2, sy(110))))
    linhas = [
        f"{aluno_atual}, o Gorila Guardiao foi derrotado!",
        "Os minerios da floresta estao a salvo.",
        f"Acertos: {pontuacao}   |   Perguntas respondidas: {ordem_resposta}",
        f"Inimigos derrotados: {inimigos_derrotados}",
    ]
    y = sy(185)
    for linha in linhas:
        surf = texto(fonte_titulo, linha, constants.WHITE)
        screen.blit(surf, surf.get_rect(center=(W // 2, y)))
        y += sy(36)
    for botao in botoes_vitoria:
        botao.desenhar(screen, posicao_de_foco(botoes_vitoria, selecao_vitoria, mouse_pos))


# ── Loop principal ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    pygame.init()
    try:
        mixer.init()
    except Exception as e:
        print(f"Mixer não inicializado: {e}")
    sons.iniciar()
    sons.definir_volume(VOLUME_EFEITOS_CONFIG)
    configurar_janela(fullscreen=False)
    pygame.display.set_caption("I.S.A - Intelligent Support Agent")
    clock = pygame.time.Clock()
    # SCREEN_WIDTH/HEIGHT permanecem 800x600 durante toda a execução:
    # a superfície virtual é que define o espaço lógico do jogo.
    tela_carregamento(screen, 0.0, "Inicializando...")

    # O gamepad é opcional: se não houver controle plugado, `conectado` fica
    # False e o jogo segue 100% no teclado/mouse. Plugar no meio da partida
    # funciona — o JOYDEVICEADDED é tratado em processar_evento.
    gamepad = GerenciadorJoystick()

    recriar_ui()
    inicializar_intro()
    tocar_musica(NOME_MUSICA)  # música inicial, já que o jogo abre no MENU

    tela_login = TelaLogin(
        screen,
        callback_voltar=voltar_menu,
        callback_entrar=confirmar_login,
        callback_config=configurar_jogo,
    )
    # Ao terminar (ou pular), a cutscene inicia a partida de fato.
    cutscene = Cutscene(
        constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT, callback_fim=iniciar_jogo
    )
    tela_configuracoes = TelaConfiguracoes(
        screen,
        constants.SCREEN_WIDTH,
        constants.SCREEN_HEIGHT,
        callback_voltar=voltar_menu,
        callback_creditos=abrir_creditos,
        # Antes este callback não era passado aqui (e era um lambda vazio no
        # handler do F11), então o botão da tela de configurações não fazia nada.
        callback_toggle_fullscreen=alternar_fullscreen,
        callback_volume_musica=aplicar_volume_musica,
        callback_volume_efeitos=aplicar_volume_efeitos,
    )

    # Mapa de teclas de letra -> resposta (além dos números 1-5)
    TECLAS_LETRA = {
        pygame.K_a: "a",
        pygame.K_b: "b",
        pygame.K_c: "c",
        pygame.K_d: "d",
        pygame.K_e: "e",
    }
    # Interagir com o cenário (entrar numa passagem). Fica junto do pulo/ESC
    # para quem joga só de teclado não precisar tirar a mão do WASD.
    TECLAS_INTERAGIR = (pygame.K_e, pygame.K_RETURN)

    TECLAS_NUMERO = {
        pygame.K_1: "a",
        pygame.K_2: "b",
        pygame.K_3: "c",
        pygame.K_4: "d",
        pygame.K_5: "e",
    }

    run = True
    while run:
        dt_ms = clock.tick(constants.FPS)
        mouse_pos = mouse_virtual()
        # Borda, não estado: zera aqui, os eventos ligam, _checar_passagens
        # consome. Sem isso, segurar E entraria na passagem, sairia e entraria
        # de novo a cada frame.
        interagir_pressionado = False

        for event in pygame.event.get():
            event = converter_evento(event)
            if event.type == pygame.QUIT:
                run = False
            gamepad.processar_evento(event)
            if event.type == pygame.MOUSEMOTION:
                # Mexeu o mouse: o destaque volta a seguir o cursor.
                foco_no_controle = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                # Antes este bloco tinha ~37 linhas: recriava interface, fontes,
                # botões, intro, tela de login, de configurações e de créditos,
                # e ainda congelava o jogo por 500ms com a tela de carregamento.
                # Nada disso é necessário — só a janela real muda de tamanho.
                alternar_fullscreen()
            elif estado_jogo == "MENU":
                for botao in botoes_menu:
                    botao.verificar_click(event)
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                ):  # ← linha nova
                    processar_clique_intro(event.pos)  # ← linha nova
            elif estado_jogo == "JOGANDO":
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_a, pygame.K_LEFT):
                        moving_left = True
                    if event.key in (pygame.K_d, pygame.K_RIGHT):
                        moving_right = True
                    if event.key in (pygame.K_w, pygame.K_UP, pygame.K_SPACE):
                        jump_pressed = True
                    if event.key in TECLAS_INTERAGIR:
                        interagir_pressionado = True
                    if event.key in TECLAS_GOLPE:
                        golpe.pedir()
                    # Antes este teste estava (por erro de indentação) dentro
                    # do ramo do JOYBUTTONDOWN: ESC não pausava pelo teclado
                    # e o botão de interagir do controle lia `event.key`
                    # num evento de joystick (AttributeError -> crash).
                    if event.key == pygame.K_ESCAPE and not transicao.ativa:
                        estado_jogo = "PAUSADO"
                        reiniciar_movimento()
                        selecao_pausa = 0
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Ataque apenas na partida; menus e quiz mantêm o clique normal.
                    # Usa o mesmo buffer/cooldown do teclado e controle.
                    if not transicao.ativa:
                        golpe.pedir()
                elif (event.type == pygame.JOYBUTTONDOWN
                      and event.button == constants.JOY_BOTAO_INTERAGIR):
                    interagir_pressionado = True
                elif event.type == pygame.KEYUP:
                    if event.key in (pygame.K_a, pygame.K_LEFT):
                        moving_left = False
                    if event.key in (pygame.K_d, pygame.K_RIGHT):
                        moving_right = False
            elif estado_jogo == "QUIZ":
                if event.type == pygame.MOUSEWHEEL:
                    quiz_tela.rolar(-event.y * 25)

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Clique numa alternativa: só conta se estiver dentro da
                    # área visível (recortada) do conteúdo, senão dá pra
                    # "clicar" numa alternativa escondida pelo scroll.
                    letra = quiz_tela.alternativa_em(event.pos)
                    if letra:
                        processar_resposta(letra)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        cancelar_quiz()   # só o quiz normal; o do boss ignora
                        continue
                    resposta = TECLAS_NUMERO.get(event.key) or TECLAS_LETRA.get(
                        event.key
                    )
                    if resposta:
                        processar_resposta(resposta)

            elif estado_jogo == "PAUSADO":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    estado_jogo = "JOGANDO"
                for botao in botoes_pausa:
                    botao.verificar_click(event)
            elif estado_jogo == "GAME_OVER":
                for botao in (botoes_game_over_boss if morreu_na_arena else botoes_game_over):
                    botao.verificar_click(event)
            elif estado_jogo == "VITORIA":
                for botao in botoes_vitoria:
                    botao.verificar_click(event)
            elif estado_jogo == "QUIZ_FEEDBACK":
                pass
            elif estado_jogo == "LOGIN":
                tela_login.handle_event(event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    sair_do_login()
            elif estado_jogo == "CUTSCENE":
                cutscene.handle_event(event)
            elif estado_jogo == "CONFIGURACOES":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    estado_jogo = "MENU"
                tela_configuracoes.handle_event(event)
            elif estado_jogo == "CREDITOS":
                tela_creditos.handle_event(event)
            elif estado_jogo == "ESTATISTICAS":
                if tela_estatisticas:
                    tela_estatisticas.handle_event(event)

        # ── Entrada do controle ───────────────────────────────────────────────
        # Lida por polling, uma vez por frame: analógico é estado contínuo, não
        # gera evento quando fica parado numa posição. O resultado se soma ao
        # teclado, então dá pra usar os dois ao mesmo tempo.
        gamepad.atualizar()
        if gamepad.conectado:
            if (
                gamepad.nav_x
                or gamepad.nav_y
                or gamepad.confirmou_agora
                or gamepad.voltou_agora
                or gamepad.pausou_agora
            ):
                foco_no_controle = True

            if estado_jogo == "JOGANDO":
                if (gamepad.acabou_de_apertar(constants.JOY_BOTAO_ATAQUE)
                        or gamepad.acabou_de_apertar(constants.JOY_BOTAO_ATAQUE_ALT)):
                    golpe.pedir()
                if gamepad.pulou_agora:
                    jump_pressed = True
                if gamepad.pausou_agora and not transicao.ativa:
                    estado_jogo = "PAUSADO"
                    reiniciar_movimento()
                    selecao_pausa = 0
            elif estado_jogo == "MENU":
                selecao_menu = navegar_menu(botoes_menu, selecao_menu, gamepad)
                if gamepad.confirmou_agora:
                    acionar(botoes_menu, selecao_menu)
            elif estado_jogo == "PAUSADO":
                if gamepad.pausou_agora or gamepad.voltou_agora:
                    estado_jogo = "JOGANDO"
                else:
                    selecao_pausa = navegar_menu(botoes_pausa, selecao_pausa, gamepad)
                    if gamepad.confirmou_agora:
                        acionar(botoes_pausa, selecao_pausa)
            elif estado_jogo == "GAME_OVER":
                lista = botoes_game_over_boss if morreu_na_arena else botoes_game_over
                selecao_game_over = navegar_menu(lista, selecao_game_over, gamepad)
                if gamepad.confirmou_agora:
                    acionar(lista, selecao_game_over)
            elif estado_jogo == "VITORIA":
                selecao_vitoria = navegar_menu(botoes_vitoria, selecao_vitoria, gamepad)
                if gamepad.confirmou_agora:
                    acionar(botoes_vitoria, selecao_vitoria)
            elif estado_jogo == "QUIZ":
                if gamepad.nav_y:
                    quiz_tela.navegar(gamepad.nav_y)
                if gamepad.scroll:
                    quiz_tela.rolar(gamepad.scroll * constants.JOY_SCROLL_PASSO)
                if gamepad.confirmou_agora:
                    letra_escolhida = quiz_tela.letra_selecionada()
                    if letra_escolhida:
                        processar_resposta(letra_escolhida)
                elif (gamepad.voltou_agora
                      and pygame.time.get_ticks() - golpe.inicio > 600):
                    # B também é o golpe: um B dado para atacar no instante em
                    # que o minério foi tocado não fecha a pergunta recém-aberta.
                    cancelar_quiz()
            elif estado_jogo == "CUTSCENE":
                if gamepad.confirmou_agora:
                    cutscene.avancar()
                elif gamepad.voltou_agora or gamepad.pausou_agora:
                    cutscene.pular()
            elif estado_jogo in ("CONFIGURACOES", "LOGIN", "CREDITOS", "ESTATISTICAS"):
                # Essas telas têm campos de texto, sliders e scroll próprios; o
                # controle só oferece a saída, o resto continua no mouse/teclado.
                if gamepad.voltou_agora:
                    if estado_jogo == "ESTATISTICAS":
                        voltar_menu()
                    elif estado_jogo == "LOGIN":
                        sair_do_login()
                    else:
                        estado_jogo = "MENU"

        # Atualização
        if estado_jogo == "MENU":
            atualizar_intro()
        elif estado_jogo == "CUTSCENE":
            cutscene.atualizar(dt_ms)
        else:
            passo_da_partida(dt_ms)

        # Renderização
        W, H = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
        if estado_jogo == "MENU":
            screen.blit(background_img, (0, 0))
            titulo = fonte_logo.render("I . S . A", True, constants.YELLOW)
            sombra = fonte_logo.render("I . S . A", True, (60, 40, 0))
            centro = (W // 2, sy(110))
            screen.blit(sombra, sombra.get_rect(center=(centro[0] + 4, centro[1] + 4)))
            screen.blit(titulo, titulo.get_rect(center=centro))
            for botao in botoes_menu:
                botao.desenhar(screen, posicao_de_foco(botoes_menu, selecao_menu, mouse_pos))
            desenhar_intro(mouse_pos)  # ← personagem por cima dos botões
        elif estado_jogo in ("JOGANDO", "PAUSADO"):
            desenhar_jogo(mouse_pos)
        elif estado_jogo == "QUIZ":
            try:
                if pergunta_em_jogo() is not None:
                    quiz_tela.desenhar(
                        screen,
                        pergunta_em_jogo(),
                        pontuacao,
                        0 if quiz_boss else indice,
                        1 if quiz_boss else len(perguntas),
                        quiz_mensagem,
                        quiz_timer,
                        # Quem manda no destaque: o controle ou o mouse.
                        # Antes era lido de uma global; agora entra como
                        # parâmetro, e a tela não conhece mais o main.
                        foco_no_controle=foco_no_controle,
                        segundos_restantes=segundos_restantes_boss(),
                    )
                else:
                    # Não deveria acontecer (a coleta já checa), mas se
                    # acontecer não pode sair daqui com a música baixa.
                    estado_jogo = "JOGANDO"
                    restaurar_volume_jogo()
            except Exception as e:
                print(f"Erro ao desenhar pergunta: {e}")
                estado_jogo = "JOGANDO"
                restaurar_volume_jogo()
        elif estado_jogo == "QUIZ_FEEDBACK":
            W2, H2 = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
            screen.blit(overlay((0, 0, 0, 220)), (0, 0))
            cor_fb = (76, 175, 80) if "ACERTOU" in quiz_mensagem else (244, 67, 54)
            fonte_fb = carregar_fonte("upheavtt.ttf", sf(32))
            msg_fb = fonte_fb.render(quiz_mensagem, True, cor_fb)
            screen.blit(msg_fb, msg_fb.get_rect(center=(W2 // 2, H2 // 2)))
            fonte_sub = carregar_fonte("upheavtt.ttf", sf(16))
            sub = fonte_sub.render("Voltando ao jogo...", True, (200, 200, 200))
            screen.blit(sub, sub.get_rect(center=(W2 // 2, H2 // 2 + sy(60))))

        elif estado_jogo == "GAME_OVER":
            screen.blit(background_img, (0, 0))
            screen.blit(overlay((0, 0, 0, 160)), (0, 0))
            surf = fonte_ui.render("GAME OVER", True, constants.RED)
            screen.blit(surf, surf.get_rect(center=(W // 2, sy(150))))
            score_surf = fonte_ui.render(
                f"Pontuacao Final: {pontuacao}", True, constants.YELLOW
            )
            screen.blit(score_surf, score_surf.get_rect(center=(W // 2, sy(200))))
            if morreu_na_arena:
                dica = fonte_titulo.render("O Gorila venceu desta vez...", True, constants.WHITE)
                screen.blit(dica, dica.get_rect(center=(W // 2, sy(238))))
            lista = botoes_game_over_boss if morreu_na_arena else botoes_game_over
            for botao in lista:
                botao.desenhar(
                    screen,
                    posicao_de_foco(lista, selecao_game_over, mouse_pos),
                )
        elif estado_jogo == "VITORIA":
            desenhar_vitoria(mouse_pos)
        elif estado_jogo == "LOGIN":
            tela_login.desenhar(mouse_pos)
        elif estado_jogo == "CUTSCENE":
            cutscene.desenhar(screen, mouse_pos, foco_no_controle)
        elif estado_jogo == "CONFIGURACOES":
            tela_configuracoes.desenhar()
        elif estado_jogo == "CREDITOS":
            screen.blit(background_img, (0, 0))
            tela_creditos.update()
            tela_creditos.desenhar(mouse_pos)
        elif estado_jogo == "ESTATISTICAS":
            if tela_estatisticas:
                tela_estatisticas.desenhar(mouse_pos)
        apresentar()
    banco_estatisticas.fechar()
    pygame.quit()