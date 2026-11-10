"""
graphiques.py - Tous les graphiques de l'interface (bibliothèque Plotly).

    carte_instance, carte_tournees, carte_reelle : les cartes (onglet Tournées)
    gantt                                        : le planning de chaque camion
    suivi                                        : les camions animés, en 3D ou en 2D
    convergence                                  : le meilleur coût au fil du temps (onglet Comparer)

Idée clé pour le suivi des camions : pour chaque camion on construit une liste
de "points clés" (heure, x, y) : départ du dépôt, arrivée chez chaque client,
fin de livraison, retour au dépôt. Entre deux points, on interpole en ligne
droite. On connaît ainsi la position de chaque camion à n'importe quelle heure.
"""

import numpy as np
import plotly.graph_objects as go

# Palette validée (8 couleurs distinguables, y compris pour les daltoniens),
# toujours utilisée dans le même ordre.
COULEURS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
            "#e87ba4", "#008300", "#6250d6", "#e34948"]
COULEUR_DEPOT = "#1f3864"
GRIS = "#9a9993"
COULEUR_SOL = "#eef1ea"
# Grandes villes écrites sur le suivi, pour se repérer (instances de Lorraine)
VILLES_REPERES = {"Metz", "Nancy", "Thionville", "Forbach", "Toul", "Sarrebourg", "Lunéville", "Longwy"}
# Couleur fixe par algorithme (une entité garde toujours sa couleur)
COULEUR_ALGO = {"Recherche tabou": COULEURS[0], "GRASP": COULEURS[1],
                "PLNE exacte (≤ 15 clients)": COULEURS[6]}


def couleur(k):
    """Couleur du camion numéro k (on recommence la palette au-delà de 8)."""
    return COULEURS[(k - 1) % len(COULEURS)]


def couleur_algo(nom):
    return COULEUR_ALGO.get(nom, COULEURS[3])


def _mise_en_page(fig, titre, hauteur=550):
    fig.update_layout(title=titre, height=hauteur, template="plotly_white",
                      margin=dict(l=10, r=10, t=50, b=10), legend_title_text="")
    return fig


def points_cles(xy, tournee):
    """Tableau (heure, x, y) du trajet d'un camion. xy : position de chaque lieu."""
    pts = [(tournee["depart"], *xy[0])]
    for a in tournee["arrets"]:
        c = a["client"]
        pts.append((a["arrivee"], *xy[c]))      # arrivée (puis attente éventuelle)
        pts.append((a["fin"], *xy[c]))          # fin de la livraison
    pts.append((tournee["retour"], *xy[0]))
    return np.array(pts)


def en_arcs(points, relief, nb=8):
    """Ajoute une hauteur z à chaque point : (heure, x, y) devient (heure, x, y, z).

    Chaque déplacement devient un arc (comme une ligne aérienne sur une carte) :
    plus le trajet est long, plus l'arc monte. Avec relief = 0, tout reste à plat.
    """
    lignes = [(*points[0], 0.0)]
    for (t0, x0, y0), (t1, x1, y1) in zip(points, points[1:]):
        longueur = np.hypot(x1 - x0, y1 - y0)
        etapes = np.linspace(0, 1, nb + 1)[1:] if relief and longueur else [1.0]
        for s in etapes:
            z = relief * longueur * np.sin(np.pi * s)
            lignes.append((t0 + s * (t1 - t0), x0 + s * (x1 - x0), y0 + s * (y1 - y0), z))
    return np.array(lignes)


def position(points, t):
    """Position (x, y, z) du camion à l'heure t (interpolation linéaire)."""
    return [np.interp(t, points[:, 0], points[:, colonne]) for colonne in (1, 2, 3)]


# ---------------------------------------------------------------------------
# Carte de l'instance et carte des tournées
# ---------------------------------------------------------------------------
def _trace_depot(inst):
    x, y = inst["coords"][0]
    return go.Scatter(x=[x], y=[y], mode="markers", name="Dépôt",
                      marker=dict(symbol="square", size=16, color=COULEUR_DEPOT,
                                  line=dict(color="white", width=2)),
                      hovertemplate="Dépôt<extra></extra>")


