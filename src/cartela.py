# -*- coding: utf-8 -*-
"""
Cartela "Comente LIVE" (08/10/2026) — chamada para o funil do ManyChat.

POR QUE EXISTE
  O perfil @moviki.oficial responde sozinho (ManyChat) quem comenta, manda
  direct ou responde story com LIVE: manda o link da live de exemplo do ramo
  da pessoa e o cadastro ja com o ramo marcado. Mas nenhum post pedia o
  comentario — o fluxo ficava parado esperando alguem adivinhar.

O QUE FAZ
  - REEL (so no Instagram): ao final do video entra uma cartela de ~7 s no
    padrao Moviki, com a voz da marca: "Quer ver como fica a live da sua
    loja? Comenta LIVE aqui embaixo, que eu te mando o link no direct."
  - STORY (so no Instagram): depois da arte do dia sai um segundo story,
    a cartela "Responda LIVE".
  - A legenda de feed e reel ja abre com a chamada (config.CHAMADA_COMENTE).

O QUE NAO FAZ (regra)
  A peca do Material de apoio NAO muda. O parceiro posta a mesma peca no
  perfil dele, onde comentar LIVE nao dispara nada. Por isso a cartela e
  colada so na COPIA que vai ao perfil oficial, na hora de publicar. O
  Facebook recebe a peca original (o ManyChat nao esta ligado nele).

NUNCA QUEBRA
  Qualquer falha (sem ffmpeg, video sem baixar, upload recusado) devolve
  None e o robo publica a peca original, como antes.

HOSPEDAGEM DO VIDEO
  Video nao entra no repositorio (regra 4). O reel com cartela sobe como
  asset do Release `cartelas` e e apagado depois de publicado — o Instagram
  copia o video para o CDN dele na criacao do container.
"""
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone

from PIL import ImageDraw

from . import arte, config
from . import util_net as net

API = "https://api.github.com"
UPLOADS = "https://uploads.github.com"
TAG_RELEASE = "cartelas"
VOZ = config.ASSETS_DIR / "cartela" / "comente-live.mp3"
FOLGA_FINAL = 0.6          # segundos de cartela parada depois da voz
DURACAO_MAX_COM_CARTELA = 180


