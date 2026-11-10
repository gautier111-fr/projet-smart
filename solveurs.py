"""
solveurs.py - Tous les algorithmes disponibles dans l'interface.

Le tabou et le GRASP de l'équipe sont dans grasp_tabou_cvrptw.py ; adaptateur.py les
branche sur l'interface (fonctions tabou et grasp).

COMMENT BRANCHER UNE AUTRE MÉTAHEURISTIQUE :
    1. mettre le fichier dans ce dossier ;
    2. il doit contenir une fonction avec EXACTEMENT cette signature :

        def resoudre(instance, temps_max=30, graine=0, suivi=None, **parametres):
            ...
            return routes          # ex : [[3, 7, 1], [5, 2]]  (sans le dépôt 0)

       - instance : dictionnaire créé par vrp_commun.charger_instance
                    (instance["distance"], instance["demande"], instance["fenetres"]...)
       - temps_max : temps de calcul autorisé en secondes (critère d'arrêt)
       - graine    : graine aléatoire (random.seed(graine)) pour pouvoir reproduire
       - suivi     : fonction optionnelle à appeler quand on trouve mieux :
                     if suivi: suivi(iteration, meilleur_cout)
                     -> sert à tracer la courbe de convergence
       - parametres : réglages propres à l'algo (taille de la liste tabou, alpha...)
    3. ajouter une ligne dans le dictionnaire FICHIERS_METAHEURISTIQUES ci-dessous.

C'est tout : l'interface, la vérification des contraintes, le gap et le
benchmark fonctionnent automatiquement avec le nouvel algorithme.
"""

import importlib
import math
import time

import numpy as np

from vrp_commun import temps_trajet

DERNIER_STATUT_PLNE = ""   # "Optimal" si la PLNE a prouvé l'optimalité


# ---------------------------------------------------------------------------
# Algorithme de référence : plus proche voisin (glouton)
# ---------------------------------------------------------------------------
def plus_proche_voisin(instance, temps_max=30, graine=0, suivi=None):
    """Construit les tournées une par une : le camion va toujours au client
    non livré le plus proche qui respecte la capacité, la fenêtre de temps et
    lui laisse le temps de rentrer au dépôt. Quand plus aucun client n'est
    possible, il rentre et un nouveau camion part.
    Sert de point de comparaison (et de solution initiale classique).
    """
    d, q, Q = instance["distance"], instance["demande"], instance["capacite"]
    fen, s = instance["fenetres"], instance["service"]
    depart = instance.get("heure_depart", fen[0, 0] if fen is not None else 0.0)
    fermeture_depot = fen[0, 1] if fen is not None else math.inf
    non_livres = set(range(1, instance["n"] + 1))
    routes = []

    while non_livres:
        route, charge, t, position = [], 0.0, depart, 0
        while True:
            candidats = np.fromiter(non_livres, dtype=int)
            candidats = candidats[np.argsort(d[position, candidats])]  # du plus proche au plus loin
            choisi = None
            for j in candidats:
                if charge + q[j] > Q:                                  # capacité
                    continue
                arrivee = t + temps_trajet(instance, position, j, t)
                debut = max(arrivee, fen[j, 0]) if fen is not None else arrivee
                if fen is not None and debut > fen[j, 1]:              # fenêtre fermée
                    continue
                fin = debut + s[j]
                if fin + temps_trajet(instance, j, 0, fin) > fermeture_depot:
                    continue                                           # retour impossible
                choisi = j
                break
            if choisi is None:
                break
            route.append(int(choisi))
            non_livres.discard(choisi)
            charge, t, position = charge + q[choisi], fin, choisi
        if not route:                         # client impossible à servir : on le signale
            route = [non_livres.pop()]        # (l'évaluation affichera la violation)
        routes.append(route)
    return routes


