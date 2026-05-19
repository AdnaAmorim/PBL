#Autor: Adna Amorim da Silva Conceição
#Componente Curricular: Mi Algoritmos
#Concluido em: 10/09/2024
#Declaro que este código foi elaborado por mim de forma individual e não contém nenhum
#trecho de código de outro colega ou de outro autor, tais como provindos de livros e
#apostilas, e páginas ou documentos eletrônicos da Internet. Qualquer trecho de código
#de outra autoria que não a minha está destacado com uma citação para o autor e a fonte
#do código, e estou ciente que estes trechos não serão considerados para fins de avaliação.

# pergunta os nomes da equipes 
equipe01 = input('Nome da equipe 1: ').strip()

#validar os nomes e não deixar o usuario digitar um espaço vazio
while equipe01 == '':
    print('O nome da equipe não pode ser um espaço em branco.')
    equipe01 = input('Nome da equipe 1: ').strip()

equipe02 = input('Nome da equipe 2: ').strip()
while equipe01 == equipe02 or equipe02 == '':
    print('Esse nome já foi escolhido ou está em branco. Por favor, escolha outro.')
    equipe02 = input('Nome da equipe 2: ').strip()

equipe03 = input('Nome da equipe 3: ').strip()
while equipe03 == equipe01 or equipe03 == equipe02 or equipe03 == '':
    print('Esse nome já foi escolhido ou está em branco. Por favor, escolha outro.')
    equipe03 = input('Nome da equipe 3: ').strip().strip()

equipe04 = input('Nome da equipe 4: ').strip()
while equipe04 == equipe01 or equipe04 == equipe02 or equipe04 == equipe03 or equipe04 == '':
    print('Esse nome já foi escolhido ou está em branco. Por favor, escolha outro.')
    equipe04 = input('Nome da equipe 4: ').strip().strip()

equipe05 = input('Nome da equipe 5: ').strip()
while equipe05 == equipe01 or equipe05 == equipe02 or equipe05 == equipe03 or equipe05 == equipe04 or equipe05 == '':
    print('Esse nome já foi escolhido ou está em branco. Por favor, escolha outro.')
    equipe05 = input('Nome da equipe 5: ').strip().strip()


# Armazernar as pontuações
pontu01 = 0
pontu02 = 0
pontu03 = 0 
pontu04 = 0
pontu05 = 0

# Armazenamento do tempo
tempo01 = 0
tempo02 = 0
tempo03 = 0
tempo04 = 0
tempo05 = 0

#Armazenar as questões facies 
facil01 = 0
facil02 = 0
facil03 = 0
facil04 = 0
facil05 = 0

#Armazenar as questões medias
media01 = 0
media02 = 0
media03 = 0
media04 = 0
media05 = 0

#Armazenar as questões dificies 
dificil01 = 0
dificil02 = 0
dificil03 = 0
dificil04 = 0
dificil05 = 0

# Definir os níveis de perguntas
nivel_facil = int(input('Quanto vale a questão fácil: '))

#validação dos níveis
nivel_medio = int(input('Quanto vale a questão média: '))
while nivel_facil == nivel_medio:
    print('Este valor já foi escolhido. Por favor, escolha outro valor.')
    nivel_medio = int(input('Quanto vale a questão média: '))

nivel_dificil = int(input('Quanto vale a questão difícil: '))
while nivel_facil == nivel_dificil or nivel_dificil == nivel_medio:
    print('Este valor já foi escolhido. Por favor, escolha outro valor.')
    nivel_dificil = int(input('Quanto vale a questão difícil: '))


#perguntar o números de rodadas 
perguntas =  int(input('Digite o números de rodadas:'))
for _ in range(perguntas):  
    # Equipe 01
    #validar a escolha do nivel
    nivel = 0
    while nivel != 1 and nivel != 2 and nivel != 3:
        nivel = int(input(f'\n{equipe01}, escolha o nível da pergunta (1: fácil, 2: médio, 3: difícil): '))
        if nivel != 1 and nivel != 2 and nivel != 3:
            print('Nível inválido, escolha 1, 2 ou 3.')
    #atribuir os números para os níveis fáceis, médias e difíceis 
    if nivel == 1:
        pontos = nivel_facil
    elif nivel == 2:
        pontos = nivel_medio
    elif nivel == 3:
        pontos = nivel_dificil

    resposta = input(f'{equipe01}, respondeu corretamente? (s/n): ').strip().lower()

    if resposta == 's':
        tempo = float(input('Digite o tempo (segundos) que a equipe realizou a questão:'))
        #atualizar a pontuação e o tempo
        pontu01 += pontos
        tempo01 += tempo
        if nivel == 1:
            facil01 += 1
        elif nivel == 2:
            media01 += 1
        elif nivel == 3:
            dificil01 += 1
        print(f'A equipe {equipe01} ganhou {pontos} pontos e respondeu em {tempo} segundos!')
    else:
        print(f'{equipe01} não ganhou pontos desta vez.')


