"""
waze_adapter.py
Adapter para estimativa de tempo de deslocamento entre pontos.

Implementa o padrão Adapter com duas versões:
  - FakeWazeAdapter: simula variação de trânsito por horário (sem API key)
  - RealWazeAdapter: estrutura pronta para integração real com API de roteamento

A função de fitness usa WazeAdapter.get_travel_time() sem saber qual
implementação está ativa — basta trocar o adapter no main.py.
"""

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass


# ──────────────────────────────────────────────
# Estruturas de dados
# ──────────────────────────────────────────────
@dataclass
class Location:
    """Representa um ponto geográfico."""
    lat: float
    lon: float


@dataclass
class TravelInfo:
    """Resultado de uma consulta de deslocamento."""
    duration_minutes: float   # tempo estimado de viagem
    distance_km: float        # distância em km
    traffic_condition: str    # "light", "moderate", "heavy"
    departure_time: str       # horário de partida usado na consulta


# ──────────────────────────────────────────────
# Interface abstrata — padrão Adapter
# ──────────────────────────────────────────────
class WazeAdapter(ABC):
    """
    Interface abstrata para adapters de roteamento.
    Qualquer implementação (fake ou real) deve seguir este contrato.
    """

    @abstractmethod
    def get_travel_info(
        self,
        origin: Location,
        destination: Location,
        departure_time: float  # hora decimal, ex: 7.5 = 07:30
    ) -> TravelInfo:
        """
        Retorna informações de deslocamento entre dois pontos.

        Parameters:
        - origin: ponto de partida
        - destination: ponto de chegada
        - departure_time: horário de partida em hora decimal

        Returns:
        - TravelInfo com duração, distância e condição do trânsito
        """
        pass


# ──────────────────────────────────────────────
# Implementação Fake — simula variação de trânsito
# ──────────────────────────────────────────────
class FakeWazeAdapter(WazeAdapter):
    """
    Simula respostas da API do Waze com variação de trânsito por horário.

    Modela três situações reais de SP:
      - Rush da manhã (07h-09h): trânsito pesado, velocidade ~18 km/h
      - Horário tranquilo (10h-16h): trânsito leve, velocidade ~35 km/h
      - Rush da tarde (17h-19h): trânsito pesado, velocidade ~15 km/h
      - Demais horários: trânsito moderado, velocidade ~28 km/h

    Adiciona variação aleatória de ±15% para simular imprevisibilidade.
    """

    # Perfis de trânsito por faixa horária
    # (hora_inicio, hora_fim, velocidade_media_kmh, condicao)
    TRAFFIC_PROFILES = [
        (6.0,  7.0,  30.0, "light"),     # madrugada/início da manhã
        (7.0,  9.0,  18.0, "heavy"),     # rush manhã
        (9.0,  10.0, 25.0, "moderate"),  # pós-rush manhã
        (10.0, 16.0, 35.0, "light"),     # horário comercial tranquilo
        (16.0, 17.0, 25.0, "moderate"),  # pré-rush tarde
        (17.0, 19.0, 15.0, "heavy"),     # rush tarde
        (19.0, 21.0, 28.0, "moderate"),  # noite
        (21.0, 24.0, 38.0, "light"),     # noite tranquila
    ]

    DEFAULT_SPEED = 28.0  # km/h para horários fora dos perfis

    def _haversine(self, origin: Location, destination: Location) -> float:
        """Calcula distância real em km entre dois pontos geográficos."""
        R = 6371
        lat1 = math.radians(origin.lat)
        lat2 = math.radians(destination.lat)
        dlat = math.radians(destination.lat - origin.lat)
        dlon = math.radians(destination.lon - origin.lon)
        a = (math.sin(dlat/2)**2 +
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2)
        return R * 2 * math.asin(math.sqrt(a))

    def _get_traffic_profile(self, departure_time: float) -> tuple:
        """Retorna (velocidade_media, condicao) para o horário informado."""
        for start, end, speed, condition in self.TRAFFIC_PROFILES:
            if start <= departure_time < end:
                return speed, condition
        return self.DEFAULT_SPEED, "moderate"

    def get_travel_info(
        self,
        origin: Location,
        destination: Location,
        departure_time: float
    ) -> TravelInfo:
        """
        Simula resposta do Waze com variação de trânsito por horário.
        Adiciona variação aleatória de ±15% para simular imprevisibilidade.
        """
        distance_km = self._haversine(origin, destination)
        avg_speed, traffic_condition = self._get_traffic_profile(departure_time)

        # Variação aleatória de ±15% para simular imprevisibilidade do trânsito
        variation = random.uniform(0.85, 1.15)
        effective_speed = avg_speed * variation

        duration_minutes = (distance_km / effective_speed) * 60

        # Formata horário de partida para exibição
        h = int(departure_time)
        m = int((departure_time % 1) * 60)
        departure_str = f"{h:02d}:{m:02d}"

        return TravelInfo(
            duration_minutes=round(duration_minutes, 1),
            distance_km=round(distance_km, 2),
            traffic_condition=traffic_condition,
            departure_time=departure_str
        )


