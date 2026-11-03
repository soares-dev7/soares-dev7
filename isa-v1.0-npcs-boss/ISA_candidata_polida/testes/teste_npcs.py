"""
Teste headless dos NPCs (src/npcs.py + assets/levels/npcs.json).

Roda o MESMO código do jogo (main.atualizar_jogando / desenhar_jogo).
Cobre: dados e sprites carregam; posicionamento válido (chão, longe de
passagens e minérios); conversa com E avança e fecha; afastar fecha;
passagem ao alcance tem prioridade; falas mudam com o progresso
(minérios coletados, setor visitado); recompensa (maçã) é entregue uma
única vez e cai em chão alcançável; desenho do aviso, do balão e da caixa.

Uso (na raiz do projeto):  python testes/teste_npcs.py
"""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("ISA_DB", os.path.join(tempfile.mkdtemp(prefix="isa_teste_npc_"), "e.db"))
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import pygame  # noqa: E402

import constants  # noqa: E402
import main as M  # noqa: E402
from src.joystick import GerenciadorJoystick  # noqa: E402
from src.npcs import validar_npcs  # noqa: E402
from utils import carregar_nivel_csv  # noqa: E402

T = constants.TILE_SIZE


def ok(msg):
    print("ok:", msg)


def preparar():
    pygame.init()
    M.configurar_janela()
    M.clock = pygame.time.Clock()
    M.gamepad = GerenciadorJoystick()
    M.recriar_ui()
    M.iniciar_jogo()
    M.estado_jogo = "JOGANDO"


def frame(n=1, apertar=False):
    for i in range(n):
        M.interagir_pressionado = apertar and i == 0
        M.atualizar_jogando(16)
        M.desenhar_jogo((0, 0))
    M.interagir_pressionado = False


def junto_de(npc, dx_tiles=0.8):
    p = M.player
    p.rect.midbottom = (npc.rect.centerx - int(dx_tiles * T), npc.rect.bottom)
    p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y)
    p.vel_y = 0
    M.reiniciar_movimento()
    M.atualizar_camera(instantaneo=True)


def npc(setor, ident):
    M.ativar_setor(setor)
    return next(n for n in M.setor_atual.npcs.itens if n.id == ident)


def teste_dados_e_posicionamento():
    total = 0
    for nome, setor in M.setores.items():
        grade = carregar_nivel_csv(os.path.join(constants.PASTA_SETORES, f"{nome}.csv"))
        problemas = validar_npcs(nome, grade, setor.npcs.itens)
        assert not problemas, problemas
        for n in setor.npcs.itens:
            assert len(n.frames) == 3 and n.frames[0].get_height() >= 60, (n.id, n.frames[0].get_size())
        total += len(setor.npcs)
    assert total == 5, total
    assert {n.id for s in M.setores.values() for n in s.npcs.itens} == \
        {"taina", "benedito", "ana", "lia", "diretor"}
    ok(f"{total} NPCs carregados; todos no chao, longe de passagens/chegadas e minerios")


def teste_conversa_avanca_e_fecha():
    t = npc("floresta", "taina")
    junto_de(t)
    frame()
    assert M.npc_ao_alcance is t, "NPC nao detectado ao alcance"
    frame(apertar=True)
    assert M.dialogo and M.dialogo["npc"] is t and M.dialogo["i"] == 0
    n = len(M.dialogo["linhas"])
    assert n == 4 and "Taina" in M.dialogo["linhas"][0]
    for i in range(1, n):
        frame(apertar=True)
        assert M.dialogo["i"] == i
    frame(apertar=True)
    assert M.dialogo is None, "conversa nao fechou no fim"
    # afastar fecha
    frame(apertar=True)
    assert M.dialogo is not None
    junto_de(t, dx_tiles=6)
    frame()
    assert M.dialogo is None, "conversa nao fechou ao se afastar"
    ok("E abre, avanca linha a linha e fecha; afastar-se fecha a conversa")