# Equipe 02
    nivel = 0
    while nivel != 1 and nivel != 2 and nivel != 3:
        nivel = int(input(f'\n{equipe02}, escolha o nível da pergunta (1: fácil, 2: médio, 3: difícil): '))
        if nivel != 1 and nivel != 2 and nivel != 3:
            print('Nível inválido, escolha 1, 2 ou 3.')

    if nivel == 1:
        pontos = nivel_facil
    elif nivel == 2:
        pontos = nivel_medio
    elif nivel == 3:
        pontos = nivel_dificil

    resposta = input(f'{equipe02}, respondeu corretamente? (s/n): ').strip().lower()

    if resposta == 's':
        tempo = float(input('Digite o tempo (segundos) que a equipe realizou a questão:'))
        pontu02 += pontos
        tempo02 += tempo
        if nivel == 1:
            facil02 += 1
        elif nivel == 2:
            media02 += 1
        elif nivel == 3:
            dificil02 += 1
        print(f'A equipe {equipe02} ganhou {pontos} pontos e respondeu em {tempo} segundos!')
    else:
        print(f'{equipe02} não ganhou pontos desta vez.')

# Equipe 03
    nivel = 0
    while nivel != 1 and nivel != 2 and nivel != 3:
        nivel = int(input(f'\n{equipe03}, escolha o nível da pergunta (1: fácil, 2: médio, 3: difícil): '))
        if nivel != 1 and nivel != 2 and nivel != 3:
            print('Nível inválido, escolha 1, 2 ou 3.')

    if nivel == 1:
        pontos = nivel_facil
    elif nivel == 2:
        pontos = nivel_medio
    elif nivel == 3:
        pontos = nivel_dificil

    resposta = input(f'{equipe03}, respondeu corretamente? (s/n): ').strip().lower()

    if resposta == 's':
        tempo = float(input('Digite o tempo (segundos) que a equipe realizou a questão:'))
        pontu03 += pontos
        tempo03 += tempo
        if nivel == 1:
            facil03 += 1
        elif nivel == 2:
            media03 += 1
        elif nivel == 3:
            dificil03 += 1
        print(f'A equipe {equipe03} ganhou {pontos} pontos e respondeu em {tempo} segundos!')
    else:
        print(f'{equipe03} não ganhou pontos desta vez.')

# Equipe 04
    nivel = 0
    while nivel != 1 and nivel != 2 and nivel != 3:
        nivel = int(input(f'\n{equipe04}, escolha o nível da pergunta (1: fácil, 2: médio, 3: difícil): '))
        if nivel != 1 and nivel != 2 and nivel != 3:
            print('Nível inválido, escolha 1, 2 ou 3.')

    if nivel == 1:
        pontos = nivel_facil
    elif nivel == 2:
        pontos = nivel_medio
    elif nivel == 3:
        pontos = nivel_dificil

    resposta = input(f'{equipe04}, respondeu corretamente? (s/n): ').strip().lower()

    if resposta == 's':
        tempo = float(input('Digite o tempo (segundos) que a equipe realizou a questão:'))
        pontu04 += pontos
        tempo04 += tempo
        if nivel == 1:
            facil04 += 1
        elif nivel == 2:
            media04 += 1
        elif nivel == 3:
            dificil04 += 1
        print(f'A equipe {equipe04} ganhou {pontos} pontos e respondeu em {tempo} segundos!')
    else:
        print(f'{equipe04} não ganhou pontos desta vez.')

# Equipe 05
    nivel = 0
    while nivel != 1 and nivel != 2 and nivel != 3:
        nivel = int(input(f'\n{equipe05}, escolha o nível da pergunta (1: fácil, 2: médio, 3: difícil): '))
        if nivel != 1 and nivel != 2 and nivel != 3:
            print('Nível inválido, escolha 1, 2 ou 3.')

    if nivel == 1:
        pontos = nivel_facil
    elif nivel == 2:
        pontos = nivel_medio
    elif nivel == 3:
        pontos = nivel_dificil

    resposta = input(f'{equipe05}, respondeu corretamente? (s/n): ').strip().lower()

    if resposta == 's':
        tempo = float(input('Digite o tempo (segundos) que a equipe realizou a questão:'))
        pontu05 += pontos
        tempo05 += tempo
        if nivel == 1:
            facil05 += 1
        elif nivel == 2:
            media05 += 1
        elif nivel == 3:
            dificil05 += 1
        print(f'A equipe {equipe05} ganhou {pontos} pontos e respondeu em {tempo} segundos!')
    else:
        print(f'{equipe05} não ganhou pontos desta vez.')


