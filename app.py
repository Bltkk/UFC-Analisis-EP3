import os
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State


app = Dash(__name__)
app.title = "UFC Fighters Dashboard"

WEIGHT_BAND_ORDER = ["<115", "115-125", "125-135", "135-145", "145-155", "155-170", "170-185", "185-205", ">205"]

# Carga del dataframe ya limpiado desde el notebook.
# Si existe el archivo exportado, se usa ese; si no, se cae al CSV original.
cleaned_path = "ufc_fighters_stats_cleaned.csv"
if os.path.exists(cleaned_path):
    df = pd.read_csv(cleaned_path)
else:
    df = pd.read_csv("ufc_fighters_stats_merged.csv")
    null_ratio = df.isna().mean()
    columns_to_drop = [col for col, ratio in null_ratio.items() if ratio > 0.85]
    df = df.drop(columns=columns_to_drop)
    df = df[df["weight"].between(90, 300)].copy()
    df["stance"] = df["stance"].fillna("Other")
    df["stance"] = df["stance"].replace({"Open Stance": "Other", "Sideways": "Other"})
    df["stance"] = df["stance"].apply(lambda x: x if x in ["Orthodox", "Southpaw", "Switch", "Other"] else "Other")
    df["total_fights"] = df["wins"] + df["losses"] + df["draws"]
    df["win_rate"] = df["wins"] / df["total_fights"].replace(0, pd.NA)
    df["weight_band"] = pd.cut(
        df["weight"],
        bins=[0, 115, 125, 135, 145, 155, 170, 185, 205, 300],
        labels=WEIGHT_BAND_ORDER,
        include_lowest=True,
    )
    # Nombre completo para el hover (evita mostrar solo el nombre de pila)
    df["name"] = (df["first"].fillna("") + " " + df["last"].fillna("")).str.strip()

prepared_df = df.copy()
# Guardamos weight_band como string ordenable manualmente, ya que dcc.Store
# no preserva el orden de una columna categórica al convertirla a dict/JSON.
prepared_df["weight_band"] = prepared_df["weight_band"].astype(str)

stance_options = ["Todos"] + sorted(prepared_df["stance"].dropna().unique().tolist())

app.layout = html.Div(
    style={"padding": "24px", "fontFamily": "Arial, sans-serif", "backgroundColor": "#f7f9fc"},
    children=[
        html.H2("UFC Fighters Dashboard", style={"marginBottom": "8px"}),
        html.P(
            "Explora el rendimiento de los peleadores filtrando por postura y experiencia.",
            style={"marginBottom": "20px", "color": "#4b5563"},
        ),
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px", "marginBottom": "20px"},
            children=[
                html.Div(
                    style={"backgroundColor": "white", "padding": "16px", "borderRadius": "10px", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                    children=[
                        html.Label("Stance", style={"fontWeight": "bold"}),
                        dcc.Dropdown(
                            id="stance-dropdown",
                            options=[{"label": option, "value": option} for option in stance_options],
                            value="Todos",
                            clearable=False,
                        ),
                    ],
                ),
                html.Div(
                    style={"backgroundColor": "white", "padding": "16px", "borderRadius": "10px", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                    children=[
                        html.Label("Mínimo de peleas", style={"fontWeight": "bold"}),
                        dcc.Slider(
                            id="min-fights-slider",
                            min=0,
                            max=30,
                            step=1,
                            value=0,
                            marks={0: "0", 5: "5", 10: "10", 15: "15", 20: "20", 25: "25", 30: "30"},
                        ),
                    ],
                ),
            ],
        ),
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "repeat(4, minmax(0, 1fr))", "gap": "16px", "marginBottom": "20px"},
            children=[
                html.Div(
                    id="fighter-count-card",
                    style={"background": "linear-gradient(135deg, #2563eb, #1d4ed8)", "color": "white", "padding": "20px", "borderRadius": "12px", "boxShadow": "0 6px 16px rgba(37, 99, 235, 0.22)"},
                ),
                html.Div(
                    id="avg-win-rate-card",
                    style={"background": "linear-gradient(135deg, #059669, #047857)", "color": "white", "padding": "20px", "borderRadius": "12px", "boxShadow": "0 6px 16px rgba(5, 150, 105, 0.22)"},
                ),
                html.Div(
                    id="strikes-landed-card",
                    style={"background": "linear-gradient(135deg, #7c3aed, #6d28d9)", "color": "white", "padding": "20px", "borderRadius": "12px", "boxShadow": "0 6px 16px rgba(124, 58, 237, 0.22)"},
                ),
                html.Div(
                    id="strikes-absorbed-card",
                    style={"background": "linear-gradient(135deg, #dc2626, #b91c1c)", "color": "white", "padding": "20px", "borderRadius": "12px", "boxShadow": "0 6px 16px rgba(220, 38, 38, 0.22)"},
                ),
            ],
        ),
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"},
            children=[
                dcc.Graph(id="win-rate-chart", config={"displayModeBar": False}),
                dcc.Graph(id="reach-chart", config={"displayModeBar": False}),
            ],
        ),
        html.Div(
            style={"marginTop": "16px", "backgroundColor": "white", "padding": "12px", "borderRadius": "10px"},
            children=[dcc.Graph(id="strike-scatter", config={"displayModeBar": False})],
        ),
        html.Div(
            style={"marginTop": "16px", "backgroundColor": "white", "padding": "12px", "borderRadius": "10px"},
            children=[dcc.Graph(id="strike-absorb-scatter", config={"displayModeBar": False})],
        ),
        dcc.Store(id="df-store", data=prepared_df.to_dict("records")),
    ],
)


