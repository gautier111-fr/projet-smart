"""
app.py - Interface de gestion des tournées de livraison (projet ADEME / CesiCDP).

Lancement :  streamlit run app.py

À gauche : on choisit l'instance, le trafic et l'algorithme, puis on lance.
Au centre, 4 onglets : Tournées | Suivi 3D / 2D | Comparer | Étude expérimentale.
"""

import json

import pandas as pd
import streamlit as st

import benchmark
import solveurs
import visualisation as vis
from vrp_commun import PROFIL_TRAFIC_DEFAUT, charger_instance, evaluer, exemple_livrable1, gap

st.set_page_config(page_title="Tournées de livraison - CesiCDP", page_icon="🚚", layout="wide")

EXEMPLE = "Exemple du livrable 1"
PLNE = "PLNE exacte (≤ 15 clients)"
# Paramètres que l'on peut faire varier dans l'étude de sensibilité (voir adaptateur.py)
PARAMETRES = {"Recherche tabou": ["taille_tabou", "taille_echantillon"],
              "GRASP": ["alpha", "taille_tabou", "iter_max", "taille_echantillon"]}


@st.cache_resource
def charger(chemin):
    return charger_instance(chemin)


@st.cache_data
def liste_instances():
    return benchmark.lister_instances()


@st.cache_resource(max_entries=6, show_spinner=False)
def figure_suivi(_inst, _solution, cle, vue):
    """Le suivi est long à construire : on le garde tant que la solution (cle) ne change pas."""
    return vis.suivi(_inst, _solution, vue)


def texte_gap(valeur):
    """Gap avec la zone de notation du sujet : 7 % et 10 % sont les seuils."""
    if valeur is None:
        return "—"
    zone = "🟢" if valeur <= 7 else ("🟠" if valeur <= 10 else "🔴")
    return f"{zone} {valeur:.2f} %"


# ---------------------------------------------------------------------------
# À GAUCHE : les choix de l'utilisateur
# ---------------------------------------------------------------------------
st.sidebar.title("🚚 Tournées de livraison")

toutes = liste_instances()
chemins = {f"{i['nom']} ({i['type']}, {i['n']} clients)": i["chemin"] for i in toutes}
choix = st.sidebar.selectbox("Instance", [EXEMPLE] + list(chemins))
base = exemple_livrable1() if choix == EXEMPLE else charger(chemins[choix])

avec_trafic = st.sidebar.toggle("Trafic selon l'heure", value=False)
inst = dict(base)                       # copie : on ne modifie pas l'instance en cache
if avec_trafic:
    inst["trafic"] = base.get("profil_trafic", PROFIL_TRAFIC_DEFAUT)

algos = ["Recherche tabou", "GRASP"]
algos_etude = list(algos)               # la PLNE ne passe pas à l'échelle : hors de l'étude
if inst["n"] <= 15:
    algos.append(PLNE)

algo = st.sidebar.radio("Algorithme", algos)
temps_max = st.sidebar.slider("Temps de calcul maximum (s)", 1, 300, 30)

# Résultats gardés en mémoire pour chaque instance, avec ou sans trafic : {algo: résultat}
if "resultats" not in st.session_state:
    st.session_state.resultats = {}
resultats = st.session_state.resultats.setdefault((inst["nom"], avec_trafic), {})


def resoudre_avec(nom_algo):
    """Lance un algorithme et garde son résultat. Renvoie True si tout s'est bien passé."""
    with st.spinner(f"{nom_algo} en cours (au plus {temps_max} s)..."):
        try:
            routes, temps, historique = solveurs.lancer(nom_algo, inst, temps_max)
        except Exception as erreur:
            st.error(f"{nom_algo} a échoué : {erreur}")
            return False
    resultats[nom_algo] = {"routes": routes, "temps": temps, "historique": historique}
    return True


if st.sidebar.button("▶ Lancer", type="primary", width="stretch"):
    resoudre_avec(algo)

# Le gap se mesure sans trafic : les solutions de référence sont calculées sans trafic.
reference = None if avec_trafic else inst["bks"]

# ---------------------------------------------------------------------------
# AU CENTRE : en-tête et onglets
# ---------------------------------------------------------------------------
st.title(inst["nom"])
st.caption(f"{inst['type']} · {inst['n']} clients · capacité {inst['capacite']:.0f} · "
           + (f"{inst['nb_vehicules']} camions" if inst["nb_vehicules"] else "camions illimités")
           + (f" · {inst['description']}" if "description" in inst else ""))
# Le gap a besoin d'une solution de référence (VRPLIB, ou optimum prouvé par la PLNE).
if inst["bks"]:
    st.caption(f"🎯 Meilleure solution connue : **{inst['bks']:.1f}**. "
               "Le gap s'affiche après ▶ Lancer.")