# Media dos pontos
media = (pontu01 + pontu02 + pontu03 + pontu04 + pontu05) / 5

# Ordem do ranking
colocacao = 1
usado01 = 0
usado02 = 0
usado03 = 0
usado04 = 0
usado05 = 0

while colocacao <= 5:
    melhor = 0
    melhor_nome = ''
    melhor_pontos = -1
    melhor_tempo = 0
    melhor_facil = 0
    melhor_media = 0
    melhor_dificil = 0

    if usado01 == 0:
        melhor = 1
        melhor_nome = equipe01
        melhor_pontos = pontu01
        melhor_tempo = tempo01
        melhor_facil = facil01
        melhor_media = media01
        melhor_dificil = dificil01

    if usado02 == 0 and (melhor == 0 or pontu02 > melhor_pontos or (pontu02 == melhor_pontos and (tempo02 < melhor_tempo or (tempo02 == melhor_tempo and dificil02 > melhor_dificil)))):
        melhor = 2
        melhor_nome = equipe02
        melhor_pontos = pontu02
        melhor_tempo = tempo02
        melhor_facil = facil02
        melhor_media = media02
        melhor_dificil = dificil02

    if usado03 == 0 and (melhor == 0 or pontu03 > melhor_pontos or (pontu03 == melhor_pontos and (tempo03 < melhor_tempo or (tempo03 == melhor_tempo and dificil03 > melhor_dificil)))):
        melhor = 3
        melhor_nome = equipe03
        melhor_pontos = pontu03
        melhor_tempo = tempo03
        melhor_facil = facil03
        melhor_media = media03
        melhor_dificil = dificil03

    if usado04 == 0 and (melhor == 0 or pontu04 > melhor_pontos or (pontu04 == melhor_pontos and (tempo04 < melhor_tempo or (tempo04 == melhor_tempo and dificil04 > melhor_dificil)))):
        melhor = 4
        melhor_nome = equipe04
        melhor_pontos = pontu04
        melhor_tempo = tempo04
        melhor_facil = facil04
        melhor_media = media04
        melhor_dificil = dificil04

    if usado05 == 0 and (melhor == 0 or pontu05 > melhor_pontos or (pontu05 == melhor_pontos and (tempo05 < melhor_tempo or (tempo05 == melhor_tempo and dificil05 > melhor_dificil)))):
        melhor = 5
        melhor_nome = equipe05
        melhor_pontos = pontu05
        melhor_tempo = tempo05
        melhor_facil = facil05
        melhor_media = media05
        melhor_dificil = dificil05

    print(f'{colocacao}º lugar: {melhor_nome} com {melhor_pontos} pontos, {melhor_tempo} segundos e {melhor_facil} questões fáceis, {melhor_media} questões médias e {melhor_dificil} questões difíceis resolvidas!')

    if melhor == 1:
        usado01 = 1
    elif melhor == 2:
        usado02 = 1
    elif melhor == 3:
        usado03 = 1
    elif melhor == 4:
        usado04 = 1
    elif melhor == 5:
        usado05 = 1

    colocacao += 1

# Ordem das equipes que mais acertaram questões difíceis
maior_dificil = dificil01

if dificil02 > maior_dificil:
    maior_dificil = dificil02
if dificil03 > maior_dificil:
    maior_dificil = dificil03
if dificil04 > maior_dificil:
    maior_dificil = dificil04
if dificil05 > maior_dificil:
    maior_dificil = dificil05

print('Equipe(s) que mais acertaram questões difíceis:')

if dificil01 == maior_dificil:
    print(f'A equipe {equipe01} acertou {dificil01} questões difíceis.')
if dificil02 == maior_dificil:
    print(f'A equipe {equipe02} acertou {dificil02} questões difíceis.')
if dificil03 == maior_dificil:
    print(f'A equipe {equipe03} acertou {dificil03} questões difíceis.')
if dificil04 == maior_dificil:
    print(f'A equipe {equipe04} acertou {dificil04} questões difíceis.')
if dificil05 == maior_dificil:
    print(f'A equipe {equipe05} acertou {dificil05} questões difíceis.')

#exibir a media das equipes 
print(f'A media das equipes foi: {media:.2f}')