def nom_lieu(inst, i):
    """Nom de la ville (instances de Lorraine) ou numéro du client."""
    if "villes" in inst:
        return inst["villes"][i]
    return "Dépôt" if i == 0 else f"Client {i}"


def _texte_client(inst, c):
    texte = f"{nom_lieu(inst, c)}<br>Demande : {inst['demande'][c]:.0f}"
    if inst["fenetres"] is not None:
        a, b = inst["fenetres"][c]
        texte += f"<br>Fenêtre : [{a:.0f} ; {b:.0f}]"
    return texte


def carte_instance(inst):
    """Clients colorés selon l'ouverture de leur fenêtre (ou leur demande)."""
    xy = inst["coords"][1:]
    if inst["fenetres"] is not None:
        valeur, titre = inst["fenetres"][1:, 0], "Ouverture<br>fenêtre"
    else:
        valeur, titre = inst["demande"][1:], "Demande"
    fig = go.Figure()
    fig.add_trace(go.Scattergl(
        x=xy[:, 0], y=xy[:, 1], mode="markers", name="Clients",
        marker=dict(size=7 if inst["n"] < 500 else 4, color=valeur, colorscale="Blues",
                    showscale=True, colorbar=dict(title=titre), line=dict(width=0.5, color=GRIS)),
        text=[_texte_client(inst, c) for c in range(1, inst["n"] + 1)],
        hovertemplate="%{text}<extra></extra>"))
    fig.add_trace(_trace_depot(inst))
    fig.update_yaxes(scaleanchor="x")
    _mise_en_page(fig, f"{inst['nom']} : {inst['n']} clients")
    # La barre de couleur occupe le côté droit : la légende va au-dessus du graphique.
    fig.update_layout(legend=dict(orientation="h", x=1, xanchor="right", y=1.02, yanchor="bottom"))
    return fig


def carte_tournees(inst, ev, titre=""):
    """Une couleur par camion, flèche implicite par l'ordre de la ligne."""
    xy = inst["coords"]
    fig = go.Figure()
    for t in ev["tournees"]:
        chemin = [0] + t["clients"] + [0]
        textes = ["Dépôt"] + [
            _texte_client(inst, a["client"]) + f"<br>Arrivée : {a['arrivee']:.1f}"
            f"<br>Attente : {a['attente']:.1f}<br>Début livraison : {a['debut']:.1f}"
            for a in t["arrets"]] + ["Retour dépôt"]
        fig.add_trace(go.Scatter(
            x=xy[chemin, 0], y=xy[chemin, 1], mode="lines+markers",
            name=f"Camion {t['numero']} ({t['charge']:.0f}/{inst['capacite']:.0f})",
            line=dict(color=couleur(t["numero"]), width=2),
            marker=dict(size=7 if inst["n"] < 300 else 3),
            text=textes, hovertemplate=f"Camion {t['numero']}<br>%{{text}}<extra></extra>"))
    fig.add_trace(_trace_depot(inst))
    fig.update_yaxes(scaleanchor="x")
    fig.update_layout(showlegend=len(ev["tournees"]) <= 30)
    return _mise_en_page(fig, titre or f"Tournées : {ev['nb_vehicules']} camions, "
                                       f"distance {ev['distance']:.1f}")


