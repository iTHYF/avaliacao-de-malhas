# Ferramenta de Avaliação Multicritério de Controladores PID

**Iniciação Científica — CNPq**

**Laboratório:** LAUT — Universidade Federal do Rio Grande do Norte (UFRN)

**Área de pesquisa:** Controle

## 1. Sobre o projeto

Este projeto consiste no desenvolvimento de uma ferramenta computacional em Python para análise e comparação de controladores PID, utilizando indicadores de desempenho e técnicas de avaliação multicritério.

A ferramenta permite simular diferentes sintonias de controladores, calcular indicadores associados ao comportamento da malha e estabelecer uma classificação considerando tanto o desempenho quanto as restrições operacionais.

A proposta é oferecer uma avaliação que não dependa exclusivamente de uma única métrica, permitindo considerar diferentes objetivos de controle.

## 2. Estrutura do código

O projeto foi organizado em módulos com responsabilidades específicas:

| Diretório | Responsabilidade |
|---|---|
| `models/` | Modelagem das plantas e representação do atraso de transporte |
| `controllers/` | Construção e discretização dos controladores PID |
| `simulation/` | Simulação da malha fechada e organização dos ensaios |
| `tests/` | Geração dos sinais de referência |
| `metrics/` | Cálculo dos indicadores e definição dos pesos |
| `storage/` | Armazenamento e consulta das avaliações |
| `reports/` | Geração dos relatórios em PDF |
| `api/` | Interface de comunicação por meio do FastAPI |

O processamento segue a sequência:

**Configuração da planta → Simulação dos controladores → Cálculo dos indicadores → Verificação das restrições → Normalização → Cálculo do Score → Ranking.**

## 3. Modelagem e discretização

### 3.1 Modelos das plantas

O código considera plantas representadas por modelos de primeira e segunda ordem com atraso de transporte.

**Primeira ordem (FOPDT):**

\[
G(s)=\frac{Ke^{-Ts}}{\tau s+1}
\]

**Segunda ordem (SOPDT):**

\[
G(s)=\frac{Ke^{-Ts}}{\tau^2s^2+2\zeta\tau s+1}
\]

Em que \(K\) é o ganho estático, \(\tau\) é a constante de tempo, \(\zeta\) é o fator de amortecimento e \(T\) representa o atraso de transporte.

A discretização da dinâmica da planta é realizada pelo método Zero-Order Hold (ZOH), implementado em `simulation/closed_loop_simulator.py`:

```python
planta_disc_sem_atraso = ct.sample_system(
    self.planta_cont_sem_atraso,
    self.Ts,
    method='zoh'
)
```

O ZOH considera a entrada constante durante cada intervalo de amostragem, representando o comportamento de um sistema amostrado com retenção de ordem zero.

O atraso é representado separadamente em `models/delay_models.py` por meio de \(z^{-d}\), sendo \(d\) calculado como um número inteiro de períodos de amostragem.

### 3.2 Controlador PID

O controlador é construído no arquivo `controllers/pid.py`, utilizando as componentes proporcional, integral e derivativa com filtragem.

A discretização é realizada pelo método de Tustin:

```python
controlador_disc = ct.sample_system(
    controlador_cont,
    Ts,
    method='tustin'
)
```

Além do PID completo, o programa constrói um controlador PI para o caminho da referência.

Na simulação, essa separação permite aplicar a ação derivativa à variável medida, evitando o efeito conhecido como *derivative kick* em mudanças bruscas do setpoint.

## 4. Simulação da malha fechada

A classe `AvaliadorPID`, localizada em `simulation/closed_loop_simulator.py`, é responsável pela execução dos ensaios.

O cálculo da resposta utiliza os sistemas discretizados da planta e do controlador. Dois caminhos são considerados: um para a variável de processo (PV) e outro para o sinal de controle (MV).

Trecho responsável pela construção dessas relações:

```python
sys_feedback = ct.feedback(planta_ss, controlador_ss)
malha_y = PI_ss * sys_feedback

sys_feedback_u = ct.feedback(1, controlador_ss * planta_ss)
malha_u = PI_ss * sys_feedback_u
```

As respostas são obtidas com `ct.forced_response()`, utilizando os sinais de referência gerados para o ensaio.

O programa trabalha com variáveis de desvio e posteriormente recupera os valores absolutos da PV e da MV a partir dos pontos iniciais de operação.

### 4.1 Ensaios com variação de setpoint

O módulo `tests/setpoint_test.py` permite gerar degraus positivos, negativos ou sequências alternadas de referência.

Os ensaios são divididos em segmentos, permitindo calcular os indicadores individualmente para cada mudança de referência.

Na avaliação por tempo máximo, os segmentos identificados como incompletos são excluídos do cálculo médio das métricas, mantendo-se a verificação de overshoot de segurança.

## 5. Indicadores de desempenho

A ferramenta utiliza 11 indicadores, distribuídos em três módulos.

### Indicadores integrais

Implementados em `metrics/integral_indices.py`:

