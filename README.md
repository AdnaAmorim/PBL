marco2pbl
Projeto desenvolvido para o Marco 2 do PBL, utilizando a placa DE1-SoC para realizar inferência de uma rede neural em hardware. O sistema usa o HPS para enviar dados para a FPGA pela lightweight bridge e um coprocessador em Verilog para executar o processamento.
Objetivo
O objetivo do projeto é classificar uma imagem 28x28 usando uma rede neural implementada na FPGA. A imagem, os pesos, os bias e os valores beta são enviados pelo HPS para o coprocessador por meio de registradores PIO mapeados em memória.
Estrutura do projeto
```text
marco2pbl-main/
├── README.md
├── arquivos/
│   ├── W\_in\_q.hex
│   ├── W\_in\_q.mif
│   ├── W\_in\_q.txt
│   ├── b\_q.hex
│   ├── b\_q.mif
│   ├── b\_q.txt
│   ├── beta\_q.hex
│   ├── beta\_q.mif
│   └── beta\_q.txt
├── coprocessador/
│   ├── CoProcessor.v
│   ├── first\_layer.v
│   ├── second\_layer.v
│   ├── neural\_unit.v
│   ├── lsu\_controller.v
│   ├── argmax\_iterativo.v
│   ├── display\_resultado.v
│   ├── reg\_bank10.v
│   ├── reg\_bank128.v
│   ├── mac\_first\_layer.v
│   ├── mac\_second\_layer.v
│   ├── tanh\_pwl\_q4\_12.v
│   ├── ghrd\_top.v
│   └── arquivos do projeto Quartus/Qsys
└── driver/
    ├── driver.s
    ├── driver.c
    ├── imagem2.bin
    ├── imagem6.bin
    ├── imagem8.bin
    ├── W\_in\_q.bin
    ├── b\_q.bin
    └── beta\_q.bin
```
Funcionamento geral
O projeto é dividido em duas partes principais:
Coprocessador em Verilog, responsável por receber os dados, armazenar a imagem, os pesos, os bias e os valores beta, executar a inferência e retornar o resultado.
Driver userspace em Assembly ARM, responsável por acessar a memória física da FPGA, enviar os dados para o coprocessador e iniciar a inferência.
O arquivo principal do driver em Assembly é:
```text
driver/driver.s
```
Esse arquivo abre o dispositivo `/dev/mem`, mapeia a região da lightweight bridge com `mmap`, envia as instruções para a FPGA e aguarda a finalização do processamento.
Comunicação HPS-FPGA
A comunicação entre o HPS e a FPGA é feita usando a lightweight bridge, com a seguinte base física:
```text
LW\_BASE = 0xFF200000
LW\_SPAN = 0x00005000
```
Os registradores PIO usados pelo driver são:
```text
PIO\_DATA\_IN   = 0x00
PIO\_DATA\_OUT  = 0x10
PIO\_CTRL      = 0x20
```
PIO_DATA_IN
Registrador usado pelo HPS para enviar instruções para a FPGA.
PIO_DATA_OUT
Registrador usado pela FPGA para retornar o status do processamento e o resultado da inferência.
PIO_CTRL
Registrador usado pelo HPS para controlar os sinais de `enable`, `clear` e `reset`.
Instruções enviadas pelo driver
O driver usa opcodes para indicar ao coprocessador qual operação deve ser executada.
Opcode	Nome	Função
0	`OP\_STORE\_IMAGE`	Envia os pixels da imagem
1	`OP\_STORE\_WEIGHT\_ADDR`	Envia o endereço do peso
2	`OP\_STORE\_WEIGHT\_VALUE`	Envia o valor do peso
3	`OP\_STORE\_BIAS`	Envia os valores de bias
4	`OP\_STORE\_BETA`	Envia os valores de beta
5	`OP\_START`	Inicia a inferência
Bits de controle
Bit	Nome	Função
0	`CTRL\_ENABLE`	Confirma o envio de uma instrução
1	`CTRL\_CLEAR`	Limpa estados antigos, como `DONE` e `ERROR`
2	`CTRL\_RESET`	Reseta a lógica da FPGA
Bits de status
Bit	Nome	Função
4	`STATUS\_DONE`	Indica que a inferência terminou
5	`STATUS\_BUSY`	Indica que a FPGA está ocupada
6	`STATUS\_ERROR`	Indica erro no processamento
0 a 3	`RESULT\_MASK`	Guarda o resultado da classificação
Fluxo do driver.s
O `driver.s` executa a seguinte sequência:
Abre o dispositivo `/dev/mem`.
Mapeia a lightweight bridge com `mmap`.
Reseta e limpa a FPGA.
Envia a imagem de entrada com 784 pixels.
Envia os pesos da rede neural.
Envia os valores de bias.
Envia os valores de beta.
Envia a instrução `START`.
Aguarda o bit `DONE` ser ativado.
Verifica se ocorreu erro na FPGA.
Lê o resultado da classificação em `PIO\_DATA\_OUT`.
Fecha `/dev/mem`.
Retorna o dígito classificado como código de saída do programa.
Arquivos binários usados pelo driver
O driver em Assembly usa `.incbin` para incluir os arquivos binários diretamente no executável.
```asm
imagem:
    .incbin "imagem8.bin"

pesos:
    .incbin "W\_in\_q.bin"

bias:
    .incbin "b\_q.bin"

beta:
    .incbin "beta\_q.bin"
```
Por causa disso, os arquivos binários precisam estar na mesma pasta do `driver.s` durante a compilação.
Arquivos necessários:
```text
imagem8.bin
W\_in\_q.bin
b\_q.bin
beta\_q.bin
```
Compilação
Entre na pasta do driver:
```bash
cd driver
```
Compile o arquivo Assembly:
```bash
gcc -o driver driver.s
```
Caso a compilação seja feita diretamente na DE1-SoC, o GCC usará a arquitetura ARM da placa.
Execução
Execute o driver com permissão de superusuário:
```bash
sudo ./driver
```
Depois da execução, veja o valor retornado pelo programa:
```bash
echo $?
```
O valor mostrado representa o dígito classificado pela rede neural.
Exemplo:
```bash
sudo ./driver
echo $?
```
Saída esperada para `imagem8.bin`:
```text
8
```
Códigos de retorno
Retorno	Significado
0 a 9	Dígito classificado pela rede
-1	Erro ao abrir `/dev/mem` ou ao fazer `mmap`
-2	Erro de processamento, erro da FPGA ou timeout
Como o Linux mostra códigos de saída em 8 bits, valores negativos podem aparecer convertidos. Por exemplo, `-1` pode aparecer como `255` e `-2` pode aparecer como `254` ao usar `echo $?`.
Observações importantes
O programa precisa ser executado com `sudo`, pois acessa `/dev/mem`.
O driver não imprime o resultado na tela; ele retorna o resultado como código de saída.
A imagem atualmente usada pelo `driver.s` é `imagem8.bin`.
Para testar outra imagem, é necessário trocar o arquivo usado no `.incbin`, por exemplo `imagem2.bin` ou `imagem6.bin`.
Os pesos, bias e beta são enviados em formato binário.
O driver usa `REV` para ajustar a ordem dos bytes dos arquivos binários.
O driver usa `ASR` para obter os valores quantizados Q4.12 com sinal.
O bit `DONE` indica que a inferência terminou.
O bit `ERROR` indica falha no processamento dentro da FPGA.
Módulos principais do coprocessador
CoProcessor.v
Módulo principal do coprocessador, responsável por integrar a comunicação com o HPS e a lógica de inferência.
lsu_controller.v
Controla o recebimento das instruções enviadas pelo driver e o armazenamento dos dados recebidos.
first_layer.v
Executa a primeira camada da rede neural.
second_layer.v
Executa a segunda camada da rede neural.
neural_unit.v
Representa a unidade neural usada no processamento da rede.
mac_first_layer.v
Executa as operações de multiplicação e acumulação da primeira camada.
mac_second_layer.v
Executa as operações de multiplicação e acumulação da segunda camada.
tanh_pwl_q4_12.v
Implementa a aproximação da função de ativação `tanh` em ponto fixo Q4.12.
argmax_iterativo.v
Seleciona a maior saída da rede neural e define a classe final.
display_resultado.v
Mostra o resultado da classificação nos displays da placa.
Autoria
Projeto desenvolvido para a disciplina TEC499, referente ao Marco 2 do PBL.
