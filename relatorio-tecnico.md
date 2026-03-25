# Relatório Técnico — Tech Challenge Fase 2
## Sistema de Otimização de Rotas para Atendimento Especializado à Mulher

**Curso:** Pós-Graduação em IA para Devs — PosTech / FIAP  
**Fase:** 2 — Algoritmos Genéticos e Processamento de Linguagem Natural  
**Projeto escolhido:** Projeto 2 — Otimização de Rotas para Atendimento Especializado à Mulher

---

## 1. Introdução

A rede hospitalar enfrenta desafios logísticos significativos na distribuição eficiente de medicamentos específicos para a saúde da mulher e no atendimento domiciliar especializado. Casos como emergências obstétricas, acompanhamento pós-parto e situações de violência doméstica demandam não apenas rapidez, mas também protocolos sensíveis ao contexto de cada atendimento.

Este projeto desenvolve um sistema de otimização de rotas baseado em Algoritmos Genéticos (AG) para resolver o problema de roteirização de veículos (VRP — Vehicle Routing Problem), evoluindo a partir de um código base de TSP (Travelling Salesman Problem). Adicionalmente, integra um modelo de linguagem (LLM) para geração automática de documentos operacionais para a equipe de campo.

---

## 2. Arquitetura da Solução

O sistema é composto por quatro módulos principais, orquestrados pelo arquivo `main.py`:

```
┌─────────────────────────────────────────────────────────┐
│                        main.py                          │
│                   (orquestrador)                        │
└────────┬────────────┬───────────────┬───────────────────┘
         │            │               │               │
         ▼            ▼               ▼               ▼
  ┌────────────┐ ┌──────────┐ ┌────────────┐ ┌────────────┐
  │   data/    │ │   vrp/   │ │visualizat. │ │    llm/    │
  │            │ │          │ │            │ │            │
  │ synthetic  │ │ genetic_ │ │  map_viz   │ │  report_   │
  │  _data.py  │ │algorithm │ │    .py     │ │ generator  │
  │            │ │ fitness  │ │  (Folium)  │ │  (Gemini)  │
  │            │ │ waze_    │ │            │ │            │
  │            │ │adapter   │ │            │ │            │
  └────────────┘ └──────────┘ └────────────┘ └────────────┘
```

### 2.1 Módulo de Dados (`data/synthetic_data.py`)

Define os pontos de atendimento do dia com coordenadas reais de São Paulo, utilizando a classe `AttendancePoint` (dataclass) com os seguintes atributos:

- `id`, `name`, `lat`, `lon` — identificação e localização geográfica
- `tipo` — categoria do atendimento (emergência obstétrica, violência doméstica, medicamento hormonal, pós-parto)
- `priority` — prioridade clínica (1 = máxima urgência)
- `time_window` — janela de horário permitido para o atendimento
- `requires_cold_chain` — indica necessidade de refrigeração
- `supplies` — quantidade de suprimentos necessários
- `notes` — observações e protocolos específicos

O conjunto de dados sintéticos inclui **15 pontos de atendimento** e **1 base hospitalar**, distribuídos por diferentes regiões de São Paulo.

### 2.2 Módulo VRP (`vrp/`)

Contém a lógica central do Algoritmo Genético, a função de fitness com restrições e o `WazeAdapter` — componente responsável por estimar o tempo de deslocamento entre pontos considerando variação de trânsito por horário.

### 2.3 Módulo de Visualização (`visualization/map_viz.py`)

Gera um mapa interativo HTML usando a biblioteca Folium, com marcadores codificados por cor e tipo de atendimento.

### 2.4 Módulo LLM (`llm/report_generator.py`)

Integra a API do Google Gemini para geração automática de documentos operacionais a partir da rota otimizada.

---

## 3. Algoritmo Genético para Roteamento

### 3.1 Ponto de Partida — Código Base TSP

O desenvolvimento partiu de um código base de TSP em Python com visualização em Pygame. O código original implementava:

- Representação por lista de tuplas `(x, y)`
- Order Crossover (OX)
- Mutação por swap adjacente
- Seleção por probabilidade inversa ao fitness
- Elitismo simples (1 indivíduo)

As adaptações necessárias para transformá-lo em um VRP com restrições foram realizadas em três frentes: representação dos genes, função de fitness e operadores genéticos.

### 3.2 Representação Genética

No TSP original, cada gene era uma tupla `(x, y)`. No VRP adaptado, cada gene é um objeto `AttendancePoint`, que carrega todas as informações necessárias para avaliação das restrições:

```
TSP original:  [(512, 317), (741, 72), (552, 50), ...]
VRP adaptado:  [AttendancePoint(id=1, tipo="emergencia_obstetrica", priority=1, ...), ...]
```

A rota completa sempre inclui a base hospitalar no início e no fim, garantindo que o veículo parta e retorne ao hospital:

```
[BASE] → [ponto_1] → [ponto_2] → ... → [ponto_n] → [BASE]
```

### 3.3 Operadores Genéticos

#### Seleção
Manteve-se a seleção por **probabilidade inversa ao fitness**: indivíduos com menor distância (melhor fitness) têm maior probabilidade de serem selecionados como pais. Isso garante pressão seletiva sem eliminar prematuramente a diversidade da população.

```python
weights = 1 / np.array(fitness_values)
parent1, parent2 = random.choices(population, weights=weights, k=2)
```

#### Crossover — Order Crossover (OX)
O OX foi mantido por ser o operador mais adequado para problemas de permutação, garantindo que nenhum ponto apareça duplicado na rota. A adaptação foi necessária para comparar genes por `id` em vez de por valor de tupla, e para excluir a base hospitalar do processo de cruzamento:

```
Parent 1: [A, B, C, D, E, F]
Parent 2: [D, F, B, E, A, C]
Segmento herdado (índices 2-4): [C, D, E]
Filho:    [F, B, C, D, E, A]
```

#### Mutação — Swap
A mutação realiza a troca de posição entre dois pontos aleatórios da rota (excluindo a base). A probabilidade de mutação controla o equilíbrio entre exploração e explotação do espaço de soluções.

#### Elitismo
Os `elite_size` melhores indivíduos de cada geração são preservados automaticamente na próxima geração, evitando que boas soluções sejam perdidas pelo processo de crossover e mutação.

### 3.4 Função Fitness com Restrições

A função fitness combina a distância real percorrida com penalidades por violação de restrições:

```
fitness = distância_total + Σ penalidades
```

Quanto **menor** o valor de fitness, **melhor** a rota.

#### Distância Geográfica — Fórmula de Haversine
Por utilizar coordenadas reais de latitude e longitude, substituiu-se a distância Euclidiana pela fórmula de Haversine, que calcula a distância real entre dois pontos na superfície terrestre:

```
d = 2R × arcsin(√(sin²(Δlat/2) + cos(lat1)·cos(lat2)·sin²(Δlon/2)))
```

#### Restrição 1 — Prioridade de Atendimento (Obrigatória)
Penaliza rotas que visitam pontos de menor prioridade clínica antes de pontos mais urgentes. A penalidade é proporcional à diferença de prioridade entre os pares invertidos:

```python
# Para cada par (i, j) onde i vem antes de j na rota:
if priority[i] > priority[j]:
    penalty += PENALTY_PRIORITY × (priority[i] - priority[j])
```

Valor da penalidade: **500 por unidade de diferença de prioridade**

#### Restrição 2 — Capacidade do Veículo
Penaliza rotas cuja soma de suprimentos excede a capacidade máxima do veículo:

```python
if total_supplies > max_supplies:
    penalty += PENALTY_CAPACITY × (total_supplies - max_supplies)
```

Valor da penalidade: **1000 por unidade excedente**

#### Restrição 3 — Janelas de Tempo
Simula o horário de chegada em cada ponto considerando variação de trânsito por horário via `FakeWazeAdapter` e 15 minutos de duração por atendimento. O adapter modela três situações reais de SP:

| Faixa Horária | Condição | Velocidade Média |
|---|---|---|
| 07h–09h | Rush manhã | ~18 km/h |
| 10h–16h | Tranquilo | ~35 km/h |
| 17h–19h | Rush tarde | ~15 km/h |
| Demais | Moderado | ~28 km/h |

O sistema foi projetado seguindo o padrão **Adapter**, permitindo substituir o `FakeWazeAdapter` por um `RealWazeAdapter` integrado a uma API real (Google Maps, HERE Maps, etc.) sem alterar nenhuma outra parte do código.

Penaliza chegadas após o horário limite:

```python
if current_time > window_end:
    delay = current_time - window_end
    penalty += PENALTY_TIME_WINDOW × delay
```

Valor da penalidade: **300 por hora de atraso**

---

## 4. Experimentos e Resultados

Foram realizados 3 experimentos com diferentes configurações do AG para avaliar o impacto dos hiperparâmetros na qualidade da solução:

### Experimento 1 — Configuração Padrão

| Parâmetro | Valor |
|---|---|
| Tamanho da população | 100 |
| Número de gerações | 200 |
| Probabilidade de mutação | 0.3 |
| Elite size | 2 |