- **IAE:** integral do erro absoluto.
- **ISE:** integral do erro quadrático.
- **ITAE:** integral do erro absoluto ponderado pelo tempo.
- **ITSE:** integral do erro quadrático ponderado pelo tempo.

Um detalhe da implementação é a utilização do tempo relativo ao início de cada segmento:

```python
t_relativo = t - t[0]

iae = np.sum(np.abs(e)) * dt
ise = np.sum(e**2) * dt
itae = np.sum(t_relativo * np.abs(e)) * dt
itse = np.sum(t_relativo * (e**2)) * dt
```

Assim, a ponderação temporal dos indicadores ITAE e ITSE começa no instante da mudança de referência, e não no início da simulação completa.

### Indicadores temporais

Implementados em `metrics/temporal_indices.py`:

- Overshoot.
- Tempo de acomodação.
- Tempo de subida (10% a 90%).
- Erro em regime permanente.

O tempo de acomodação é avaliado a partir de uma banda de tolerância definida em relação ao valor final do setpoint.

### Indicadores de oscilação

Implementados em `metrics/oscillation_indices.py`:

- Variância da saída.
- Variância do sinal de controle.
- Quantidade de cruzamentos do setpoint.

Esses indicadores complementam a avaliação, considerando características da oscilação da resposta e do comportamento do sinal aplicado ao atuador.

## 6. Avaliação multicritério

A avaliação multicritério é implementada principalmente em `metrics/composite_indices.py` e nos módulos responsáveis pelo processamento e classificação dos resultados.

### 6.1 Definição dos pesos

A classe `DecisorDeMetricas` recebe as preferências informadas pelo usuário e utiliza uma matriz de ponderação para determinar a importância relativa dos 11 indicadores.

O cálculo é realizado por:

```python
pesos_brutos = np.dot(self.W, x)

pesos_normalizados = (
    pesos_brutos / np.sum(pesos_brutos)
)
```

A matriz `W` relaciona as alternativas do questionário aos indicadores, enquanto o vetor `x` representa as opções selecionadas.

A normalização garante:

\[
\sum_{i=1}^{11}w_i=1
\]

### 6.2 Normalização Min-Max

Como os indicadores possuem unidades e escalas diferentes, é necessário normalizá-los antes da agregação.

O método adotado é:

\[
m_{i,\mathrm{norm}}=
\frac{m_i-m_{i,\min}}{m_{i,\max}-m_{i,\min}}
\]

A normalização é realizada considerando os controladores aprovados pelas verificações operacionais.

Quando todos os candidatos aprovados possuem o mesmo valor para determinado indicador, a implementação atribui valor normalizado zero a esse indicador.

### 6.3 Cálculo do Score

O índice global de desempenho é calculado pela soma ponderada dos indicadores normalizados:

\[
\boxed{J=\sum_{i=1}^{11}w_i\,m_{i,\mathrm{norm}}}
\]

Trecho utilizado no processamento:

```python
score = 0.0

for metrica in decisor.nomes_indices:
    val = ind_bruto[metrica]
    vmin = limites_metricas[metrica]["min"]
    vmax = limites_metricas[metrica]["max"]

    norm = 0.0 if vmax == vmin else (
        (val - vmin) / (vmax - vmin)
    )

    score += norm * pesos[metrica]
```

O Score permite ordenar os controladores aprovados, sendo considerados melhores os menores valores de \(J\).

Essa classificação é relativa ao conjunto de candidatos avaliados e às preferências utilizadas na definição dos pesos.

## 7. Restrições operacionais

Antes da classificação multicritério, a ferramenta verifica o atendimento às restrições definidas para o ensaio.

Entre as verificações estão:

- Limite de overshoot.
- Limite de esforço de controle.
- Faixa operacional da variável de processo.
- Limites mínimo e máximo da variável manipulada.
- Condições de divergência numérica identificadas durante a simulação.

Os candidatos que não atendem às restrições são bloqueados e recebem um status correspondente ao critério violado.

A verificação de saturação utiliza os valores calculados para a MV; a saturação física não é inserida na dinâmica da malha simulada.

## 8. Armazenamento e apresentação dos resultados

A ferramenta disponibiliza diferentes formas de consulta dos resultados.

**Histórico em Excel:** o módulo `storage/` organiza os registros das avaliações, incluindo dados dos controladores, indicadores, pesos e classificação.

**Gráficos:** o Matplotlib é utilizado para visualizar as respostas da PV, o comportamento da MV e os Scores obtidos.

**Relatórios em PDF:** o módulo `reports/pdf_report.py` reúne os parâmetros do ensaio, resultados numéricos, pesos, indicadores e gráficos em um documento técnico.

**API REST:** o FastAPI disponibiliza endpoints para avaliação de controladores, consulta do histórico e exportação de resultados, incluindo relatórios PDF.

## 9. Perspectivas de desenvolvimento

O projeto permanece em desenvolvimento. Entre as possibilidades previstas para etapas futuras estão o aprimoramento dos indicadores, a análise de ruído, a integração com dados de malhas industriais e a investigação da aplicação de inteligência artificial à ferramenta.



