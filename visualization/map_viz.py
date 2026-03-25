"""
map_viz.py
Visualização das rotas otimizadas em mapa interativo usando Folium.

Gera um arquivo HTML com:
  - Marcadores coloridos por tipo de atendimento
  - Linha da rota otimizada
  - Popups com informações de cada ponto
  - Legenda com os tipos de atendimento
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import folium
import webbrowser
import os
from typing import List
from data.synthetic_data import AttendancePoint, BASE, COLOR_MAP, PRIORITY_MAP


# ──────────────────────────────────────────────
# Mapa de cores compatível com folium
# folium usa nomes de cores em inglês
# ──────────────────────────────────────────────
FOLIUM_COLOR_MAP = {
    "emergencia_obstetrica": "red",
    "violencia_domestica":   "orange",
    "medicamento_hormonal":  "blue",
    "pos_parto":             "green",
    "base":                  "black",
}

FOLIUM_ICON_MAP = {
    "emergencia_obstetrica": "plus-sign",
    "violencia_domestica":   "exclamation-sign",
    "medicamento_hormonal":  "tint",
    "pos_parto":             "heart",
    "base":                  "home",
}

TYPE_LABELS = {
    "emergencia_obstetrica": "Emergência Obstétrica",
    "violencia_domestica":   "Violência Doméstica",
    "medicamento_hormonal":  "Medicamento Hormonal",
    "pos_parto":             "Pós-Parto",
    "base":                  "Base Hospitalar",
}


def build_popup(point: AttendancePoint, order: int = None) -> str:
    """
    Monta o HTML do popup de cada marcador no mapa.
    """
    order_str = f"<b>Parada #{order}</b><br>" if order and point.tipo != "base" else ""
    cold_chain = "❄️ Cadeia fria necessária<br>" if point.requires_cold_chain else ""
    time_str   = f"⏰ Janela: {point.time_window[0]}h às {point.time_window[1]}h<br>"
    supplies   = f"📦 Suprimentos: {point.supplies}<br>" if point.tipo != "base" else ""

    return f"""
    <div style="font-family: Arial; min-width: 220px;">
        {order_str}
        <b style="font-size:13px;">{point.name}</b><br>
        <span style="color: gray;">{TYPE_LABELS.get(point.tipo, point.tipo)}</span><br>
        <hr style="margin:4px 0">
        {time_str}
        {supplies}
        {cold_chain}
        <i style="font-size:11px; color:#555;">{point.notes}</i>
    </div>
    """


def create_route_map(
    route: List[AttendancePoint],
    output_path: str = "route_map.html",
    open_browser: bool = True
) -> str:
    """
    Cria o mapa interativo com a rota otimizada.

    Parameters:
    - route: lista ordenada de AttendancePoint (resultado do GA)
    - output_path: caminho do arquivo HTML gerado
    - open_browser: se True, abre o mapa no navegador automaticamente

    Returns:
    - caminho do arquivo HTML gerado
    """

    # Centro do mapa: média das coordenadas de todos os pontos
    lats = [p.lat for p in route]
    lons = [p.lon for p in route]
    center = [sum(lats) / len(lats), sum(lons) / len(lons)]

    # Cria o mapa base
    m = folium.Map(
        location=center,
        zoom_start=12,
        tiles="CartoDB positron"  # mapa limpo e moderno
    )

    # ── Desenha a linha da rota ──
    route_coords = [(p.lat, p.lon) for p in route]
    folium.PolyLine(
        locations=route_coords,
        color="#2c3e50",
        weight=2.5,
        opacity=0.7,
        tooltip="Rota otimizada"
    ).add_to(m)

    # ── Adiciona marcadores ──
    attendance_order = 0
    for point in route:

        # Não duplica o marcador da base (ela aparece no início e fim da rota)
        if point.tipo == "base" and attendance_order > 0:
            continue

        if point.tipo != "base":
            attendance_order += 1

        color = FOLIUM_COLOR_MAP.get(point.tipo, "gray")
        icon  = FOLIUM_ICON_MAP.get(point.tipo, "info-sign")

        popup_html = build_popup(
            point,
            order=attendance_order if point.tipo != "base" else None
        )

        folium.Marker(
            location=[point.lat, point.lon],
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"{'🏥 Base' if point.tipo == 'base' else f'#{attendance_order} — {point.name}'}",
            icon=folium.Icon(color=color, icon=icon, prefix="glyphicon")
        ).add_to(m)

        # Número da parada sobre o marcador (exceto base)
        if point.tipo != "base":
            folium.Marker(
                location=[point.lat + 0.002, point.lon],
                icon=folium.DivIcon(
                    html=f"""
                    <div style="
                        font-size: 10px;
                        font-weight: bold;
                        color: #2c3e50;
                        background: white;
                        border: 1px solid #ccc;
                        border-radius: 50%;
                        width: 18px;
                        height: 18px;
                        text-align: center;
                        line-height: 18px;
                        box-shadow: 1px 1px 2px rgba(0,0,0,0.3);
                    ">{attendance_order}</div>
                    """,
                    icon_size=(18, 18),
                    icon_anchor=(9, 9)
                )
            ).add_to(m)

    # ── Legenda ──
    legend_items = "".join([
        f"""
        <div style="display:flex; align-items:center; margin-bottom:6px;">
            <div style="
                width:14px; height:14px; border-radius:50%;
                background:{_folium_to_hex(color)};
                margin-right:8px; flex-shrink:0;
            "></div>
            <span>{TYPE_LABELS[tipo]}</span>
        </div>
        """
        for tipo, color in FOLIUM_COLOR_MAP.items()
    ])

    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 30px; left: 30px;
        background: white;
        padding: 14px 18px;
        border-radius: 8px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.2);
        font-family: Arial;
        font-size: 13px;
        z-index: 1000;
        min-width: 200px;
    ">
        <b style="font-size:14px;">Tipos de Atendimento</b>
        <hr style="margin: 8px 0;">
        {legend_items}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # ── Salva o arquivo ──
    m.save(output_path)
    print(f"✅ Mapa salvo em: {os.path.abspath(output_path)}")

    if open_browser:
        webbrowser.open(f"file://{os.path.abspath(output_path)}")

    return output_path


def _folium_to_hex(color_name: str) -> str:
    """Converte nome de cor folium para hex (para a legenda)."""
    color_table = {
        "red":    "#d9534f",
        "orange": "#f0ad4e",
        "blue":   "#337ab7",
        "green":  "#5cb85c",
        "black":  "#2c3e50",
        "gray":   "#888888",
    }
    return color_table.get(color_name, "#888888")


# ──────────────────────────────────────────────
# Execução direta para teste
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from data.synthetic_data import ATTENDANCE_POINTS
    from vrp.genetic_algorithm import run_genetic_algorithm

    print("Rodando GA para gerar rota otimizada...")
    best_route, best_fitness, history = run_genetic_algorithm(
        attendance_points=ATTENDANCE_POINTS,
        population_size=100,
        n_generations=200,
        mutation_prob=0.3,
        verbose=True
    )

    print(f"\nFitness final: {best_fitness:.2f}")
    print("Gerando mapa...")

    create_route_map(
        route=best_route,
        output_path="route_map.html",
        open_browser=True
    )