# ──────────────────────────────────────────────
# Implementação Real — estrutura para API real
# ──────────────────────────────────────────────
class RealWazeAdapter(WazeAdapter):
    """
    Estrutura pronta para integração com uma API real de roteamento.
    (Google Maps Directions API, HERE Maps, TomTom, etc.)

    Para ativar:
    1. Obtenha uma API key do serviço escolhido
    2. Configure a variável de ambiente: ROUTING_API_KEY=sua-chave
    3. Implemente o método get_travel_info() com a chamada real
    4. No main.py, troque FakeWazeAdapter() por RealWazeAdapter()

    Exemplo de payload para Google Maps Directions API:
    GET https://maps.googleapis.com/maps/api/directions/json
        ?origin=-23.47,-46.67
        &destination=-23.50,-46.62
        &departure_time=1711270200   (timestamp Unix)
        &traffic_model=best_guess
        &key=SUA_API_KEY
    """

    def __init__(self, api_key: str = None):
        import os
        self.api_key = api_key or os.environ.get("ROUTING_API_KEY")
        if not self.api_key:
            raise EnvironmentError(
                "ROUTING_API_KEY não encontrada.\n"
                "Configure com: export ROUTING_API_KEY='sua-chave-aqui'\n"
                "Ou passe a chave diretamente: RealWazeAdapter(api_key='...')"
            )

    def get_travel_info(
        self,
        origin: Location,
        destination: Location,
        departure_time: float
    ) -> TravelInfo:
        """
        TODO: Implementar chamada real à API de roteamento.

        Exemplo com Google Maps Directions API:

        import requests
        from datetime import datetime, timedelta

        # Converte hora decimal para timestamp Unix
        today = datetime.now().replace(
            hour=int(departure_time),
            minute=int((departure_time % 1) * 60),
            second=0
        )
        timestamp = int(today.timestamp())

        response = requests.get(
            "https://maps.googleapis.com/maps/api/directions/json",
            params={
                "origin": f"{origin.lat},{origin.lon}",
                "destination": f"{destination.lat},{destination.lon}",
                "departure_time": timestamp,
                "traffic_model": "best_guess",
                "key": self.api_key
            }
        )
        data = response.json()
        leg = data["routes"][0]["legs"][0]

        return TravelInfo(
            duration_minutes=leg["duration_in_traffic"]["value"] / 60,
            distance_km=leg["distance"]["value"] / 1000,
            traffic_condition="real",
            departure_time=f"{int(departure_time):02d}:{int((departure_time%1)*60):02d}"
        )
        """
        raise NotImplementedError(
            "RealWazeAdapter não implementado. "
            "Consulte a docstring desta classe para instruções."
        )


# ──────────────────────────────────────────────
# Teste direto
# ──────────────────────────────────────────────
if __name__ == "__main__":
    adapter = FakeWazeAdapter()

    origin      = Location(lat=-23.4766, lon=-46.6723)  # Base hospitalar
    destination = Location(lat=-23.5029, lon=-46.6267)  # Paciente Ana Lima

    print("Simulação de deslocamento — Base → Paciente Ana Lima")
    print("=" * 55)

    horarios = [7.0, 8.0, 10.0, 12.0, 17.0, 18.0, 20.0]
    for h in horarios:
        info = adapter.get_travel_info(origin, destination, departure_time=h)
        print(
            f"  {info.departure_time} | "
            f"{info.duration_minutes:5.1f} min | "
            f"{info.distance_km} km | "
            f"trânsito: {info.traffic_condition}"
        )