# ------------------------------------------------------------------ arte
def imagem(modo="reel", semente=None):
    """Cartela 1080x1920 no padrao Moviki.

    modo 'reel'  -> "COMENTE LIVE" (o reel tem caixa de comentario).
    modo 'story' -> "RESPONDA LIVE" (o story tem caixa de resposta).
    Conteudo no miolo: o reel tem legenda e botoes por cima do rodape e da
    borda direita; o story tem cabecalho no topo e caixa de resposta embaixo.
    """
    base = arte.fundo_padrao(arte.STORY, semente or f"cartela-{modo}")
    l, a = base.size
    arte._cabecalho(base, "Teste grátis")
    d = ImageDraw.Draw(base)
    margem = 96
    larg = l - margem * 2

    titulo = "Quer ver a live da sua loja funcionando?"
    f_tit, linhas = arte._caber(d, titulo.upper(), config.FONTE_TITULO, larg, 128, 72, 4)
    y = int(a * 0.20)
    for i, linha in enumerate(linhas):
        cor = arte.CIANO if i == len(linhas) - 1 else arte.BRANCO
        arte._centro(d, y, linha, f_tit, cor, l)
        y += int(f_tit.size * 1.08)

    # pilula grande com a palavra-chave
    acao = "COMENTE" if modo == "reel" else "RESPONDA"
    y += 70
    f_acao = arte._fonte(config.FONTE_FORTE, 52)
    f_live = arte._fonte(config.FONTE_TITULO, 150)
    arte._centro(d, y, acao, f_acao, arte.BRANCO, l)
    y += f_acao.size + 26
    w_live = arte._largura(d, "LIVE", f_live)
    x0 = (l - w_live) // 2 - 70
    caixa = (x0, y, x0 + w_live + 140, y + f_live.size + 70)
    d.rounded_rectangle(caixa, radius=42, fill=arte.VERDE)
    bbox = d.textbbox((0, 0), "LIVE", font=f_live)
    d.text(((l - w_live) // 2, y + (caixa[3] - caixa[1]) // 2 - (bbox[1] + bbox[3]) // 2),
           "LIVE", font=f_live, fill=arte.TINTA)
    y = caixa[3] + 60

    if modo == "reel":
        sub = "Escreva LIVE nos comentários e eu te mando no direct o link de uma live de exemplo do seu ramo."
        larg_sub = larg - 120     # a coluna de botoes do reel fica na borda direita
    else:
        sub = "Responda esta história com LIVE e eu te mando no direct o link de uma live de exemplo do seu ramo."
        larg_sub = larg
    f_sub = arte._fonte(config.FONTE_FORTE, 40)
    for linha in arte._quebrar(d, sub, f_sub, larg_sub)[:3]:
        arte._centro(d, y, linha, f_sub, (225, 236, 252), l)
        y += f_sub.size + 14

    y += 30
    f_mini = arte._fonte(config.FONTE_FORTE, 30)
    arte._centro(d, y, "30 dias grátis  •  sem cartão  •  pelo celular", f_mini, arte.CINZA_AZUL, l)
    return base


# ------------------------------------------------------------------ ffmpeg
def _ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return None


def _sondar(exe, caminho):
    """(duracao_s, tem_audio) lendo a saida do proprio ffmpeg (sem ffprobe)."""
    r = subprocess.run([exe, "-hide_banner", "-i", str(caminho)], capture_output=True, text=True)
    txt = r.stderr or ""
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", txt)
    dur = (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) if m else None
    return dur, bool(re.search(r"Stream #\S+.*Audio:", txt))


def montar(video, voz, img, saida, exe=None):
    """Video original + cartela com a voz, em 1080x1920/30 fps, H.264 + AAC.

    O original e enquadrado (sem distorcer) em 1080x1920; video sem audio
    ganha trilha muda para a emenda funcionar. Devolve o caminho de saida.
    """
    exe = exe or _ffmpeg()
    if not exe:
        raise RuntimeError("ffmpeg indisponivel")
    dur_v, tem_audio = _sondar(exe, video)
    dur_voz, _ = _sondar(exe, voz)
    if not dur_v or not dur_voz:
        raise RuntimeError("nao consegui medir o video ou a voz")
    if dur_v + dur_voz + FOLGA_FINAL > DURACAO_MAX_COM_CARTELA:
        raise RuntimeError("reel longo demais para receber cartela")
    dur_c = round(dur_voz + FOLGA_FINAL, 2)

    entradas = ["-i", str(video), "-loop", "1", "-t", str(dur_c), "-i", str(img), "-i", str(voz)]
    if not tem_audio:
        entradas += ["-f", "lavfi", "-t", str(round(dur_v, 2)), "-i", "anullsrc=r=44100:cl=stereo"]
    a_orig = "[0:a]" if tem_audio else "[3:a]"
    filtro = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,fps=30,setsar=1,format=yuv420p[v0];"
        "[1:v]scale=1080:1920,fps=30,setsar=1,format=yuv420p[v1];"
        f"{a_orig}aformat=sample_rates=44100:channel_layouts=stereo[a0];"
        f"[2:a]aformat=sample_rates=44100:channel_layouts=stereo,apad=whole_dur={dur_c}[a1];"
        "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
    )
    cmd = [exe, "-hide_banner", "-loglevel", "error", "-y", *entradas,
           "-filter_complex", filtro, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-maxrate", "6M", "-bufsize", "12M",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(saida)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not os.path.exists(saida) or os.path.getsize(saida) < 10000:
        raise RuntimeError(f"ffmpeg falhou: {(r.stderr or '')[-300:]}")
    return saida


# ------------------------------------------------------------------ release
def _cabecalhos():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if not token:
        raise RuntimeError("GITHUB_TOKEN ausente")
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def _release_id(h):
    r = net.get(f"{API}/repos/{config.GH_REPO}/releases/tags/{TAG_RELEASE}", headers=h)
    if r.status_code == 200:
        return r.json()["id"]
    r = net.post(f"{API}/repos/{config.GH_REPO}/releases", headers=h, json={
        "tag_name": TAG_RELEASE, "name": "Cartelas temporarias (robo)", "prerelease": True,
        "body": "Reels com a cartela 'Comente LIVE', hospedados so ate o Instagram copiar. "
                "O robo apaga cada arquivo depois de publicar."})
    if r.status_code not in (200, 201):
        raise RuntimeError(f"release: HTTP {r.status_code}")
    return r.json()["id"]


def hospedar(caminho):
    """Sobe o mp4 como asset do Release e devolve (url_direta, asset_id).

    A URL de download do GitHub responde com redirecionamento; o robo entrega
    ao Instagram o endereco final (assinado, vale alguns minutos — o
    Instagram baixa na criacao do container)."""
    h = _cabecalhos()
    rid = _release_id(h)
    nome = "reel-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + ".mp4"
    with open(caminho, "rb") as f:
        dados = f.read()
    r = net.post(f"{UPLOADS}/repos/{config.GH_REPO}/releases/{rid}/assets?name={nome}",
                 headers={**h, "Content-Type": "video/mp4"}, data=dados, timeout=300)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"upload do reel: HTTP {r.status_code}")
    asset = r.json()
    url = asset["browser_download_url"]
    try:
        import requests
        rr = requests.get(url, allow_redirects=False, timeout=30)
        if rr.status_code in (301, 302, 303, 307, 308) and rr.headers.get("Location", "").startswith("https://"):
            url = rr.headers["Location"]
    except Exception:  # noqa: BLE001
        pass
    return url, asset["id"]


