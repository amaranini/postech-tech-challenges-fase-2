# 🏥 VRP — Sistema de Roteirização em Saúde da Mulher

Sistema de otimização de rotas para distribuição de medicamentos e atendimento domiciliar especializado à mulher, desenvolvido como parte do **Tech Challenge — Fase 2** da pós-graduação em IA para Devs (FIAP/PosTech).

---

## 📋 Sobre o Projeto

A rede hospitalar enfrenta desafios logísticos na distribuição eficiente de medicamentos específicos para a saúde da mulher e no atendimento domiciliar especializado — incluindo casos de violência doméstica, acompanhamento pós-parto e emergências obstétricas.

Este projeto resolve esse problema com duas tecnologias principais:

- **Algoritmo Genético** — otimiza a ordem de visitas respeitando prioridades clínicas, capacidade do veículo e janelas de tempo
- **LLM (Google Gemini)** — transforma a rota otimizada em documentos práticos para a equipe de campo

---

## 🗂️ Estrutura do Projeto

```
projeto-vrp/
│
├── data/
│   ├── __init__.py
│   └── synthetic_data.py       # Pontos de atendimento sintéticos (SP)
│
├── vrp/
│   ├── __init__.py
│   ├── constraints.py         # Restrições do problema
│   ├── fitness.py              # Função fitness com penalidades
│   └── genetic_algorithm.py    # Algoritmo Genético (OX crossover + swap mutation)
│   └── waze_adapter.py         # Adapter para estimativa de tempo com trânsito
│
├── visualization/
│   ├── __init__.py
│   └── map_viz.py              # Mapa interativo com Folium
│
├── llm/
│   ├── __init__.py
│   └── report_generator.py    # Integração com Google Gemini
│
├── main.py                    # Pipeline completo
├── pyproject.toml             # Metadados, versão do Python e dependências
├── .python-version            # Versão sugerida para pyenv
└── README.md
```

---

## 🚀 Como Executar

### 1. Clone o repositório

```bash
git clone https://github.com/amaranini/postech-tech-challenges-fase-2.git
cd postech-tech-challenges-fase-2
```

### 2. Use Python 3.11

O projeto foi configurado para aceitar apenas versões compatíveis com Python 3.11:

```toml
requires-python = ">=3.11,<3.12"
```

Se você usa `pyenv`, pode ativar uma versão local com:

```bash
pyenv local 3.11
```

### 3. Crie e ative o ambiente virtual

```bash
python3.11 -m venv .venv

# Mac/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate
```

### 4. Instale o projeto e as dependências

```bash
pip install -e .
```

As dependências e a versão mínima de Python estão definidas em [pyproject.toml](pyproject.toml).

### 5. Configure a API key do Gemini

Obtenha sua chave gratuita em [aistudio.google.com](https://aistudio.google.com)

```bash
# Mac/Linux:
export GEMINI_API_KEY="sua-chave-aqui"

# Windows:
set GEMINI_API_KEY="sua-chave-aqui"
```

### 6. Execute o pipeline completo

```bash
python main.py
```

Se quiser testar partes isoladas do projeto, você também pode executar:

```bash
python vrp/genetic_algorithm.py
python visualization/map_viz.py
```

---

## 📦 Arquivos Gerados

| Arquivo | Descrição |
|---|---|
| `route_map.html` | Mapa interativo com a rota otimizada |
| `manual_equipe.txt` | Manual de instruções para a equipe de campo |
| `roteiro_visitas.txt` | Roteiro cronológico detalhado |
| `llm_responses.json` | Respostas da LLM salvas para fine-tuning (Fase 3) |

---

## 🧬 Algoritmo Genético

### Representação
Cada indivíduo é uma lista ordenada de pontos de atendimento (cromossomo), onde cada gene é um `AttendancePoint`. A rota sempre começa e termina na base hospitalar.

### Operadores
| Operador | Implementação |
|---|---|
| Seleção | Probabilidade inversa ao fitness |
| Crossover | Order Crossover (OX) |
| Mutação | Swap de dois pontos aleatórios |
| Elitismo | Preserva os N melhores por geração |

### Função Fitness
```
fitness = distância_total + penalidades

penalidades:
  + PENALTY_PRIORITY    × inversões de prioridade
  + PENALTY_CAPACITY    × excesso de suprimentos
  + PENALTY_TIME_WINDOW × horas de atraso nas janelas
```

### Restrições Implementadas
- ✅ **Prioridade de atendimento** (obrigatória) — emergências obstétricas primeiro
- ✅ **Capacidade do veículo** — limite de suprimentos transportados
- ✅ **Janelas de tempo** — horários permitidos por tipo de atendimento, com tempo de deslocamento estimado via `WazeAdapter` (simula variação de trânsito por horário)

---

## 🤖 Integração com LLM

O Google Gemini (`gemini-2.5-flash`) é utilizado para gerar automaticamente:

- **Manual de instruções** — briefing do dia, protocolos por tipo de atendimento, procedimentos de segurança
- **Roteiro de visitas** — cronograma legível com horários estimados e observações
- **Chat em linguagem natural** — respostas a perguntas sobre a rota em tempo real

### Técnicas de Prompt Engineering
- System prompt especializado em saúde da mulher
- Contexto estruturado da rota injetado no prompt
- Protocolos sensíveis para casos de violência doméstica
- Linguagem adequada para equipes de campo

---

## 🗺️ Tipos de Atendimento

| Tipo | Prioridade | Cor no Mapa |
|---|---|---|
| Emergência Obstétrica | 1 (máxima) | 🔴 Vermelho |
| Violência Doméstica | 2 | 🟠 Laranja |
| Medicamento Hormonal | 3 | 🔵 Azul |
| Pós-Parto | 4 | 🟢 Verde |
| Base Hospitalar | — | ⚫ Preto |

---

## ⚖️ Considerações Éticas

- **Privacidade**: nomes e localizações são dados sintéticos, sem exposição de dados reais de pacientes
- **Protocolos sensíveis**: casos de violência doméstica têm instruções especiais de discrição
- **Equidade**: o sistema prioriza atendimentos por gravidade clínica, não por localização geográfica
- **Confidencialidade**: a LLM é instruída a não expor dados desnecessários nos documentos gerados

---

## 🧪 Experimentos Realizados

| Experimento | População | Gerações | Mutação | Fitness Final |
|---|---|---|---|---|
| 1 | 100 | 200 | 0.3 | 121.09 |
| 2 | 200 | 300 | 0.2 | 121.09 |
| 3 | 50  | 500 | 0.5 | 122.67 |

---

## 📚 Dependências

As dependências são gerenciadas em [pyproject.toml](pyproject.toml).

```
numpy>=1.26,<3
folium>=0.16,<1
google-generativeai>=0.8,<1
```

> O tempo de deslocamento é estimado via `FakeWazeAdapter`, que simula variação
> de trânsito por horário (rush manhã/tarde). Para usar uma API real de roteamento,
> troque por `RealWazeAdapter` em `fitness.py` e configure `ROUTING_API_KEY`.
---

## 👩‍💻 Autora

Desenvolvido como entrega do Tech Challenge Fase 2 — PosTech IA para Devs.