else:
    st.caption("🎯 Instance inventée : pas de solution de référence, donc pas de gap. "
               "Le gap se mesure sur les instances VRPLIB (X, Solomon, Homberger, Leuven).")

onglets = st.tabs(["🚚 Tournées", "🗺️ Suivi 3D / 2D", "⚖️ Comparer", "📊 Étude expérimentale"])
solution = evaluer(inst, resultats[algo]["routes"]) if algo in resultats else None

# ---------------------------------------------------------------------------
# ONGLET 1 - Tournées de l'algorithme choisi à gauche
# ---------------------------------------------------------------------------
with onglets[0]:
    if solution is None:
        st.info(f"Cliquez sur ▶ Lancer pour calculer les tournées avec : {algo}.")
        carte = vis.carte_reelle(inst) if "latlon" in inst else vis.carte_instance(inst)
    else:
        camions = str(solution["nb_vehicules"])
        if inst["nb_vehicules"]:
            camions += f" / {inst['nb_vehicules']}"
        c = st.columns(4)
        c[0].metric("Distance totale", f"{solution['distance']:.1f}")
        c[1].metric("Gap", texte_gap(gap(solution["distance"], reference)))
        c[2].metric("Camions", camions)
        c[3].metric("Temps de calcul", f"{resultats[algo]['temps']:.2f} s")

        if avec_trafic and inst["bks"]:
            st.caption("Gap non calculé avec le trafic : les références VRPLIB sont sans trafic.")
        elif reference:
            st.caption("Gap = 100 × (coût − référence) / référence. 🟢 ≤ 7 %, 🟠 7 à 10 %, "
                       "🔴 > 10 %.")

        if solution["realisable"]:
            st.success("✅ Toutes les contraintes sont respectées.")
        else:
            st.error(f"❌ {len(solution['violations'])} contrainte(s) non respectée(s)")
            for violation in solution["violations"][:15]:
                st.write("•", violation)
        carte = (vis.carte_reelle(inst, solution) if "latlon" in inst
                 else vis.carte_tournees(inst, solution))

    st.plotly_chart(carte, width="stretch")

    if solution is not None:
        st.dataframe(pd.DataFrame([{
            "Camion": t["numero"],
            "Charge": f"{t['charge']:.0f} / {inst['capacite']:.0f}",
            "Distance": round(t["distance"], 1),
            "Parcours": " → ".join(vis.nom_lieu(inst, i) for i in [0] + t["clients"] + [0]),
        } for t in solution["tournees"]]), hide_index=True, width="stretch")

        with st.expander("Planning des camions (trajet, attente, livraison)"):
            st.plotly_chart(vis.gantt(solution), width="stretch")

# ---------------------------------------------------------------------------
# ONGLET 2 - Suivi 3D
# ---------------------------------------------------------------------------
with onglets[1]:
    if solution is None:
        st.info("Lancez d'abord la résolution pour suivre les camions.")
    else:
        vue = st.radio("Vue", ["3D", "2D"], horizontal=True, label_visibility="collapsed")
        cle = (inst["nom"], avec_trafic, str(resultats[algo]["routes"]))
        st.plotly_chart(figure_suivi(inst, solution, cle, vue), width="stretch")
        st.caption("Cliquez sur ▶ Lecture. Trait pâle : tournée prévue. Trait épais : déjà "
                   "parcouru. Double-cliquez sur un camion dans la légende pour ne voir que lui."
                   + (" En 3D, chaque trajet est un arc au-dessus du plan ; faites tourner "
                      "le plateau à la souris." if vue == "3D" else ""))
        if solution["nb_vehicules"] > 30:
            st.caption(f"Seuls les 30 premiers camions sur {solution['nb_vehicules']} sont affichés.")

# ---------------------------------------------------------------------------
# ONGLET 3 - Comparer les algorithmes sur cette instance
# ---------------------------------------------------------------------------
with onglets[2]:
    st.caption(f"Toutes les méthodes sur la même instance, avec {temps_max} s chacune."
               + (" La PLNE donne la solution optimale : elle vérifie les métaheuristiques."
                  if PLNE in algos else ""))
    if st.button("▶ Lancer toutes les méthodes"):
        if all([resoudre_avec(a) for a in algos]):
            st.rerun()                  # réaffiche la page pour remplir les autres onglets
    if resultats:
        lignes = []
        for nom_algo, res in resultats.items():
            ev = evaluer(inst, res["routes"])
            lignes.append({"Méthode": nom_algo, "Distance": round(ev["distance"], 1),
                           "Gap": texte_gap(gap(ev["distance"], reference)),
                           "Camions": ev["nb_vehicules"], "Temps (s)": round(res["temps"], 2),
                           "Contraintes": "✅" if ev["realisable"] else "❌"})
        st.dataframe(pd.DataFrame(lignes), hide_index=True, width="stretch")

        historiques = {a: r["historique"] for a, r in resultats.items() if r["historique"]}
        if historiques:
            st.plotly_chart(vis.convergence(historiques, reference), width="stretch")
            st.caption("Convergence : meilleur coût trouvé au fil du temps de calcul.")

