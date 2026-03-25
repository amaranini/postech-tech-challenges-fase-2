"""
main.py
Ponto de entrada do projeto VRP — Saúde da Mulher.

Orquestra todo o pipeline:
  1. Carrega os dados sintéticos
  2. Roda o Algoritmo Genético
  3. Gera a visualização no mapa
  4. Integra com LLM para gerar relatórios
  5. Salva os resultados
"""

import os
import sys

# Garante que a raiz do projeto está no path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.synthetic_data import ATTENDANCE_POINTS, get_points_summary
from vrp.genetic_algorithm import run_genetic_algorithm
from vrp.fitness import fitness_breakdown
from visualization.map_viz import create_route_map
from llm.report_generator import (
    generate_team_manual,
    generate_visit_itinerary,
    ask_about_route,
    save_llm_responses
)


# ──────────────────────────────────────────────
# Configurações do GA
# elite_size = 2 fixo para isolar o efeito das outras variáveis nos experimentos 
#   -> valor seguro e bem estabelecido para populações de 50-200 indivíduos
# ──────────────────────────────────────────────
# Experimento 1
# GA_CONFIG = {
#     "population_size": 200,
#     "n_generations":   300,
#     "mutation_prob":   0.2,
#     "elite_size":      2, 
# }

# Experimento 2
# GA_CONFIG = {
#     "population_size": 200,
#     "n_generations":   300,
#     "mutation_prob":   0.2,
#     "elite_size":      2,
# }

# Experimento 3
GA_CONFIG = {
    "population_size": 50,
    "n_generations":   500,
    "mutation_prob":   0.5,
    "elite_size":      2,
}


def run_pipeline(ga_config: dict = GA_CONFIG, open_map: bool = True) -> dict:
    """
    Executa o pipeline completo do projeto.

    Parameters:
    - ga_config: configurações do algoritmo genético
    - open_map: se True, abre o mapa no navegador automaticamente

    Returns:
    - dict com os resultados do pipeline
    """

    print("\n" + "="*60)
    print("  VRP — SISTEMA DE ROTEIRIZAÇÃO EM SAÚDE DA MULHER")
    print("="*60)

    # ── 1. Dados ──────────────────────────────
    print("\n📋 ETAPA 1 — Carregando dados dos atendimentos do dia...")
    get_points_summary()

    # ── 2. Algoritmo Genético ─────────────────
    print("\n🧬 ETAPA 2 — Otimizando rota com Algoritmo Genético...")
    print(f"   Configuração: {ga_config}")

    best_route, best_fitness, history = run_genetic_algorithm(
        attendance_points=ATTENDANCE_POINTS,
        population_size=ga_config["population_size"],
        n_generations=ga_config["n_generations"],
        mutation_prob=ga_config["mutation_prob"],
        elite_size=ga_config["elite_size"],
        verbose=True
    )

    print("\n✅ Rota otimizada!")
    print("\n📊 Detalhamento do fitness:")
    breakdown = fitness_breakdown(best_route)
    for k, v in breakdown.items():
        print(f"   {k}: {v}")

    print("\n🗺️  Ordem de visitas:")
    for i, point in enumerate(best_route):
        if point.tipo == "base":
            print(f"   🏥 {point.name}")
        else:
            print(f"   {i:02d}. [{point.tipo}] {point.name}")

    # ── 3. Mapa ───────────────────────────────
    print("\n🗺️  ETAPA 3 — Gerando visualização no mapa...")
    map_path = create_route_map(
        route=best_route,
        output_path="route_map.html",
        open_browser=open_map
    )

    # ── 4. LLM ───────────────────────────────
    print("\n🤖 ETAPA 4 — Gerando relatórios com IA...")

    print("   Gerando manual de instruções...")
    manual = generate_team_manual(best_route)

    print("   Gerando roteiro de visitas...")
    itinerary = generate_visit_itinerary(best_route)

    print("   Testando perguntas sobre a rota...")
    questions = [
        "Quantas paradas de emergência temos hoje?",
        "Quais medicamentos precisam de cadeia fria?",
        "Qual o próximo atendimento prioritário após as emergências?",
        "Qual o tempo total estimado de rota?",
    ]

    chat_session = None
    qa_pairs = []
    for q in questions:
        print(f"\n   ❓ {q}")
        answer, chat_session = ask_about_route(q, best_route, chat_session)
        print(f"   💬 {answer}")
        qa_pairs.append((q, answer))

    # ── 5. Salva resultados ───────────────────
    print("\n💾 ETAPA 5 — Salvando resultados...")
    save_llm_responses(
        route=best_route,
        manual=manual,
        itinerary=itinerary,
        qa_pairs=qa_pairs,
        output_path="llm_responses.json"
    )

    # Salva o manual e roteiro em arquivos de texto também
    with open("manual_equipe.txt", "w", encoding="utf-8") as f:
        f.write(manual)
    print("✅ Manual salvo em: manual_equipe.txt")

    with open("roteiro_visitas.txt", "w", encoding="utf-8") as f:
        f.write(itinerary)
    print("✅ Roteiro salvo em: roteiro_visitas.txt")

    print("\n" + "="*60)
    print("  PIPELINE CONCLUÍDO COM SUCESSO!")
    print("="*60)
    print(f"\n  Arquivos gerados:")
    print(f"  📍 route_map.html      — mapa interativo da rota")
    print(f"  📄 manual_equipe.txt   — manual para a equipe")
    print(f"  📄 roteiro_visitas.txt — roteiro detalhado")
    print(f"  🗃️  llm_responses.json  — dados para fine-tuning")

    return {
        "best_route":   best_route,
        "best_fitness": best_fitness,
        "history":      history,
        "breakdown":    breakdown,
        "manual":       manual,
        "itinerary":    itinerary,
        "qa_pairs":     qa_pairs,
    }


if __name__ == "__main__":
    run_pipeline()