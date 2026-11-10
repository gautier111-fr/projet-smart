"""
Benchmark VRPLIB : on lance GRASP + Tabou sur des instances de référence
et on calcule le GAP par rapport à la meilleure solution connue (BKS).

    gap = 100 * (notre coût - coût optimal) / coût optimal

Prérequis :
    pip install vrplib pandas matplotlib
    les instances (.vrp + .sol) dans un dossier "instances/"
    (copiées depuis https://github.com/PyVRP/Instances, dossier VRPTW/Solomon et CVRP)
"""

import math
import os
import random
import time
import urllib.request

import vrplib
from algorithmes import grasp_tabou_cvrptw as g   # notre code GRASP + Tabou


# -----------------------------------------------------------------------------
# 1. Charger une instance VRPLIB dans notre code
# -----------------------------------------------------------------------------
URL = "https://raw.githubusercontent.com/PyVRP/Instances/main/"


def telecharger(nom):
    """
    Télécharge instances/<nom>.vrp et .sol depuis le dépôt PyVRP/Instances
    s'ils ne sont pas déjà là (utile sur Colab, où le dossier est vide).
    Les instances X sont dans CVRP/, les instances Solomon dans VRPTW/Solomon/.
    """
    os.makedirs("instances", exist_ok=True)
    dossier = "CVRP/" if nom.startswith("X-") else "VRPTW/Solomon/"
    for ext in ("vrp", "sol"):
        fichier = f"instances/{nom}.{ext}"
        if not os.path.exists(fichier):
            urllib.request.urlretrieve(URL + dossier + f"{nom}.{ext}", fichier)


def charger_vrplib(nom):
    """Lit instances/<nom>.vrp et .sol, prépare g, renvoie le coût optimal."""
    telecharger(nom)
    inst = vrplib.read_instance(f"instances/{nom}.vrp")
    bks = vrplib.read_solution(f"instances/{nom}.sol")["cost"]

    coords = inst["node_coord"].tolist()
    demandes = inst["demand"].tolist()
    n = len(coords)

    # Fenêtres de temps : seulement pour le CVRPTW
    if "time_window" in inst:
        fenetres = inst["time_window"].tolist()
        s = inst["service_time"]
        # dans ces fichiers, service_time est un seul nombre (le même pour tous)
        service = [0] + [s] * (n - 1) if isinstance(s, (int, float)) else s.tolist()
        service[0] = 0  # pas de service au dépôt
    else:
        fenetres, service = None, None   # CVRP simple

    g.charger_instance(coords, demandes, inst["capacity"], fenetres, service)

    # Convention des BKS :
    #  - Solomon (VRPTW) : distances tronquées à 1 décimale
    #  - X (CVRP)        : distances arrondies à l'entier
    for i in range(n):
        for j in range(n):
            d = math.dist(coords[i], coords[j])
            g.dist[i][j] = math.floor(d * 10) / 10 if fenetres else round(d)

    return bks


# -----------------------------------------------------------------------------
# 2. Lancer une instance et calculer le gap
# -----------------------------------------------------------------------------
def tester(nom, graine=0, temps_max=20, alpha=0.1, taille_tabou=10,
           iter_max=30, taille_echantillon=25):
    random.seed(graine)
    bks = charger_vrplib(nom)

    t0 = time.time()
    sol, cout = g.grasp_tabou(nb_starts=1000, alpha=alpha, taille_tabou=taille_tabou,
                              iter_max=iter_max, taille_echantillon=taille_echantillon,
                              temps_max=temps_max, verbose=False)
    duree = time.time() - t0

    gap = 100 * (cout - bks) / bks
    return {"instance": nom, "graine": graine, "n": g.n - 1,
            "camions": len(sol), "cout": round(cout, 1), "bks": bks,
            "gap_%": round(gap, 2), "temps_s": round(duree, 1),
            "valide": g.verifier_solution(sol)}


# -----------------------------------------------------------------------------
# 3. Plan d'expérience : 20+ instances de familles différentes
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import pandas as pd

    # temps par instance en secondes : python benchmark_vrplib.py 60
    # (dans Colab, sys.argv[1] vaut "-f" : on garde alors 20 s)
    TEMPS = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 20

    instances = [
        # C = clients groupés, R = aléatoires, RC = mixte
        # 1 = fenêtres serrées, 2 = fenêtres larges
        "C101", "C102", "C105", "C201", "C202", "C205",
        "R101", "R102", "R105", "R201", "R202", "R205",
        "RC101", "RC102", "RC105", "RC201", "RC202", "RC205",
        # CVRP (pas de fenêtres)
        "X-n101-k25", "X-n110-k13",
    ]

    resultats = []
    for nom in instances:
        r = tester(nom, graine=0, temps_max=TEMPS)
        print(r)
        resultats.append(r)

    df = pd.DataFrame(resultats)
    df["famille"] = df["instance"].str.extract(r"^([A-Z]+\d?)")[0]
    os.makedirs("resultats", exist_ok=True)
    df.to_csv(f"resultats/resultats_{TEMPS}s.csv", index=False)

    print("\n=== Gap moyen par famille ===")
    print(df.groupby("famille")[["gap_%", "temps_s"]].mean().round(2))
    print(f"\nGap moyen global : {df['gap_%'].mean():.2f} %")

    # Graphique : gap par instance
    import matplotlib.pyplot as plt
    df.plot.bar(x="instance", y="gap_%", legend=False, figsize=(11, 4))
    plt.axhline(7, color="red", linestyle="--", label="objectif 7 %")
    plt.ylabel("Gap (%)")
    plt.title(f"Gap par instance (GRASP + Tabou, {TEMPS} s)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"resultats/gap_par_instance_{TEMPS}s.png")