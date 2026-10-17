# -*- coding: utf-8 -*-
"""
Montagem do story em VIDEO (17/10/2026).

POR QUE EXISTE
  Ate 16/10/2026 o story era so arte parada, sem som, e cada arte vinha
  seguida da mesma cartela "Responda LIVE" — duas vezes por dia. Quem assistia
  via sempre a mesma tela. Os 50 videos do Material de apoio nunca entravam
  em story.

O QUE FAZ
  - CORTE de video: pega um trecho de 9 a 20 s de um video do Material de
    apoio (ou do acervo da grade). O corte cai SEMPRE numa pausa da fala
    (nunca no meio de uma palavra). Cada rodada usa o proximo corte do mesmo
    video, entao o mesmo video rende varios stories diferentes.
  - ARTE ANIMADA: a arte 9:16 do Material de apoio vira um video de 7 s com
    zoom lento e trilha.
  - TRILHA: biblioteca propria em assets/musica (gerada no Kairogen,
    instrumental, sem direito autoral de terceiro). Video que ja tem fundo
    musical mantem o proprio som; video so com voz ganha a trilha baixinha
    por baixo, abaixando sozinha quando a voz fala (ducking).
  - CHAMADA embutida: quando a vez pede, os 3 s finais sao a cartela
    "Responda LIVE" (com variacao de titulo), na mesma trilha. Substitui o
    segundo story estatico que saia depois de toda arte.

NUNCA QUEBRA
  Qualquer falha levanta excecao para quem chamou (src/story.py), que cai no
  story original, como antes.
"""
import os
import re
import subprocess
import tempfile
from array import array
from pathlib import Path

from . import arte, cartela, config

TRILHAS_DIR = config.ASSETS_DIR / "musica"

CORTE_MIN = 9.0
CORTE_ALVO = 15.0
CORTE_MAX = 20.0
VIDEO_MIN = 8.0          # video mais curto que isso nao vira story
ARTE_SEG = 7.0           # arte animada
CTA_SEG = 3.2            # cartela no fim
XF = 0.35                # transicao entre o trecho e a cartela
TAXA = 8000              # analise de audio (mono 8 kHz basta para achar pausa)
FUNDO_DB = -50.0         # piso acima disso = o video ja tem fundo musical
VOL_TRILHA_SOB_VOZ = 0.22
VOL_TRILHA_SOZINHA = 0.75

TITULOS_CTA = (
    "Quer ver a live da sua loja funcionando?",
    "Imagina a sua loja vendendo ao vivo assim?",
    "Quer uma live dessas na sua loja?",
    "Sua loja ao vivo, pelo celular. Quer ver?",
)


# ------------------------------------------------------------------ trilhas
def trilhas():
    if not TRILHAS_DIR.exists():
        return []
    return sorted(p for p in TRILHAS_DIR.glob("*.mp3") if p.stat().st_size > 50000)


def escolher_trilha(recentes_trilhas, lista=None):
    """Trilha inedita primeiro; senao a usada ha mais tempo."""
    lista = trilhas() if lista is None else lista
    if not lista:
        return None
    rec = list(recentes_trilhas or [])

    def idade(p):
        return len(rec) + 1 if p.stem not in rec else rec.index(p.stem)

    return max(lista, key=idade)


# ------------------------------------------------------------------ analise
def _rms_db(amostras, ini, fim):
    n = fim - ini
    if n <= 0:
        return -120.0
    s = 0
    for i in range(ini, fim):
        v = amostras[i]
        s += v * v
    import math
    rms = math.sqrt(s / n) / 32768.0
    return 20 * math.log10(rms) if rms > 1e-6 else -120.0


