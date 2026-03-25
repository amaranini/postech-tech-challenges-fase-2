"""
report_generator.py
Integração com a API do Google Gemini para geração de:
  - Manual de instruções para a equipe de transporte
  - Roteiro detalhado de visitas
  - Respostas a perguntas em linguagem natural sobre a rota

As respostas são salvas em JSON para uso futuro (fine-tuning Fase 3).
"""

import os
import json
import math
from datetime import datetime
from typing import List, Tuple
import google.generativeai as genai

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.synthetic_data import AttendancePoint, VEHICLE_CONFIG


# ──────────────────────────────────────────────
# System prompt base — contexto médico feminino
# Definido antes de get_client() pois é usado dentro dele
# ──────────────────────────────────────────────
SYSTEM_PROMPT = """Você é um assistente especializado em logística hospitalar focado na saúde da mulher.

Suas respostas devem sempre:
- Usar linguagem clara, objetiva e sensível ao contexto feminino
- Respeitar a privacidade e confidencialidade das pacientes (use apenas nomes e endereços mínimos necessários)
- Destacar protocolos especiais para casos de violência doméstica (discrição total)
- Sinalizar claramente requisitos de cadeia fria para medicamentos
- Priorizar comunicação de emergências obstétricas
- Usar terminologia médica adequada mas acessível à equipe de campo

Você está gerando documentos operacionais para equipes de saúde em campo.
A precisão e sensibilidade das informações pode impactar diretamente a segurança das pacientes."""


# ──────────────────────────────────────────────
# Cliente Gemini
# A API key deve estar na variável de ambiente:
#
# Mac/Linux:  export GEMINI_API_KEY="sua-chave-aqui"
# Windows:    set GEMINI_API_KEY="sua-chave-aqui"
#
# Obtenha sua chave gratuita em: https://aistudio.google.com
# ──────────────────────────────────────────────
def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY não encontrada.\n"
            "Configure com: export GEMINI_API_KEY='sua-chave-aqui'\n"
            "Obtenha sua chave gratuita em: https://aistudio.google.com"
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT
    )


# ──────────────────────────────────────────────
# Helpers para montar o contexto da rota
# ──────────────────────────────────────────────
def _haversine(p1: AttendancePoint, p2: AttendancePoint) -> float:
    R = 6371
    lat1, lon1 = math.radians(p1.lat), math.radians(p1.lon)
    lat2, lon2 = math.radians(p2.lat), math.radians(p2.lon)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


TYPE_LABELS = {
    "emergencia_obstetrica": "Emergência Obstétrica",
    "violencia_domestica":   "Violência Doméstica",
    "medicamento_hormonal":  "Medicamento Hormonal",
    "pos_parto":             "Pós-Parto",
    "base":                  "Base Hospitalar",
}


