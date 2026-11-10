"""
benchmark.py - Étude expérimentale (onglet 📊 de l'interface).

On lance chaque méthode sur chaque instance, plusieurs fois (graines), et on enregistre
une ligne par essai dans un CSV, au même format que le benchmark de l'équipe :
    instance, famille, n, algorithme, graine, cout, bks, gap_%, camions, temps_s, valide
plus temps_meilleure_s : le moment où la meilleure solution a été trouvée.

Ce que demande le sujet, et la fonction qui y répond :
    qualité des solutions (gap VRPLIB)              -> resume_par_methode, graphique_gap
    robustesse (stabilité d'une graine à l'autre)   -> resume_par_methode
    comportement selon le type d'instance           -> resume_par_famille
    temps de calcul selon la taille                 -> graphique_temps, pente_complexite
    sensibilité aux paramètres                      -> graphique_sensibilite
    analyse statistique (tabou contre GRASP)        -> test_wilcoxon

En ligne de commande, pour une longue campagne :
    python benchmark.py --graines 5 --temps 60
"""

import argparse
import glob
import os
import time

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats

import solveurs
from instances_lorraine import lister_instances_lorraine
from vrp_commun import charger_instance, evaluer, famille_instance, gap
from visualisation import COULEUR_ALGO, COULEURS

DOSSIER = os.path.dirname(os.path.abspath(__file__))
DOSSIER_INSTANCES = os.path.join(DOSSIER, "instances")
DOSSIER_RESULTATS = os.path.join(DOSSIER, "resultats")
SEUIL_GAP = 7          # au-delà de 7-10 % de gap, la note est limitée à B (sujet)


# ---------------------------------------------------------------------------
# Liste des instances disponibles
# ---------------------------------------------------------------------------
def lister_instances():
    """Parcourt les sous-dossiers de instances/ (CVRP, VRPTW, GENERE) et lit juste l'en-tête
    de chaque fichier. Les fichiers posés directement dans instances/ servent au
    benchmark_vrplib.py de l'équipe : on ne les compte pas deux fois."""
    liste = []
    for chemin in glob.glob(os.path.join(DOSSIER_INSTANCES, "*", "*.vrp")):
        entete = {}
        with open(chemin, encoding="utf-8", errors="replace") as f:
            for ligne in f:
                if "SECTION" in ligne:
                    break
                if ":" in ligne:
                    cle, valeur = ligne.split(":", 1)
                    entete[cle.strip()] = valeur.strip()
        nom = entete.get("NAME", os.path.basename(chemin)[:-4])
        liste.append({
            "nom": nom,
            "famille": famille_instance(nom),
            "type": "CVRPTW" if "TW" in entete.get("TYPE", "") else "CVRP",
            "n": int(entete["DIMENSION"]) - 1,
            "bks connue": os.path.exists(chemin[:-4] + ".sol"),
            "chemin": chemin,
        })
    liste += lister_instances_lorraine()                # villes de Metz / Nancy
    return sorted(liste, key=lambda i: (i["type"], i["n"], i["nom"]))


# ---------------------------------------------------------------------------
# Lancer les essais et enregistrer le CSV
# ---------------------------------------------------------------------------
def executer(chemins, configurations, graines, temps_max, progression=None):
    """Lance chaque configuration sur chaque instance avec chaque graine.

    configurations : liste de (nom affiché, algorithme, paramètres), par exemple
                     [("GRASP", "GRASP", {}), ("GRASP alpha=0.1", "GRASP", {"alpha": 0.1})]
    progression    : fonction(fraction, message) pour la barre de progression.
    Renvoie un tableau pandas : une ligne par essai.
    """
    lignes = []
    total, fait = len(chemins) * len(configurations) * len(graines), 0
    for chemin in chemins:
        inst = charger_instance(chemin)
        for etiquette, algo, parametres in configurations:
            for graine in graines:
                if progression:
                    progression(fait / total, f"{inst['nom']} - {etiquette} - graine {graine}")
                ligne = {"instance": inst["nom"], "famille": inst["famille"], "n": inst["n"],
                         "algorithme": etiquette, "graine": graine}
                try:
                    routes, temps, historique = solveurs.lancer(algo, inst, temps_max, graine,
                                                                parametres)
                    ev = evaluer(inst, routes)
                    ecart = gap(ev["distance"], inst["bks"])
                    # Les méthodes utilisent tout le temps donné : ce qui mesure leur rapidité,
                    # c'est le moment où elles ont trouvé leur meilleure solution.
                    trouve = historique[-1][0] if historique else temps
                    ligne.update({"cout": round(ev["distance"], 1), "bks": inst["bks"],
                                  "gap_%": None if ecart is None else round(ecart, 2),
                                  "camions": ev["nb_vehicules"], "temps_s": round(temps, 2),
                                  "temps_meilleure_s": round(trouve, 2),
                                  "valide": ev["realisable"]})
                except Exception as erreur:               # un plantage ne bloque pas tout
                    ligne.update({"valide": False, "erreur": repr(erreur)})
                lignes.append(ligne)
                fait += 1
    if progression:
        progression(1.0, "Terminé")
    return pd.DataFrame(lignes)


