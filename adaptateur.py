"""
adaptateur.py - Branche le code de l'équipe (grasp_tabou_cvrptw.py) sur l'interface.

Le code de l'équipe garde ses données dans des variables globales (n, q, Q, tw, s, dist).
preparer() les remplit à partir de l'instance de l'interface, puis on lance l'algorithme.

Deux méthodes, pour pouvoir les comparer :
  - tabou : UNE construction gloutonne (alpha = 0), puis recherche tabou jusqu'au temps max ;
  - grasp : construction RANDOMISÉE répétée (multi-start), chacune améliorée par un tabou court.
"""

import random
import time

import grasp_tabou_cvrptw as equipe
from vrp_commun import temps_trajet

INFINI = float("inf")


def preparer(instance):
    """Copie l'instance de l'interface dans les variables du code de l'équipe."""
    fenetres = instance["fenetres"]
    equipe.n = instance["n"] + 1                          # sommets, dépôt compris
    equipe.q = instance["demande"].tolist()
    equipe.Q = instance["capacite"]
    equipe.tw = fenetres.tolist() if fenetres is not None else [(0, INFINI)] * equipe.n
    equipe.s = instance["service"].tolist()
    equipe.dist = instance["distance"].tolist()           # mêmes distances (et arrondis) que l'interface
    equipe.depart = instance.get("heure_depart", equipe.tw[0][0])
    equipe.k_max = instance["nb_vehicules"]
    # AMÉLIORATION : pour chaque sommet, ses 40 clients les plus proches (sans lui-même ni le dépôt).
    # Le tabou et le GRASP ne regardent qu'eux : beaucoup plus rapide sur les grandes instances.
    ordre = instance["distance"].argsort(axis=1)       # chaque ligne : sommets du plus proche au plus loin
    equipe.proches = [[int(j) for j in ligne if j != 0 and j != i][:40] for i, ligne in enumerate(ordre)]
    if instance.get("trafic"):                            # durée = distance x coefficient de l'heure
        equipe.trajet = lambda i, j, heure: temps_trajet(instance, i, j, heure)
    else:
        equipe.trajet = lambda i, j, heure: equipe.dist[i][j]


def tabou(instance, temps_max=30, graine=0, suivi=None,
          taille_tabou=10, taille_echantillon=25):
    random.seed(graine)
    preparer(instance)
    solution = equipe.grasp_construction(alpha=0)         # glouton pur : pas de hasard
    if suivi:
        suivi(0, equipe.cout_solution(solution))
    return equipe.recherche_tabou(solution, taille_tabou, iter_max=INFINI,
                                  taille_echantillon=taille_echantillon,
                                  heure_fin=time.time() + temps_max, suivi=suivi)


def grasp(instance, temps_max=30, graine=0, suivi=None,
          alpha=0.2, taille_tabou=10, iter_max=30, taille_echantillon=25):
    random.seed(graine)
    preparer(instance)
    solution, _ = equipe.grasp_tabou(nb_starts=10**9, alpha=alpha, taille_tabou=taille_tabou,
                                     iter_max=iter_max, taille_echantillon=taille_echantillon,
                                     temps_max=temps_max, verbose=False, suivi=suivi)
    return solution
