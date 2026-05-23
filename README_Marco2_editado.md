# Marco 2 — Driver Linux em Assembly ARM
## Classificador Embarcado de Digitos Numericos | DE1-SoC | ARM Cortex-A9
**TEC 499 - MI Sistemas Digitais · UEFS · 2026.1**

Integracao HPS com FPGA via MMIO para inferencia de rede neural ELM (Extreme Learning Machine) em hardware reconfiguravel. O driver e inteiramente implementado em Assembly ARMv7, sem bibliotecas externas, comunicando-se com o co-processador sintetizado no Cyclone V por meio de Memory-Mapped I/O sobre a Lightweight HPS-to-FPGA Bridge.

---

## Sumario

> Clique em um tópico no sumário para ir até ele. Depois, clique no título do bloco para abrir ou fechar o conteúdo.

| Tópico | O que você encontra |
|---|---|
| [Contexto do Projeto](#contexto-do-projeto) | Objetivo do Marco 2 e exigências da entrega. |
| [Requisitos Principais](#requisitos-principais) | Entrada, saída, driver Assembly e aplicação C. |
| [Configuracao do Hardware — Quartus e Platform Designer](#configuracao-do-hardware-quartus-e-platform-designer) | PIOs, bridge, offsets e mapa de registradores. |
| [Driver — Implementacao em Assembly](#driver-implementacao-em-assembly) | rotinas.s, instrucoes.s, handshake MMIO, ISA e erros. |
| [driver.h — Interface Publica da API](#driver-h-interface-publica-da-api) | Funções chamadas pelo main.c para controlar a FPGA. |
| [Aplicacao C — main.c](#aplicacao-c-main-c) | Fluxo do benchmark e cálculo das métricas. |
| [Build e Execucao](#build-e-execucao) | Makefile, compilação, execução e saída esperada. |
| [Co-processador ELM — Resumo](#co-processador-elm-resumo) | Fluxo da rede ELM e módulos principais em Verilog. |
| [Aritmetica em Ponto Fixo Q4.12](#aritmetica-em-ponto-fixo-q4-12) | Formato numérico usado nos pesos, bias e ativações. |
| [Testes e Validacao](#testes-e-validacao) | Critérios de teste, estabilidade e transações MMIO. |

---

<details id="contexto-do-projeto">
<summary><strong>Contexto do Projeto</strong></summary>


## Contexto do Projeto

Este repositorio corresponde ao **Marco 2** da disciplina MI Sistemas Digitais (TEC 499 — UEFS 2026.1). O objetivo e integrar o co-processador ELM sintetizado na FPGA (Marco 1) ao HPS (ARM Cortex-A9) rodando Linux, por meio de um driver escrito inteiramente em Assembly ARM, expondo uma API C limpa para a aplicacao de benchmark.

O problema academico proposto exige:

- Implementar um driver Linux (userspace via `/dev/mem`) em Assembly ARM para controlar o co-processador via MMIO
- Expor uma API C com inicializacao, envio de parametros, disparo de inferencia e leitura de resultado
- Demonstrar estabilidade: 1.000 inferencias da mesma imagem sem falhas
- Medir latencia media, throughput e acuracia

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="requisitos-principais">
<summary><strong>Requisitos Principais</strong></summary>


## Requisitos Principais

### Entrada e Saida

A entrada e uma imagem em escala de cinza com **28×28 pixels, 8 bits por pixel** (valores 0 a 255), totalizando 784 bytes. Cada imagem representa um unico digito (0 a 9) do dataset MNIST.

A saida e um inteiro `pred` no intervalo [0, 9], representado nos bits `[3:0]` do registrador `PIO_DATA_OUT`, lido pelo HPS apos a sinalizacao de `DONE`.

| Sinal | Bits em `PIO_DATA_OUT` | Descricao |
|---|---|---|
| `predicted_digit` | [3:0] | Digito classificado pela rede |
| `fl_processor_done` | [4] | Inferencia concluida (`DONE`) |
| `fl_processor_busy` | [5] | Co-processador ocupado (`BUSY`) |
| `fl_error` | [6] | Instrucao invalida ou endereco fora do limite (`ERROR`) |

---

### Driver Assembly ARM

O driver e implementado em dois arquivos Assembly ARMv7 (`rotinas.s` e `instrucoes.s`) e uma interface de cabecalho C (`driver.h`). Nao ha dependencia de bibliotecas externas alem da libc padrao. Toda comunicacao com o hardware ocorre por acesso direto a memoria fisica via `/dev/mem`, respeitando a ABI ARM EABI em todas as funcoes exportadas.

---

### Aplicacao C

O `main.c` e responsavel pelo benchmark de 1.000 inferencias, medicao de metricas e impressao dos resultados. Nao acessa o hardware diretamente — toda comunicacao passa pelas funcoes do driver.

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="configuracao-do-hardware-quartus-e-platform-designer">
<summary><strong>Configuracao do Hardware — Quartus e Platform Designer</strong></summary>


## Configuracao do Hardware — Quartus e Platform Designer

Antes de qualquer linha de Assembly, e necessario preparar o hardware na FPGA. As etapas abaixo descrevem o processo completo de integracao HPS com FPGA no Quartus Prime.

| Etapa | Descricao |
|---|---|
| 1. Instanciar os PIOs | Adicionar 3 componentes PIO de 32 bits no Platform Designer: `PIO_DATA_IN` (escrita do HPS), `PIO_DATA_OUT` (leitura do HPS), `PIO_CTRL` (controle) |
| 2. Enderecar na Bridge | Mapear os PIOs na Lightweight HPS-to-FPGA Bridge: base `0xFF200000`, `DATA_IN → +0x00`, `DATA_OUT → +0x10`, `CTRL → +0x20` |
| 3. Gerar o sistema | Gerar o `.qsys` e incluir o IP no top-level `ghrd_top.v`, conectando os sinais PIO as portas do modulo ELM |
| 4. Modificar `ghrd_top.v` | Adicionar as instancias do `elm_accel` e dos PIOs; conectar `clk`, `reset`, `pio_ctrl`, `pio_data_in`, `pio_data_out` |
| 5. Compilar e gravar | Full Compilation no Quartus Prime, gerar o `.sof` e gravar na FPGA via JTAG. Verificar sinais com o SignalTap |
| 6. Documentar o mapa | Registrar o mapa final de bits dos registradores PIO |

### Mapa de Registradores PIO

**`PIO_CTRL` (escrita, offset `+0x20`):**

| Bit | Nome | Funcao |
|---|---|---|
| 0 | `CTRL_ENABLE` | Sinaliza nova instrucao disponivel em `PIO_DATA_IN` |
| 1 | `CTRL_CLEAR` | Zera flags de status na FPGA (`fl_done`, `fl_error`) |
| 2 | `CTRL_RESET` | Reinicia a logica interna do co-processador |

**`PIO_DATA_OUT` (leitura, offset `+0x10`):**

| Bits | Nome | Funcao |
|---|---|---|
| [3:0] | `RESULT` | Digito predito (0–9) |
| [4] | `STATUS_DONE` | Inferencia concluida |
| [5] | `STATUS_BUSY` | Co-processador ocupado |
| [6] | `STATUS_ERROR` | Erro interno |

**`PIO_DATA_IN` (escrita, offset `+0x00`):**

Palavra de instrucao de 32 bits. O formato dos campos varia por opcode — detalhado na secao [Conjunto de Instrucoes](#conjunto-de-instrucoes-isa).

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="driver-implementacao-em-assembly">
<summary><strong>Driver — Implementacao em Assembly</strong></summary>


## Driver — Implementacao em Assembly

### rotinas.s — Ciclo de Vida da Conexao

Gerencia a abertura, mapeamento e fechamento da conexao com o hardware. Exporta duas variaveis globais compartilhadas com `instrucoes.s`:

| Variavel global | Valor inicial | Descricao |
|---|---|---|
| `fd_devmem` | `-1` | File descriptor de `/dev/mem` |
| `base_virtual` | `0` | Ponteiro virtual para a Lightweight Bridge apos `mmap` |

**Constantes de configuracao:**

| Constante | Valor | Descricao |
|---|---|---|
| `BRIDGE_ENDERECO_FISICO` | `0xFF200000` | Endereco fisico da Lightweight HPS-to-FPGA Bridge |
| `BRIDGE_TAMANHO` | `0x00005000` | Janela de mapeamento: 20 KB |
| `FLAG_RDWR` | `2` | `O_RDWR` |
| `FLAG_SYNC` | `0x101000` | `O_SYNC`: escritas chegam ao hardware imediatamente |
| `MMAP_PROT_RDWR` | `3` | `PROT_READ | PROT_WRITE` |
| `MMAP_COMPARTILHADO` | `1` | `MAP_SHARED`: alteracoes refletem diretamente no hardware |

**`inicializar_fpga()`**

```
1. open("/dev/mem", O_RDWR | O_SYNC)       -> fd
   Se fd < 0: retorna NULL

2. mmap(NULL, 0x5000, PROT_RW, MAP_SHARED, fd, 0xFF200000)
   Argumentos 5 e 6 vao na pilha (ABI ARM EABI)
   Se retorno == -1: close(fd) e retorna NULL

3. Salva fd em fd_devmem
   Salva ponteiro em base_virtual

4. Retorna ponteiro base virtual
```

**`reset_clean_fpga()`**

```
Pulso RESET:
  PIO_CTRL <- BIT_RESET  |  loop 1000 iteracoes  |  PIO_CTRL <- 0  |  loop 1000

Pulso CLEAR:
  PIO_CTRL <- BIT_CLEAR  |  loop 1000 iteracoes  |  PIO_CTRL <- 0  |  loop 1000
```

Garante estado inicial limpo antes do envio de qualquer dado. Sem retorno (`void`).

**`finalizar_fpga()`**

```
1. Le fd_devmem; se == -1, pula para zeragem
2. munmap(base_virtual, 0x5000)
3. close(fd_devmem)
4. fd_devmem   <- -1
5. base_virtual <- 0
```

Zera ambas as variaveis globais para evitar uso acidental apos o encerramento.

---

### instrucoes.s — Protocolo MMIO

Implementa o protocolo de handshake e as funcoes de envio. Toda comunicacao passa pela funcao interna `enviar_instrucao`, que nao e exportada.

**Funcao interna `enviar_instrucao`:**

```
Entrada:  R0 = palavra de instrucao de 32 bits
Retorno:  R0 = 0 (sucesso) | -3 (erro FPGA) | -99 (timeout)

Passo 1  STR R0, [R6, #PIO_DATA_IN]         escreve instrucao
Passo 2  STR #CTRL_ENABLE, [R6, #PIO_CTRL]  ativa ENABLE
Passo 3  Polling BUSY sobe  (timeout 200.000 iteracoes)
Passo 4  STR #0, [R6, #PIO_CTRL]            desativa ENABLE (FPGA confirmou leitura)
Passo 5  Polling BUSY desce (timeout 200.000 iteracoes)  checa STATUS_ERROR
Passo 6  STATUS_ERROR ativo -> retorna -3
         BUSY = 0           -> retorna 0
```

**Constantes de status e timeout:**

| Constante | Valor | Descricao |
|---|---|---|
| `STATUS_DONE` | `0x10` | Bit 4 de `PIO_DATA_OUT` |
| `STATUS_BUSY` | `0x20` | Bit 5 de `PIO_DATA_OUT` |
| `STATUS_ERROR` | `0x40` | Bit 6 de `PIO_DATA_OUT` |
| `RESULT_MASK` | `0x0F` | Mascara bits [3:0] para extrair o digito |
| `TIMEOUT_INSTR` | `200.000` | Iteracoes maximas por handshake de instrucao |
| `TIMEOUT_START` | `2.000.000` | Iteracoes maximas aguardando `DONE` apos `START` |

**Funcoes publicas de envio:**

| Funcao | Volume | Formato da instrucao / Comportamento |
|---|---|---|
| `enviar_bias()` | 128 valores | `[25:10]` valor Q4.12 · `[9:3]` indice · `[2:0]` op=3 |
| `enviar_beta()` | 1.280 valores | `[29:14]` valor Q4.12 · `[13:3]` indice · `[2:0]` op=4 |
| `enviar_pesos()` | 100.352 pesos | 2 instrucoes por peso: `OP_STORE_WEIGHT_ADDR` + `OP_STORE_WEIGHT_VALUE` |
| `enviar_imagem()` | 784 pixels | `[20:13]` pixel (0–255) · `[12:3]` indice · `[2:0]` op=0 |
| `inferencia()` | 1 disparo | Pulso `CLEAR` -> `OP_START` -> polling `STATUS_DONE` (timeout 2M) |
| `ler_resultado()` | 1 leitura | `LDR PIO_DATA_OUT` -> `AND #RESULT_MASK` -> retorna bits [3:0] |

**Conversao de endianness nos pesos:**

Os arquivos de pesos sao armazenados em big-endian. Antes de montar a instrucao, cada valor e convertido para little-endian via:

```asm
REV   Rn, Rn        @ inverte bytes (big -> little endian)
ASR   Rn, Rn, #16   @ alinha o valor de 16 bits
UXTH  Rn, Rn        @ zera bits superiores, mantem 16 bits
```

---

### Conjunto de Instrucoes (ISA)

Todas as instrucoes tem 32 bits. Os 3 bits menos significativos definem o opcode. Os campos de endereco e dado sao empacotados nos bits restantes da mesma palavra.

| Opcode [2:0] | Mnemonica | Campos da palavra de 32 bits | Limite |
|---|---|---|---|
| `000` | `STORE_IMG` | `[20:13]` pixel (8b) · `[12:3]` addr (10b) | addr <= 783 |
| `001` | `STORE_WEIGHTS_ADDR` | `[19:3]` addr (17b) | addr <= 100.351 |
| `010` | `STORE_WEIGHTS_VALUE` | `[18:3]` valor Q4.12 (16b) | usa addr do par anterior |
| `011` | `STORE_BIAS` | `[25:10]` valor Q4.12 (16b) · `[9:3]` addr (7b) | addr <= 127 |
| `100` | `STORE_BETA` | `[29:14]` valor Q4.12 (16b) · `[13:3]` addr (11b) | addr <= 1.279 |
| `101` | `START` | — | dispara inferencia |
| `110` | `STATUS` | — | retorna ao `ST_IDLE` |
| `111` | `NOP` | — | sem operacao |

Regras do ISA:

- `STORE_WEIGHTS_ADDR` e `STORE_WEIGHTS_VALUE` sao sempre emitidas em par. O endereco e retido em registrador interno do co-processador e reutilizado pela instrucao de valor seguinte.
- Qualquer endereco acima do limite seta `fl_error` no ciclo de decode.
- `STATUS` e `NOP` retornam ao `ST_IDLE` sem modificar memorias.

---

### Codigos de Erro

| Codigo | Funcao | Causa |
|---|---|---|
| `0` | qualquer | Sucesso |
| `-2` | `inferencia()` | Timeout aguardando `STATUS_DONE` (2.000.000 iteracoes) |
| `-3` | qualquer | Bit `STATUS_ERROR` ativo na FPGA |
| `-99` | `enviar_instrucao` | Timeout de handshake: `BUSY` nao subiu ou nao desceu (200.000 iteracoes) |

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="driver-h-interface-publica-da-api">
<summary><strong>driver.h — Interface Publica da API</strong></summary>


## driver.h — Interface Publica da API

```c
/* Ciclo de vida (rotinas.s) */
void *inicializar_fpga(void);   // Abre /dev/mem, mapeia bridge. Retorna ponteiro ou NULL.
void  finalizar_fpga(void);     // Desfaz mmap, fecha /dev/mem, zera globais.
void  reset_clean_fpga(void);   // Pulsa RESET e CLEAR com delay de 1000 ciclos cada.

/* Comunicacao MMIO (instrucoes.s) */
int enviar_bias(void);          // 128 valores Q4.12 via OP_STORE_BIAS.
int enviar_beta(void);          // 1280 valores Q4.12 via OP_STORE_BETA.
int enviar_pesos(void);         // 100352 pesos: WEIGHT_ADDR + WEIGHT_VALUE (par).
int enviar_imagem(void);        // 784 pixels via OP_STORE_IMAGE.
int inferencia(void);           // CLEAR + START + polling DONE.
int ler_resultado(void);        // Retorna bits [3:0] de PIO_DATA_OUT (0-9).
```

Todas as funcoes `enviar_*` e `inferencia` retornam `0` em sucesso ou codigo negativo em erro.

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="aplicacao-c-main-c">
<summary><strong>Aplicacao C — main.c</strong></summary>


## Aplicacao C — main.c

### Fluxo de Execucao

```
inicializar_fpga()
  open("/dev/mem", O_RDWR|O_SYNC)
  mmap(0xFF200000, 0x5000, MAP_SHARED) -> base_virtual

reset_clean_fpga()
  RESET + CLEAR

enviar_bias()    <- parametros fixos, carregados uma unica vez
enviar_beta()
enviar_pesos()

inicio_total = clock_gettime()

for i = 0 .. 999:
    inicio_latencia = clock_gettime()
    enviar_imagem()          <- troca a cada iteracao
    inferencia()             <- disparo + polling DONE
    ler_resultado()          <- bits [3:0] de PIO_DATA_OUT
    fim_latencia = clock_gettime()
    soma_latencia_ms += diferenca(inicio, fim)

fim_total = clock_gettime()

calcular_metricas()
imprimir_resultados()

finalizar_fpga()
  munmap + close
  fd_devmem = -1, base_virtual = 0
```

Se `enviar_imagem()` ou `inferencia()` retornar valor negativo, incrementa `falhas` e encerra o loop com `break`.

Os parametros da rede (bias, beta, pesos) sao enviados uma unica vez antes do loop, pois sao constantes. Apenas a imagem e reenviada a cada iteracao.

### Metricas de Desempenho

Medicao feita com `clock_gettime(CLOCK_MONOTONIC)` — escolhido em substituicao ao `MRC p15` (registrador de ciclos `PMCCNTR`), que nao esta disponivel no kernel padrao Intel/Altera do DE1-SoC.

| Metrica | Formula | Descricao |
|---|---|---|
| Throughput | `validas / (tempo_total_ms / 1000)` | Inferencias por segundo |
| Latencia media | `soma_latencia_ms / validas` | Tempo medio por inferencia em ms |
| Tempo total | `fim_total - inicio_total` | Duracao completa do benchmark em ms |
| Acuracia | `(acertos / validas) * 100` | Percentual de inferencias com resultado valido |

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="build-e-execucao">
<summary><strong>Build e Execucao</strong></summary>


## Build e Execucao

**Makefile:**

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

`main.c` e os dois arquivos Assembly sao compilados e linkados diretamente pelo `gcc`. A flag `-lrt` e obrigatoria para `clock_gettime`. A execucao requer `sudo` pelo acesso a `/dev/mem`.

**Saida esperada:**

```
---------- Resultados ----------
Digito identificado : 4
Repeticoes          : 1000
Execucoes validas   : 1000
Falhas              : 0
Porcentagem acertos : 100.0%
Throughput          : XX.XX inf/s
Latencia media      : X.XXX ms
Tempo total         : XXXX.XXX ms
```

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="co-processador-elm-resumo">
<summary><strong>Co-processador ELM — Resumo</strong></summary>


## Co-processador ELM — Resumo

O co-processador implementado na FPGA executa as quatro etapas da inferencia ELM:

```
x (784 pixels)
    |
    v
h = tanh(W_in . x + b)     <- camada oculta, 128 neuronios, tanh aproximada por PWL
    |
    v
y = beta . h                <- camada de saida, 10 neuronios, sem ativacao
    |
    v
pred = argmax(y)            <- indice 0..9 do maior score
```

**Topologia:**

| Etapa | Modulo Verilog | Descricao |
|---|---|---|
| Camada oculta | `first_layer.v` + `mac_first_layer.v` | 784x128 MACs + bias + tanh PWL |
| Buffer intermediario | `reg_bank128.v` | 128 registradores Q4.12 |
| Camada de saida | `second_layer.v` + `mac_second_layer.v` | 128x10 MACs + beta |
| Buffer final | `reg_bank10.v` | 10 registradores Q4.12 |
| Classificador | `argmax_iterativo.v` | Indice do maior entre 10 scores |
| Controle global | `CoProcessor.v` + `neural_unit.v` | FSMs de controle e inferencia |
| Memorias | `lsu_controller.v` (x4) | BRAMs Cyclone V M10K via `altsyncram` |
| Ativacao | `tanh_pwl_q4_12.v` | 4 segmentos lineares, logica combinacional pura |
| Display | `display_resultado.v` | Decodificador 4b para display HEX7 (7 segmentos) |

Para documentacao detalhada do hardware (FSMs, MACs, LSUs, ISA de hardware), consulte o README do Marco 1 neste repositorio.

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="aritmetica-em-ponto-fixo-q4-12">
<summary><strong>Aritmetica em Ponto Fixo Q4.12</strong></summary>


## Aritmetica em Ponto Fixo Q4.12

Todos os pesos, bias, ativacoes e scores usam o formato **Q4.12**: 16 bits com sinal em complemento de dois, com 4 bits de parte inteira (incluindo sinal) e 12 bits de parte fracionaria.

| Propriedade | Valor |
|---|---|
| Bits totais | 16 |
| Parte inteira | 4 bits (inclui sinal) |
| Parte fracionaria | 12 bits |
| Valor maximo | +7.9997... (32767 / 4096) |
| Valor minimo | -8.0 (-32768 / 4096) |
| Resolucao | ~0.000244 (1 / 4096) |

**Multiplicacao Q4.12 x Q4.12:**

```
A * B  ->  produto Q8.24 de 32 bits
produto >>> 12  ->  realinha para Q4.12
acumulador 32 bits (Q20.12)  ->  satura para 16 bits na saida
```

**Conversao de pixel uint8 para Q4.12:**

```
pixel [7:0]  ->  {3'b000, pixel[7:0], 4'b0000}  =  pixel * 16
```

Desloca 4 bits a esquerda para alinhar a virgula fracionaria com os pesos antes da multiplicacao.

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="testes-e-validacao">
<summary><strong>Testes e Validacao</strong></summary>


## Testes e Validacao

O teste minimo exigido pelo enunciado — classificar uma imagem conhecida repetidas vezes sem falhas — e atendido pelo loop de 1.000 inferencias do `main.c`. A estabilidade e confirmada pela metrica `Falhas = 0` na saida.

**Criterios de validacao:**

| Criterio | Resultado esperado |
|---|---|
| 1.000 inferencias consecutivas | 0 falhas |
| Retorno de `enviar_*` e `inferencia` | sempre 0 (sucesso) |
| Bits `STATUS_ERROR` em `PIO_DATA_OUT` | nunca ativos durante o benchmark |
| Digito predito | consistente entre todas as iteracoes para a mesma imagem |
| Timeout de handshake | nunca acionado (`-99` nao ocorre) |

**Resumo dos volumes de comunicacao por inferencia:**

| Operacao | Instrucoes MMIO | Observacao |
|---|---|---|
| `enviar_bias` | 128 | Uma vez antes do loop |
| `enviar_beta` | 1.280 | Uma vez antes do loop |
| `enviar_pesos` | 200.704 | 2 instrucoes x 100.352 pesos; uma vez antes do loop |
| `enviar_imagem` | 784 | A cada iteracao |
| `inferencia` | 1 | A cada iteracao (+ polling ate DONE) |
| **Total por benchmark** | **~203.897 transacoes** | Maioria na carga inicial dos pesos |

---


[Voltar ao sumário](#sumario)

</details>

---
