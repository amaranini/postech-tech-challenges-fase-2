"""
synthetic_data.py
Dados sintéticos para o problema de roteirização de veículos (VRP)
focado na saúde da mulher - coordenadas reais de São Paulo/SP
"""

from dataclasses import dataclass, field
from typing import Optional
import random

# ──────────────────────────────────────────────
# Tipos de atendimento e suas prioridades
# (quanto menor o número, maior a prioridade)
# ──────────────────────────────────────────────
PRIORITY_MAP = {
    "emergencia_obstetrica": 1,
    "violencia_domestica":   2,
    "medicamento_hormonal":  3,
    "pos_parto":             4,
}

# Cores para visualização no mapa (folium)
COLOR_MAP = {
    "emergencia_obstetrica": "red",
    "violencia_domestica":   "orange",
    "medicamento_hormonal":  "blue",
    "pos_parto":             "green",
    "base":                  "black",
}

# Ícones para visualização no mapa (folium)
ICON_MAP = {
    "emergencia_obstetrica": "plus-sign",
    "violencia_domestica":   "exclamation-sign",
    "medicamento_hormonal":  "tint",
    "pos_parto":             "heart",
    "base":                  "home",
}


@dataclass
class AttendancePoint:
    """Representa um ponto de atendimento na rota."""
    id: int
    name: str
    lat: float
    lon: float
    tipo: str                          # tipo de atendimento
    priority: int                      # 1 = mais urgente
    time_window: tuple                 # (hora_inicio, hora_fim) em horas inteiras
    requires_cold_chain: bool = False  # medicamentos que precisam de frio
    supplies: int = 1                  # unidades de suprimento necessárias
    notes: str = ""                    # observações para a equipe

    @property
    def color(self):
        return COLOR_MAP.get(self.tipo, "gray")

    @property
    def icon(self):
        return ICON_MAP.get(self.tipo, "info-sign")


# ──────────────────────────────────────────────
# BASE HOSPITALAR (ponto de partida e chegada)
# ──────────────────────────────────────────────
BASE = AttendancePoint(
    id=0,
    name="Hospital Maternidade Vila Nova Cachoeirinha",
    lat=-23.4766,
    lon=-46.6723,
    tipo="base",
    priority=0,
    time_window=(6, 22),
    supplies=0,
    notes="Base de operações. Ponto de partida e retorno da rota."
)

