# Banco de fundos

Fundos aprovados, nomeados por **macro-segmento**. O robô escolhe o fundo
do segmento do negócio e escreve por cima o nome, o segmento, a cidade e o
link. Sem fundo do segmento cai em `generico-*`; sem nenhum fundo cai num
degradê na cor do lojista — degrada, nunca quebra.

Formato: JPG, 1080x1080. **Sem texto na imagem** e com área escura livre no
centro e embaixo — é ali que o nome do negócio e o link são escritos.

## Já gerados (baixar da galeria Kairogen e salvar aqui com estes nomes)

| Arquivo | Cena |
|---|---|
| `alimentacao-01.jpg` | Food truck à noite, fila, calçada molhada |
| `hortifruti-01.jpg` | Feira livre ao amanhecer, barracas coloridas |
| `bebidas-01.jpg` | Carrinho de bebidas geladas na praia ao entardecer |
| `moda-01.jpg` | Arara de brechó em feira de rua |
| `artesanato-01.jpg` | Banca de cerâmica e bijuteria artesanal |
| `servicos-01.jpg` | Barbeiro móvel atendendo na calçada |
| `belezaperfumaria-01.jpg` | Banca de perfumaria, frascos de vidro |
| `papelarialivraria-01.jpg` | Banca de livros usados e papelaria |
| `tecnologia-01.jpg` | Banca de relógios e cabos |
| `institucional-01.jpg` | Rua vista de cima, carrinhos como pontos de luz |
| `generico-01.jpg` | Retrato de vendedor ambulante ao lado do carrinho |

## Segmentos ainda sem fundo próprio

Nenhum — os 9 macros estão cobertos. Para variar mais, gere `-02`, `-03`
do mesmo segmento: o robô sorteia entre todos que começam com o prefixo.

## Prompt que funciona (validado)

Fotografia cinematográfica, cena real brasileira de rua, e **a instrução
explícita de deixar grande área escura e vazia ocupando o centro e toda a
parte inferior do enquadramento para sobreposição de texto**, mais "sem
nenhum texto, sem letras, sem logotipos". Sem essa instrução o modelo
preenche o quadro inteiro e não sobra lugar pro nome do negócio.

Modelo: `seedream-5-pro`, 2 créditos por imagem.

**Revisar antes de commitar.** Já aconteceu de um fundo sair com o que
parecia logotipo de fabricante em capinhas de celular — foi refeito. Marca
de terceiro num post é risco desnecessário.