def carte_reelle(inst, ev=None):
    """Vraie carte (OpenStreetMap) pour les instances de Lorraine.
    Les traits relient les villes à vol d'oiseau (pas le tracé exact des routes)."""
    lat, lon = inst["latlon"][:, 0], inst["latlon"][:, 1]
    fig = go.Figure()
    if ev is None:                                    # juste les clients
        fig.add_trace(go.Scattermap(
            lat=lat[1:], lon=lon[1:], mode="markers", name="Clients",
            marker=dict(size=10, color=COULEURS[0]),
            hovertext=[_texte_client(inst, c) for c in range(1, inst["n"] + 1)],
            hoverinfo="text"))
    else:
        for t in ev["tournees"]:
            chemin = [0] + t["clients"] + [0]
            fig.add_trace(go.Scattermap(
                lat=lat[chemin], lon=lon[chemin], mode="lines+markers",
                name=f"Camion {t['numero']} ({t['charge']:.0f}/{inst['capacite']:.0f})",
                line=dict(width=3, color=couleur(t["numero"])), marker=dict(size=9),
                hovertext=[nom_lieu(inst, i) for i in chemin], hoverinfo="text"))
    fig.add_trace(go.Scattermap(lat=[lat[0]], lon=[lon[0]], mode="markers", name="Entrepôt",
                                hovertext=[f"Entrepôt {inst['villes'][0]}"], hoverinfo="text",
                                marker=dict(size=18, color=COULEUR_DEPOT)))
    fig.update_layout(map=dict(style="open-street-map", zoom=8.2,
                               center=dict(lat=lat.mean(), lon=lon.mean())))
    return _mise_en_page(fig, "Carte de la tournée" if ev else "Clients à livrer", hauteur=650)


# ---------------------------------------------------------------------------
# Planning des camions (diagramme de Gantt)
# ---------------------------------------------------------------------------
def gantt(ev, max_camions=40):
    """Pour chaque camion : trajet, attente (arrivé trop tôt) et livraison."""
    morceaux = {"Trajet": ([], [], []), "Attente": ([], [], []), "Livraison": ([], [], [])}
    for t in ev["tournees"][:max_camions]:
        nom, heure = f"Camion {t['numero']}", t["depart"]
        for a in t["arrets"]:
            for type_, debut, fin in [("Trajet", heure, a["arrivee"]),
                                      ("Attente", a["arrivee"], a["debut"]),
                                      ("Livraison", a["debut"], a["fin"])]:
                if fin - debut > 1e-9:
                    morceaux[type_][0].append(nom)
                    morceaux[type_][1].append(debut)
                    morceaux[type_][2].append(fin - debut)
            heure = a["fin"]
        morceaux["Trajet"][0].append(nom)
        morceaux["Trajet"][1].append(heure)
        morceaux["Trajet"][2].append(t["retour"] - heure)
    fig = go.Figure()
    for (type_, (y, base, duree)), coul in zip(morceaux.items(), [GRIS, COULEURS[3], COULEURS[2]]):
        fig.add_trace(go.Bar(y=y, x=duree, base=base, orientation="h", name=type_,
                             marker=dict(color=coul, line=dict(color="white", width=1)),
                             hovertemplate="%{y}<br>" + type_ + " de %{base:.1f} "
                                           "pendant %{x:.1f}<extra></extra>"))
    nb = min(len(ev["tournees"]), max_camions)
    fig.update_layout(barmode="overlay", xaxis_title="Temps", yaxis=dict(autorange="reversed"))
    return _mise_en_page(fig, "Planning des camions", hauteur=max(300, 22 * nb + 120))


