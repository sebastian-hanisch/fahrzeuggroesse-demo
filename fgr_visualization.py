"""Plotly-Abbildungen. Alle Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht am Diagramm hängen bleiben."""

import plotly.graph_objects as go

import fgr_constants as C
import fgr_model as M
import fgr_results as R

CELL_COLORS = {"front": C.COLOR_FRONT, "zwischen": C.COLOR_ZWISCHEN, "keine": C.COLOR_KEINE}


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height=360):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.25), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def build_map(inst, routes, title=""):
    """Depot (Stern), Kunden (Größe = Menge), Touren in eigenen Farben. Gleiches Seitenverhältnis über `scaleanchor` mit automatischem Bereich
    (zwei unsichtbare Eckmarker erzwingen den Rand)."""
    fig = go.Figure()
    for ri, r in enumerate(routes):
        if not r:
            continue
        pts = [0] + list(r) + [0]
        color = C.COLOR_ROUTES[ri % len(C.COLOR_ROUTES)]
        load = sum(inst.dem[c] for c in r)
        fig.add_trace(go.Scatter(x=[inst.xy[p][0] for p in pts], y=[inst.xy[p][1] for p in pts], mode="lines", line=dict(color=color, width=2.5),
                                 name=f"Tour {ri + 1} (Last {load} von {inst.Q})", hoverinfo="skip"))
    max_dem = max(inst.dem[1:]) if inst.n else 1
    ids = list(range(1, inst.n + 1))
    fig.add_trace(go.Scatter(
        x=[inst.xy[c][0] for c in ids], y=[inst.xy[c][1] for c in ids], mode="markers", name="Kunde", showlegend=False,
        marker=dict(color="#4a5568", size=[6 + 9 * inst.dem[c] / max_dem for c in ids], line=dict(color="white", width=1)),
        text=[f"Kunde {c}: Menge {inst.dem[c]}" for c in ids], hovertemplate="%{text}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[inst.xy[0][0]], y=[inst.xy[0][1]], mode="markers", name="Depot", marker=dict(color=C.COLOR_DEPOT, size=14, symbol="star"),
                             hovertemplate="Depot<extra></extra>"))
    fig.add_trace(go.Scatter(x=[-2, 102], y=[-2, 102], mode="markers", marker=dict(opacity=0, size=1), showlegend=False, hoverinfo="skip"))
    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False)
    fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False, scaleanchor="x", scaleratio=1)
    if title:
        fig.add_annotation(text=title, x=0.5, y=1.0, xref="paper", yref="paper", yanchor="bottom", showarrow=False, font=dict(size=12))
    fig = _base(fig, 330)
    fig.update_layout(margin=dict(l=10, r=10, t=28 if title else 10, b=10), showlegend=False)
    return fig


def build_cost_lines(sols, fix):
    """Gesamtkosten f · V + D über den Fixkosten f für die drei Lösungen der Instanz; senkrechte Linien bei dem gewählten f und beim Kipppunkt."""
    fig = go.Figure()
    xs = [0, C.FIX_MAX]
    colors = {"f0": C.COLOR_F0, "sel": C.COLOR_SEL, "f400": C.COLOR_F400}
    seen = set()
    for s in sols:
        sig = (s.vehicles, s.dist)
        if sig in seen:
            continue
        seen.add(sig)
        ys = [f * s.vehicles + s.dist / M.SCALE for f in xs]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=f"{s.vehicles} Fahrzeuge, Distanz {s.dist / M.SCALE:.1f}".replace(".", ","), line=dict(color=colors[s.key], width=3),
                                 hovertemplate="f = %{x}: %{y:.1f}<extra></extra>"))
    fig.add_vline(x=fix, line=dict(color="#555", dash="dot", width=1), annotation_text=f"gewählt f = {fix}", annotation_position="top")
    fig.update_xaxes(title_text="Fixkosten je Fahrzeug f (Längeneinheiten)", range=[0, C.FIX_MAX])
    fig.update_yaxes(title_text="Gesamtkosten f · V + D", rangemode="tozero")
    return _base(fig, 330)


def build_cell_map(current=None):
    """Zellenkarte: 32 Zellen (Zeilen: Reserve und Ladungen, Spalten: Kunden und Depot), Farbe = Klasse aus ΔV, Text = ΔV. `current` = (n, depot, k, s) wird umrandet."""
    cols = [(n, d) for n in C.N_OPTIONS for d in C.DEPOT_OPTIONS]
    rows = [(s, k) for s in C.RESERVE_OPTIONS for k in C.K_OPTIONS]
    col_labels = [f"{n} Kunden · {'Rand' if d == 'rand' else 'Mitte'}" for n, d in cols]
    row_labels = [f"{R.num(100 * s, 0)} % Reserve · {k} Ladungen" for s, k in rows]
    z, text = [], []
    for s, k in rows:
        zr, tr = [], []
        for n, d in cols:
            c = R.cell_of(n, d, k, s)
            zr.append({"keine": 0, "zwischen": 1, "front": 2}[c["klass"]])
            tr.append(R.num(c["dV"], 2))
        z.append(zr)
        text.append(tr)
    fig = go.Figure(go.Heatmap(
        z=z, x=col_labels, y=row_labels, text=text, texttemplate="%{text}", showscale=False, xgap=3, ygap=3,
        colorscale=[[0, C.COLOR_KEINE], [0.5, C.COLOR_ZWISCHEN], [1, C.COLOR_FRONT]], zmin=0, zmax=2,
        hovertemplate="%{y}, %{x}: ΔV %{text}<extra></extra>"))
    if current is not None:
        n, d, k, s = current
        xi, yi = cols.index((n, d)), rows.index((s, k))
        fig.add_shape(type="rect", x0=xi - 0.5, x1=xi + 0.5, y0=yi - 0.5, y1=yi + 0.5, line=dict(color="#111", width=3))
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def build_v_lines():
    """Mittlere Zahl Fahrzeuge über der unteren Schranke ⌈Σd / Q⌉ in Abhängigkeit von f, je Reserve (Instanzen mit 3 oder 5 Ladungen)."""
    fig = go.Figure()
    for s in C.RESERVE_OPTIONS:
        d = R.by_reserve(s)
        fig.add_trace(go.Scatter(x=[str(f) for f in R.load()["meta"]["fs"]], y=d["Vf_excess"], mode="lines+markers", line=dict(color=C.RESERVE_COLORS[s], width=3),
                                 name=f"{R.num(100 * s, 0)} % Reserve", hovertemplate="f = %{x}: %{y:.2f}<extra></extra>"))
    fig.update_xaxes(title_text="Fixkosten je Fahrzeug f (Längeneinheiten)")
    fig.update_yaxes(title_text="Fahrzeuge über der unteren Schranke", rangemode="tozero")
    return _base(fig, 330)


