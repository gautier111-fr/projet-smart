"""
app.py - L'interface : choisir une instance et une méthode, lancer, voir et suivre les tournées.
Lancement : streamlit run app.py   (ou double-clic sur lancer_interface.bat)
"""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from algorithmes.methodes import GRASP_TABOU, PLNE, lancer
from probleme.contraintes import PROFIL_TRAFIC_DEFAUT, evaluer, gap
from probleme.instances import charger_instance, exemple_livrable1, lister_instances

st.set_page_config(page_title="Tournées de livraison", page_icon="🚚", layout="wide")
st.title("🚚 Tournées de livraison")

# 1. Les choix, à gauche
chemins = {i["nom"]: i["chemin"] for i in lister_instances()}
nom = st.sidebar.selectbox("Instance", ["Exemple du livrable 1"] + list(chemins))
inst = charger_instance(chemins[nom]) if nom in chemins else exemple_livrable1()
if st.sidebar.toggle("Trafic selon l'heure"):
    inst["trafic"] = inst.get("profil_trafic", PROFIL_TRAFIC_DEFAUT)
methode = st.sidebar.radio("Méthode", [GRASP_TABOU] + ([PLNE] if inst["n"] <= 15 else []))
temps_max = st.sidebar.slider("Temps de calcul maximum (s)", 1, 120, 10)
st.caption(f"{inst['type']}, {inst['n']} clients, capacité {inst['capacite']:.0f}, "
           f"meilleure solution connue : {inst['bks'] or 'aucune'}")
if not st.sidebar.button("▶ Lancer", type="primary"):
    st.info("Choisissez une instance et une méthode à gauche, puis cliquez sur ▶ Lancer.")
    st.stop()

# 2. La résolution, puis la vérification de toutes les contraintes
routes, temps = lancer(methode, inst, temps_max)
ev = evaluer(inst, routes)

# 3. Le résultat
ecart = None if inst["trafic"] else gap(ev["distance"], inst["bks"])   # références sans trafic
c = st.columns(4)
c[0].metric("Distance totale", f"{ev['distance']:.1f}")
c[1].metric("Gap", "—" if ecart is None else f"{ecart:.2f} %")
c[2].metric("Camions", ev["nb_vehicules"])
c[3].metric("Temps de calcul", f"{temps:.1f} s")
if ev["realisable"]:
    st.success("✅ Toutes les contraintes sont respectées.")
else:
    st.error("❌ " + " ; ".join(ev["violations"][:10]))

# 4. Le suivi 2D : position de chaque camion à 100 moments de la journée.
#    Un camion va en ligne droite d'un lieu au suivant, et reste sur place pendant
#    l'attente et la livraison (np.interp interpole entre ces points de passage).
#    Le moment de la journée est affiché en vrai horaire pour la Lorraine (minutes depuis
#    minuit), et en % de la journée pour les autres instances, dont le temps n'est pas
#    une heure (0 % = ouverture du dépôt, 100 % = fermeture).
ouverture, fermeture = inst["fenetres"][0] if inst["fenetres"] is not None else (0, inst["horizon"])


def moment(h):
    if "villes" in inst:
        return f"{int(h) // 60}h{int(h) % 60:02d}"
    return f"{100 * (h - ouverture) / (fermeture - ouverture):.1f} %"


# Une image par étiquette différente (sinon plotly fusionne deux images et on croirait
# voir plusieurs positions du même camion)
xy = inst["coords"]
images = {moment(h): h for h in np.linspace(min(t["depart"] for t in ev["tournees"]),
                                             max(t["retour"] for t in ev["tournees"]), 100)}
lignes = []
for t in ev["tournees"]:
    lieux, passages = [0], [t["depart"]]                # départ du dépôt
    for a in t["arrets"]:                               # arrivée chez le client, puis fin de livraison
        lieux += [a["client"], a["client"]]
        passages += [a["arrivee"], a["fin"]]
    lieux.append(0)                                     # retour au dépôt
    passages.append(t["retour"])
    for etiquette, h in images.items():
        lignes.append({"moment": etiquette, "camion": f"Camion {t['numero']}",
                       "x": np.interp(h, passages, xy[lieux, 0]), "y": np.interp(h, passages, xy[lieux, 1])})

couleurs = px.colors.qualitative.Plotly                # la même couleur pour un camion et sa tournée
marge = 0.05 * np.ptp(xy)
suivi = px.scatter(pd.DataFrame(lignes), x="x", y="y", color="camion", animation_frame="moment",
                   color_discrete_sequence=couleurs,
                   labels={"x": "", "y": "", "camion": "", "moment": "Heure" if "villes" in inst else "Journée"},
                   range_x=[xy[:, 0].min() - marge, xy[:, 0].max() + marge],
                   range_y=[xy[:, 1].min() - marge, xy[:, 1].max() + marge], height=650)
suivi.update_traces(marker_size=12)
for i, t in enumerate(ev["tournees"]):                  # les tournées : trait fin + un point par livraison
    chemin = [0] + t["clients"] + [0]
    suivi.add_scatter(x=xy[chemin, 0], y=xy[chemin, 1], mode="lines+markers", showlegend=False,
                      line=dict(width=1, color=couleurs[i % len(couleurs)]), marker_size=5)
suivi.add_scatter(x=xy[:1, 0], y=xy[:1, 1], mode="markers", name="Dépôt",
                  marker=dict(symbol="square", size=15, color="black"))
suivi.update_yaxes(scaleanchor="x")                     # même échelle en x et en y
suivi.update_layout(showlegend=ev["nb_vehicules"] <= 20)
# Lecture : 0,1 s par image et pas de glissement entre deux images (sinon les points
# laissent une traînée et on croit en voir plusieurs).
suivi.layout.updatemenus[0].buttons[0].args[1].update(frame=dict(duration=100), transition=dict(duration=0))
suivi.layout.sliders[0].transition.duration = 0
onglet_2d, onglet_3d = st.tabs(["Suivi 2D", "Suivi 3D (bonus)"])
onglet_2d.plotly_chart(suivi, width="stretch")
onglet_2d.caption("Cliquez sur ▶ (sous la carte) pour voir les camions avancer au fil de la journée. "
           "Hors Lorraine, le temps des instances n'est pas une heure : il est donné en % de la "
           "journée (0 % = ouverture du dépôt, 100 % = fermeture).")
with onglet_3d:   # BONUS facultatif (affichage seulement) : tout son code est à part, dans bonus_3d/
    from bonus_3d.suivi_3d import afficher_suivi_3d
    afficher_suivi_3d(inst, ev)

# 5. Le détail de chaque tournée
nom_lieu = inst.get("villes") or ["Dépôt"] + [f"Client {i}" for i in range(1, inst["n"] + 1)]
st.dataframe(pd.DataFrame([{
    "Camion": t["numero"],
    "Charge": f"{t['charge']:.0f} / {inst['capacite']:.0f}",
    "Distance": round(t["distance"], 1),
    "Parcours": " → ".join(nom_lieu[i] for i in [0] + t["clients"] + [0]),
} for t in ev["tournees"]]), hide_index=True, width="stretch")