def sauvegarder(df):
    """Enregistre le CSV dans resultats/ (relisible avec pandas.read_csv)."""
    os.makedirs(DOSSIER_RESULTATS, exist_ok=True)
    chemin = os.path.join(DOSSIER_RESULTATS, time.strftime("resultats_%Y%m%d_%H%M%S.csv"))
    df.to_csv(chemin, index=False)
    return chemin


# ---------------------------------------------------------------------------
# Tableaux
# ---------------------------------------------------------------------------
def resume_par_methode(df):
    """Qualité et robustesse de chaque méthode, en un tableau."""
    lignes = []
    for algo, g in df.groupby("algorithme", sort=False):
        valides = g[g["valide"] == True]
        gaps = valides.groupby("instance")["gap_%"].mean().dropna()   # instances avec référence
        # Robustesse : de combien le coût varie d'une graine à l'autre (en % du coût moyen)
        variation = valides.groupby("instance")["cout"].agg(
            lambda x: 100 * x.std(ddof=1) / x.mean() if len(x) > 1 else 0)
        lignes.append({
            "méthode": algo,
            "gap moyen (%)": gaps.mean(),
            "gap max (%)": gaps.max(),
            f"instances ≤ {SEUIL_GAP} %": f"{(gaps <= SEUIL_GAP).sum()} / {len(gaps)}",
            "variation entre graines (%)": variation.mean(),
            "meilleure trouvée après (s)": valides["temps_meilleure_s"].mean(),
            "solutions valides": f"{len(valides)} / {len(g)}",
        })
    return pd.DataFrame(lignes).round(2)


def resume_par_famille(df):
    """Gap moyen par type d'instance (taille, répartition des clients, fenêtres de temps)."""
    valides = df[(df["valide"] == True) & df["gap_%"].notna()]
    tableau = valides.pivot_table(index="famille", columns="algorithme", values="gap_%",
                                  aggfunc="mean").round(2)
    tableau.insert(0, "n moyen", valides.groupby("famille")["n"].mean().round(0))
    return tableau.reset_index()


# ---------------------------------------------------------------------------
# Statistiques
# ---------------------------------------------------------------------------
def test_wilcoxon(df, algo_a, algo_b):
    """Test de Wilcoxon apparié : A et B donnent-ils des gaps différents ?
    On compare, instance par instance, le gap moyen (sur les graines) de A et de B.
    p < 0,05 -> la différence n'est pas due au hasard."""
    moyennes = df[df["valide"] == True].pivot_table(index="instance", columns="algorithme",
                                                     values="gap_%", aggfunc="mean")
    paires = moyennes[[algo_a, algo_b]].dropna()
    if len(paires) < 6:
        return f"Pas assez d'instances avec référence en commun ({len(paires)}, il en faut 6)."
    diff = paires[algo_a] - paires[algo_b]
    if np.allclose(diff, 0):
        return f"Sur {len(paires)} instances : les deux méthodes donnent les mêmes coûts."
    p = stats.wilcoxon(paires[algo_a], paires[algo_b]).pvalue
    meilleur = algo_a if diff.mean() < 0 else algo_b
    if p < 0.05:
        return f"Sur {len(paires)} instances : {meilleur} est significativement meilleur (p = {p:.4f})."
    return f"Sur {len(paires)} instances : pas de différence significative (p = {p:.3f})."