# ---------------------------------------------------------------------------
# Suivi animé des camions, en 3D ou en 2D
# ---------------------------------------------------------------------------
def suivi(inst, ev, vue="3D", nb_images=60, max_camions=30):
    """Anime les camions sur un plan fixe : leur trajet se dessine au fur et à mesure.

    3D : le plan est posé comme un plateau, chaque trajet est un arc au-dessus du sol.
    2D : le même plan vu de dessus.
    """
    en_3d = vue == "3D"
    xy = inst["coords"]
    tournees = ev["tournees"][:max_camions]
    trajets = [en_arcs(points_cles(xy, t), relief=0.18 if en_3d else 0) for t in tournees]
    debut = min(t["depart"] for t in tournees)
    fin = max(t["retour"] for t in tournees)

    # Les limites du plan sont fixées une fois pour toutes : l'image ne bouge pas à la lecture.
    (x_min, y_min), (x_max, y_max) = xy.min(axis=0), xy.max(axis=0)
    marge = 0.06 * max(x_max - x_min, y_max - y_min)
    x_min, x_max, y_min, y_max = x_min - marge, x_max + marge, y_min - marge, y_max + marge
    x0, y0 = xy[0]
    haut_entrepot = 2 * marge

    def trace(x, y, z, **reglages):
        """Le même tracé en 3D et en 2D (la hauteur z ne sert qu'en 3D)."""
        return go.Scatter3d(x=x, y=y, z=z, **reglages) if en_3d else go.Scatter(x=x, y=y, **reglages)

    fig = go.Figure()
    if en_3d:                                          # le plateau : deux triangles au sol
        fig.add_trace(go.Mesh3d(x=[x_min, x_max, x_max, x_min], y=[y_min, y_min, y_max, y_max],
                                z=[0, 0, 0, 0], i=[0, 0], j=[1, 2], k=[2, 3],
                                color=COULEUR_SOL, hoverinfo="skip"))

    # 1) La tournée complète de chaque camion en couleur pâle, et ses clients au sol
    for t, p in zip(tournees, trajets):
        k, clients = t["numero"], t["clients"]
        fig.add_trace(trace(p[:, 1], p[:, 2], p[:, 3], mode="lines", name=f"Camion {k}",
                            legendgroup=str(k), opacity=0.45, hoverinfo="skip",
                            line=dict(color=couleur(k), width=3)))
        fig.add_trace(trace(xy[clients, 0], xy[clients, 1], [0] * len(clients), mode="markers",
                            legendgroup=str(k), showlegend=False,
                            marker=dict(color=couleur(k), size=4 if en_3d else 7),
                            text=[nom_lieu(inst, c) for c in clients],
                            hovertemplate=f"Camion {k}<br>%{{text}}<extra></extra>"))

    # 2) L'entrepôt : un mât en 3D, un point en 2D
    fig.add_trace(trace([x0, x0], [y0, y0], [0, haut_entrepot], mode="lines+markers", name="Entrepôt",
                        line=dict(color=COULEUR_DEPOT, width=8),
                        marker=dict(color=COULEUR_DEPOT, size=6 if en_3d else 14),
                        hovertemplate="Entrepôt<extra></extra>"))

    # 3) Ce qui bouge : le trajet déjà parcouru et le camion (2 tracés par camion)
    numeros = [t["numero"] for t in tournees]

    def image(heure):
        """Les tracés animés à une heure donnée (position seulement)."""
        traces = []
        for t, p in zip(tournees, trajets):
            passes = p[p[:, 0] <= heure]               # les points déjà atteints
            x, y, z = position(p, heure)               # la position actuelle
            traces += [trace([*passes[:, 1], x], [*passes[:, 2], y], [*passes[:, 3], z]),
                       trace([x], [y], [z])]
        return traces

    premier = len(fig.data)
    for numero_trace, depart in enumerate(image(debut)):
        k = numeros[numero_trace // 2]
        if numero_trace % 2 == 0:                      # trajet parcouru : trait épais
            depart.update(mode="lines", line=dict(color=couleur(k), width=7 if en_3d else 4),
                          hoverinfo="skip")
        else:                                          # le camion : point + numéro
            depart.update(mode="markers+text", marker=dict(color=couleur(k), size=7 if en_3d else 12),
                          text=[str(k)], textposition="top center", hoverinfo="skip")
        depart.update(legendgroup=str(k), showlegend=False)
        fig.add_trace(depart)

    heures = np.linspace(debut, fin, nb_images)
    animes = list(range(premier, len(fig.data)))
    fig.frames = [go.Frame(data=image(h), traces=animes, name=str(i))
                  for i, h in enumerate(heures)]

    # Les grandes villes pour se repérer (Lorraine), ajoutées en dernier pour rester au-dessus
    reperes = [i for i, ville in enumerate(inst.get("villes", [])) if ville in VILLES_REPERES]
    if reperes:
        fig.add_trace(trace(xy[reperes, 0], xy[reperes, 1], [marge / 2] * len(reperes), mode="text",
                            text=[inst["villes"][i] for i in reperes], textposition="middle right",
                            textfont=dict(color="#1f2933", size=13), hoverinfo="skip", showlegend=False))

    # 4) Mise en page propre à chaque vue
    if en_3d:
        z_max = max(haut_entrepot, *(p[:, 3].max() for p in trajets))
        fig.update_layout(scene=dict(                  # axes masqués : il ne reste que le plateau
            xaxis=dict(visible=False, range=[x_min, x_max]),
            yaxis=dict(visible=False, range=[y_min, y_max]),
            zaxis=dict(visible=False, range=[0, z_max * 1.05]),
            aspectmode="data", camera=dict(eye=dict(x=0, y=-2, z=2), center=dict(x=0, y=0, z=-0.3))))
    else:
        fig.update_xaxes(visible=False, range=[x_min, x_max])
        fig.update_yaxes(visible=False, range=[y_min, y_max], scaleanchor="x")
        fig.update_layout(plot_bgcolor=COULEUR_SOL)
    fig.update_layout(showlegend=len(tournees) <= 25, uirevision="garder")   # garde le zoom choisi
    _mise_en_page(fig, "", hauteur=700)
    _ajouter_lecture(fig, [_heure(inst, h) for h in heures], redessiner=en_3d)
    return fig


def _heure(inst, t):
    """Heure lisible pour la Lorraine (540 -> 9h00), sinon l'unité de temps de l'instance."""
    return f"{int(t) // 60}h{int(t) % 60:02d}" if "villes" in inst else f"{t:.0f}"


def _ajouter_lecture(fig, etiquettes, redessiner):
    """Boutons Lecture / Pause et curseur de temps.
    redessiner : obligatoire en 3D ; inutile en 2D, où seuls les camions sont mis à jour."""
    reglage = dict(frame=dict(duration=120, redraw=redessiner), transition=dict(duration=0),
                   fromcurrent=True, mode="immediate")
    fig.update_layout(
        margin=dict(b=110),
        updatemenus=[dict(type="buttons", direction="left", x=0, y=0, xanchor="left",
                          yanchor="top", pad=dict(t=60, r=10),
                          buttons=[dict(label="▶ Lecture", method="animate", args=[None, reglage]),
                                   dict(label="⏸ Pause", method="animate",
                                        args=[[None], dict(frame=dict(duration=0, redraw=False),
                                                           mode="immediate")])])],
        sliders=[dict(x=0.2, len=0.8, y=0, yanchor="top", pad=dict(t=40),
                      ticklen=0, minorticklen=0, font=dict(color="rgba(0,0,0,0)"),   # graduations masquées
                      currentvalue=dict(prefix="Heure : ", font=dict(color="#52514e")),
                      steps=[dict(label=etiquette, method="animate",
                                  args=[[str(k)], dict(frame=dict(duration=0, redraw=redessiner),
                                                       mode="immediate")])
                             for k, etiquette in enumerate(etiquettes)])])


# ---------------------------------------------------------------------------
# Courbe de convergence (si l'algorithme appelle suivi(iteration, cout))
# ---------------------------------------------------------------------------
def convergence(historiques, bks=None):
    """historiques : {nom_algo: [(temps, iteration, meilleur_cout), ...]}"""
    fig = go.Figure()
    for nom, h in historiques.items():
        if h:
            fig.add_trace(go.Scatter(x=[p[0] for p in h], y=[p[2] for p in h], name=nom,
                                     mode="lines+markers",       # un point = une amélioration
                                     line=dict(shape="hv", width=2, color=couleur_algo(nom))))
    if bks:
        fig.add_hline(y=bks, line_dash="dash", line_color=GRIS,
                      annotation_text="Meilleure solution connue")
    fig.update_layout(xaxis_title="Temps de calcul (s)", yaxis_title="Meilleur coût trouvé",
                      hovermode="x unified")
    return _mise_en_page(fig, "Convergence", hauteur=400)