# ──────────────────────────────────────────────
# PONTOS DE ATENDIMENTO
# ──────────────────────────────────────────────
ATTENDANCE_POINTS = [

    # ── EMERGÊNCIAS OBSTÉTRICAS (prioridade 1) ──
    AttendancePoint(
        id=1,
        name="Paciente Ana Lima - Santana",
        lat=-23.5029,
        lon=-46.6267,
        tipo="emergencia_obstetrica",
        priority=1,
        time_window=(6, 10),
        supplies=2,
        notes="Gestante 38 semanas com contrações irregulares. Atendimento imediato."
    ),
    AttendancePoint(
        id=2,
        name="Paciente Carla Souza - Penha",
        lat=-23.5289,
        lon=-46.5378,
        tipo="emergencia_obstetrica",
        priority=1,
        time_window=(6, 9),
        supplies=2,
        notes="Sangramento pós-parto relatado por telefone. Prioridade máxima."
    ),
    AttendancePoint(
        id=3,
        name="Paciente Fernanda Rocha - Itaquera",
        lat=-23.5384,
        lon=-46.4558,
        tipo="emergencia_obstetrica",
        priority=1,
        time_window=(7, 11),
        supplies=1,
        notes="Pressão arterial elevada. Risco de pré-eclâmpsia."
    ),

    # ── VIOLÊNCIA DOMÉSTICA (prioridade 2) ──
    AttendancePoint(
        id=4,
        name="Paciente Beatriz Costa - Bom Retiro",
        lat=-23.5238,
        lon=-46.6367,
        tipo="violencia_domestica",
        priority=2,
        time_window=(8, 14),
        supplies=1,
        notes="PROTOCOLO ESPECIAL: Não identificar veículo. Bater discretamente. "
              "Aguardar resposta por até 3 minutos antes de contatar central."
    ),
    AttendancePoint(
        id=5,
        name="Paciente Daniela Ferreira - Lapa",
        lat=-23.5209,
        lon=-46.7028,
        tipo="violencia_domestica",
        priority=2,
        time_window=(9, 15),
        supplies=1,
        notes="PROTOCOLO ESPECIAL: Visita sob codinome 'entrega de farmácia'. "
              "Não mencionar hospital em caso de terceiros presentes."
    ),
    AttendancePoint(
        id=6,
        name="Paciente Juliana Martins - Santo André",
        lat=-23.6615,
        lon=-46.5322,
        tipo="violencia_domestica",
        priority=2,
        time_window=(10, 16),
        supplies=2,
        notes="PROTOCOLO ESPECIAL: Acompanhamento psicológico remoto durante a visita. "
              "Contato prévio com assistente social confirmado."
    ),

    # ── MEDICAMENTOS HORMONAIS (prioridade 3) ──
    AttendancePoint(
        id=7,
        name="Paciente Helena Nascimento - Moema",
        lat=-23.6058,
        lon=-46.6655,
        tipo="medicamento_hormonal",
        priority=3,
        time_window=(8, 18),
        requires_cold_chain=True,
        supplies=1,
        notes="Insulina + hormônios tireoidianos. Manter entre 2°C e 8°C. "
              "Usar bolsa térmica compartimento azul."
    ),
    AttendancePoint(
        id=8,
        name="UBS Saúde da Mulher - Pinheiros",
        lat=-23.5632,
        lon=-46.6847,
        tipo="medicamento_hormonal",
        priority=3,
        time_window=(7, 12),
        requires_cold_chain=True,
        supplies=3,
        notes="Anticoncepcional injetável trimestral (lote 3 unidades). "
              "Receber apenas com a enfermeira Patrícia. Temperatura máxima: 25°C."
    ),
    AttendancePoint(
        id=9,
        name="Clínica Feminina - Tatuapé",
        lat=-23.5408,
        lon=-46.5765,
        tipo="medicamento_hormonal",
        priority=3,
        time_window=(9, 17),
        requires_cold_chain=False,
        supplies=2,
        notes="Terapia de reposição hormonal. Entregar na recepção com assinatura."
    ),
    AttendancePoint(
        id=10,
        name="Paciente Roberta Alves - Vila Mariana",
        lat=-23.5873,
        lon=-46.6361,
        tipo="medicamento_hormonal",
        priority=3,
        time_window=(10, 20),
        requires_cold_chain=True,
        supplies=1,
        notes="Hormônios para tratamento de SOP. Conservar em frio. "
              "Paciente trabalha até as 18h — preferência pela tarde."
    ),

    # ── PÓS-PARTO (prioridade 4) ──
    AttendancePoint(
        id=11,
        name="Paciente Camila Oliveira - Ipiranga",
        lat=-23.5896,
        lon=-46.6062,
        tipo="pos_parto",
        priority=4,
        time_window=(9, 17),
        supplies=1,
        notes="7 dias pós-parto. Verificar amamentação, cicatriz e sinais de baby blues."
    ),
    AttendancePoint(
        id=12,
        name="Paciente Larissa Pereira - Jabaquara",
        lat=-23.6441,
        lon=-46.6468,
        tipo="pos_parto",
        priority=4,
        time_window=(10, 18),
        supplies=2,
        notes="15 dias pós-parto cesárea. Curativo e orientações sobre higiene da incisão."
    ),
    AttendancePoint(
        id=13,
        name="Paciente Marina Santos - Brooklin",
        lat=-23.6150,
        lon=-46.6918,
        tipo="pos_parto",
        priority=4,
        time_window=(8, 16),
        supplies=1,
        notes="21 dias pós-parto. Acompanhamento nutricional e vacinação do recém-nascido."
    ),
    AttendancePoint(
        id=14,
        name="Paciente Priscila Mendes - Campo Belo",
        lat=-23.6272,
        lon=-46.6672,
        tipo="pos_parto",
        priority=4,
        time_window=(11, 19),
        supplies=1,
        notes="30 dias pós-parto. Consulta de retorno e coleta para exame."
    ),
    AttendancePoint(
        id=15,
        name="Paciente Tatiane Gomes - Saúde",
        lat=-23.6183,
        lon=-46.6289,
        tipo="pos_parto",
        priority=4,
        time_window=(9, 15),
        supplies=2,
        notes="10 dias pós-parto gemelar. Apoio intensivo à amamentação."
    ),
]

# ──────────────────────────────────────────────
# CONFIGURAÇÕES DO VEÍCULO
# ──────────────────────────────────────────────
VEHICLE_CONFIG = {
    "max_stops": 10,          # número máximo de paradas por rota
    "max_supplies": 25,       # capacidade máxima de suprimentos
    "start_hour": 7,          # hora de saída da base
    "avg_speed_kmh": 30,      # velocidade média em SP (tráfego urbano)
    "has_cold_chain": True,   # veículo possui compartimento refrigerado
}


# ──────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ──────────────────────────────────────────────
def get_all_points() -> list:
    """Retorna base + todos os pontos de atendimento."""
    return [BASE] + ATTENDANCE_POINTS


def get_points_by_type(tipo: str) -> list:
    """Retorna pontos filtrados por tipo de atendimento."""
    return [p for p in ATTENDANCE_POINTS if p.tipo == tipo]


def get_points_summary() -> None:
    """Imprime um resumo dos pontos cadastrados."""
    print("=" * 55)
    print("  RESUMO DOS PONTOS DE ATENDIMENTO")
    print("=" * 55)
    for tipo, priority in PRIORITY_MAP.items():
        pontos = get_points_by_type(tipo)
        print(f"  [{priority}] {tipo.replace('_', ' ').title()}: {len(pontos)} pontos")
    print(f"\n  Total de atendimentos: {len(ATTENDANCE_POINTS)}")
    print(f"  Suprimentos totais:    {sum(p.supplies for p in ATTENDANCE_POINTS)}")
    cold = [p for p in ATTENDANCE_POINTS if p.requires_cold_chain]
    print(f"  Requerem cadeia fria:  {len(cold)}")
    print("=" * 55)


if __name__ == "__main__":
    get_points_summary()

    print("\nDetalhes dos pontos:")
    for p in get_all_points():
        print(f"  [{p.id:02d}] {p.name}")
        print(f"        tipo={p.tipo} | prioridade={p.priority} "
              f"| janela={p.time_window} | suprimentos={p.supplies}")