# Marco 2 — Driver Linux em Assembly ARM
## Classificador Embarcado de Dígitos Numéricos | DE1-SoC | ARM Cortex-A9
**TEC 499 - MI Sistemas Digitais · UEFS · 2026.1**

Integração HPS com FPGA via MMIO para inferência de rede neural ELM (Extreme Learning Machine) em hardware reconfigurável. O driver é inteiramente implementado em Assembly ARMv7, sem bibliotecas externas, comunicando-se com o co-processador sintetizado no Cyclone V por meio de Memory-Mapped I/O sobre a Lightweight HPS-to-FPGA Bridge.

---

## Sumário

> Clique em um tópico no sumário para ir até ele. Depois, clique no título do bloco para abrir ou fechar o conteúdo.

| Tópico | O que você encontra |
|---|---|
| [Contexto do Projeto](#contexto-do-projeto) | Objetivo do Marco 2 e exigências da entrega. |
| [Requisitos Principais](#requisitos-principais) | Entrada, saída, driver Assembly e aplicação C. |
| [Configuração do Hardware — Quartus e Platform Designer](#configuração-do-hardware-quartus-e-platform-designer) | PIOs, bridge, offsets e mapa de registradores. |
| [Driver — Implementação em Assembly](#driver-implementacao-em-assembly) | rotinas.s, instrucoes.s, handshake MMIO, ISA e erros. |
| [driver.h — Interface Pública da API](#driver-h-interface-publica-da-api) | Funções chamadas pelo main.c para controlar a FPGA. |
| [Aplicação C — main.c](#aplicação-c-main-c) | Fluxo do benchmark e cálculo das métricas. |
| [Build e Execução](#build-e-execução) | Makefile, compilação, execução e saída esperada. |
| [Co-processador ELM — Resumo](#co-processador-elm-resumo) | Fluxo da rede ELM e módulos principais em Verilog. |
| [Aritmética em Ponto Fixo Q4.12](#aritmetica-em-ponto-fixo-q4-12) | Formato numérico usado nos pesos, bias e ativações. |
| [Testes e Validação](#testes-e-validacao) | Critérios de teste, estabilidade e transações MMIO. |

---

<details id="contexto-do-projeto">
<summary><strong>Contexto do Projeto</strong></summary>


## Contexto do Projeto

Este repositório corresponde ao **Marco 2** da disciplina MI Sistemas Digitais (TEC 499 — UEFS 2026.1). O objetivo é integrar o co-processador ELM sintetizado na FPGA (Marco 1) ao HPS (ARM Cortex-A9) rodando Linux, por meio de um driver escrito inteiramente em Assembly ARM, expondo uma API C limpa para a aplicação de benchmark.

O problema acadêmico proposto exige:

- Implementar um driver Linux (userspace via `/dev/mem`) em Assembly ARM para controlar o co-processador via MMIO
- Expor uma API C com inicialização, envio de parâmetros, disparo de inferência e leitura de resultado
- Demonstrar estabilidade: 1.000 inferências da mesma imagem sem falhas
- Medir latência média, throughput e acurácia

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="requisitos-principais">
<summary><strong>Requisitos Principais</strong></summary>


## Requisitos Principais

### Entrada e Saída

A entrada é uma imagem em escala de cinza com **28×28 pixels, 8 bits por pixel** (valores 0 a 255), totalizando 784 bytes. Cada imagem representa um único digito (0 a 9) do dataset MNIST.

A saída é um inteiro `pred` no intervalo [0, 9], representado nos bits `[3:0]` do registrador `PIO_DATA_OUT`, lido pelo HPS após a sinalizacao de `DONE`.

| Sinal | Bits em `PIO_DATA_OUT` | Descrição |
|---|---|---|
| `predicted_digit` | [3:0] | Dígito classificado pela rede |
| `fl_processor_done` | [4] | Inferencia concluída (`DONE`) |
| `fl_processor_busy` | [5] | Co-processador ocupado (`BUSY`) |
| `fl_error` | [6] | Instrução inválida ou endereço fora do limite (`ERROR`) |

---

### Driver Assembly ARM

O driver e implementado em dois arquivos Assembly ARMv7 (`rotinas.s` e `instrucoes.s`) é uma interface de cabeçalho C (`driver.h`). Não há dependência de bibliotecas externas além da libc padrão. Toda comunicação com o hardware ocorre por acesso direto a memória física via `/dev/mem`, respeitando a ABI ARM EABI em todas as funções exportadas.

---

### Aplicação C

O `main.c` e responsável pelo benchmark de 1.000 inferências, medição de metricas e impressão dos resultados. Não acessa o hardware diretamente — toda comunicação passa pelas funções do driver.

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="configuracao-do-hardware-quartus-e-platform-designer">
<summary><strong>Configuração do Hardware — Quartus e Platform Designer</strong></summary>


## Configuração do Hardware — Quartus e Platform Designer

Antes de qualquer linha de Assembly, e necessário preparar o hardware na FPGA. As etapas abaixo descrevem o processo completo de integração HPS com FPGA no Quartus Prime.

| Etapa | Descrição |
|---|---|
| 1. Instanciar os PIOs | Adicionar 3 componentes PIO de 32 bits no Platform Designer: `PIO_DATA_IN` (escrita do HPS), `PIO_DATA_OUT` (leitura do HPS), `PIO_CTRL` (controle) |
| 2. Endereçar na Bridge | Mapear os PIOs na Lightweight HPS-to-FPGA Bridge: base `0xFF200000`, `DATA_IN → +0x00`, `DATA_OUT → +0x10`, `CTRL → +0x20` |
| 3. Gerar o sistema | Gerar o `.qsys` e incluir o IP no top-level `ghrd_top.v`, conectando os sinais PIO às portas do módulo ELM |
| 4. Modificar `ghrd_top.v` | Adicionar as instâncias do `elm_accel` e dos PIOs; conectar `clk`, `reset`, `pio_ctrl`, `pio_data_in`, `pio_data_out` |
| 5. Compilar e gravar | Full Compilation no Quartus Prime, gerar o `.sof` e gravar na FPGA via JTAG. Verificar sinais com o SignalTap |
| 6. Documentar o mapa | Registrar o mapa final de bits dos registradores PIO |

### Mapa de Registradores PIO

**`PIO_CTRL` (escrita, offset `+0x20`):**

| Bit | Nome | Função |
|---|---|---|
| 0 | `CTRL_ENABLE` | Sinaliza nova instrução disponível em `PIO_DATA_IN` |
| 1 | `CTRL_CLEAR` | Zera flags de status na FPGA (`fl_done`, `fl_error`) |
| 2 | `CTRL_RESET` | Reinicia a lógica interna do co-processador |

**`PIO_DATA_OUT` (leitura, offset `+0x10`):**

| Bits | Nome | Função |
|---|---|---|
| [3:0] | `RESULT` | Dígito predito (0–9) |
| [4] | `STATUS_DONE` | Inferencia concluída |
| [5] | `STATUS_BUSY` | Co-processador ocupado |
| [6] | `STATUS_ERROR` | Erro interno |

**`PIO_DATA_IN` (escrita, offset `+0x00`):**

Palavra de instrução de 32 bits. O formato dos campos varia por opcode — detalhado na seção [Conjunto de Instruções](#conjunto-de-instrucoes-isa).

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="driver-implementacao-em-assembly">
<summary><strong>Driver — Implementação em Assembly</strong></summary>


## Driver — Implementação em Assembly

### rotinas.s — Ciclo de Vida da Conexão

Gerencia a abertura, mapeamento e fechamento da conexão com o hardware. Exporta duas variáveis globais compartilhadas com `instrucoes.s`:

| Variável global | Valor inicial | Descrição |
|---|---|---|
| `fd_devmem` | `-1` | File descriptor de `/dev/mem` |
| `base_virtual` | `0` | Ponteiro virtual para a Lightweight Bridge após `mmap` |

**Constantes de configuração:**

| Constante | Valor | Descrição |
|---|---|---|
| `BRIDGE_ENDERECO_FISICO` | `0xFF200000` | Endereço físico da Lightweight HPS-to-FPGA Bridge |
| `BRIDGE_TAMANHO` | `0x00005000` | Janela de mapeamento: 20 KB |
| `FLAG_RDWR` | `2` | `O_RDWR` |
| `FLAG_SYNC` | `0x101000` | `O_SYNC`: escritas chegam ao hardware imédiatamente |
| `MMAP_PROT_RDWR` | `3` | `PROT_READ | PROT_WRITE` |
| `MMAP_COMPARTILHADO` | `1` | `MAP_SHARED`: alterações refletem diretamente no hardware |

**`inicializar_fpga()`**

```
1. open("/dev/mem", O_RDWR | O_SYNC)       -> fd
   Se fd < 0: retorna NULL

2. mmap(NULL, 0x5000, PROT_RW, MAP_SHARED, fd, 0xFF200000)
   Argumentos 5 e 6 vão na pilha (ABI ARM EABI)
   Se retorno == -1: close(fd) e retorna NULL

3. Salva fd em fd_devmem
   Salva ponteiro em base_virtual

4. Retorna ponteiro base virtual
```

**`reset_clean_fpga()`**

```
Pulso RESET:
  PIO_CTRL <- BIT_RESET  |  loop 1000 iterações  |  PIO_CTRL <- 0  |  loop 1000

Pulso CLEAR:
  PIO_CTRL <- BIT_CLEAR  |  loop 1000 iterações  |  PIO_CTRL <- 0  |  loop 1000
```

Garante estado inicial limpo antes do envio de qualquer dado. Sem retorno (`void`).

**`finalizar_fpga()`**

```
1. Lê fd_devmem; se == -1, pula para zeragem
2. munmap(base_virtual, 0x5000)
3. close(fd_devmem)
4. fd_devmem   <- -1
5. base_virtual <- 0
```

Zera ambas as variáveis globais para evitar uso acidental após o encerramento.

---

### instrucoes.s — Protocolo MMIO

Implementa o protocolo de handshake e as funções de envio. Toda comunicação passa pela funcao interna `enviar_instrucao`, que não e exportada.

**Função interna `enviar_instrucao`:**

```
Entrada:  R0 = palavra de instrução de 32 bits
Retorno:  R0 = 0 (sucesso) | -3 (erro FPGA) | -99 (timeout)

Passo 1  STR R0, [R6, #PIO_DATA_IN]         escreve instrução
Passo 2  STR #CTRL_ENABLE, [R6, #PIO_CTRL]  ativa ENABLE
Passo 3  Polling BUSY sobe  (timeout 200.000 iterações)
Passo 4  STR #0, [R6, #PIO_CTRL]            desativa ENABLE (FPGA confirmou leitura)
Passo 5  Polling BUSY desce (timeout 200.000 iterações)  checa STATUS_ERROR
Passo 6  STATUS_ERROR ativo -> retorna -3
         BUSY = 0           -> retorna 0
```

**Constantes de status e timeout:**

| Constante | Valor | Descrição |
|---|---|---|
| `STATUS_DONE` | `0x10` | Bit 4 de `PIO_DATA_OUT` |
| `STATUS_BUSY` | `0x20` | Bit 5 de `PIO_DATA_OUT` |
| `STATUS_ERROR` | `0x40` | Bit 6 de `PIO_DATA_OUT` |
| `RESULT_MASK` | `0x0F` | Máscara bits [3:0] para extrair o digito |
| `TIMEOUT_INSTR` | `200.000` | Iteracoes máximas por handshake de instrução |
| `TIMEOUT_START` | `2.000.000` | Iteracoes máximas aguardando `DONE` após `START` |

**Funções públicas de envio:**

| Função | Volume | Formato da instrução / Comportamento |
|---|---|---|
| `enviar_bias()` | 128 valores | `[25:10]` valor Q4.12 · `[9:3]` índice · `[2:0]` op=3 |
| `enviar_beta()` | 1.280 valores | `[29:14]` valor Q4.12 · `[13:3]` índice · `[2:0]` op=4 |
| `enviar_pesos()` | 100.352 pesos | 2 instrucoes por peso: `OP_STORE_WEIGHT_ADDR` + `OP_STORE_WEIGHT_VALUE` |
| `enviar_imagem()` | 784 pixels | `[20:13]` pixel (0–255) · `[12:3]` índice · `[2:0]` op=0 |
| `inferência()` | 1 disparo | Pulso `CLEAR` -> `OP_START` -> polling `STATUS_DONE` (timeout 2M) |
| `ler_resultado()` | 1 leitura | `LDR PIO_DATA_OUT` -> `AND #RESULT_MASK` -> retorna bits [3:0] |

**Conversão de endianness nos pesos:**

Os arquivos de pesos são armazenados em big-endian. Antes de montar a instrução, cada valor é convertido para little-endian via:

```asm
REV   Rn, Rn        @ inverte bytes (big -> little endian)
ASR   Rn, Rn, #16   @ alinha o valor de 16 bits
UXTH  Rn, Rn        @ zera bits superiores, mantém 16 bits
```

---

### Conjunto de Instruções (ISA)

Todas as instruções têm 32 bits. Os 3 bits menos significativos definem o opcode. Os campos de endereço e dado são empacotados nos bits restantes da mesma palavra.

| Opcode [2:0] | Mnemônica | Campos da palavra de 32 bits | Limite |
|---|---|---|---|
| `000` | `STORE_IMG` | `[20:13]` pixel (8b) · `[12:3]` addr (10b) | addr <= 783 |
| `001` | `STORE_WEIGHTS_ADDR` | `[19:3]` addr (17b) | addr <= 100.351 |
| `010` | `STORE_WEIGHTS_VALUE` | `[18:3]` valor Q4.12 (16b) | usa addr do par anterior |
| `011` | `STORE_BIAS` | `[25:10]` valor Q4.12 (16b) · `[9:3]` addr (7b) | addr <= 127 |
| `100` | `STORE_BETA` | `[29:14]` valor Q4.12 (16b) · `[13:3]` addr (11b) | addr <= 1.279 |
| `101` | `START` | — | dispara inferência |
| `110` | `STATUS` | — | retorna ao `ST_IDLE` |
| `111` | `NOP` | — | sem operacao |

Regras da ISA:

- `STORE_WEIGHTS_ADDR` e `STORE_WEIGHTS_VALUE` são sempre emitidas em par. O endereço e retido em registrador interno do co-processador é reutilizado pela instrução de valor seguinte.
- Qualquer endereço acima do limite seta `fl_error` no ciclo de decode.
- `STATUS` e `NOP` retornam ao `ST_IDLE` sem modificar memórias.

---

### Códigos de Erro

| Código | Função | Causa |
|---|---|---|
| `0` | qualquer | Sucesso |
| `-2` | `inferência()` | Timeout aguardando `STATUS_DONE` (2.000.000 iterações) |
| `-3` | qualquer | Bit `STATUS_ERROR` ativo na FPGA |
| `-99` | `enviar_instrucao` | Timeout de handshake: `BUSY` não subiu ou não desceu (200.000 iterações) |

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="driver-h-interface-publica-da-api">
<summary><strong>driver.h — Interface Pública da API</strong></summary>


## driver.h — Interface Pública da API

```c
/* Ciclo de vida (rotinas.s) */
void *inicializar_fpga(void);   // Abre /dev/mem, mapeia bridge. Retorna ponteiro ou NULL.
void  finalizar_fpga(void);     // Desfaz mmap, fecha /dev/mem, zera globais.
void  reset_clean_fpga(void);   // Pulsa RESET e CLEAR com delay de 1000 ciclos cada.

/* Comunicação MMIO (instrucoes.s) */
int enviar_bias(void);          // 128 valores Q4.12 via OP_STORE_BIAS.
int enviar_beta(void);          // 1280 valores Q4.12 via OP_STORE_BETA.
int enviar_pesos(void);         // 100352 pesos: WEIGHT_ADDR + WEIGHT_VALUE (par).
int enviar_imagem(void);        // 784 pixels via OP_STORE_IMAGE.
int inferência(void);           // CLEAR + START + polling DONE.
int ler_resultado(void);        // Retorna bits [3:0] de PIO_DATA_OUT (0-9).
```

Todas as funções `enviar_*` e `inferência` retornam `0` em sucesso ou código negativo em erro.

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="aplicacao-c-main-c">
<summary><strong>Aplicação C — main.c</strong></summary>


## Aplicação C — main.c

### Fluxo de Execução

```
inicializar_fpga()
  open("/dev/mem", O_RDWR|O_SYNC)
  mmap(0xFF200000, 0x5000, MAP_SHARED) -> base_virtual

reset_clean_fpga()
  RESET + CLEAR

enviar_bias()    <- parâmetros fixos, carregados uma única vez
enviar_beta()
enviar_pesos()

inicio_total = clock_gettime()

for i = 0 .. 999:
    inicio_latência = clock_gettime()
    enviar_imagem()          <- troca a cada iteracao
    inferência()             <- disparo + polling DONE
    ler_resultado()          <- bits [3:0] de PIO_DATA_OUT
    fim_latência = clock_gettime()
    soma_latência_ms += diferenca(inicio, fim)

fim_total = clock_gettime()

calcular_metricas()
imprimir_resultados()

finalizar_fpga()
  munmap + close
  fd_devmem = -1, base_virtual = 0
```

Se `enviar_imagem()` ou `inferência()` retornar valor negativo, incrementa `falhas` e encerra o loop com `break`.

Os parâmetros da rede (bias, beta, pesos) são enviados uma única vez antes do loop, pois são constantes. Apenas a imagem é reenviada a cada iteracao.

### Métricas de Desempenho

Medicao feita com `clock_gettime(CLOCK_MONOTONIC)` — escolhido em substituição ao `MRC p15` (registrador de ciclos `PMCCNTR`), que não está disponível no kernel padrão Intel/Altera do DE1-SoC.

| Metrica | Fórmula | Descrição |
|---|---|---|
| Throughput | `validas / (tempo_total_ms / 1000)` | Inferências por segundo |
| Latencia média | `soma_latência_ms / validas` | Tempo medio por inferência em ms |
| Tempo total | `fim_total - inicio_total` | Duração completa do benchmark em ms |
| Acuracia | `(acertos / validas) * 100` | Percentual de inferências com resultado valido |

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="build-e-execucao">
<summary><strong>Build e Execução</strong></summary>


## Build e Execução

**Makefile:**

```makefile
CC     = gcc
TARGET = inferência
SRC    = main.c rotinas.s instrucoes.s

all:
    $(CC) -o $(TARGET) $(SRC) -lrt

run: all
    sudo ./$(TARGET)

clean:
    rm -f $(TARGET) *.o
```

`main.c` e os dois arquivos Assembly são compilados e linkados diretamente pelo `gcc`. A flag `-lrt` e obrigatória para `clock_gettime`. A execução requer `sudo` pelo acesso a `/dev/mem`.

**Saída esperada:**

```
---------- Resultados ----------
Dígito identificado : 4
Repetições          : 1000
Execuções validas   : 1000
Falhas              : 0
Porcentagem acertos : 100.0%
Throughput          : XX.XX inf/s
Latencia média      : X.XXX ms
Tempo total         : XXXX.XXX ms
```

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="co-processador-elm-resumo">
<summary><strong>Co-processador ELM — Resumo</strong></summary>


## Co-processador ELM — Resumo

O co-processador implementado na FPGA executa as quatro etapas da inferência ELM:

```
x (784 pixels)
    |
    v
h = tanh(W_in . x + b)     <- camada oculta, 128 neurônios, tanh aproximada por PWL
    |
    v
y = beta . h                <- camada de saída, 10 neurônios, sem ativação
    |
    v
pred = argmax(y)            <- índice 0..9 do maior score
```

**Topologia:**

| Etapa | Módulo Verilog | Descrição |
|---|---|---|
| Camada oculta | `first_layer.v` + `mac_first_layer.v` | 784x128 MACs + bias + tanh PWL |
| Buffer intermediário | `reg_bank128.v` | 128 registradores Q4.12 |
| Camada de saída | `second_layer.v` + `mac_second_layer.v` | 128x10 MACs + beta |
| Buffer final | `reg_bank10.v` | 10 registradores Q4.12 |
| Classificador | `argmax_iterativo.v` | Índice do maior entre 10 scores |
| Controle global | `CoProcessor.v` + `neural_unit.v` | FSMs de controle e inferência |
| Memorias | `lsu_controller.v` (x4) | BRAMs Cyclone V M10K via `altsyncram` |
| Ativacao | `tanh_pwl_q4_12.v` | 4 segmentos lineares, lógica combinacional pura |
| Display | `display_resultado.v` | Decodificador 4b para display HEX7 (7 segmentos) |

Para documentação detalhada do hardware (FSMs, MACs, LSUs, ISA de hardware), consulte o README do Marco 1 neste repositório.

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="aritmetica-em-ponto-fixo-q4-12">
<summary><strong>Aritmética em Ponto Fixo Q4.12</strong></summary>


## Aritmética em Ponto Fixo Q4.12

Todos os pesos, bias, ativacoes e scores usam o formato **Q4.12**: 16 bits com sinal em complemento de dois, com 4 bits de parte inteira (incluindo sinal) e 12 bits de parte fracionária.

| Propriedade | Valor |
|---|---|
| Bits totais | 16 |
| Parte inteira | 4 bits (inclui sinal) |
| Parte fracionária | 12 bits |
| Valor máximo | +7.9997... (32767 / 4096) |
| Valor mínimo | -8.0 (-32768 / 4096) |
| Resolução | ~0.000244 (1 / 4096) |

**Multiplicação Q4.12 x Q4.12:**

```
A * B  ->  produto Q8.24 de 32 bits
produto >>> 12  ->  realinha para Q4.12
acumulador 32 bits (Q20.12)  ->  satura para 16 bits na saída
```

**Conversão de pixel uint8 para Q4.12:**

```
pixel [7:0]  ->  {3'b000, pixel[7:0], 4'b0000}  =  pixel * 16
```

Desloca 4 bits a esquerda para alinhar a vírgula fracionária com os pesos antes da multiplicacao.

---


[Voltar ao sumário](#sumario)

</details>

---

<details id="testes-e-validacao">
<summary><strong>Testes e Validação</strong></summary>


## Testes e Validação

O teste mínimo exigido pelo enunciado — classificar uma imagem conhecida repetidas vezes sem falhas — é atendido pelo loop de 1.000 inferências do `main.c`. A estabilidade é confirmada pela metrica `Falhas = 0` na saída.

**Critérios de validacao:**

| Criterio | Resultado esperado |
|---|---|
| 1.000 inferências consecutivas | 0 falhas |
| Retorno de `enviar_*` e `inferência` | sempre 0 (sucesso) |
| Bits `STATUS_ERROR` em `PIO_DATA_OUT` | nunca ativos durante o benchmark |
| Dígito predito | consistente entre todas as iterações para a mesma imagem |
| Timeout de handshake | nunca acionado (`-99` não ocorre) |

**Resumo dos volumes de comunicação por inferência:**

| Operação | Instruções MMIO | Observação |
|---|---|---|
| `enviar_bias` | 128 | Uma vez antes do loop |
| `enviar_beta` | 1.280 | Uma vez antes do loop |
| `enviar_pesos` | 200.704 | 2 instrucoes x 100.352 pesos; uma vez antes do loop |
| `enviar_imagem` | 784 | A cada iteracao |
| `inferência` | 1 | A cada iteracao (+ polling até DONE) |
| **Total por benchmark** | **~203.897 transacoes** | Maioria na carga inicial dos pesos |

---


[Voltar ao sumário](#sumario)

</details>

---
