"""
methodes.py - Les deux méthodes proposées dans l'interface, et lancer() pour les chronométrer.

  GRASP + Tabou : la métaheuristique de l'équipe (grasp_tabou_cvrptw.py). Le GRASP construit
                  des solutions, la recherche tabou les améliore, et on recommence (multi-start).
  PLNE exacte   : la solution optimale, pour les petites instances (plne.py).

Les deux ont la même forme : methode(instance, temps_max, graine) -> routes,
par exemple [[3, 7, 1], [5, 2]] (une liste de clients par camion, sans le dépôt 0).
"""

import random
import time

from algorithmes import grasp_tabou_cvrptw as equipe
from algorithmes.plne import plne_exacte
from probleme.contraintes import temps_trajet

GRASP_TABOU = "GRASP + Tabou"
PLNE = "PLNE exacte (≤ 15 clients)"


def preparer(instance):
    """Charge l'instance dans le code de l'équipe, avec les réglages de l'interface."""
    fenetres = instance["fenetres"]
    equipe.charger_instance(instance["coords"].tolist(), instance["demande"].tolist(),
                            instance["capacite"], None if fenetres is None else fenetres.tolist(),
                            instance["service"].tolist())
    equipe.dist = instance["distance"].tolist()       # les mêmes distances que partout ailleurs
    equipe.depart = instance.get("heure_depart", equipe.tw[0][0])
    equipe.k_max = instance["nb_vehicules"]
    if instance.get("trafic"):                        # durée = distance x coefficient de l'heure
        equipe.trajet = lambda i, j, heure: temps_trajet(instance, i, j, heure)
    else:
        equipe.trajet = lambda i, j, heure: equipe.dist[i][j]


def grasp_tabou(instance, temps_max=30, graine=0):
    """Construction GRASP + recherche tabou, répétées jusqu'à la fin du temps, avec les
    réglages du benchmark de l'équipe (alpha = 0,1 jusqu'à 500 clients, 0 au-delà)."""
    random.seed(graine)
    preparer(instance)
    alpha = 0.1 if instance["n"] <= 500 else 0.0
    solution, _ = equipe.grasp_tabou(nb_starts=10**9, alpha=alpha, taille_tabou=10, iter_max=30,
                                     taille_echantillon=25, temps_max=temps_max, verbose=False)
    return solution


METHODES = {GRASP_TABOU: grasp_tabou, PLNE: plne_exacte}


def lancer(nom, instance, temps_max=30, graine=0):
    """Lance une méthode et la chronomètre. Renvoie (routes, temps de calcul en s)."""
    debut = time.perf_counter()
    routes = [[int(c) for c in r] for r in METHODES[nom](instance, temps_max=temps_max, graine=graine) if r]
    if not routes:
        raise RuntimeError("aucune tournée trouvée : essayez avec plus de temps de calcul.")
    return routes, time.perf_counter() - debut