def teste_falas_mudam_com_progresso():
    t = npc("floresta", "taina")
    junto_de(t)
    guardados = list(M.setor_atual.itens)
    del M.setor_atual.itens[:4]            # 4 minérios "coletados"
    try:
        frame()
        assert t.tem_novidade(M.contexto_npcs()), "novidade nao sinalizada"
        frame(apertar=True)
        assert "4 de" in M.dialogo["linhas"][0], M.dialogo["linhas"][0]
        M.dialogo = None
    finally:
        M.setor_atual.itens[:] = guardados
    b = npc("floresta", "benedito")
    junto_de(b)
    frame(apertar=True)
    primeira = M.dialogo["linhas"][0]
    M.dialogo = None
    M.setores_visitados.add("caverna")
    frame(apertar=True)
    assert M.dialogo["linhas"][0] != primeira and "caverna" in M.dialogo["linhas"][0].lower()
    M.dialogo = None
    M.setores_visitados.discard("caverna")
    ok("falas mudam com minerios coletados e com o setor visitado; '!' de novidade")


def teste_recompensa_unica():
    a = npc("caverna", "ana")
    junto_de(a)
    curas_antes = len(M.curas)
    frame(apertar=True)                    # sem minérios: só falas
    assert len(M.curas) == curas_antes and not a.recompensa_entregue
    M.dialogo = None
    guardados = list(M.setor_atual.itens)
    del M.setor_atual.itens[:8]
    try:
        frame(apertar=True)
        assert a.recompensa_entregue and len(M.curas) == curas_antes + 1, "maca nao entregue"
        assert "maca" in M.dialogo["linhas"][0].lower()
        maca = M.curas[-1]
        # a maçã cai em chão: tem bloco sólido logo abaixo
        col = maca.rect.centerx // T
        assert M.world._solidos[maca.rect.bottom // T][col] is not None, "maca sem chao"
        M.dialogo = None
        frame(apertar=True)
        assert len(M.curas) == curas_antes + 1, "recompensa entregue duas vezes"
        M.dialogo = None
        M.player.player_health = 20
        M.player.rect.center = maca.rect.center
        M._verificar_coletas()
        assert M.player.player_health == 20 + constants.ITEM_CURA_VIDA
    finally:
        M.setor_atual.itens[:] = guardados
        M.player.player_health = constants.PLAYER_HEALTH
    ok("recompensa: maca entregue uma unica vez, em chao alcancavel, e cura")


def teste_passagem_tem_prioridade():
    M.ativar_setor("floresta")
    passagem = M.passagens_cenario.itens[0]
    t = M.setor_atual.npcs.itens[0]
    guarda = (t.rect.copy(), t.coluna)
    t.rect.midbottom = passagem.rect.midbottom          # NPC "em cima" da passagem
    M.player.rect.midbottom = passagem.rect.midbottom
    M.player.pos_x, M.player.pos_y = float(M.player.rect.x), float(M.player.rect.y)
    M._checar_passagens()
    M._checar_npcs()
    assert M.passagem_ao_alcance is not None and M.npc_ao_alcance is None
    t.rect, t.coluna = guarda
    M.transicao.ativa = False
    ok("passagem ao alcance tem prioridade sobre a conversa")


def teste_diretor_usa_arte_existente():
    d = npc("copas", "diretor")
    assert d.frames[0].get_height() == 72
    junto_de(d)
    frame(apertar=True)
    assert M.dialogo and "minerios" in " ".join(M.dialogo["linhas"])
    M.desenhar_jogo((0, 0))
    M.dialogo = None
    ok("Diretor (arte S7 das cutscenes) conversa com o total de minerios da partida")


if __name__ == "__main__":
    preparar()
    teste_dados_e_posicionamento()
    teste_conversa_avanca_e_fecha()
    teste_falas_mudam_com_progresso()
    teste_recompensa_unica()
    teste_passagem_tem_prioridade()
    teste_diretor_usa_arte_existente()
    print("TODOS OS TESTES DE NPC PASSARAM")