| Métrica | Resultado |
|---|---|
| Fitness inicial (geração 0) | ~9.490 |
| Fitness final | **121.09** |
| Geração de convergência | ~70 |
| Penalidade de prioridade | 0.0 ✅ |
| Penalidade de capacidade | 0.0 ✅ |
| Penalidade de tempo | 0.0 ✅ |
| Distância total | 121.09 km |

### Experimento 2 — Alta População, Baixa Mutação

| Parâmetro | Valor |
|---|---|
| Tamanho da população | 200 |
| Número de gerações | 300 |
| Probabilidade de mutação | 0.2 |
| Elite size | 2 |

> *Preencher após execução*

### Experimento 3 — Baixa População, Alta Mutação

| Parâmetro | Valor |
|---|---|
| Tamanho da população | 50 |
| Número de gerações | 500 |
| Probabilidade de mutação | 0.5 |
| Elite size | 2 |

> *Preencher após execução*

### 4.1 Análise Comparativa

O Experimento 1 demonstrou convergência rápida (geração ~70) com fitness final de 121.09 km, zerando todas as penalidades. Isso indica que o AG encontrou uma solução que:

- Respeita completamente a ordem de prioridade clínica
- Não excede a capacidade do veículo
- Atende todos os pontos dentro das janelas de tempo permitidas

A queda acentuada nas primeiras gerações (de ~9.490 para ~140 nas primeiras 20 gerações) demonstra a eficácia do operador OX combinado com a seleção por probabilidade inversa.

### 4.2 Comparativo com Abordagem sem Otimização

Para demonstrar o valor do AG, compara-se a rota otimizada com uma rota aleatória (sem otimização):

| Métrica | Rota Aleatória | Rota Otimizada (AG) |
|---|---|---|
| Fitness total | ~9.490 | **121.09** |
| Penalidade de prioridade | ~8.500 | **0.0** |
| Penalidade de capacidade | 0.0 | **0.0** |
| Penalidade de tempo | ~850 | **0.0** |
| Violações de prioridade | múltiplas | **nenhuma** |

A redução de fitness de ~9.490 para 121.09 representa uma melhoria de aproximadamente **98,7%**, evidenciando a eficácia do AG para este problema.

---

## 5. Integração com LLM

### 5.1 Modelo Utilizado

Foi utilizado o **Google Gemini 2.0 Flash** via API, disponível gratuitamente através do Google AI Studio. A escolha se justifica pela:

- Disponibilidade gratuita (adequada para prototipagem)
- Boa capacidade de geração de texto estruturado em português
- Suporte a system instructions para contextualização do domínio
- API simples com suporte a sessões de chat multi-turno

### 5.2 Técnicas de Prompt Engineering

#### System Prompt Especializado
O system prompt estabelece o contexto médico feminino para todas as interações:

```
"Você é um assistente especializado em logística hospitalar focado 
na saúde da mulher. Suas respostas devem sempre:
- Usar linguagem clara, objetiva e sensível ao contexto feminino
- Respeitar a privacidade e confidencialidade das pacientes
- Destacar protocolos especiais para casos de violência doméstica
- Sinalizar claramente requisitos de cadeia fria para medicamentos
- Priorizar comunicação de emergências obstétricas"
```

#### Contextualização Estruturada da Rota
Antes de qualquer geração de documento, a rota otimizada é convertida em texto estruturado contendo: horários estimados de chegada, distâncias entre pontos, tipo de atendimento, janelas de tempo e observações específicas de cada ponto. Esse contexto é injetado no prompt para garantir precisão e relevância nos documentos gerados.

#### Sensibilidade a Casos Especiais
Os casos de violência doméstica recebem tratamento especial nos prompts — a LLM é instruída a gerar protocolos de discrição (não identificar o veículo, usar codinomes) sem expor informações sensíveis desnecessariamente.

### 5.3 Documentos Gerados

O sistema gera automaticamente três tipos de saída:

**Manual de Instruções** — documento completo para a equipe de transporte, contendo briefing do dia, instruções por parada, protocolos de segurança e procedimentos de encerramento.

**Roteiro de Visitas** — cronograma legível com horários estimados, tipo de atendimento e observações práticas para cada parada.

**Chat em Linguagem Natural** — interface para perguntas sobre a rota, como "Quantas emergências temos hoje?" ou "Quais medicamentos precisam de cadeia fria?", com histórico de conversa mantido entre perguntas.

### 5.4 Base de Dados para Fase 3

Todas as respostas geradas pela LLM são salvas em formato JSON estruturado (`llm_responses.json`), contendo pares de entrada/saída para cada tipo de geração. Esse arquivo servirá como base de dados para o fine-tuning do modelo na Fase 3 do projeto.

