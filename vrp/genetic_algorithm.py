"""
genetic_algorithm.py
Algoritmo Genético adaptado para o VRP especializado em saúde da mulher.

Mantém a mesma estrutura do TSP original, adaptando:
  - Genes: AttendancePoint (em vez de tuplas x,y)
  - Fitness: distância + penalidades (importado de fitness.py)
  - Rota completa: base → atendimentos → base
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import copy
from typing import List, Tuple
import numpy as np

from data.synthetic_data import ATTENDANCE_POINTS, AttendancePoint, BASE
from vrp.fitness import calculate_fitness, fitness_breakdown


# ──────────────────────────────────────────────
# Geração da população inicial
# ──────────────────────────────────────────────
def generate_random_population(
    attendance_points: List[AttendancePoint],
    population_size: int
) -> List[List[AttendancePoint]]:
    """
    Gera uma população inicial de rotas aleatórias.
    Cada rota começa e termina na base.

    Parameters:
    - attendance_points: lista de pontos de atendimento (sem a base)
    - population_size: número de indivíduos na população

    Returns:
    - Lista de rotas, onde cada rota é [BASE, ...pontos..., BASE]
    """
    population = []
    for _ in range(population_size):
        shuffled = random.sample(attendance_points, len(attendance_points))
        route = [BASE] + shuffled + [BASE]
        population.append(route)
    return population


# ──────────────────────────────────────────────
# Order Crossover (OX) — adaptado para AttendancePoint
# Mantém a lógica do código original, agora comparando por id
# ──────────────────────────────────────────────
def order_crossover(
    parent1: List[AttendancePoint],
    parent2: List[AttendancePoint]
) -> List[AttendancePoint]:
    """
    Realiza o Order Crossover (OX) entre dois pais.
    Opera apenas nos pontos de atendimento (ignora base no início e fim).

    Returns:
    - Nova rota com [BASE, ...filho..., BASE]
    """
    # Extrai apenas os pontos de atendimento (sem base)
    p1 = [p for p in parent1 if p.tipo != "base"]
    p2 = [p for p in parent2 if p.tipo != "base"]

    length = len(p1)
    start = random.randint(0, length - 1)
    end   = random.randint(start + 1, length)

    # Segmento herdado do parent1
    child_segment = p1[start:end]
    child_ids     = {p.id for p in child_segment}

    # Posições restantes preenchidas com a ordem do parent2
    remaining = [p for p in p2 if p.id not in child_ids]

    child = []
    ri = 0  # índice em remaining
    for i in range(length):
        if start <= i < end:
            child.append(child_segment[i - start])
        else:
            child.append(remaining[ri])
            ri += 1

    return [BASE] + child + [BASE]


# ──────────────────────────────────────────────
# Mutação por swap — igual ao original
# ──────────────────────────────────────────────
def mutate(
    route: List[AttendancePoint],
    mutation_probability: float
) -> List[AttendancePoint]:
    """
    Mutação por swap: troca dois pontos de atendimento de posição.
    Não altera a base (primeiro e último elemento).

    Parameters:
    - route: rota completa [BASE, ...pontos..., BASE]
    - mutation_probability: probabilidade de ocorrer mutação

    Returns:
    - Rota mutada
    """
    mutated = copy.deepcopy(route)

    if random.random() < mutation_probability:
        # Índices válidos: apenas os pontos de atendimento (1 até len-2)
        attendance_indices = list(range(1, len(mutated) - 1))

        if len(attendance_indices) < 2:
            return mutated

        i, j = random.sample(attendance_indices, 2)
        mutated[i], mutated[j] = mutated[j], mutated[i]

    return mutated


# ──────────────────────────────────────────────
# Ordenação da população por fitness
# ──────────────────────────────────────────────
def sort_population(
    population: List[List[AttendancePoint]],
    fitness_values: List[float]
) -> Tuple[List[List[AttendancePoint]], List[float]]:
    """
    Ordena a população pelo fitness (menor = melhor).
    """
    combined = list(zip(population, fitness_values))
    combined.sort(key=lambda x: x[1])
    sorted_pop, sorted_fit = zip(*combined)
    return list(sorted_pop), list(sorted_fit)


# ──────────────────────────────────────────────
# Loop principal do GA
# ──────────────────────────────────────────────
def run_genetic_algorithm(
    attendance_points: List[AttendancePoint],
    population_size: int  = 100,
    n_generations: int    = 200,
    mutation_prob: float  = 0.3,
    elite_size: int       = 2,
    verbose: bool         = True
) -> Tuple[List[AttendancePoint], float, List[float]]:
    """
    Executa o Algoritmo Genético para otimização de rotas VRP.

    Parameters:
    - attendance_points: pontos de atendimento do dia
    - population_size: tamanho da população
    - n_generations: número de gerações
    - mutation_prob: probabilidade de mutação (0 a 1)
    - elite_size: quantos melhores indivíduos são preservados por geração
    - verbose: imprime progresso a cada 10 gerações

    Returns:
    - best_route: melhor rota encontrada
    - best_fitness: fitness da melhor rota
    - history: lista com o melhor fitness de cada geração (para plotar)
    """

    # Geração da população inicial
    population = generate_random_population(attendance_points, population_size)
    history = []

    for generation in range(n_generations):

        # Avalia fitness de toda a população
        fitness_values = [calculate_fitness(ind) for ind in population]

        # Ordena pelo fitness
        population, fitness_values = sort_population(population, fitness_values)

        best_fitness = fitness_values[0]
        history.append(best_fitness)

        if verbose and (generation % 10 == 0 or generation == n_generations - 1):
            print(f"  Geração {generation:03d} | Fitness: {best_fitness:.2f}")

        # Elitismo: preserva os N melhores
        new_population = population[:elite_size]

        # Seleção por probabilidade inversa ao fitness
        weights = 1 / np.array(fitness_values)

        while len(new_population) < population_size:
            parent1, parent2 = random.choices(population, weights=weights, k=2)
            child = order_crossover(parent1, parent2)
            child = mutate(child, mutation_prob)
            new_population.append(child)

        population = new_population

    # Resultado final
    final_fitness = [calculate_fitness(ind) for ind in population]
    population, final_fitness = sort_population(population, final_fitness)

    best_route   = population[0]
    best_fitness = final_fitness[0]

    return best_route, best_fitness, history


# ──────────────────────────────────────────────
# Execução direta para teste
# ──────────────────────────────────────────────
if __name__ == "__main__":
    from data.synthetic_data import ATTENDANCE_POINTS

    print("=" * 55)
    print("  RODANDO GA — VRP Saúde da Mulher")
    print("=" * 55)

    best_route, best_fitness, history = run_genetic_algorithm(
        attendance_points=ATTENDANCE_POINTS,
        population_size=100,
        n_generations=200,
        mutation_prob=0.3,
        verbose=True
    )

    print("\n✅ Melhor rota encontrada:")
    for i, point in enumerate(best_route):
        prefix = "🏥" if point.tipo == "base" else f"  {i:02d}."
        print(f"  {prefix} [{point.tipo}] {point.name}")

    print("\n📊 Detalhamento do fitness:")
    breakdown = fitness_breakdown(best_route)
    for k, v in breakdown.items():
        print(f"  {k}: {v}")