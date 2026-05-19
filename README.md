# Sistema de Pontuação de Equipes

## Descrição

Este projeto é um sistema simples em Python para controlar a pontuação de uma competição entre cinco equipes.

O programa permite cadastrar o nome das equipes, definir a pontuação de perguntas fáceis, médias e difíceis, registrar as respostas corretas de cada equipe, calcular a pontuação final e exibir o ranking ao final da competição.

O código foi desenvolvido para a disciplina de **MI Algoritmos**.

## Funcionalidades

- Cadastro de 5 equipes.
- Validação para impedir nomes repetidos ou em branco.
- Definição da pontuação para perguntas fáceis, médias e difíceis.
- Registro da quantidade de rodadas.
- Escolha do nível da pergunta por equipe.
- Registro se a equipe acertou ou não a questão.
- Registro do tempo gasto para responder corretamente.
- Cálculo da pontuação total de cada equipe.
- Exibição do ranking final.
- Critério de desempate por:
  - maior pontuação;
  - menor tempo;
  - maior quantidade de questões difíceis acertadas.
- Exibição da média de pontos das equipes.
- Exibição da equipe ou equipes que mais acertaram questões difíceis.

## Como executar

Para executar o programa, é necessário ter o Python instalado no computador.

No terminal, acesse a pasta onde está o arquivo e execute:

```bash
python pbl01.py
```

ou, dependendo da instalação:

```bash
python3 pbl01.py
```

## Como usar

Ao iniciar o programa, o usuário deve informar:

1. O nome das cinco equipes.
2. O valor da questão fácil.
3. O valor da questão média.
4. O valor da questão difícil.
5. A quantidade de rodadas da competição.

Durante cada rodada, cada equipe deverá:

1. Escolher o nível da pergunta:
   - `1` para fácil;
   - `2` para médio;
   - `3` para difícil.
2. Informar se respondeu corretamente:
   - `s` para sim;
   - `n` para não.
3. Caso tenha acertado, informar o tempo gasto para responder.

Ao final, o programa mostra o ranking das equipes, a média geral de pontos e a equipe que mais acertou questões difíceis.

## Exemplo de execução

```text
Nome da equipe 1: Azul
Nome da equipe 2: Vermelha
Nome da equipe 3: Verde
Nome da equipe 4: Amarela
Nome da equipe 5: Roxa

Quanto vale a questão fácil: 10
Quanto vale a questão média: 20
Quanto vale a questão difícil: 30

Digite o números de rodadas: 1
```

Depois disso, cada equipe escolhe o nível da pergunta e informa se acertou ou não.

## Regras de pontuação

A equipe só recebe pontos quando responde corretamente.

Se a equipe errar a pergunta, ela não ganha pontos e o tempo não é somado.

As questões fáceis, médias e difíceis só são contabilizadas quando a equipe acerta a questão.

## Critérios do ranking

O ranking é organizado da seguinte forma:

1. A equipe com maior pontuação fica na frente.
2. Em caso de empate, vence a equipe com menor tempo total.
3. Se ainda houver empate, vence a equipe com maior quantidade de questões difíceis acertadas.

## Estrutura do código

O programa é dividido em partes principais:

- Entrada e validação dos nomes das equipes.
- Inicialização das variáveis de pontuação, tempo e quantidade de questões.
- Definição dos valores das questões.
- Execução das rodadas.
- Cálculo da média.
- Geração do ranking.
- Exibição da equipe com mais acertos em questões difíceis.

## Tecnologias utilizadas

- Python 3

## Autora

Adna Amorim da Silva Conceição
