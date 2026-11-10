"""
app.py - L'interface des tournées de livraison. Lancement : streamlit run app.py

À gauche : l'instance, le trafic, la méthode et le temps de calcul, puis ▶ Lancer.
Au centre, 3 onglets : Tournées | Suivi 3D / 2D | Étude expérimentale.
"""

import json

import pandas as pd
import streamlit as st

from algorithmes.methodes import GRASP_TABOU, PARAMETRES, PLNE, lancer
from interface import etude
from interface import graphiques as vis
from probleme.contraintes import PROFIL_TRAFIC_DEFAUT, evaluer, gap
from probleme.instances import charger_instance, exemple_livrable1, lister_instances

st.set_page_config(page_title="Tournées de livraison", page_icon="🚚", layout="wide")
EXEMPLE = "Exemple du livrable 1"


@st.cache_resource
def charger(chemin):
    return charger_instance(chemin)


@st.cache_resource(max_entries=6, show_spinner=False)
def figure_suivi(_inst, _solution, cle, vue):
    """Le suivi est long à construire : on le garde tant que la solution (cle) ne change pas."""
    return vis.suivi(_inst, _solution, vue)


def texte_gap(valeur):
    """Le gap avec la zone de notation du sujet (seuils de 7 % et 10 %)."""
    if valeur is None:
        return "—"
    return ("🟢" if valeur <= 7 else "🟠" if valeur <= 10 else "🔴") + f" {valeur:.2f} %"


# ---------------------------------------------------------------------------
# À GAUCHE : les choix
# ---------------------------------------------------------------------------
st.sidebar.title("🚚 Tournées de livraison")
toutes = lister_instances()
chemins = {f"{i['nom']} ({i['type']}, {i['n']} clients)": i["chemin"] for i in toutes}
choix = st.sidebar.selectbox("Instance", [EXEMPLE] + list(chemins))
inst = dict(exemple_livrable1() if choix == EXEMPLE else charger(chemins[choix]))  # copie

if st.sidebar.toggle("Trafic selon l'heure"):
    inst["trafic"] = inst.get("profil_trafic", PROFIL_TRAFIC_DEFAUT)
methode = st.sidebar.radio("Méthode", [GRASP_TABOU] + ([PLNE] if inst["n"] <= 15 else []))
temps_max = st.sidebar.slider("Temps de calcul maximum (s)", 1, 300, 30)

# Résultats gardés en mémoire pour chaque instance, avec ou sans trafic : {méthode: résultat}
resultats = st.session_state.setdefault("resultats", {}).setdefault(
    (inst["nom"], bool(inst["trafic"])), {})
if st.sidebar.button("▶ Lancer", type="primary", width="stretch"):
    with st.spinner(f"{methode} en cours (au plus {temps_max} s)..."):
        try:
            routes, temps, historique = lancer(methode, inst, temps_max)
            resultats[methode] = {"routes": routes, "temps": temps, "historique": historique}
        except Exception as erreur:
            st.sidebar.error(f"{methode} a échoué : {erreur}")

# Les solutions de référence sont calculées sans trafic : pas de gap avec le trafic.
reference = None if inst["trafic"] else inst["bks"]

# ---------------------------------------------------------------------------
# AU CENTRE
# ---------------------------------------------------------------------------
st.title(inst["nom"])
st.caption(f"{inst['type']} · {inst['n']} clients · capacité {inst['capacite']:.0f} · "
           + (f"{inst['nb_vehicules']} camions" if inst["nb_vehicules"] else "camions illimités")
           + (f" · {inst['description']}" if "description" in inst else ""))
st.caption(f"🎯 Meilleure solution connue : **{inst['bks']:.1f}**" if inst["bks"] else
           "🎯 Instance inventée : pas de solution de référence, donc pas de gap.")

onglets = st.tabs(["🚚 Tournées", "🗺️ Suivi 3D / 2D", "📊 Étude expérimentale"])
solution = evaluer(inst, resultats[methode]["routes"]) if methode in resultats else None

with onglets[0]:                                        # ---------- Tournées
    if solution is None:
        st.info(f"Cliquez sur ▶ Lancer pour calculer les tournées avec : {methode}.")
    else:
        camions = str(solution["nb_vehicules"]) + (f" / {inst['nb_vehicules']}"
                                                   if inst["nb_vehicules"] else "")
        c = st.columns(4)
        c[0].metric("Distance totale", f"{solution['distance']:.1f}")
        c[1].metric("Gap", texte_gap(gap(solution["distance"], reference)))
        c[2].metric("Camions", camions)
        c[3].metric("Temps de calcul", f"{resultats[methode]['temps']:.2f} s")
        if len(resultats) == 2:                         # petite instance : les deux méthodes
            st.caption("Comparaison : " + " · ".join(
                f"{m} {evaluer(inst, r['routes'])['distance']:.1f}" for m, r in resultats.items()))

        if solution["realisable"]:
            st.success("✅ Toutes les contraintes sont respectées.")
        else:
            st.error(f"❌ {len(solution['violations'])} contrainte(s) non respectée(s)")
            for violation in solution["violations"][:15]:
                st.write("•", violation)

        carte = vis.carte_reelle if "latlon" in inst else vis.carte_tournees
        st.plotly_chart(carte(inst, solution), width="stretch")
        st.dataframe(pd.DataFrame([{
            "Camion": t["numero"],
            "Charge": f"{t['charge']:.0f} / {inst['capacite']:.0f}",
            "Distance": round(t["distance"], 1),
            "Parcours": " → ".join(vis.nom_lieu(inst, i) for i in [0] + t["clients"] + [0]),
        } for t in solution["tournees"]]), hide_index=True, width="stretch")

        with st.expander("Planning des camions (trajet, attente, livraison)"):
            st.plotly_chart(vis.gantt(solution), width="stretch")
        if resultats[methode]["historique"]:
            with st.expander("Convergence (meilleur coût trouvé au fil du temps)"):
                st.plotly_chart(vis.convergence(resultats[methode]["historique"], reference),
                                width="stretch")