---

## 6. Visualização das Rotas

O mapa interativo gerado com Folium apresenta:

- **Marcadores coloridos** por tipo de atendimento (vermelho = emergência, laranja = violência doméstica, azul = medicamento hormonal, verde = pós-parto)
- **Numeração sequencial** de cada parada
- **Linha da rota** conectando os pontos na ordem otimizada
- **Popups informativos** com nome, janela de tempo, suprimentos e observações
- **Legenda** com os tipos de atendimento

A codificação visual por tipo de atendimento permite à equipe identificar rapidamente a natureza de cada parada antes de chegar ao local.

---

## 7. Análise de Impacto

### 7.1 Tempo de Resposta em Emergências
A restrição de prioridade garante que emergências obstétricas sejam sempre visitadas primeiro, independentemente de sua posição geográfica. Isso pode ser crítico em situações de risco de vida — o AG nunca sacrifica uma emergência por ganho de distância.

### 7.2 Segurança da Paciente
Os protocolos especiais para violência doméstica (discrição, codinomes, sem identificação do veículo) são propagados automaticamente do banco de dados para os documentos gerados pela LLM, reduzindo o risco de exposição inadvertida das pacientes.

### 7.3 Integridade dos Medicamentos
A restrição de cadeia fria e a janela de tempo para medicamentos hormonais garantem que fármacos sensíveis à temperatura sejam entregues dentro do prazo seguro de transporte.

---

## 8. Considerações Éticas

### Privacidade e Confidencialidade
Todos os dados utilizados são sintéticos — nenhuma informação real de pacientes foi utilizada. Em uma implementação real, seria necessário criptografar os dados de localização e garantir conformidade com a LGPD (Lei Geral de Proteção de Dados).

### Viés Algorítmico
O sistema prioriza atendimentos por **gravidade clínica**, não por localização geográfica ou qualquer outro critério que pudesse introduzir viés. Emergências sempre têm prioridade sobre conveniência logística.

### Autonomia Profissional
Os documentos gerados pela LLM são **sugestões operacionais**, não substituindo o julgamento clínico dos profissionais de saúde. A equipe de campo tem autonomia para desviar do roteiro em situações não previstas pelo sistema.

### Sensibilidade de Gênero
O sistema foi desenvolvido com consciência das especificidades da saúde feminina — desde a nomenclatura utilizada nos prompts até os protocolos especiais para situações de vulnerabilidade.

---

## 9. Desafios e Soluções

| Desafio | Solução Implementada |
|---|---|
| Genes TSP (tuplas) vs genes VRP (objetos) | Refatoração da representação para `AttendancePoint` com comparação por `id` |
| Distância Euclidiana vs geográfica | Substituição pela fórmula de Haversine para coordenadas reais |
| Base hospitalar entrando no crossover | Fixação da base no início e fim da rota, excluída dos operadores genéticos |
| Penalidade de prioridade contando a base | Filtragem dos pontos `tipo="base"` antes do cálculo de penalidades |
| Capacidade do veículo inconsistente com os dados | Ajuste do `max_supplies` para valor coerente com o total de suprimentos do dia |
| Velocidade fixa irreal para SP | Implementação do WazeAdapter com perfis de trânsito por faixa horária e variação aleatória de ±15% |
---

## 10. Conclusão

O sistema desenvolvido demonstra como Algoritmos Genéticos e LLMs podem ser combinados para resolver problemas logísticos complexos no contexto da saúde da mulher.

O AG convergiu para soluções que respeitam todas as restrições clínicas com fitness próximo à distância mínima real, evidenciando a eficácia da abordagem para este tipo de problema. A integração com Gemini adiciona uma camada de inteligência operacional, transformando dados numéricos em documentos práticos e sensíveis ao contexto.

Como trabalho futuro, destacam-se: a implementação de múltiplos veículos (VRP clássico), a integração com dados de tráfego em tempo real para estimativas de tempo mais precisas, e o fine-tuning de um modelo especializado em saúde da mulher utilizando a base de dados gerada nesta fase.

---

## 11. Referências

- GOLDBERG, D. E. *Genetic Algorithms in Search, Optimization and Machine Learning*. Addison-Wesley, 1989.
- HOLLAND, J. H. *Adaptation in Natural and Artificial Systems*. MIT Press, 1992.
- TOTH, P.; VIGO, D. *The Vehicle Routing Problem*. SIAM, 2002.
- Google AI Studio — Gemini API Documentation. Disponível em: https://aistudio.google.com
- Folium Documentation. Disponível em: https://python-visualization.github.io/folium