# ---------------------------------------------------------------------------
# ONGLET 4 - Étude expérimentale (plusieurs instances, plusieurs répétitions)
# ---------------------------------------------------------------------------
with onglets[3]:
    noms = [i["nom"] for i in toutes]
    choisies = st.multiselect("Instances (le sujet en demande au moins 20)", noms, noms)
    c1, c2 = st.columns(2)
    nb_graines = c1.number_input("Répétitions par instance (graines)", 1, 30, 3)
    temps_etude = c2.number_input("Temps max par essai (s)", 1, 3600, 10)

    with st.expander("Sensibilité à un paramètre (facultatif)"):
        algo_sens = st.selectbox("Méthode étudiée", algos_etude)
        nom_param = st.selectbox("Paramètre", PARAMETRES.get(algo_sens, []))
        valeurs = st.text_input("Valeurs à tester, séparées par des virgules", "",
                                placeholder="5, 10, 20")

    configurations = [(a, a, {}) for a in algos_etude]
    valeur_de = {}
    if nom_param and valeurs:
        try:
            nombres = [json.loads(v) for v in valeurs.split(",")]
        except json.JSONDecodeError:
            st.error("Valeurs invalides : écrivez des nombres séparés par des virgules.")
            nombres = []
        valeur_de = {f"{algo_sens} {nom_param}={v}": v for v in nombres}
        configurations = [(e, algo_sens, {nom_param: v}) for e, v in valeur_de.items()]

    nb_essais = len(choisies) * len(configurations) * nb_graines
    st.caption(f"{nb_essais} essais, {nb_essais * temps_etude / 60:.0f} min au maximum.")

    if st.button("▶ Lancer l'étude", type="primary", disabled=not (choisies and configurations)):
        barre = st.progress(0.0)
        fichiers = [i["chemin"] for i in toutes if i["nom"] in choisies]
        df = benchmark.executer(fichiers, configurations, list(range(nb_graines)), temps_etude,
                                progression=lambda f, m: barre.progress(f, text=m))
        if valeur_de:
            df["valeur"] = df["algorithme"].map(valeur_de)
        st.session_state.etude = df
        st.success(f"Résultats enregistrés dans {benchmark.sauvegarder(df)}")

    df = st.session_state.get("etude")
    if df is not None and "cout" not in df:
        st.error(f"Tous les essais ont échoué : {df['erreur'].iloc[0]}")
    elif df is not None:
        st.subheader("1. Qualité des solutions et robustesse")
        st.dataframe(benchmark.resume_par_methode(df), hide_index=True, width="stretch")
        st.caption("Gap calculé sur les instances qui ont une solution de référence. "
                   "Variation entre graines : plus elle est faible, plus la méthode est stable.")
        st.plotly_chart(benchmark.graphique_gap(df), width="stretch")

        st.subheader("2. Selon le type d'instance")
        st.dataframe(benchmark.resume_par_famille(df), hide_index=True, width="stretch")
        st.caption("Gap moyen (%) par famille : taille, répartition des clients (C regroupés, "
                   "R aléatoires, RC mixtes) et fenêtres de temps (série 1 serrées, 2 larges).")

        st.subheader("3. Temps de calcul selon la taille")
        st.plotly_chart(benchmark.graphique_temps(df), width="stretch")
        pentes = benchmark.pente_complexite(df)
        st.caption("Les méthodes utilisent tout le temps donné : on mesure donc le moment où "
                   "elles trouvent leur meilleure solution."
                   + (" Complexité observée (temps ≈ a·nᵇ) : "
                      + ", ".join(f"{a} : b = {b}" for a, b in pentes.items()) if pentes else ""))

        if "valeur" in df:
            st.subheader("4. Sensibilité au paramètre")
            st.plotly_chart(benchmark.graphique_sensibilite(df, nom_param or "paramètre"),
                            width="stretch")

        if {"Recherche tabou", "GRASP"} <= set(df["algorithme"]):
            st.subheader("Test statistique : tabou contre GRASP (Wilcoxon)")
            st.write(benchmark.test_wilcoxon(df, "Recherche tabou", "GRASP"))
