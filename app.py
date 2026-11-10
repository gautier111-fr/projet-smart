"""
app.py - L'interface : choisir une instance et une méthode, lancer, voir les tournées.
Lancement : streamlit run app.py   (ou double-clic sur lancer_interface.bat)
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from algorithmes.methodes import GRASP_TABOU, PLNE, lancer
from probleme.contraintes import PROFIL_TRAFIC_DEFAUT, evaluer, gap
from probleme.instances import charger_instance, exemple_livrable1, lister_instances

st.set_page_config(page_title="Tournées de livraison", page_icon="🚚", layout="wide")
st.title("🚚 Tournées de livraison")

# 1. Les choix, à gauche
EXEMPLE = "Exemple du livrable 1"
chemins = {i["nom"]: i["chemin"] for i in lister_instances()}
nom = st.sidebar.selectbox("Instance", [EXEMPLE] + list(chemins))
inst = exemple_livrable1() if nom == EXEMPLE else charger_instance(chemins[nom])
if st.sidebar.toggle("Trafic selon l'heure"):
    inst["trafic"] = inst.get("profil_trafic", PROFIL_TRAFIC_DEFAUT)
methode = st.sidebar.radio("Méthode", [GRASP_TABOU] + ([PLNE] if inst["n"] <= 15 else []))
temps_max = st.sidebar.slider("Temps de calcul maximum (s)", 1, 120, 10)

st.caption(f"{inst['nom']} : {inst['type']}, {inst['n']} clients, capacité {inst['capacite']:.0f}, "
           f"meilleure solution connue : {inst['bks'] or 'aucune (instance inventée)'}")
if not st.sidebar.button("▶ Lancer", type="primary"):
    st.info("Choisissez une instance et une méthode à gauche, puis cliquez sur ▶ Lancer.")
    st.stop()

# 2. La résolution, puis la vérification de toutes les contraintes
with st.spinner(f"{methode} en cours (au plus {temps_max} s)..."):
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
    st.error("❌ Contraintes non respectées : " + " ; ".join(ev["violations"][:10]))

# La carte : une ligne par camion, le dépôt en carré noir
xy, carte = inst["coords"], go.Figure()
for t in ev["tournees"]:
    chemin = [0] + t["clients"] + [0]
    carte.add_trace(go.Scatter(x=xy[chemin, 0], y=xy[chemin, 1], mode="lines+markers",
                               name=f"Camion {t['numero']}"))
carte.add_trace(go.Scatter(x=xy[:1, 0], y=xy[:1, 1], mode="markers", name="Dépôt",
                           marker=dict(symbol="square", size=15, color="black")))
carte.update_yaxes(scaleanchor="x")                     # même échelle en x et en y
st.plotly_chart(carte, width="stretch")

# Le détail de chaque tournée
nom_lieu = inst.get("villes") or ["Dépôt"] + [f"Client {i}" for i in range(1, inst["n"] + 1)]
st.dataframe(pd.DataFrame([{
    "Camion": t["numero"],
    "Charge": f"{t['charge']:.0f} / {inst['capacite']:.0f}",
    "Distance": round(t["distance"], 1),
    "Parcours": " → ".join(nom_lieu[i] for i in [0] + t["clients"] + [0]),
} for t in ev["tournees"]]), hide_index=True, width="stretch")
