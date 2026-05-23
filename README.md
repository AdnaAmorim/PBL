# Co-processador de Inferencia Neural em FPGA — ELM

**Classificador de digitos manuscritos (MNIST) implementado em hardware reconfiguravel.**  
Sistema embarcado com arquitetura HPS + FPGA (Intel Cyclone V SoC), comunicacao via MMIO e rede neural MLP de duas camadas em ponto fixo Q4.12.

---

## Sumario

- [Introducao](#introducao)
- [Requisitos Principais](#requisitos-principais)
  - [Entrada e Saida](#entrada-e-saida)
  - [Driver](#driver)
    - [rotinas.s — Ciclo de Vida da FPGA](#rotinass--ciclo-de-vida-da-fpga)
    - [instrucoes.s — Protocolo MMIO](#instrucoess--protocolo-mmio)
    - [Codigos de Erro](#codigos-de-erro)
  - [Aplicacao C](#aplicacao-c)
  - [Makefile e Build](#makefile-e-build)
- [Co-processador ELM](#co-processador-elm)
  - [Unidade de Controle](#unidade-de-controle)
  - [Unidade de Inferencia](#unidade-de-inferencia)
  - [Load/Store Unit](#loadstore-unit)
  - [Conjunto de Instrucoes](#conjunto-de-instrucoes)
  - [Fluxo de Execucao](#fluxo-de-execucao)
- [Modulos Computacionais](#modulos-computacionais)
  - [MAC da Primeira Camada](#mac-da-primeira-camada)
  - [MAC da Segunda Camada](#mac-da-segunda-camada)
  - [Funcao de Ativacao tanh PWL](#funcao-de-ativacao-tanh-pwl)
  - [Argmax Iterativo](#argmax-iterativo)
  - [Bancos de Registradores](#bancos-de-registradores)
  - [Display de Resultado](#display-de-resultado)
- [Aritmetica em Ponto Fixo Q4.12](#aritmetica-em-ponto-fixo-q412)
- [Metodologia de Desenvolvimento](#metodologia-de-desenvolvimento)
- [Estrutura do Repositorio](#estrutura-do-repositorio)
- [Parametros da Rede Neural](#parametros-da-rede-neural)

---

## Introducao

Este projeto implementa um **co-processador dedicado a inferencia de redes neurais** diretamente em fabric FPGA, integrado ao processador ARM Cortex-A9 (HPS) do kit DE1-SoC (Intel Cyclone V).

O objetivo e classificar digitos manuscritos do dataset MNIST com latencia minima, transferindo o custo computacional das operacoes de MAC (Multiply-Accumulate) do processador de proposito geral para logica dedicada em hardware. A rede neural utiliza representacao em **ponto fixo Q4.12** (16 bits), eliminando a necessidade de unidade de ponto flutuante e reduzindo drasticamente a area e o consumo do circuito.

A comunicacao entre o HPS e o co-processador ocorre por **mapeamento de memoria (MMIO)** atraves da Lightweight HPS-to-FPGA Bridge no endereco fisico `0xFF200000`, com um protocolo de instrucoes de 32 bits baseado em handshake por polling implementado inteiramente em Assembly ARMv7.

---

## Requisitos Principais

### Entrada e Saida

O sistema opera sobre imagens de **28 x 28 pixels em escala de cinza** (784 bytes, valores de 0 a 255), no formato PNG organizado por classe (0 a 9) conforme a estrutura padrao do MNIST.

A saida e um **unico digito (0 a 9)**, representado em 4 bits nos bits `[3:0]` do registrador `PIO_DATA_OUT`, lido pelo HPS apos a sinalizacao de conclusao (`DONE`).

| Sinal | Bits em `data_out` | Descricao |
|---|---|---|
| `predicted_digit` | [3:0] | Digito classificado pela rede |
| `fl_processor_done` | [4] | Inferencia concluida |
| `fl_processor_busy` | [5] | Co-processador ocupado |
| `fl_error` | [6] | Instrucao invalida ou endereco fora do limite |

---

### Driver

O driver e a camada de abstração entre o codigo C e o hardware da FPGA. E implementado em dois arquivos Assembly ARMv7 (`rotinas.s` e `instrucoes.s`) com interface publica declarada em `driver.h`. Toda comunicacao com o hardware e feita por acesso direto a memoria fisica atraves de `/dev/mem`, sem sistema operacional de tempo real.

**Registradores PIO mapeados na Lightweight Bridge:**

| Registrador | Offset | Funcao |
|---|---|---|
| `PIO_DATA_IN` | `0x00` | Palavra de instrucao de 32 bits enviada ao co-processador |
| `PIO_DATA_OUT` | `0x10` | Status e resultado lidos do co-processador |
| `PIO_CTRL` | `0x20` | Controle de `ENABLE` (bit 0), `CLEAR` (bit 1) e `RESET` (bit 2) |

---

#### rotinas.s — Ciclo de Vida da FPGA

Gerencia a abertura, mapeamento e fechamento da conexao com o hardware. Exporta duas variaveis globais compartilhadas com `instrucoes.s`:

| Variavel global | Tipo | Descricao |
|---|---|---|
| `fd_devmem` | `.word` | File descriptor de `/dev/mem`; `-1` indica nao aberto |
| `base_virtual` | `.word` | Ponteiro virtual para a Lightweight Bridge apos `mmap`; `0` indica nao mapeado |

**Constantes de mapeamento:**

| Constante | Valor | Descricao |
|---|---|---|
| `BRIDGE_ENDERECO_FISICO` | `0xFF200000` | Endereco fisico da Lightweight HPS-to-FPGA Bridge |
| `BRIDGE_TAMANHO` | `0x00005000` | Janela de mapeamento (20 KB) |
| `FLAG_RDWR` | `2` | `O_RDWR`: abre `/dev/mem` para leitura e escrita |
| `FLAG_SYNC` | `0x101000` | `O_SYNC`: escritas chegam ao hardware imediatamente |
| `MMAP_PROT_RDWR` | `3` | `PROT_READ | PROT_WRITE` |
| `MMAP_COMPARTILHADO` | `1` | `MAP_SHARED`: alteracoes refletem diretamente no hardware |

**Funcoes exportadas:**

`inicializar_fpga()` — Abre `/dev/mem` com `O_RDWR | O_SYNC` e chama `mmap` com `MAP_SHARED` sobre o endereco fisico da bridge. Salva o file descriptor em `fd_devmem` e o ponteiro resultante em `base_virtual`. Retorna o ponteiro base (nao-nulo) em sucesso ou `0` em falha. Trata separadamente erro de `open` e erro de `mmap`, fechando o fd antes de retornar no segundo caso.

`finalizar_fpga()` — Le `fd_devmem`; se valido, chama `munmap` sobre `base_virtual` e depois `close` sobre o fd. Ao fim, zera ambas as variaveis globais para evitar uso acidental apos o encerramento.

`reset_clean_fpga()` — Executa dois pulsos sequenciais no registrador `PIO_CTRL`: primeiro `BIT_RESET` (bit 2), depois `BIT_CLEAR` (bit 1). Cada pulso segue o padrao: ativa o bit, aguarda um loop de 1000 iteracoes, desativa, aguarda mais 1000 iteracoes. Garante estabilizacao do estado interno do co-processador antes do primeiro uso.

**Sequencia de reset:**

```
PIO_CTRL <- BIT_RESET    -> delay ~1000 ciclos
PIO_CTRL <- 0            -> delay ~1000 ciclos
PIO_CTRL <- BIT_CLEAR    -> delay ~1000 ciclos
PIO_CTRL <- 0            -> delay ~1000 ciclos
```

---

#### instrucoes.s — Protocolo MMIO

Implementa o protocolo de handshake e as funcoes de envio dos parametros da rede neural. Toda comunicacao passa pela funcao interna `enviar_instrucao`, que nao e exportada.

**Funcao interna `enviar_instrucao` (handshake completo):**

```
Entrada:  R0 = palavra de instrucao de 32 bits
Retorno:  R0 = 0 (sucesso) | -99 (timeout) | -3 (erro interno da FPGA)

1. Escreve instrucao em PIO_DATA_IN
2. Ativa CTRL_ENABLE  -> FPGA le e levanta BUSY
3. Aguarda BUSY subir   (FPGA confirmou recebimento)    timeout: 200.000 iteracoes
4. Desativa CTRL_ENABLE
5. Aguarda BUSY descer  (FPGA terminou de processar)    timeout: 200.000 iteracoes
6. Verifica STATUS_ERROR -> retorna -3 se ativo
```

**Bits de status lidos em `PIO_DATA_OUT`:**

| Constante | Valor | Descricao |
|---|---|---|
| `STATUS_DONE` | `0x10` | Inferencia concluida |
| `STATUS_BUSY` | `0x20` | Co-processador ocupado |
| `STATUS_ERROR` | `0x40` | Erro interno sinalizado pela FPGA |
| `RESULT_MASK` | `0x0F` | Mascara para extrair o digito [3:0] |

**Opcodes de instrucao:**

| Constante | Valor [2:0] | Funcao |
|---|---|---|
| `OP_STORE_IMAGE` | `0` | Armazena pixel da imagem |
| `OP_STORE_WEIGHT_ADDR` | `1` | Define endereco para escrita de peso |
| `OP_STORE_WEIGHT_VALUE` | `2` | Armazena valor do peso no endereco anterior |
| `OP_STORE_BIAS` | `3` | Armazena valor de bias |
| `OP_STORE_BETA` | `4` | Armazena valor de beta |
| `OP_START` | `5` | Dispara a inferencia |

**Tamanhos dos vetores:**

| Constante | Valor | Descricao |
|---|---|---|
| `TAM_IMAGEM` | `784` | Pixels (28x28) |
| `TAM_BIAS` | `128` | Valores de bias da camada oculta |
| `TAM_BETA` | `1280` | Pesos da camada de saida (128 x 10) |
| `TAM_PESOS` | `100352` | Pesos da camada oculta (784 x 128) |

**Funcoes exportadas:**

| Funcao | Instrucoes enviadas | Descricao |
|---|---|---|
| `enviar_bias()` | 128 | Envia os 128 valores de bias via `OP_STORE_BIAS` |
| `enviar_beta()` | 1280 | Envia os 1280 valores de beta via `OP_STORE_BETA` |
| `enviar_pesos()` | 200.704 | Envia os 100.352 pesos via `OP_STORE_WEIGHT_ADDR` + `OP_STORE_WEIGHT_VALUE` (2 instrucoes por peso) |
| `enviar_imagem()` | 784 | Envia os 784 pixels via `OP_STORE_IMAGE` |
| `inferencia()` | 1 | Pulsa `CLEAR`, envia `OP_START`, aguarda `STATUS_DONE`; timeout de 2.000.000 iteracoes |
| `ler_resultado()` | — | Le `PIO_DATA_OUT` e retorna `data & RESULT_MASK` |

---

#### Codigos de Erro

| Codigo | Origem | Significado |
|---|---|---|
| `0` | — | Sucesso |
| `-2` | `inferencia()` | Timeout aguardando `STATUS_DONE` |
| `-3` | qualquer funcao | Erro interno sinalizado por `STATUS_ERROR` na FPGA |
| `-99` | `enviar_instrucao` | Timeout de handshake (BUSY nao subiu ou nao desceu) |

---

### Aplicacao C

O arquivo `main.c` implementa um **benchmark completo** de 1.000 inferencias consecutivas, medindo latencia individual e throughput agregado com `clock_gettime(CLOCK_MONOTONIC)` para precisao em nanossegundos.

**Sequencia de execucao:**

```
inicializar_fpga()
reset_clean_fpga()

enviar_bias()                          <- parametros fixos, enviados uma unica vez
enviar_beta()
enviar_pesos()

loop 1000 vezes:
    enviar_imagem()
    inferencia()
    ler_resultado()

finalizar_fpga()
```

Os parametros da rede (bias, beta, pesos) sao enviados uma unica vez antes do loop, pois sao constantes para todas as inferencias. Apenas a imagem e trocada a cada iteracao.

**Metricas reportadas ao final:**

| Metrica | Formula | Descricao |
|---|---|---|
| Digito identificado | — | Resultado da ultima inferencia valida |
| Repeticoes | — | Total de inferencias tentadas (1000) |
| Execucoes validas | `REPETICOES - falhas` | Inferencias concluidas sem erro |
| Falhas | — | Erros de comunicacao ou timeout |
| Porcentagem de acertos | `acertos / validas * 100` | Taxa de inferencias com resultado valido |
| Throughput | `validas / (tempo_total / 1000)` | Inferencias por segundo |
| Latencia media | `soma_latencias / validas` | Media das latencias individuais em ms |
| Tempo total | — | Duracao total do benchmark em ms |

---

### Makefile e Build

O projeto usa um `Makefile` minimalista voltado para compilacao cruzada no proprio DE1-SoC (ARM Linux).

```makefile
CC     = gcc
TARGET = inferencia
SRC    = main.c rotinas.s instrucoes.s

all:
    $(CC) -o $(TARGET) $(SRC) -lrt

run: all
    sudo ./$(TARGET)

clean:
    rm -f $(TARGET) *.o
```

O arquivo `main.c` e os dois Assembly sao compilados e linkados diretamente pelo `gcc`. A flag `-lrt` e obrigatoria para `clock_gettime`. A execucao requer `sudo` por conta do acesso direto a `/dev/mem`.

---

## Co-processador ELM

O co-processador e composto por tres subsistemas: a **Unidade de Controle** (`CoProcessor.v`), a **Unidade de Inferencia** (`neural_unit.v`) e as **Load/Store Units** (`lsu_controller.v`).

---

### Unidade de Controle

Modulo topo do co-processador (`CoProcessor.v`). Implementa uma FSM de quatro estados responsavel por receber instrucoes do HPS, rotear escritas nas memorias internas e disparar a inferencia.

**FSM de estados:**

```
         enable && !busy
ST_IDLE ----------------> ST_DECODE
   ^                          |
   |          instrucao de    |  START
   |          memoria         v
   +<-------- ST_MEMORY <-- (split)
   |          lsu_done         |
   |                           v
   +<-------- ST_INFERENCE <---+
              inference_done
```

| Estado | Descricao |
|---|---|
| `ST_IDLE` | Aguarda `enable` ativo. Garante que `busy` so sobe com nova instrucao valida. Baixa `busy` quando `enable` desce (handshake seguro) |
| `ST_DECODE` | Decodifica `data_in[2:0]`, valida enderecos, configura sinais de controle e decide o proximo estado |
| `ST_MEMORY` | Aguarda a LSU correspondente sinalizar `done`. Ao concluir, seta `fl_processor_done` e retorna a IDLE |
| `ST_INFERENCE` | Aguarda `inference_done` da `neural_unit`. Captura `inference_output` em `predicted_digit_register` ao concluir |

**Multiplexador de barramento das memorias:**

Durante a inferencia (`inference_controller = 1`), o controle das quatro BRAMs e transferido integralmente para a `neural_unit`. Os sinais de enable e endereco de leitura passam a vir da unidade de inferencia, garantindo acesso exclusivo sem arbitragem adicional.

```verilog
wire lsu_img_en_final    = inference_controller ? req_pixel : lsu_img_en_inst;
wire lsu_bias_en_final   = inference_controller ? req_bias  : lsu_bias_en_inst;
wire lsu_beta_en_final   = inference_controller ? req_beta  : lsu_beta_en_inst;
wire lsu_weigth_en_final = inference_controller ? req_win   : lsu_weigth_en_inst;
```

**Interface de portas:**

| Porta | Largura | Direcao | Descricao |
|---|---|---|---|
| `clk` | 1 | entrada | Clock principal do sistema |
| `data_in` | 32 | entrada | Palavra de instrucao vinda do HPS |
| `enable` | 1 | entrada | Sinal de handshake do HPS |
| `clr_operation` | 1 | entrada | Limpa `fl_done` e `fl_error` |
| `rst` | 1 | entrada | Reset sincrono global |
| `data_out` | 32 | saida | `{25'b0, error, busy, done, digit[3:0]}` |

---

### Unidade de Inferencia

Modulo `neural_unit.v` — orquestra a execucao sequencial das camadas da rede neural. Instancia e conecta todos os modulos computacionais.

**FSM de estados:**

```
IDLE -> FIRST_LAYER -> SECOND_LAYER -> ARGMAX -> DONE -> IDLE
```

| Estado | Acao | Condicao de avanco |
|---|---|---|
| `IDLE` | Aguarda `enable` da unidade de controle | `enable = 1` |
| `FIRST_LAYER` | Ativa `first_layer`, mantem `rst_first_layer = 0` | `first_layer_iteration_done = 1` |
| `SECOND_LAYER` | Ativa `second_layer`, libera reset do argmax | `second_layer_iteration_done = 1` |
| `ARGMAX` | Ativa `argmax_iterativo` | `argmax_iteration_done = 1` |
| `DONE` | Seta `done = 1` por um ciclo | automatico |

**Topologia da rede neural implementada:**

```
Entrada (784 pixels, uint8)
        |
   [first_layer]        <- 784 x 128 MACs + bias + tanh PWL
        |
  [reg_bank128]         <- 128 resultados Q4.12 armazenados
        |
   [second_layer]       <- 128 x 10 MACs + beta
        |
   [reg_bank10]         <- 10 scores Q4.12 armazenados
        |
 [argmax_iterativo]     <- indice do maior score
        |
  Saida: digito [3:0]
```

**Modulos instanciados:**

| Instancia | Modulo | Funcao |
|---|---|---|
| `fr_layer` | `first_layer` | Camada oculta: 784->128 neuronios com bias e tanh |
| `reg_first_layer` | `reg_bank128` | 128 registradores para saidas da camada 1 |
| `sd_layer` | `second_layer` | Camada de saida: 128->10 neuronios com beta |
| `reg_second_layer` | `reg_bank10` | 10 registradores para scores finais |
| `agm` | `argmax_iterativo` | Classificador: retorna indice do maior score |

---

### Load/Store Unit

Modulo `lsu_controller.v` — abstrai o acesso as BRAMs internas (Intel `altsyncram`) com uma interface de handshake baseada em `enable/done`. E parametrizavel e instanciado quatro vezes no sistema com configuracoes distintas.

**FSM interna:**

```
IDLE -> IN_OPERATION (conta CYCLES_PER_OP ciclos) -> DONE (pulso de 1 ciclo) -> IDLE
```

A BRAM e instanciada no modo `DUAL_PORT`: porta A para escrita, porta B para leitura. O endereco de leitura e passado diretamente (sem registro), permitindo acesso de leitura em qualquer ciclo. A escrita e registrada no momento do `enable` para garantir dados coerentes durante a latencia.

**Parametros de instanciacao:**

| Parametro | Tipo | Descricao |
|---|---|---|
| `DATA_WIDTH` | inteiro | Largura do dado em bits |
| `MEM_SIZE` | inteiro | Numero de posicoes de memoria |
| `CYCLES_PER_OP` | inteiro | Latencia de operacao em ciclos |
| `DEVICE_FAMILY` | string | Familia alvo para inferencia de bloco RAM |
| `RAM_TYPE` | string | Tipo de RAM (`"AUTO"`, `"M10K"`, etc.) |
| `INIT_FILE` | string | Arquivo `.mif` de inicializacao (opcional) |

**Instancias no co-processador:**

| Instancia | DATA_WIDTH | MEM_SIZE | Capacidade | Conteudo |
|---|---|---|---|---|
| `mem_img` | 8 bits | 784 | 784 B | Pixels da imagem de entrada (uint8) |
| `mem_bias` | 16 bits | 128 | 256 B | Bias da camada oculta (Q4.12) |
| `mem_beta` | 16 bits | 1.280 | 2,5 KB | Pesos da camada de saida (Q4.12) |
| `mem_weigth` | 16 bits | 100.352 | ~196,8 KB | Pesos da camada oculta (Q4.12) |

Todas as instancias usam `CYCLES_PER_OP = 3`, `DEVICE_FAMILY = "Cyclone V"` e `RAM_TYPE = "AUTO"`.

---

### Conjunto de Instrucoes

O protocolo e baseado em palavras de **32 bits** com os 3 bits menos significativos como opcode. Os campos de endereco e dado estao empacotados nos bits restantes da mesma palavra, minimizando o numero de transacoes para a maioria das operacoes.

| Opcode [2:0] | Mnemonica | Campos | Limite de endereco |
|---|---|---|---|
| `000` | `STORE_IMG` | `[12:3]` addr (10b) + `[20:13]` pixel (8b) | 783 |
| `001` | `STORE_WEIGHTS_ADDR` | `[19:3]` addr (17b) | 100.351 |
| `010` | `STORE_WEIGHTS_VALUE` | `[18:3]` valor (16b) | — |
| `011` | `STORE_BIAS` | `[9:3]` addr (7b) + `[25:10]` valor (16b) | 127 |
| `100` | `STORE_BETA` | `[13:3]` addr (11b) + `[29:14]` valor (16b) | 1.279 |
| `101` | `START` | — | — |
| `110` | `STATUS` | — | — |
| `111` | `NOP` | — | — |

Observacoes sobre o ISA:

- `STORE_WEIGHTS_ADDR` e `STORE_WEIGHTS_VALUE` sao sempre emitidas em par. O endereco e armazenado em `addr_weigth_register` e reutilizado pela instrucao de valor seguinte. A instrucao de endereco retorna direto ao `ST_IDLE` sem passar por `ST_MEMORY`.
- Qualquer endereco acima do limite seta `fl_error = 1` no ciclo de decode, abortando a operacao e retornando ao `ST_IDLE`.
- `STATUS` e `NOP` retornam imediatamente ao `ST_IDLE` sem modificar memorias ou flags (exceto `clr_operation`, que pode limpar flags antes).

---

### Fluxo de Execucao

Diagrama completo de uma inferencia, do software ao resultado:

```
HPS (ARM Cortex-A9)                       FPGA (Cyclone V)
-----------------------------------------  ------------------------------------
inicializar_fpga()
  open("/dev/mem", O_RDWR|O_SYNC)
  mmap(0xFF200000, 0x5000, MAP_SHARED)
  -> base_virtual

reset_clean_fpga()
  PIO_CTRL <- BIT_RESET  -> delay -> 0 -> delay
  PIO_CTRL <- BIT_CLEAR  -> delay -> 0 -> delay

enviar_bias()    (128x handshake)  -----> ST_DECODE -> ST_MEMORY (x128)
enviar_beta()   (1280x handshake)  -----> ST_DECODE -> ST_MEMORY (x1280)
enviar_pesos() (100352x 2 instr.)  -----> STORE_WEIGHTS_ADDR + VALUE (x100352)

[ loop 1000x ]

  enviar_imagem()  (784x handshake)  ---> ST_DECODE -> ST_MEMORY (x784)

  inferencia():
    PIO_CTRL <- CLEAR
    envia OP_START             --------> ST_DECODE -> ST_INFERENCE
                                           neural_unit: IDLE -> FIRST_LAYER
                                             first_layer:
                                               128 neuronios, para cada:
                                                 MAC(784 pixels x pesos) + bias
                                                 tanh_pwl_q4_12(resultado)
                                               -> reg_bank128 (128 x Q4.12)
                                           -> SECOND_LAYER
                                             second_layer:
                                               10 neuronios, para cada:
                                                 MAC(128 saidas x beta)
                                               -> reg_bank10 (10 x Q4.12)
                                           -> ARGMAX
                                             argmax_iterativo:
                                               itera 10 posicoes
                                               retorna indice do max
                                           -> DONE
                                             fl_processor_done = 1

    polling PIO_DATA_OUT       <-------- data_out[4] (STATUS_DONE)

  ler_resultado()
    data_out & RESULT_MASK     <-------- predicted_digit[3:0]

[ fim do loop ]

finalizar_fpga()
  munmap(base_virtual, 0x5000)
  close(fd_devmem)
  fd_devmem   <- -1
  base_virtual <- 0
```

---

## Modulos Computacionais

### MAC da Primeira Camada

Modulo `mac_first_layer.v` — unidade de multiplicacao-acumulacao para a camada oculta. Recebe um pixel (uint8 ou o valor `1` para o bias) e um peso Q4.12, e acumula o produto em ponto fixo.

**Caminho de dados:**

```
pixel[7:0] -> in_signed[15:0] = {3'b000, pixel, 4'b0000}  (converte uint8 para Q4.12)
weigth[15:0] (Q4.12, signed)

product_q8_24 = in_signed * weigth               (32 bits, Q8.24)
product_q12   = product_q8_24 >>> 12             (realinha para Q4.12)
accumulator  += product_q12                      (32 bits, protege overflow)

out_q4_12 = saturate(accumulator, -32768, 32767) (clipping para 16 bits)
```

O pixel e convertido para Q4.12 deslocando 4 bits a esquerda, alinhando a virgula fracionaria com os pesos antes da multiplicacao. O acumulador de 32 bits absorve ate 784 produtos sem risco de overflow. A saturacao (clipping) na saida garante que o resultado cabe em 16 bits antes de ser passado para a funcao de ativacao.

**Portas:**

| Porta | Largura | Descricao |
|---|---|---|
| `weigth_or_bias` | 16b signed | Peso ou bias em Q4.12 |
| `one_or_pixel` | 9b | Pixel (0-255) ou `1` para operacao de bias |
| `clk` | 1b | Clock |
| `enable` | 1b | Acumula quando ativo |
| `rst` | 1b | Reset assincrono do acumulador |
| `clear_acc` | 1b | Zera o acumulador (inicio de novo neuronio) |
| `out_q4_12` | 16b signed | Resultado acumulado em Q4.12 |

---

### MAC da Segunda Camada

Modulo `mac_second_layer.v` — unidade MAC para a camada de saida. Opera sobre dois valores Q4.12 (saida do banco de registradores e coeficiente beta).

**Caminho de dados:**

```
data_register[15:0] (Q4.12, saida da camada oculta)
data_beta[15:0]     (Q4.12, peso da camada de saida)

product_q8_24 = data_beta * data_register        (32 bits, Q8.24)
product_q12   = product_q8_24 >>> 12             (realinha para Q4.12)
accumulator  += product_q12                      (32 bits, protege overflow)

out_q4_12 = saturate(accumulator, -32768, 32767)
```

Identico ao MAC da primeira camada em estrutura, mas opera sobre dois Q4.12 diretamente (sem conversao de uint8). O acumulador de 32 bits suporta 128 acumulacoes sem overflow para valores Q4.12.

---

### Funcao de Ativacao tanh PWL

Modulo `tanh_pwl_q4_12.v` — aproximacao da funcao tanh por **4 segmentos lineares**, implementada como logica combinacional pura (sem clock). Opera sobre valores Q4.12 (16 bits com sinal).

**Segmentos de aproximacao (sobre o valor absoluto):**

| Intervalo (real) | Intervalo (Q4.12) | Aproximacao | Formula Q4.12 |
|---|---|---|---|
| [0.0, 0.5) | [0, 2048) | `y = x` | `abs_y = abs_x` |
| [0.5, 1.0) | [2048, 4096) | `y = 0.5x + 0.25` | `abs_y = (abs_x >>> 1) + 1024` |
| [1.0, 1.5) | [4096, 6144) | `y = 0.25x + 0.5` | `abs_y = (abs_x >>> 2) + 2048` |
| [1.5, 2.5) | [6144, 10240) | `y = 0.125x + 0.6875` | `abs_y = (abs_x >>> 3) + 2816` |
| [2.5, inf) | [10240, inf) | `y = 1.0` | `abs_y = 4096` |

A simetria da tanh e explorada calculando a aproximacao sobre `|x|` e reaplicando o sinal original ao final. Todos os deslocamentos (`>>>`) sao aritmeticos e preservam o sinal. As constantes somadas estao em Q4.12 (ex: `1024 = 0.25`, `2048 = 0.5`, `4096 = 1.0`).

---

### Argmax Iterativo

Modulo `argmax_iterativo.v` — determina o indice do maior valor entre os 10 scores de saida da rede. Implementado como FSM de 3 estados com acesso sequencial ao `reg_bank10`.

**FSM:**

```
IDLE -> REQUEST_DATA -> EVALUATE -> (REQUEST_DATA | DONE)
```

| Estado | Acao |
|---|---|
| `IDLE` | Inicializa `counter = 0`, `max_score = -32768` (menor Q4.12) |
| `REQUEST_DATA` | Apresenta `counter` como endereco de leitura (`addr_r = counter`) |
| `EVALUATE` | Compara `data_in` com `max_score`. Atualiza se maior. Incrementa `counter`. Se `counter == 9`, seta `done = 1` |

O `max_score` e inicializado com `-32768` (`-16'sd32768`), o menor valor representavel em Q4.12 com sinal, garantindo que qualquer score valido venca a primeira comparacao. O modulo itera sobre os 10 indices em 20 ciclos (2 ciclos por posicao: `REQUEST_DATA` + `EVALUATE`).

---

### Bancos de Registradores

**`reg_bank128`** — 128 registradores de 16 bits (Q4.12) para armazenar as saidas da primeira camada. Porta de escrita e leitura sincronas na borda de subida do clock. Enderecamento de 7 bits em ambas as portas.

**`reg_bank10`** — 10 registradores de 16 bits (Q4.12) para armazenar os scores finais. Identico ao `reg_bank128` em estrutura, com enderecamento de 4 bits.

Ambos sao inferidos como registradores distribuidos (flip-flops) pelo Quartus, nao como blocos M10K, dada a profundidade reduzida.

| Modulo | Profundidade | Largura | Enderecos | Uso estimado |
|---|---|---|---|---|
| `reg_bank128` | 128 posicoes | 16 bits | 7 bits | 2.048 bits (FFs) |
| `reg_bank10` | 10 posicoes | 16 bits | 4 bits | 160 bits (FFs) |

---

### Display de Resultado

Modulo `display_resultado.v` — decodificador de 4 bits para display de 7 segmentos (catodo comum). Converte o digito predito (0-9) no padrao de segmentos para o display `HEX7` da DE1-SoC.

**Mapeamento de segmentos (ativo em baixo: `0` = aceso, `1` = apagado):**

| Digito | `hex_out[6:0]` | Segmentos ativos |
|---|---|---|
| 0 | `1000000` | a, b, c, d, e, f |
| 1 | `1111001` | b, c |
| 2 | `0100100` | a, b, d, e, g |
| 3 | `0110000` | a, b, c, d, g |
| 4 | `0011001` | b, c, f, g |
| 5 | `0010010` | a, c, d, f, g |
| 6 | `0000010` | a, c, d, e, f, g |
| 7 | `1111000` | a, b, c |
| 8 | `0000000` | todos |
| 9 | `0010000` | a, b, c, d, f, g |
| 10-15 (invalido) | `1111111` | display apagado |

---

## Aritmetica em Ponto Fixo Q4.12

Todos os pesos, bias, ativacoes e scores do sistema usam o formato **Q4.12**: 16 bits com sinal em complemento de dois, sendo 1 bit de sinal, 3 bits de parte inteira e 12 bits de parte fracionaria.

| Propriedade | Valor |
|---|---|
| Formato | Q4.12 (signed, complemento de dois) |
| Bits totais | 16 |
| Bits de parte inteira | 4 (incluindo sinal) |
| Bits de parte fracionaria | 12 |
| Valor maximo | 32767 / 4096 = +7.999... |
| Valor minimo | -32768 / 4096 = -8.0 |
| Resolucao | 1 / 4096 ≈ 0.000244 |

**Multiplicacao Q4.12 x Q4.12:**

O produto de dois Q4.12 produz um resultado Q8.24 (32 bits). Para realinhar a virgula, e necessario deslocar 12 posicoes a direita (`>>> 12`). O acumulador de 32 bits e mantido no formato Q20.12, absorvendo ate milhares de produtos sem overflow antes da saturacao final para 16 bits.

```
A (Q4.12) x B (Q4.12) = P (Q8.24, 32 bits)
P >>> 12               = resultado (Q4.12, alinhado, nos 16 bits inferiores)
```

**Conversao de uint8 para Q4.12 (MAC da camada 1):**

```
pixel_uint8[7:0] -> {3'b000, pixel[7:0], 4'b0000}
                    = pixel * 16 (desloca 4 bits a esquerda)
                    = pixel em Q4.12 (parte fracionaria zerada)
```

---

## Metodologia de Desenvolvimento

O projeto segue praticas de **co-design hardware/software**, com separacao clara de responsabilidades entre os dominios.

**Hardware (Verilog/Quartus):**  
Cada modulo e projetado como uma FSM independente com interface padronizada `enable/done/rst`, permitindo composicao hierarquica e testabilidade individual. A separacao entre plano de controle (FSMs) e plano de dados (MACs, BRAMs, registradores) e mantida em todos os niveis. A sintese foi realizada no **Intel Quartus Prime** com target **Cyclone V SoC (5CSEMA5F31C6)**.

**Quantizacao dos pesos:**  
Os pesos foram treinados em ponto flutuante e pos-quantizados para Q4.12. Os arquivos de saida em `.hex` e `.mif` estao prontos para carregamento via driver ou inicializacao de BRAM no Quartus. O formato `.txt` serve para inspecao e debug.

**Software (C + Assembly ARMv7):**  
O driver foi escrito diretamente em Assembly para controle preciso do protocolo de handshake MMIO, minimizando overhead de camadas de abstracao. A ABI ARM EABI e respeitada integralmente (convencao de registradores, passagem de argumentos na pilha para o 5o e 6o argumentos do `mmap`). A aplicacao C concentra logica de benchmark e metricas, chamando as funcoes Assembly como chamadas C convencionais.

**Validacao:**  
O dataset MNIST em PNG esta organizado em `arquivos/mnist_png/` por classe, permitindo scripts externos de validacao de acuracia sobre amostras reais. O benchmark reporta porcentagem de acertos sobre as 1.000 execucoes.

---

## Estrutura do Repositorio

```
marco2pbl/
|
+-- arquivos/
|   +-- W_in_q.hex / .mif / .txt    <- Pesos da camada oculta (Q4.12, 100352 valores)
|   +-- b_q.hex / .mif / .txt       <- Bias da camada oculta (Q4.12, 128 valores)
|   +-- beta_q.hex / .mif / .txt    <- Pesos da camada de saida (Q4.12, 1280 valores)
|   +-- mnist_png/                  <- Dataset MNIST organizado por digito (0-9)
|
+-- coprocessador/
|   +-- CoProcessor.v               <- Unidade de controle principal (FSM 4 estados)
|   +-- neural_unit.v               <- Orquestrador da inferencia (FSM 5 estados)
|   +-- first_layer.v               <- Camada oculta (784->128, 2 FSMs concorrentes)
|   +-- second_layer.v              <- Camada de saida (128->10, 2 FSMs concorrentes)
|   +-- mac_first_layer.v           <- Unidade MAC com conversao uint8->Q4.12
|   +-- mac_second_layer.v          <- Unidade MAC Q4.12 x Q4.12
|   +-- tanh_pwl_q4_12.v            <- Ativacao tanh por 4 segmentos lineares
|   +-- lsu_controller.v            <- Load/Store Unit (wrapper altsyncram)
|   +-- argmax_iterativo.v          <- Classificador argmax (FSM 3 estados, 20 ciclos)
|   +-- reg_bank128.v               <- 128 registradores Q4.12 (saidas camada 1)
|   +-- reg_bank10.v                <- 10 registradores Q4.12 (scores finais)
|   +-- display_resultado.v         <- Decodificador 4b -> 7 segmentos (HEX7)
|   +-- ghrd_top.v                  <- Top-level SoC (HPS + FPGA integrados)
|   +-- soc_system.qpf              <- Arquivo de projeto Quartus
|   +-- soc_system.qsf              <- Atribuicoes de pinos e configuracoes de sintese
|   +-- soc_system.qsys             <- Plataforma Platform Designer (HPS + bridges)
|   +-- soc_system_timing.sdc       <- Constraints de timing (SDC)
|   +-- hps_0.h                     <- Header C gerado pelo Platform Designer
|
+-- driver/
    +-- main.c                      <- Benchmark: 1000 inferencias, latencia e throughput
    +-- driver.h                    <- Interface publica do driver (declaracoes C)
    +-- instrucoes.s                <- Protocolo MMIO em Assembly ARMv7
    +-- rotinas.s                   <- Ciclo de vida da FPGA em Assembly ARMv7
    +-- Makefile                    <- Build: gcc + -lrt, target ARM Linux
    +-- data/                       <- Dados de entrada para testes do driver
    +-- inferencia/                 <- Resultados de inferencias de referencia
```

---

## Parametros da Rede Neural

| Parametro | Valor |
|---|---|
| Arquitetura | MLP 2 camadas (fully connected) |
| Entrada | 784 pixels (28x28, uint8, 0-255) |
| Neuronios ocultos | 128 |
| Neuronios de saida | 10 (digitos 0-9) |
| Ativacao oculta | tanh (aproximacao PWL, 4 segmentos) |
| Ativacao de saida | Nenhuma (argmax direto sobre scores brutos) |
| Representacao numerica | Ponto fixo Q4.12 (16 bits, complemento de dois) |
| Pesos da camada 1 (W_in) | 784 x 128 = 100.352 valores |
| Bias da camada 1 (b) | 128 valores |
| Pesos da camada 2 (beta) | 128 x 10 = 1.280 valores |
| Total de parametros | 101.760 valores x 16 bits = ~199 KB |
| Dataset | MNIST (digitos manuscritos, 60k treino / 10k teste) |
| Plataforma alvo | Intel Cyclone V SoC — DE1-SoC (5CSEMA5F31C6) |
| Ferramenta de sintese | Intel Quartus Prime |
| Latencia de memoria (BRAM) | 3 ciclos por acesso (`lsu_controller`) |
| Argmax | 20 ciclos (2 por posicao x 10 posicoes) |