with onglets[1]:                                        # ---------- Suivi 3D / 2D
    if solution is None:
        st.info("Lancez d'abord la résolution pour suivre les camions.")
    else:
        vue = st.radio("Vue", ["3D", "2D"], horizontal=True, label_visibility="collapsed")
        cle = (inst["nom"], bool(inst["trafic"]), str(resultats[methode]["routes"]))
        st.plotly_chart(figure_suivi(inst, solution, cle, vue), width="stretch")
        st.caption("Cliquez sur ▶ Lecture. Trait pâle : tournée prévue ; trait épais : déjà "
                   "parcouru. Double-clic sur un camion dans la légende pour ne voir que lui. "
                   "Au plus 30 camions affichés.")

with onglets[2]:                                        # ---------- Étude expérimentale
    noms = [i["nom"] for i in toutes]
    choisies = st.multiselect("Instances (le sujet en demande au moins 20)", noms, noms)
    c1, c2 = st.columns(2)
    nb_graines = c1.number_input("Répétitions par instance (graines)", 1, 30, 3)
    temps_etude = c2.number_input("Temps max par essai (s)", 1, 3600, 10)
    with st.expander("Sensibilité à un paramètre (facultatif)"):
        nom_param = st.selectbox("Paramètre", PARAMETRES)
        valeurs = st.text_input("Valeurs à tester, séparées par des virgules", placeholder="0.05, 0.1, 0.3")

    # Un réglage = (nom affiché, méthode, paramètres). Sans sensibilité : le réglage par défaut.
    reglages, valeur_de = [(GRASP_TABOU, GRASP_TABOU, {})], {}
    if valeurs:
        try:
            valeur_de = {f"{nom_param}={v}": v for v in (json.loads(x) for x in valeurs.split(","))}
            reglages = [(e, GRASP_TABOU, {nom_param: v}) for e, v in valeur_de.items()]
        except json.JSONDecodeError:
            st.error("Valeurs invalides : écrivez des nombres séparés par des virgules.")

    nb_essais = len(choisies) * len(reglages) * nb_graines
    st.caption(f"{nb_essais} essais, {nb_essais * temps_etude / 60:.0f} min au maximum.")
    if st.button("▶ Lancer l'étude", type="primary", disabled=not choisies):
        barre = st.progress(0.0)
        fichiers = [i["chemin"] for i in toutes if i["nom"] in choisies]
        df = etude.executer(fichiers, reglages, list(range(nb_graines)), temps_etude,
                            progression=lambda f, m: barre.progress(f, text=m))
        if valeur_de:
            df["valeur"] = df["algorithme"].map(valeur_de)
        st.session_state.etude = df
        st.success(f"Résultats enregistrés dans {etude.sauvegarder(df)}")

    df = st.session_state.get("etude")
    if df is not None and "cout" not in df:
        st.error(f"Tous les essais ont échoué : {df['erreur'].iloc[0]}")
    elif df is not None:
        st.subheader("1. Qualité des solutions et robustesse")
        st.dataframe(etude.resume_qualite(df), hide_index=True, width="stretch")
        st.caption("Gap calculé sur les instances qui ont une solution de référence. Variation "
                   "entre graines : plus elle est faible, plus la méthode est stable.")
        st.plotly_chart(etude.graphique_gap(df), width="stretch")

        st.subheader("2. Selon le type d'instance")
        st.dataframe(etude.resume_par_famille(df), hide_index=True, width="stretch")
        st.caption("Gap moyen (%) par famille : taille, répartition des clients (C regroupés, "
                   "R aléatoires, RC mixtes), fenêtres de temps (série 1 serrées, 2 larges).")

        st.subheader("3. Temps de calcul selon la taille")
        st.plotly_chart(etude.graphique_temps(df), width="stretch")
        pentes = etude.pente_complexite(df)
        st.caption("La méthode utilise tout le temps donné : on mesure le moment où elle trouve "
                   "sa meilleure solution." + "".join(
                       f" Complexité observée (temps ≈ a·nᵇ) : b = {b}." for b in pentes.values()))

        if "valeur" in df:
            st.subheader("4. Sensibilité au paramètre")
            st.plotly_chart(etude.graphique_sensibilite(df, nom_param), width="stretch")