def build_route_context(route: List[AttendancePoint]) -> str:
    """
    Transforma a rota em texto estruturado para enviar à LLM.
    """
    lines = ["ROTA OTIMIZADA DO DIA\n"]
    lines.append(f"Data: {datetime.now().strftime('%d/%m/%Y')}")
    lines.append(f"Veículo: capacidade {VEHICLE_CONFIG['max_supplies']} suprimentos")
    lines.append(f"Saída prevista: {VEHICLE_CONFIG['start_hour']}h00\n")
    lines.append("=" * 50)

    speed = VEHICLE_CONFIG["avg_speed_kmh"]
    current_time = float(VEHICLE_CONFIG["start_hour"])
    total_distance = 0.0
    attendance_order = 0

    for i, point in enumerate(route):
        if point.tipo == "base" and i == 0:
            lines.append(f"\n🏥 PONTO DE PARTIDA: {point.name}")
            continue

        if point.tipo == "base" and i > 0:
            dist = _haversine(route[i-1], point)
            total_distance += dist
            travel_time = dist / speed
            current_time += travel_time
            h, m = int(current_time), int((current_time % 1) * 60)
            lines.append(f"\n🏥 RETORNO À BASE: {point.name}")
            lines.append(f"   Chegada estimada: {h:02d}h{m:02d}")
            lines.append(f"\n{'='*50}")
            lines.append(f"📊 DISTÂNCIA TOTAL: {total_distance:.1f} km")
            continue

        attendance_order += 1
        dist = _haversine(route[i-1], point)
        total_distance += dist
        travel_time = dist / speed
        current_time += travel_time

        window_start, window_end = point.time_window
        if current_time < window_start:
            current_time = float(window_start)

        h, m = int(current_time), int((current_time % 1) * 60)
        current_time += 0.25  # 15 min por atendimento

        cold = " ❄️ CADEIA FRIA" if point.requires_cold_chain else ""
        lines.append(f"\nPARADA #{attendance_order:02d} — {TYPE_LABELS[point.tipo].upper()}{cold}")
        lines.append(f"  Local:      {point.name}")
        lines.append(f"  Chegada:    {h:02d}h{m:02d} (janela: {window_start}h-{window_end}h)")
        lines.append(f"  Distância:  {dist:.1f} km da parada anterior")
        lines.append(f"  Suprimentos: {point.supplies} unidade(s)")
        lines.append(f"  Observação: {point.notes}")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# 1. Manual de instruções para a equipe
# ──────────────────────────────────────────────
def generate_team_manual(route: List[AttendancePoint]) -> str:
    """
    Gera um manual prático de instruções para a equipe de transporte,
    com orientações específicas para cada tipo de atendimento.
    """
    model = get_client()
    route_context = build_route_context(route)

    prompt = f"""Com base na rota otimizada abaixo, gere um MANUAL DE INSTRUÇÕES completo para a equipe de transporte.

{route_context}

O manual deve conter:

1. BRIEFING GERAL DO DIA
   - Resumo dos tipos de atendimento e quantidades
   - Alertas prioritários (emergências, casos especiais)
   - Checklist de materiais antes de sair

2. INSTRUÇÕES POR PARADA
   Para cada parada, inclua:
   - O que fazer ao chegar
   - Protocolos específicos do tipo de atendimento
   - O que observar e registrar
   - Quando acionar suporte adicional

3. PROTOCOLOS DE SEGURANÇA
   - Procedimentos para casos de violência doméstica
   - Manuseio de medicamentos com cadeia fria
   - Contatos de emergência

4. ENCERRAMENTO DO DIA
   - Procedimentos de retorno à base
   - O que registrar no sistema

Escreva de forma direta e prática, como se fosse um documento que a equipe vai consultar durante o percurso."""

    response = model.generate_content(prompt)
    return response.text


# ──────────────────────────────────────────────
# 2. Roteiro detalhado de visitas
# ──────────────────────────────────────────────
def generate_visit_itinerary(route: List[AttendancePoint]) -> str:
    """
    Gera um roteiro legível e prático com ordem de visitas,
    tempos estimados e informações relevantes para cada parada.
    """
    model = get_client()
    route_context = build_route_context(route)

    prompt = f"""Com base na rota abaixo, gere um ROTEIRO DETALHADO DE VISITAS para a equipe.

{route_context}

O roteiro deve ser um documento de fácil leitura durante o percurso, contendo:

- Ordem clara de cada visita com horário estimado
- Tipo de atendimento em linguagem simples
- Informações práticas para cada entrega/atendimento
- Estimativas de tempo de deslocamento entre pontos
- Notas importantes para cada parada (sem expor dados sensíveis desnecessariamente)

Formate como um roteiro cronológico, direto e fácil de seguir."""

    response = model.generate_content(prompt)
    return response.text