def pente_complexite(df):
    """Ajuste temps = a x n^b (une droite en échelle log-log) pour chaque méthode,
    avec le temps mis pour trouver la meilleure solution. b ~ 1 : linéaire, b ~ 2 : quadratique."""
    pentes = {}
    for algo, g in df[df["temps_meilleure_s"] > 0].groupby("algorithme"):
        g = g.groupby("n")["temps_meilleure_s"].mean().reset_index()
        if len(g) >= 3:
            pentes[algo] = round(np.polyfit(np.log(g["n"]), np.log(g["temps_meilleure_s"]), 1)[0], 2)
    return pentes


# ---------------------------------------------------------------------------
# Graphiques
# ---------------------------------------------------------------------------
def _couleurs(df):
    algos = list(dict.fromkeys(df["algorithme"]))
    return {a: COULEUR_ALGO.get(a, COULEURS[i % len(COULEURS)]) for i, a in enumerate(algos)}


def graphique_gap(df):
    """Gap par instance (moyenne sur les graines, barre = écart-type)."""
    g = df[(df["valide"] == True) & df["gap_%"].notna()] \
        .groupby(["instance", "n", "algorithme"])["gap_%"].agg(["mean", "std"]) \
        .reset_index().sort_values("n")
    fig = px.bar(g, x="instance", y="mean", error_y="std", color="algorithme",
                 barmode="group", color_discrete_map=_couleurs(df),
                 labels={"mean": "Gap moyen (%)", "instance": "", "algorithme": ""})
    fig.add_hline(y=SEUIL_GAP, line_dash="dash", line_color="#e34948")
    fig.update_layout(template="plotly_white", height=450,
                      title=f"Gap par instance (ligne rouge : {SEUIL_GAP} % ; trait noir : "
                            "écart-type entre graines)")
    return fig


def graphique_temps(df):
    g = df.groupby(["n", "algorithme"])["temps_meilleure_s"].mean().reset_index()
    fig = px.scatter(g, x="n", y="temps_meilleure_s", color="algorithme", log_x=True,
                     log_y=True, color_discrete_map=_couleurs(df),
                     labels={"n": "Nombre de clients", "temps_meilleure_s": "Temps (s)",
                             "algorithme": ""})
    fig.update_traces(mode="lines+markers", marker=dict(size=9))
    fig.update_layout(template="plotly_white", height=420,
                      title="Temps pour trouver la meilleure solution, selon la taille (log-log)")
    return fig


def graphique_sensibilite(df, parametre):
    g = df[df["valide"] == True].groupby("valeur")["gap_%"].agg(["mean", "std"]).reset_index()
    fig = go.Figure(go.Scatter(x=g["valeur"], y=g["mean"], error_y=dict(array=g["std"]),
                               mode="lines+markers", line=dict(color=COULEURS[0], width=2),
                               marker=dict(size=9)))
    fig.update_layout(template="plotly_white", height=400, xaxis_title=parametre,
                      yaxis_title="Gap moyen (%)", title=f"Sensibilité au paramètre « {parametre} »")
    return fig


# ---------------------------------------------------------------------------
# Ligne de commande
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parseur = argparse.ArgumentParser(description="Étude expérimentale : tabou et GRASP")
    parseur.add_argument("--graines", type=int, default=3, help="nombre de répétitions")
    parseur.add_argument("--temps", type=float, default=30, help="temps max par essai (s)")
    args = parseur.parse_args()

    algos = ["Recherche tabou", "GRASP"]
    instances = [i["chemin"] for i in lister_instances()]
    print(f"{len(instances)} instances x {len(algos)} méthodes x {args.graines} graines")
    resultats = executer(instances, [(a, a, {}) for a in algos], list(range(args.graines)),
                         args.temps, progression=lambda f, m: print(f"[{100 * f:5.1f} %] {m}"))
    print(resume_par_methode(resultats).to_string(index=False))
    print(resume_par_famille(resultats).to_string(index=False))
    print("Fichier :", sauvegarder(resultats))
