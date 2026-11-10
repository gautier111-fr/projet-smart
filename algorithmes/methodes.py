"""
methodes.py - Les trois méthodes proposées dans l'interface, et lancer() pour les chronométrer.

  Recherche tabou : une construction gloutonne, puis la recherche tabou jusqu'au temps maximum.
  GRASP           : des constructions au hasard répétées, chacune améliorée par un tabou court.
  PLNE exacte     : la solution optimale, pour les petites instances (voir plne.py).

Le tabou et le GRASP viennent du code de l'équipe (grasp_tabou_cvrptw.py). Ce code garde ses
données dans des variables globales : preparer() les remplit à partir de l'instance.
Toutes les méthodes ont la même forme :
    methode(instance, temps_max, graine, suivi) -> routes, ex. [[3, 7, 1], [5, 2]] (sans le dépôt 0)
"""

import random
import time

from algorithmes import grasp_tabou_cvrptw as equipe
from algorithmes.plne import plne_exacte
from probleme.contraintes import temps_trajet

INFINI = float("inf")


# ---------------------------------------------------------------------------
# 1. Brancher le code de l'équipe sur l'instance
# ---------------------------------------------------------------------------
def preparer(instance):
    """Copie l'instance de l'interface dans les variables du code de l'équipe."""
    fenetres = instance["fenetres"]
    equipe.n = instance["n"] + 1                      # nombre de sommets, dépôt compris
    equipe.q = instance["demande"].tolist()
    equipe.Q = instance["capacite"]
    equipe.tw = fenetres.tolist() if fenetres is not None else [(0, INFINI)] * equipe.n
    equipe.s = instance["service"].tolist()
    equipe.dist = instance["distance"].tolist()       # les mêmes distances que partout ailleurs
    equipe.depart = instance.get("heure_depart", equipe.tw[0][0])
    equipe.k_max = instance["nb_vehicules"]

    # Les 40 clients les plus proches de chaque sommet : le tabou et le GRASP ne regardent
    # qu'eux, c'est ce qui les rend rapides sur les grandes instances.
    ordre = instance["distance"].argsort(axis=1)      # chaque ligne : du plus proche au plus loin
    equipe.proches = [[int(j) for j in ligne if j not in (0, i)][:40] for i, ligne in enumerate(ordre)]

    if instance.get("trafic"):                        # durée = distance x coefficient de l'heure
        equipe.trajet = lambda i, j, heure: temps_trajet(instance, i, j, heure)
    else:
        equipe.trajet = lambda i, j, heure: equipe.dist[i][j]


# ---------------------------------------------------------------------------
# 2. Les deux métaheuristiques
# ---------------------------------------------------------------------------
def tabou(instance, temps_max=30, graine=0, suivi=None,
          taille_tabou=10, taille_echantillon=25):
    """Une seule construction gloutonne (alpha = 0, sans hasard), puis la recherche tabou
    jusqu'à la fin du temps (iter_max infini : seul le temps l'arrête)."""
    random.seed(graine)
    preparer(instance)
    solution = equipe.grasp_construction(alpha=0)
    if suivi:
        suivi(0, equipe.cout_solution(solution))
    return equipe.recherche_tabou(solution, taille_tabou, iter_max=INFINI,
                                  taille_echantillon=taille_echantillon,
                                  heure_fin=time.time() + temps_max, suivi=suivi)


def grasp(instance, temps_max=30, graine=0, suivi=None,
          alpha=0.1, taille_tabou=10, iter_max=30, taille_echantillon=25):
    """Multi-start : construction randomisée + tabou court, répétés jusqu'à la fin du temps ;
    on garde la meilleure solution. Valeurs par défaut : celles du benchmark de l'équipe."""
    random.seed(graine)
    preparer(instance)
    solution, _ = equipe.grasp_tabou(nb_starts=10**9, alpha=alpha, taille_tabou=taille_tabou,
                                     iter_max=iter_max, taille_echantillon=taille_echantillon,
                                     temps_max=temps_max, verbose=False, suivi=suivi)
    return solution


# ---------------------------------------------------------------------------
# 3. Les méthodes proposées, et leur lancement chronométré
# ---------------------------------------------------------------------------
METHODES = {
    "Recherche tabou": tabou,
    "GRASP": grasp,
    "PLNE exacte (≤ 15 clients)": plne_exacte,
}


def lancer(nom_algo, instance, temps_max=30, graine=0, parametres=None):
    """Lance une méthode et la chronomètre.

    Renvoie (routes, temps_de_calcul_en_s, historique) où historique est la
    liste des (temps, iteration, meilleur_cout) envoyés par 'suivi'.
    """
    historique = []
    debut = time.perf_counter()

    def suivi(iteration, cout):
        historique.append((time.perf_counter() - debut, iteration, float(cout)))

    resultat = METHODES[nom_algo](instance, temps_max=temps_max, graine=graine,
                                  suivi=suivi, **(parametres or {}))
    temps_calcul = time.perf_counter() - debut

    routes = [[int(c) for c in r] for r in resultat if len(r) > 0]
    if not routes:
        raise RuntimeError("aucune tournée trouvée : essayez avec plus de temps de calcul.")
    return routes, temps_calcul, historique