def _decodificar(exe, caminho):
    r = subprocess.run([exe, "-v", "error", "-i", str(caminho), "-vn", "-ac", "1", "-ar", str(TAXA),
                        "-f", "s16le", "-"], capture_output=True, timeout=300)
    a = array("h")
    if r.returncode == 0 and r.stdout:
        a.frombytes(r.stdout[: len(r.stdout) // 2 * 2])
    return a


def perfil(amostras, janela=0.05):
    """dB por janela de 50 ms."""
    passo = int(TAXA * janela)
    return [_rms_db(amostras, i, min(i + passo, len(amostras))) for i in range(0, len(amostras), passo)]


def pausas(dbs, janela=0.05, minimo=0.18):
    """Meio de cada pausa da fala (s). Limite relativo: 10 dB abaixo da
    mediana — funciona com e sem fundo musical."""
    if not dbs:
        return []
    fala = sorted(d for d in dbs if d > -90)
    if not fala:
        return []
    limite = fala[len(fala) // 2] - 10
    saida, ini = [], None
    for i, d in enumerate(dbs + [0.0]):
        if d < limite:
            ini = i if ini is None else ini
        elif ini is not None:
            if (i - ini) * janela >= minimo:
                saida.append(round((ini + i) / 2 * janela, 2))
            ini = None
    return saida


def tem_fundo(dbs):
    """O video ja tem trilha? Piso (10o percentil) acima de FUNDO_DB."""
    miolo = dbs[10:-10] if len(dbs) > 40 else dbs
    if not miolo:
        return False
    s = sorted(miolo)
    return s[len(s) // 10] > FUNDO_DB


def _vale(dbs, de, ate, janela=0.05):
    """Instante (s) de menor energia entre `de` e `ate` (media de 150 ms):
    o respiro mais fundo da fala quando nao ha pausa clara."""
    i0, i1 = int(de / janela), min(int(ate / janela), len(dbs) - 2)
    if i1 <= i0 + 1:
        return None
    melhor = min(range(max(i0, 1), i1), key=lambda i: dbs[i - 1] + dbs[i] + dbs[i + 1])
    return round(melhor * janela, 2)


def cortes(dur, marcas, mn=CORTE_MIN, alvo=CORTE_ALVO, mx=CORTE_MAX, dbs=None):
    """Trechos (ini, fim) que cobrem o video, cada um terminando numa pausa
    (ou, sem pausa clara, no respiro mais fundo do intervalo).
    Video curto vira um corte so. Sobra final menor que `mn` fica de fora."""
    if dur <= mx + 2:
        return [(0.0, round(dur, 2))]
    saida, s = [], 0.0
    while dur - s >= mn:
        if dur - s <= mx:
            saida.append((round(s, 2), round(dur, 2)))
            break
        dentro = [p for p in marcas if s + mn <= p <= s + mx]
        if dentro:
            e = min(dentro, key=lambda p: abs(p - (s + alvo)))
        else:
            e = (_vale(dbs, s + mn, s + mx) if dbs else None) or s + alvo
        saida.append((round(s, 2), round(e, 2)))
        s = e
    return saida


def analisar(caminho, exe=None):
    """{'dur', 'audio', 'fundo', 'cortes'} do video."""
    exe = exe or cartela._ffmpeg()
    if not exe:
        raise RuntimeError("ffmpeg indisponivel")
    dur, audio = cartela._sondar(exe, caminho)
    if not dur:
        raise RuntimeError("nao consegui medir o video")
    if not audio:
        return {"dur": dur, "audio": False, "fundo": False, "cortes": cortes(dur, [])}
    dbs = perfil(_decodificar(exe, caminho))
    return {"dur": dur, "audio": True, "fundo": tem_fundo(dbs), "cortes": cortes(dur, pausas(dbs), dbs=dbs)}


# ------------------------------------------------------------------ cartela
def imagem_cta(semente):
    """Cartela 'Responda LIVE' com o titulo variando pela semente."""
    titulo = TITULOS_CTA[sum(map(ord, str(semente))) % len(TITULOS_CTA)]
    return cartela.imagem("story", semente=f"cta-{semente}", titulo=titulo)


# ------------------------------------------------------------------ ffmpeg
def _rodar(exe, cmd, saida):
    r = subprocess.run([exe, "-hide_banner", "-loglevel", "error", "-y", *cmd], capture_output=True,
                       text=True, timeout=600)
    if r.returncode != 0 or not os.path.exists(saida) or os.path.getsize(saida) < 10000:
        raise RuntimeError(f"ffmpeg falhou: {(r.stderr or '')[-300:]}")
    return saida


_SAIDA = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-maxrate", "6M", "-bufsize", "12M",
          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
          "-movflags", "+faststart"]
_ENQ = ("scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,fps=30,setsar=1,format=yuv420p")


def _zoom(seg, de=1.0, ate=1.04):
    """Zoom lento e centralizado (upscale antes para nao tremer)."""
    q = int(seg * 30)
    passo = (ate - de) / max(q, 1)
    return (f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
            f"zoompan=z='min({de}+on*{passo:.6f},{ate})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={q}:s=1080x1920:fps=30,setsar=1,format=yuv420p")


def montar(saida, video=None, ini=0.0, fim=None, imagem=None, trilha=None, cta=None,
           fundo=False, audio=True, exe=None):
    """Monta o story em 1080x1920/30 fps, H.264 + AAC.

    video+ini/fim -> corte do video;  imagem -> arte animada (ARTE_SEG).
    cta = caminho da cartela (None = sem chamada).  trilha = mp3 (None = sem).
    fundo = o video ja tem trilha propria (a nossa so entra na cartela).
    """
    exe = exe or cartela._ffmpeg()
    if not exe:
        raise RuntimeError("ffmpeg indisponivel")
    if video is None and imagem is None:
        raise ValueError("video ou imagem")
    seg = ARTE_SEG if video is None else round(float(fim) - float(ini), 2)
    total = round(seg + (CTA_SEG - XF if cta else 0.0), 2)
    if total > config.STORY_DURACAO_MAX:
        raise RuntimeError("story longo demais")

    entradas, f = [], []
    if video is not None:
        entradas += ["-ss", f"{float(ini):.2f}", "-t", f"{seg:.2f}", "-i", str(video)]
        f.append(f"[0:v]{_ENQ},trim=duration={seg},setpts=PTS-STARTPTS[vbase]")
    else:
        entradas += ["-loop", "1", "-t", f"{seg:.2f}", "-i", str(imagem)]
        f.append(f"[0:v]{_zoom(seg)},trim=duration={seg},setpts=PTS-STARTPTS[vbase]")
    n = 1
    if cta:
        entradas += ["-loop", "1", "-t", f"{CTA_SEG:.2f}", "-i", str(cta)]
        f.append(f"[{n}:v]{_zoom(CTA_SEG, 1.0, 1.04)},trim=duration={CTA_SEG}[vcta]")
        f.append(f"[vbase][vcta]xfade=transition=fade:duration={XF}:offset={seg - XF:.2f}[v]")
        n += 1
    else:
        f.append(f"[vbase]fade=t=out:st={max(seg - 0.25, 0):.2f}:d=0.25[v]")

    # ---- audio
    voz = None
    if video is not None and audio:
        f.append(f"[0:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                 f"afade=t=in:d=0.12,afade=t=out:st={max(seg - 0.3, 0):.2f}:d=0.3,"
                 f"apad=whole_dur={total}[voz]")
        voz = "[voz]"
    mus = None
    if trilha:
        entradas += ["-stream_loop", "-1", "-i", str(trilha)]
        base = (f"[{n}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                f"atrim=duration={total},asetpts=PTS-STARTPTS")
        if voz and fundo:
            # o video ja tem trilha: a nossa entra so na cartela
            if cta:
                ini_c = seg - XF
                f.append(f"{base},volume='if(lt(t,{ini_c:.2f}),0,{VOL_TRILHA_SOZINHA})':eval=frame,"
                         f"afade=t=out:st={total - 0.6:.2f}:d=0.6[mus]")
                mus = "[mus]"
        elif voz:
            f.append(f"{base},volume={VOL_TRILHA_SOB_VOZ},afade=t=in:d=0.6,"
                     f"afade=t=out:st={total - 0.8:.2f}:d=0.8[musb]")
            f.append("[voz]asplit=2[vozm][vozsc]")
            f.append("[musb][vozsc]sidechaincompress=threshold=0.04:ratio=6:attack=15:release=350[mus]")
            voz, mus = "[vozm]", "[mus]"
        else:
            f.append(f"{base},volume={VOL_TRILHA_SOZINHA},afade=t=in:d=0.4,"
                     f"afade=t=out:st={total - 0.8:.2f}:d=0.8[mus]")
            mus = "[mus]"
    if voz and mus:
        f.append(f"{voz}{mus}amix=inputs=2:duration=first:normalize=0,atrim=duration={total}[a]")
    elif voz or mus:
        f.append(f"{voz or mus}anull,atrim=duration={total}[a]")
    else:
        entradas += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=44100:cl=stereo"]
        f.append(f"[{n}:a]anull[a]")

    cmd = [*entradas, "-filter_complex", ";".join(f), "-map", "[v]", "-map", "[a]",
           "-t", f"{total:.2f}", *_SAIDA, str(saida)]
    return _rodar(exe, cmd, saida)


def pasta_temp():
    return Path(tempfile.mkdtemp(prefix="story-"))


def nome_seguro(txt):
    return re.sub(r"[^a-z0-9-]+", "-", str(txt).lower()).strip("-")[:50] or "story"


def salvar_cta(semente, pasta):
    return arte.salvar(imagem_cta(semente), str(Path(pasta) / "cta.png"))