def build_fstar_bars():
    """Verteilung der ersten Fixkostenstufe mit weniger Fahrzeugen als bei f = 0 (Obergrenze des Kipppunkts) über die Instanzen, je Reserve (k in {3, 5}, je 200 Instanzen)."""
    fig = go.Figure()
    stufen = [str(f) for f in C.FIX_OPTIONS[1:]]
    for s in C.RESERVE_OPTIONS:
        d = R.by_reserve(s)
        total = {f: d["per_k"]["3"]["fstar_counts"][f] + d["per_k"]["5"]["fstar_counts"][f] for f in stufen}
        fig.add_trace(go.Bar(x=stufen, y=[total[f] for f in stufen], name=f"{R.num(100 * s, 0)} % Reserve", marker_color=C.RESERVE_COLORS[s],
                             hovertemplate="erste Stufe %{x}: %{y} Instanzen<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_xaxes(title_text="Erste Fixkostenstufe mit weniger Fahrzeugen (Obergrenze des Kipppunkts)")
    fig.update_yaxes(title_text="Instanzen (von je 200)")
    return _base(fig, 330)


def build_formula_curve(inst, a, b, points):
    """Formelkurve D̂(Q) über der Kapazität mit den gelösten Punkten (k, Q, D); Reserve 10 % bei den Punkten."""
    import fgr_formula as FO
    qs = [inst.Q * 0.5 + i * (inst.Q * 2.6) / 60 for i in range(61)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=qs, y=[FO.predicted_distance(inst, q, a, b) / M.SCALE for q in qs], mode="lines", name="Formel D̂(Q)", line=dict(color=C.COLOR_F0, width=3),
                             hovertemplate="Q = %{x:.0f}: %{y:.1f}<extra></extra>"))
    if points:
        fig.add_trace(go.Scatter(x=[p[1] for p in points], y=[p[2] / M.SCALE for p in points], mode="markers+text", name="gelöst (f = 0)",
                                 text=[f"k = {p[0]}" for p in points], textposition="top center", marker=dict(color=C.COLOR_F400, size=11),
                                 hovertemplate="Q = %{x}: %{y:.1f}<extra></extra>"))
    fig.update_xaxes(title_text="Kapazität Q")
    fig.update_yaxes(title_text="Gesamtdistanz D (Längeneinheiten)", rangemode="tozero")
    return _base(fig, 330)


def build_error_map():
    """Fehlerkarte der Formel: mittlerer Betrag der relativen Abweichung je Zelle (Reserve 10 %, f = 0), 16 Zellen."""
    cells = R.load()["formel"]["cells"]
    cols = [(n, d) for n in C.N_OPTIONS for d in C.DEPOT_OPTIONS]
    ks = sorted({c["k"] for c in cells})
    z, text = [], []
    for k in ks:
        zr, tr = [], []
        for n, d in cols:
            c = next(c for c in cells if (c["n"], c["depot"], c["k"]) == (n, d, k))
            zr.append(c["err_mean"])
            tr.append(R.num(c["err_mean"], 1))
        z.append(zr)
        text.append(tr)
    fig = go.Figure(go.Heatmap(z=z, x=[f"{n} Kunden · {'Rand' if d == 'rand' else 'Mitte'}" for n, d in cols], y=[f"{k} Ladungen" for k in ks], text=text, texttemplate="%{text} %",
                               showscale=False, xgap=3, ygap=3, colorscale=[[0, "#cfe6d8"], [0.5, "#f1dfa8"], [1, "#e9a38f"]], zmin=0, zmax=10,
                               hovertemplate="%{y}, %{x}: Fehler %{text} %<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=230, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def build_reserve_bars():
    """Anteil der Instanzen mit weniger Fahrzeugen bei f = 400 als bei f = 0 je Reserve und Ladungen (je 100 Instanzen)."""
    fig = go.Figure()
    for k, color in ((3, "#7fb0dc"), (5, "#2a6fb0")):
        ys = [100.0 * R.by_reserve(s)["per_k"][str(k)]["n_front_inst"] / R.by_reserve(s)["per_k"][str(k)]["m"] for s in C.RESERVE_OPTIONS]
        fig.add_trace(go.Bar(x=[f"{R.num(100 * s, 0)} %" for s in C.RESERVE_OPTIONS], y=ys, name=f"{k} Ladungen", marker_color=color,
                             text=[f"{R.num(y, 0)} %" for y in ys], textposition="outside", hovertemplate="%{x}: %{y:.0f} %<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_xaxes(title_text="Kapazitätsreserve")
    fig.update_yaxes(title_text="Instanzen mit weniger Fahrzeugen bei f = 400 (%)", range=[0, 100])
    return _base(fig, 330)