# ──────────────────────────────────────────────
# 3. Chat em linguagem natural sobre a rota
# ──────────────────────────────────────────────
def ask_about_route(
    question: str,
    route: List[AttendancePoint],
    chat_session=None
) -> Tuple[str, object]:
    """
    Responde perguntas em linguagem natural sobre a rota otimizada.
    Mantém histórico de conversa para perguntas encadeadas.

    Exemplos de perguntas:
    - "Qual o próximo atendimento prioritário?"
    - "Quantas paradas de emergência temos hoje?"
    - "Quais medicamentos precisam de cadeia fria?"

    Parameters:
    - question: pergunta em linguagem natural
    - route: rota otimizada
    - chat_session: sessão de chat existente (None para iniciar nova)

    Returns:
    - Tuple com (resposta, chat_session) — passe chat_session de volta
      para manter o histórico nas próximas perguntas
    """
    model = get_client()
    route_context = build_route_context(route)

    # Inicia nova sessão de chat se não existir
    if chat_session is None:
        chat_session = model.start_chat(history=[])
        # Envia o contexto da rota como primeira mensagem para estabelecer contexto
        chat_session.send_message(
            f"Contexto da rota de hoje:\n\n{route_context}\n\n"
            f"Confirme que recebeu as informações e está pronto para responder perguntas."
        )

    response = chat_session.send_message(question)
    return response.text, chat_session


# ──────────────────────────────────────────────
# Salvar respostas para fine-tuning (Fase 3)
# ──────────────────────────────────────────────
def save_llm_responses(
    route: List[AttendancePoint],
    manual: str,
    itinerary: str,
    qa_pairs: list = None,
    output_path: str = "llm_responses.json"
) -> None:
    """
    Salva as respostas da LLM em JSON para uso na Fase 3 (fine-tuning).
    """
    route_context = build_route_context(route)

    data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "model": "gemini-2.5-flash",
            "n_attendance_points": len([p for p in route if p.tipo != "base"]),
        },
        "training_samples": [
            {
                "type": "manual_generation",
                "input": route_context,
                "output": manual
            },
            {
                "type": "itinerary_generation",
                "input": route_context,
                "output": itinerary
            }
        ]
    }

    if qa_pairs:
        for q, a in qa_pairs:
            data["training_samples"].append({
                "type": "route_qa",
                "input": q,
                "output": a
            })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Respostas salvas em: {output_path}")


# ──────────────────────────────────────────────
# Execução direta para teste
# ──────────────────────────────────────────────
if __name__ == "__main__":
    # import google.generativeai as genai
    # import os

    # genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

    # for model in genai.list_models():
    #     if "generateContent" in model.supported_generation_methods:
    #         print(model.name)
            
    from data.synthetic_data import ATTENDANCE_POINTS
    from vrp.genetic_algorithm import run_genetic_algorithm

    print("Rodando GA...")
    best_route, best_fitness, _ = run_genetic_algorithm(
        attendance_points=ATTENDANCE_POINTS,
        population_size=100,
        n_generations=200,
        mutation_prob=0.3,
        verbose=False
    )

    print(f"Rota otimizada! Fitness: {best_fitness:.2f}\n")

    # Gera manual
    print("Gerando manual de instruções...")
    manual = generate_team_manual(best_route)
    print("\n" + "="*60)
    print("MANUAL DE INSTRUÇÕES")
    print("="*60)
    print(manual)

    # Gera roteiro
    print("\nGerando roteiro de visitas...")
    itinerary = generate_visit_itinerary(best_route)
    print("\n" + "="*60)
    print("ROTEIRO DE VISITAS")
    print("="*60)
    print(itinerary)

    # Perguntas sobre a rota
    print("\nTestando perguntas sobre a rota...")
    questions = [
        "Quantas paradas de emergência temos hoje?",
        "Quais medicamentos precisam de cadeia fria?",
        "Qual o próximo atendimento prioritário após as emergências?",
    ]

    chat_session = None
    qa_pairs = []
    for q in questions:
        print(f"\n❓ {q}")
        answer, chat_session = ask_about_route(q, best_route, chat_session)
        print(f"💬 {answer}")
        qa_pairs.append((q, answer))

    # Salva tudo para Fase 3
    save_llm_responses(
        route=best_route,
        manual=manual,
        itinerary=itinerary,
        qa_pairs=qa_pairs,
        output_path="llm_responses.json"
    )