# ---------------------------------------------------------------------------
# Méthode exacte : PLNE du livrable 1 résolu par CBC (via PuLP)
# ---------------------------------------------------------------------------
def plne_exacte(instance, temps_max=60, graine=0, suivi=None):
    """Modèle PLNE du livrable 1 (version à 2 indices : comme les camions sont
    identiques, x_ij suffit, x_ijk n'apporte rien et ralentit le solveur).
    Réservé aux petites instances : le temps explose au-delà de ~15 clients.
    Le trafic n'est pas pris en compte dans ce modèle (durées fixes c_ij).
    """
    import pulp

    n = instance["n"]
    if n > 15:
        raise ValueError("La PLNE est réservée aux petites instances (15 clients maximum).")
    c, q, Q = instance["distance"], instance["demande"], instance["capacite"]
    fen, s, K = instance["fenetres"], instance["service"], instance["nb_vehicules"]
    V, C = range(n + 1), range(1, n + 1)

    pb = pulp.LpProblem("CVRPTW", pulp.LpMinimize)
    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", cat="Binary") for i in V for j in V if i != j}
    u = {i: pulp.LpVariable(f"u_{i}", lowBound=q[i], upBound=Q) for i in C}

    pb += pulp.lpSum(c[i, j] * x[i, j] for (i, j) in x)                   # objectif
    for j in C:                                                            # visite unique
        pb += pulp.lpSum(x[i, j] for i in V if i != j) == 1
        pb += pulp.lpSum(x[j, l] for l in V if l != j) == 1                # continuité
    pb += pulp.lpSum(x[0, j] for j in C) == pulp.lpSum(x[i, 0] for i in C)
    if K:
        pb += pulp.lpSum(x[0, j] for j in C) <= K                          # flotte
    for i in C:                                                            # capacité + MTZ
        for j in C:
            if i != j:
                pb += u[i] - u[j] + Q * x[i, j] <= Q - q[j]
    if fen is not None:                                                    # fenêtres de temps
        T = {i: pulp.LpVariable(f"T_{i}", lowBound=fen[i, 0], upBound=fen[i, 1]) for i in C}
        M = fen[0, 1] + s.max() + c.max()
        for j in C:
            pb += T[j] >= fen[0, 0] + c[0, j] - M * (1 - x[0, j])
            for i in C:
                if i != j:
                    pb += T[i] + s[i] + c[i, j] - T[j] <= M * (1 - x[i, j])
            pb += T[j] + s[j] + c[j, 0] <= fen[0, 1] + M * (1 - x[j, 0])

    pb.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=temps_max))
    global DERNIER_STATUT_PLNE
    # "Optimal" seulement si CBC a prouvé l'optimalité avant la limite de temps
    DERNIER_STATUT_PLNE = pulp.LpStatus[pb.status] if pb.sol_status == 1 else "Limite de temps"
    if pulp.LpStatus[pb.status] not in ("Optimal", "Not Solved"):
        raise RuntimeError(f"Le solveur n'a pas trouvé de solution ({pulp.LpStatus[pb.status]}).")

    # Reconstruction des tournées en suivant les arcs x_ij = 1 depuis le dépôt
    arcs = [(i, j) for (i, j), var in x.items() if var.value() and var.value() > 0.5]
    suivant = {i: j for (i, j) in arcs if i != 0}        # successeur de chaque client
    routes = []
    for premier in [j for (i, j) in arcs if i == 0]:      # chaque départ du dépôt = 1 camion
        route, courant = [], premier
        while courant != 0:
            route.append(courant)
            courant = suivant[courant]
        routes.append(route)
    return routes


# ---------------------------------------------------------------------------
# Registre des algorithmes
# ---------------------------------------------------------------------------
ALGORITHMES = {
    "Plus proche voisin (référence)": plus_proche_voisin,
    "PLNE exacte (≤ 15 clients)": plne_exacte,
}

# Nom affiché dans l'interface -> (fichier python sans .py, nom de la fonction)
FICHIERS_METAHEURISTIQUES = {
    "Recherche tabou": ("adaptateur", "tabou"),
    "GRASP": ("adaptateur", "grasp"),
}

ERREURS_CHARGEMENT = {}   # pour afficher dans l'interface pourquoi un algo manque

for nom_affiche, (module, fonction) in FICHIERS_METAHEURISTIQUES.items():
    try:
        ALGORITHMES[nom_affiche] = getattr(importlib.import_module(module), fonction)
    except ModuleNotFoundError:
        ERREURS_CHARGEMENT[nom_affiche] = f"fichier {module}.py pas encore ajouté"
    except Exception as erreur:                     # bug dans le fichier de l'équipe
        ERREURS_CHARGEMENT[nom_affiche] = f"erreur dans {module}.py : {erreur!r}"


def lancer(nom_algo, instance, temps_max=30, graine=0, parametres=None):
    """Lance un algorithme, chronomètre, et nettoie la sortie.

    Renvoie (routes, temps_de_calcul_en_s, historique) où historique est la
    liste des (temps, iteration, meilleur_cout) envoyés par 'suivi'.
    """
    historique = []
    debut = time.perf_counter()

    def suivi(iteration, cout):
        historique.append((time.perf_counter() - debut, iteration, float(cout)))

    resultat = ALGORITHMES[nom_algo](instance, temps_max=temps_max, graine=graine,
                                     suivi=suivi, **(parametres or {}))
    temps_calcul = time.perf_counter() - debut

    # Tolérance : on accepte aussi un dict {"routes": ...} ou un tuple (routes, cout)
    if isinstance(resultat, dict):
        resultat = resultat["routes"]
    elif isinstance(resultat, tuple):
        resultat = resultat[0]
    # On enlève le dépôt (0) si l'algo l'a laissé dans les tournées
    routes = [[int(c) for c in r if int(c) != 0] for r in resultat]
    routes = [r for r in routes if r]
    if not routes:
        raise RuntimeError("aucune tournée trouvée : essayez avec plus de temps de calcul.")
    return routes, temps_calcul, historique
