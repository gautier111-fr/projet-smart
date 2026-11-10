"""
solveurs.py - Les méthodes proposées dans l'interface.

  Recherche tabou et GRASP : le code de l'équipe (grasp_tabou_cvrptw.py), branché par adaptateur.py.
  PLNE exacte              : le modèle du livrable 1, résolu par CBC (petites instances seulement).

Chaque méthode a la même forme :
    methode(instance, temps_max, graine, suivi) -> routes   ex. [[3, 7, 1], [5, 2]] (sans le dépôt 0)
"""

import time

from adaptateur import grasp, tabou

DERNIER_STATUT_PLNE = ""   # "Optimal" si la PLNE a prouvé l'optimalité


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
# Les méthodes proposées dans l'interface
# ---------------------------------------------------------------------------
ALGORITHMES = {
    "Recherche tabou": tabou,
    "GRASP": grasp,
    "PLNE exacte (≤ 15 clients)": plne_exacte,
}


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
