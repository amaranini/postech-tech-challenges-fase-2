"""
fitness.py
Função de fitness para o VRP especializado em saúde da mulher.

Avalia uma rota considerando:
  - Distância total percorrida
  - Penalidade por violação de prioridade (obrigatório)
  - Penalidade por violação de capacidade de suprimentos (obrigatório)
  - Penalidade por violação de janela de tempo (obrigatório)
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
from typing import List
from data.synthetic_data import AttendancePoint, VEHICLE_CONFIG
from vrp.waze_adapter import FakeWazeAdapter, Location

adapter = FakeWazeAdapter()


# ──────────────────────────────────────────────
# Pesos das penalidades
# Quanto maior, mais o GA evita violar aquela restrição
# ──────────────────────────────────────────────
PENALTY_PRIORITY    = 500   # visitar emergência depois de pós-parto, por ex.
PENALTY_CAPACITY    = 1000  # exceder capacidade de suprimentos
PENALTY_TIME_WINDOW = 300   # chegar fora da janela de tempo permitida

# ──────────────────────────────────────────────
# Adapter de roteamento
# Troque FakeWazeAdapter() por RealWazeAdapter() quando tiver API key
# ──────────────────────────────────────────────
_adapter = FakeWazeAdapter()

# ──────────────────────────────────────────────
# Distância geográfica (Haversine)
# Usamos Haversine porque os pontos têm lat/lon reais
# ──────────────────────────────────────────────
def haversine(point1: AttendancePoint, point2: AttendancePoint) -> float:
    """
    Calcula a distância em km entre dois pontos geográficos
    usando a fórmula de Haversine.
    """
    R = 6371  # raio da Terra em km

    lat1, lon1 = math.radians(point1.lat), math.radians(point1.lon)
    lat2, lon2 = math.radians(point2.lat), math.radians(point2.lon)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def calculate_total_distance(route: List[AttendancePoint]) -> float:
    """Soma a distância total de todos os segmentos da rota."""
    total = 0.0
    for i in range(len(route) - 1):
        total += haversine(route[i], route[i + 1])
    return total


# ──────────────────────────────────────────────
# Penalidade 1 — Prioridade (OBRIGATÓRIA)
# Penaliza quando um ponto de menor prioridade
# aparece antes de um de maior prioridade na rota.
# Ex: visitar pós-parto (4) antes de emergência (1) = penalizado
# ──────────────────────────────────────────────
def penalty_priority(route: List[AttendancePoint]) -> float:
    """
    Conta quantas inversões de prioridade existem na rota.
    Cada inversão multiplica a penalidade base.
    """
    penalty = 0.0
    # Filtra só os pontos de atendimento, ignora a base
    attendance_only = [p for p in route if p.tipo != "base"]
    for i in range(len(attendance_only)):
        for j in range(i + 1, len(attendance_only)):
            if attendance_only[i].priority > attendance_only[j].priority:
                priority_diff = attendance_only[i].priority - attendance_only[j].priority
                penalty += PENALTY_PRIORITY * priority_diff
    return penalty


# ──────────────────────────────────────────────
# Penalidade 2 — Capacidade de suprimentos
# O veículo tem um limite de suprimentos que pode carregar.
# Se a rota exige mais do que o veículo suporta, penaliza.
# ──────────────────────────────────────────────
def penalty_capacity(route: List[AttendancePoint]) -> float:
    """
    Verifica se a soma de suprimentos da rota excede
    a capacidade máxima do veículo.
    """
    total_supplies = sum(p.supplies for p in route if p.tipo != "base")
    max_supplies = VEHICLE_CONFIG["max_supplies"]

    if total_supplies > max_supplies:
        excess = total_supplies - max_supplies
        return PENALTY_CAPACITY * excess
    return 0.0


# ──────────────────────────────────────────────
# Penalidade 3 — Janelas de tempo
# Cada ponto tem um horário permitido de atendimento.
# Estimamos o horário de chegada e penalizamos se estiver fora.
# ──────────────────────────────────────────────
def penalty_time_window(route: List[AttendancePoint]) -> float:
    """
    Simula o horário de chegada em cada ponto e penaliza
    chegadas fora da janela de tempo permitida.
 
    O tempo de deslocamento entre pontos é estimado via WazeAdapter,
    que considera variação de trânsito por horário (rush manhã/tarde etc.)
    em vez de velocidade média fixa.
 
    Assume:
    - Saída da base no horário definido em VEHICLE_CONFIG
    - 15 minutos de duração por atendimento
    """
    penalty = 0.0
    current_time = float(VEHICLE_CONFIG["start_hour"])  # hora decimal (ex: 7.0 = 07:00)
    attendance_duration = 0.25  # 15 minutos = 0.25h

    for i in range(len(route) - 1):

        # Consulta o adapter para obter tempo de deslocamento com trânsito
        origin      = Location(lat=route[i].lat,     lon=route[i].lon)
        destination = Location(lat=route[i+1].lat,   lon=route[i+1].lon)
 
        travel_info   = _adapter.get_travel_info(origin, destination, current_time)
        travel_time_h = travel_info.duration_minutes / 60  # converte para horas
 
        current_time += travel_time_h # avança o horário de chegada no próximo ponto

        next_point = route[i + 1]
        if next_point.tipo == "base":
            continue

        window_start, window_end = next_point.time_window

        if current_time < window_start:
            # Chegou cedo demais — espera (não penaliza, apenas aguarda)
            current_time = float(window_start)
        elif current_time > window_end:
            # Chegou tarde — penaliza proporcionalmente ao atraso
            delay = current_time - window_end
            penalty += PENALTY_TIME_WINDOW * delay

        current_time += attendance_duration  # tempo gasto no atendimento

    return penalty


# ──────────────────────────────────────────────
# FITNESS FINAL
# Combina distância + todas as penalidades
# Quanto MENOR o valor, MELHOR a rota
# ──────────────────────────────────────────────
def calculate_fitness(route: List[AttendancePoint]) -> float:
    """
    Calcula o fitness de uma rota.
    Retorna a distância total + penalidades.
    Quanto menor, melhor.

    Parameters:
    - route: lista ordenada de AttendancePoint (inclui base no início e fim)

    Returns:
    - float: valor de fitness (distância em km + penalidades)
    """
    distance   = calculate_total_distance(route)
    pen_prio   = penalty_priority(route)
    pen_cap    = penalty_capacity(route)
    pen_time   = penalty_time_window(route)

    return distance + pen_prio + pen_cap + pen_time


def fitness_breakdown(route: List[AttendancePoint]) -> dict:
    """
    Retorna o detalhamento do fitness para análise e debug.
    """
    distance = calculate_total_distance(route)
    pen_prio = penalty_priority(route)
    pen_cap  = penalty_capacity(route)
    pen_time = penalty_time_window(route)

    return {
        "distancia_km":         round(distance, 2),
        "penalidade_prioridade": round(pen_prio, 2),
        "penalidade_capacidade": round(pen_cap, 2),
        "penalidade_tempo":      round(pen_time, 2),
        "fitness_total":         round(distance + pen_prio + pen_cap + pen_time, 2),
    }


if __name__ == "__main__":
    from data.synthetic_data import get_all_points, BASE

    # Teste com rota aleatória (base → pontos → base)
    import random
    points = get_all_points()
    attendance = [p for p in points if p.tipo != "base"]
    random.shuffle(attendance)
    route = [BASE] + attendance + [BASE]

    print("Testando fitness com rota aleatória:")
    breakdown = fitness_breakdown(route)
    for k, v in breakdown.items():
        print(f"  {k}: {v}")