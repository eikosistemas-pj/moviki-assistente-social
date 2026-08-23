# Banco de Reels

Os videos NAO ficam versionados no git. Um Reel de 8s sai com 5-10 MB; a
~8 por mes isso viraria ~800 MB de historico em um ano, e git nao esquece
binario. Em vez disso cada Reel mora como ASSET DE RELEASE do proprio repo
(URL publica permanente, fora do historico) e este arquivo guarda so o
ponteiro.

## Como acrescentar um Reel

1. Gerar o video (Kairogen, `veo-3-1-fast`, 9:16) e **revisar antes**.
2. No GitHub: `Releases` -> `Draft a new release` -> tag `reels`
   (reaproveite a mesma release pra todos) -> arraste o `.mp4` em
   *Attach binaries*.
3. Clique com o botao direito no arquivo anexado -> copiar endereco do
   link. Vai ter a forma:
   `https://github.com/eikosistemas-pj/moviki-assistente-social/releases/download/reels/<arquivo>.mp4`
4. Cole num bloco novo aqui embaixo, tirando o comentario `<!--`/`-->`.

Formato:

    ## <id-unico>
    tipo: educativo | conversao | parceiro | bastidor
    url: <URL do asset de release>
    capa: (opcional) URL de uma imagem 1080x1920 pra capa
    titulo: <do que o video fala, so pra referencia humana>
    angulo: <instrucao pra IA escrever a legenda>

Enquanto nao houver nenhum bloco ativo, o workflow de Reels termina sem
publicar e avisa no log — nao quebra.

---

<!-- APAGUE ESTA LINHA DE COMENTARIO (e a do fim) QUANDO SUBIR OS VIDEOS

## endereco-que-muda-reel
tipo: educativo
url: https://github.com/eikosistemas-pj/moviki-assistente-social/releases/download/reels/endereco-que-muda.mp4
titulo: O carrinho sai de uma esquina de noite e amanhece em outra praca
angulo: Mostre a dor de quem trabalha em carrinho: o cliente de ontem nao sabe onde voce esta hoje. Primeira linha precisa segurar quem esta rolando o feed. Feche mandando pro link da bio.

## quem-procura-reel
tipo: educativo
url: https://github.com/eikosistemas-pj/moviki-assistente-social/releases/download/reels/quem-procura.mp4
titulo: Pessoa procurando na rua ate achar o carrinho aberto
angulo: Vire o post pro lado de QUEM PROCURA, nao do lojista. Bateu vontade e a pessoa nao sabe se ele esta na praca hoje. Agora sabe. Feche mandando pro link da bio.

## abrir-o-dia-reel
tipo: bastidor
url: https://github.com/eikosistemas-pj/moviki-assistente-social/releases/download/reels/abrir-o-dia.mp4
titulo: Vendedor abrindo o carrinho no comeco do dia
angulo: Post de posicionamento e respeito. Trabalhar na rua nao e menos negocio, e so um negocio que anda. Sem pieguice, sem vitimizacao, sem numero inventado.

FIM DO COMENTARIO -->