# Callback principal para actualizar las tarjetas KPI y los cuatro gráficos con los filtros.
@app.callback(
    [
        Output("fighter-count-card", "children"),
        Output("avg-win-rate-card", "children"),
        Output("strikes-landed-card", "children"),
        Output("strikes-absorbed-card", "children"),
        Output("win-rate-chart", "figure"),
        Output("reach-chart", "figure"),
        Output("strike-scatter", "figure"),
        Output("strike-absorb-scatter", "figure"),
    ],
    [
        Input("stance-dropdown", "value"),
        Input("min-fights-slider", "value"),
    ],
    [State("df-store", "data")],
)
def update_dashboard(selected_stance, min_fights, df_store):
    df_filtered = pd.DataFrame(df_store)

    if selected_stance != "Todos":
        df_filtered = df_filtered[df_filtered["stance"] == selected_stance]

    df_filtered = df_filtered[df_filtered["total_fights"] >= min_fights]

    total_fighters = len(df_filtered)
    avg_win_rate = df_filtered["win_rate"].mean()
    avg_strikes_landed = df_filtered["str_landed_per_min"].mean()
    avg_strikes_absorbed = df_filtered["str_absorbed_per_min"].mean()

    fighter_count_card = [
        html.H4("Peleadores filtrados", style={"marginBottom": "6px", "fontSize": "16px"}),
        html.H2(f"{total_fighters}", style={"margin": "0", "fontSize": "28px"}),
        html.P("Total de registros activos", style={"marginTop": "8px", "opacity": "0.9", "fontSize": "13px"}),
    ]

    win_rate_card = [
        html.H4("Win rate promedio", style={"marginBottom": "6px", "fontSize": "16px"}),
        html.H2(f"{avg_win_rate * 100:.1f}%", style={"margin": "0", "fontSize": "28px"}),
        html.P("Promedio de victorias", style={"marginTop": "8px", "opacity": "0.9", "fontSize": "13px"}),
    ]

    strikes_landed_card = [
        html.H4("Golpes conectados/min", style={"marginBottom": "6px", "fontSize": "16px"}),
        html.H2(f"{avg_strikes_landed:.2f}", style={"margin": "0", "fontSize": "28px"}),
        html.P("Volumen promedio de golpeo", style={"marginTop": "8px", "opacity": "0.9", "fontSize": "13px"}),
    ]

    strikes_absorbed_card = [
        html.H4("Golpes absorbidos/min", style={"marginBottom": "6px", "fontSize": "16px"}),
        html.H2(f"{avg_strikes_absorbed:.2f}", style={"margin": "0", "fontSize": "28px"}),
        html.P("Promedio de impacto recibido", style={"marginTop": "8px", "opacity": "0.9", "fontSize": "13px"}),
    ]

    # Gráfico de barras: win rate promedio por stance.
    if not df_filtered.empty:
        bar_df = (
            df_filtered.groupby("stance", dropna=False)["win_rate"]
            .mean()
            .reset_index()
            .sort_values("win_rate", ascending=False)
        )
        bar_df["win_rate_pct"] = (bar_df["win_rate"] * 100).round(1)
        win_rate_fig = px.bar(
            bar_df,
            x="stance",
            y="win_rate_pct",
            color="stance",
            text="win_rate_pct",
            title="Tasa de victorias promedio por stance",
            labels={"stance": "Stance", "win_rate_pct": "Win rate (%)"},
        )
    else:
        win_rate_fig = px.bar(title="Tasa de victorias promedio por stance")
        win_rate_fig.add_annotation(text="No hay datos para los filtros seleccionados", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)

    # Gráfico de línea: alcance promedio por rango de peso.
    if not df_filtered.empty:
        reach_df = (
            df_filtered.dropna(subset=["reach", "weight_band"])
            .groupby("weight_band", dropna=False)["reach"]
            .mean()
            .reset_index()
        )
        reach_df["reach_cm"] = reach_df["reach"].round(1)

        # Fix: weight_band viaja como string por el dcc.Store, así que perdió su
        # orden categórico. El groupby lo deja en orden alfabético ("<115" y
        # ">205" quedan al final), y aunque el eje se vea bien, la LÍNEA se sigue
        # dibujando en ese orden alfabético, generando un segmento que "vuelve
        # atrás" (se ve como una segunda línea). Por eso ordenamos las filas
        # explícitamente antes de graficar, no solo el eje.
        reach_df["weight_band"] = pd.Categorical(
            reach_df["weight_band"], categories=WEIGHT_BAND_ORDER, ordered=True
        )
        reach_df = reach_df.sort_values("weight_band")

        reach_fig = px.line(
            reach_df,
            x="weight_band",
            y="reach_cm",
            markers=True,
            title="Alcance promedio por rango de peso",
            labels={"weight_band": "Rango de peso", "reach_cm": "Alcance promedio (cm)"},
        )
        reach_fig.update_xaxes(
            categoryorder="array",
            categoryarray=WEIGHT_BAND_ORDER,
        )
    else:
        reach_fig = px.line(title="Alcance promedio por rango de peso")
        reach_fig.add_annotation(text="No hay datos para los filtros seleccionados", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)

    # Gráfico de dispersión: volumen de golpeo vs precisión, coloreado por stance.
    if not df_filtered.empty:
        scatter_df = df_filtered.dropna(subset=["str_landed_per_min", "striking_accuracy_pct", "stance"])
        scatter_fig = px.scatter(
            scatter_df,
            x="str_landed_per_min",
            y="striking_accuracy_pct",
            color="stance",
            size="total_fights",
            hover_name="name",
            hover_data={"total_fights": True, "win_rate": True},
            title="Volumen de golpeo vs precisión",
            labels={
                "str_landed_per_min": "Golpes conectados por minuto",
                "striking_accuracy_pct": "Precisión de golpeo (%)",
                "stance": "Stance",
            },
            render_mode="svg",
        )
    else:
        scatter_fig = px.scatter(title="Volumen de golpeo vs precisión")
        scatter_fig.add_annotation(text="No hay datos para los filtros seleccionados", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)

    # Gráfico de dispersión: golpes conectados vs absorbidos por minuto.
    if not df_filtered.empty:
        absorb_df = df_filtered.dropna(subset=["str_landed_per_min", "str_absorbed_per_min", "stance"])
        absorb_fig = px.scatter(
            absorb_df,
            x="str_absorbed_per_min",
            y="str_landed_per_min",
            color="stance",
            size="total_fights",
            hover_name="name",
            hover_data={"total_fights": True, "win_rate": True},
            title="Golpes conectados vs absorbidos por minuto",
            labels={
                "str_absorbed_per_min": "Golpes absorbidos por minuto",
                "str_landed_per_min": "Golpes conectados por minuto",
                "stance": "Stance",
            },
            render_mode="svg",
        )
    else:
        absorb_fig = px.scatter(title="Golpes conectados vs absorbidos por minuto")
        absorb_fig.add_annotation(text="No hay datos para los filtros seleccionados", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)

    return (
        fighter_count_card,
        win_rate_card,
        strikes_landed_card,
        strikes_absorbed_card,
        win_rate_fig,
        reach_fig,
        scatter_fig,
        absorb_fig,
    )


if __name__ == "__main__":
    app.run(debug=True)