def apagar(asset_id):
    if not asset_id:
        return
    try:
        import requests
        requests.delete(f"{API}/repos/{config.GH_REPO}/releases/assets/{asset_id}",
                        headers=_cabecalhos(), timeout=30)
    except Exception as e:  # noqa: BLE001
        print(f"cartela: nao apagou o asset {asset_id} ({net.sem_segredo(e)})")


# ------------------------------------------------------------------ uso
def reel_com_cartela(url_video):
    """URL do reel com a cartela no fim, pronta para o Instagram, e o id do
    asset para apagar depois. (None, None) se desligado ou se algo falhar."""
    if not config.CARTELA_REEL:
        return None, None
    try:
        exe = _ffmpeg()
        if not exe or not VOZ.exists():
            print("cartela: sem ffmpeg ou sem a voz -> reel original.")
            return None, None
        pasta = tempfile.mkdtemp(prefix="cartela-")
        original = os.path.join(pasta, "original.mp4")
        r = net.get(url_video, timeout=120)
        if r.status_code != 200 or len(r.content) < 10000:
            raise RuntimeError(f"video: HTTP {r.status_code}")
        with open(original, "wb") as f:
            f.write(r.content)
        img = arte.salvar(imagem("reel"), os.path.join(pasta, "cartela.png"))
        saida = montar(original, VOZ, img, os.path.join(pasta, "reel-cartela.mp4"), exe)
        print(f"cartela: reel montado ({os.path.getsize(saida) // 1024} KB)")
        if config.DRY_RUN:
            return saida, None
        return hospedar(saida)
    except Exception as e:  # noqa: BLE001
        print(f"cartela: falhou ({net.sem_segredo(e)}) -> reel original.")
        return None, None


def story_cartela():
    """URL publica da cartela 'Responda LIVE' para o story, ou None."""
    if not config.CARTELA_STORY:
        return None
    try:
        dia = datetime.now(timezone.utc).strftime("%Y%m%d")
        caminho = arte.salvar(imagem("story", semente=f"cartela-story-{dia}"), "/tmp/story-cartela.jpg")
        if config.DRY_RUN:
            print(f"DRY_RUN: cartela do story em {caminho}")
            return caminho
        from . import hospedagem
        return hospedagem.publicar_arquivo(caminho, prefixo="story-cartela")
    except Exception as e:  # noqa: BLE001
        print(f"cartela: story falhou ({net.sem_segredo(e)}) -> sem cartela hoje.")
        return None
