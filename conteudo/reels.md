# Banco de Reels

Os vídeos NÃO ficam versionados no git. Um Reel de 8s sai com 5-10 MB; a
~8 por mês isso viraria ~800 MB de histórico em um ano, e git não esquece
binário. Em vez disso cada Reel mora como ASSET DE RELEASE do próprio repo
(URL pública permanente, fora do histórico) e este arquivo guarda só o
ponteiro.

## Como acrescentar um Reel

1. Gerar o vídeo (Kairogen, `veo-3-1-fast`, 9:16) e **assistir antes**.
2. No GitHub: `Releases` → editar a release `reels` (ícone de lápis) →
   arraste o `.mp4` em *Attach binaries* → `Update release`.
3. Copiar o endereço do link do arquivo anexado. Vai ter a forma
   `https://github.com/eikosistemas-pj/moviki-assistente-social/releases/download/reels/<arquivo>.mp4`
4. Colar num bloco novo aqui embaixo.

Formato:

    ## <id-unico>
    tipo: educativo | conversao | parceiro | bastidor
    url: <URL do asset de release>
    capa: (opcional) URL de uma imagem 1080x1920 pra capa
    titulo: <gancho da legenda — VAI AO AR, escreva com acento>
    angulo: <instrucao pra IA escrever a legenda; nunca vai ao ar>

⚠️ `titulo` é publicado (vira a primeira linha da legenda se a IA falhar).
Escreva como gancho de verdade, não como descrição do vídeo.

Enquanto não houver nenhum bloco ativo, o workflow de Reels termina sem
publicar e avisa no log — não quebra.

---

(Os 3 reels de 2026-09 "endereco-que-muda", "quem-procura" e "abrir-o-dia" sairam em 20/10/2026: falavam so de mapa, posicionamento aposentado. Os videos continuam na release `reels`.)
