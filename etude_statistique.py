"""
Étude statistique du GRASP + Tabou
==================================

4 expériences, chacune enregistre un CSV et un graphique dans resultats/ :

  1. ROBUSTESSE   : même instance, plusieurs graines -> moyenne, écart-type, min, max
  2. CONVERGENCE  : gap en fonction du temps de calcul accordé
  3. TAILLE       : gap et temps de construction en fonction du nombre de clients
  4. SENSIBILITÉ  : effet des paramètres alpha (GRASP) et taille de la liste tabou

Lancement :
    python etude_statistique.py            (les 4, environ 25 min)
    python etude_statistique.py 1 3        (seulement les expériences 1 et 3)
"""

import os
import sys
import time
import random

import pandas as pd
import matplotlib
matplotlib.use("Agg")              # pas de fenêtre : on enregistre les images
import matplotlib.pyplot as plt

import benchmark_vrplib as b
import grasp_tabou_cvrptw as g

os.makedirs("resultats", exist_ok=True)

# Une instance par famille : groupés / aléatoires / mixtes, fenêtres serrées (1) / larges (2)
INSTANCES = ["C101", "C201", "R101", "R201", "RC101", "RC201"]


def lancer(liste_essais, fichier):
    """Lance tous les essais (dict de paramètres pour b.tester) et enregistre un CSV."""
    lignes = []
    for i, essai in enumerate(liste_essais, 1):
        r = b.tester(**essai)
        r.update({k: v for k, v in essai.items() if k != "nom"})  # on garde les paramètres
        print(f"[{i}/{len(liste_essais)}] {r['instance']:12} gap = {r['gap_%']:6.2f} %")
        lignes.append(r)
    df = pd.DataFrame(lignes)
    df.to_csv(f"resultats/{fichier}.csv", index=False)
    return df


# =============================================================================
# 1. ROBUSTESSE : 5 graines par instance
# =============================================================================
def experience_robustesse(nb_graines=5, temps=10):
    """L'algorithme est aléatoire : on mesure la dispersion des résultats."""
    essais = [{"nom": nom, "graine": gr, "temps_max": temps}
              for nom in INSTANCES for gr in range(nb_graines)]
    df = lancer(essais, "1_robustesse")

    stats = df.groupby("instance")["gap_%"].agg(["mean", "std", "min", "max"]).round(2)
    print("\n", stats)

    # boxplot : une boîte par instance
    df.boxplot(column="gap_%", by="instance", figsize=(9, 4))
    plt.axhline(7, color="red", linestyle="--")
    plt.suptitle("")
    plt.title(f"Robustesse : gap sur {nb_graines} graines ({temps} s par essai)")
    plt.ylabel("Gap (%)")
    plt.tight_layout()
    plt.savefig("resultats/1_robustesse.png")
    plt.close()
    return stats


# =============================================================================
# 2. CONVERGENCE : gap en fonction du temps accordé
# =============================================================================
def experience_convergence(temps_liste=(2, 5, 10, 30)):
    """Est-ce que donner plus de temps améliore vraiment la solution ?"""
    essais = [{"nom": nom, "graine": 0, "temps_max": t}
              for nom in ["C201", "R201", "RC201", "X-n101-k25"] for t in temps_liste]
    df = lancer(essais, "2_convergence")

    plt.figure(figsize=(7, 4))
    for nom, groupe in df.groupby("instance"):
        plt.plot(groupe["temps_max"], groupe["gap_%"], marker="o", label=nom)
    plt.xlabel("Temps accordé (s)")
    plt.ylabel("Gap (%)")
    plt.title("Convergence : gap en fonction du temps de calcul")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("resultats/2_convergence.png")
    plt.close()
    return df.pivot(index="instance", columns="temps_max", values="gap_%")


# =============================================================================
# 3. TAILLE : de 100 à 1000 clients (CVRP, instances X)
# =============================================================================
def experience_taille(temps=60):
    """Comportement quand l'instance grossit (même temps accordé)."""
    lignes = []
    for nom in ["X-n101-k25", "X-n200-k36", "X-n502-k39", "X-n1001-k43"]:
        random.seed(0)
        b.charger_vrplib(nom)
        t0 = time.time()
        g.grasp_construction(0.2)               # temps d'UNE construction GRASP
        t_construction = time.time() - t0

        r = b.tester(nom, graine=0, temps_max=temps)
        r["temps_construction_s"] = round(t_construction, 2)
        print(f"{nom:12} n = {r['n']:5}  gap = {r['gap_%']:6.2f} %  "
              f"construction = {t_construction:.2f} s")
        lignes.append(r)
    df = pd.DataFrame(lignes)
    df.to_csv("resultats/3_taille.csv", index=False)

    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].plot(df["n"], df["gap_%"], marker="o")
    ax[0].set(xlabel="Nombre de clients", ylabel="Gap (%)",
              title=f"Gap selon la taille ({temps} s)")
    ax[1].plot(df["n"], df["temps_construction_s"], marker="o", color="orange")
    ax[1].set(xlabel="Nombre de clients", ylabel="Temps (s)",
              title="Temps d'une construction GRASP")
    for a in ax:
        a.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("resultats/3_taille.png")
    plt.close()
    return df[["instance", "n", "gap_%", "temps_construction_s"]]


# =============================================================================
# 4. SENSIBILITÉ AUX PARAMÈTRES
# =============================================================================
def experience_sensibilite(temps=10):
    """On fait varier UN paramètre à la fois, les autres gardent leur valeur par défaut."""
    instances = ["C201", "R101", "RC201"]
    essais = []
    for alpha in (0.0, 0.1, 0.2, 0.4, 0.7):
        essais += [{"nom": n, "temps_max": temps, "alpha": alpha} for n in instances]
    for taille in (3, 10, 20, 40):
        essais += [{"nom": n, "temps_max": temps, "taille_tabou": taille} for n in instances]
    df = lancer(essais, "4_sensibilite")

    # on sépare les deux séries (alpha varie / taille_tabou varie)
    df_alpha = df[df["taille_tabou"].isna()]
    df_tabou = df[df["alpha"].isna()]
    res_alpha = df_alpha.groupby("alpha")["gap_%"].mean().round(2)
    res_tabou = df_tabou.groupby("taille_tabou")["gap_%"].mean().round(2)

    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    res_alpha.plot(ax=ax[0], marker="o", title="Effet de alpha (RCL du GRASP)")
    res_tabou.plot(ax=ax[1], marker="o", color="green", title="Effet de la taille tabou")
    for a in ax:
        a.set_ylabel("Gap moyen (%)")
        a.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("resultats/4_sensibilite.png")
    plt.close()
    return res_alpha, res_tabou


if __name__ == "__main__":
    a_lancer = sys.argv[1:] or ["1", "2", "3", "4"]
    if "1" in a_lancer:
        print("=== 1. Robustesse ===");  print(experience_robustesse())
    if "2" in a_lancer:
        print("=== 2. Convergence ==="); print(experience_convergence())
    if "3" in a_lancer:
        print("=== 3. Taille ===");      print(experience_taille())
    if "4" in a_lancer:
        print("=== 4. Sensibilité ==="); print(*experience_sensibilite(), sep="\n")
