"""
Livrable 2 - GRASP + Recherche Tabou pour le CVRPTW
====================================================

Idée générale (même logique que le Workshop du sac à dos) :
  - une SOLUTION = une liste de tournées, chaque tournée = une liste de clients
    (le dépôt 0 n'est pas écrit, il est implicite au début et à la fin)
        ex : [[1, 2, 3], [5, 4, 6]]  <=>  0→1→2→3→0  et  0→5→4→6→0
  - GRASP  = construction gloutonne RANDOMISÉE (remplace random_solution())
  - TABOU  = on va au meilleur voisin non tabou, même s'il est moins bon
  - MULTI-START = on répète GRASP + Tabou plusieurs fois et on garde le meilleur

Fonctionne pour :
  - le CVRP   (si pas de fenêtres : a = 0, b = très grand, service = 0)
  - le CVRPTW (fenêtres de temps [a_i, b_i], attente autorisée)
"""

import math
import random
import time
from collections import deque


# =============================================================================
# 1. DONNÉES DE L'INSTANCE
# =============================================================================
# On stocke tout dans des variables globales, comme dans le workshop


def charger_instance(coords, demandes, Q_cap, fenetres=None, service=None):
    """
    Prépare l'instance.
    coords   : liste de (x, y), indice 0 = dépôt
    demandes : liste des demandes q_i (q_0 = 0)
    Q_cap    : capacité d'un camion
    fenetres : liste de (a_i, b_i)  (None => pas de fenêtres = CVRP)
    service  : liste des temps de service s_i (None => 0 partout)
    """
    global n, q, Q, tw, s, dist

    n = len(coords)                      # nombre de sommets (dépôt compris)
    q = list(demandes)
    Q = Q_cap
    tw = list(fenetres) if fenetres is not None else [(0, float("inf"))] * n
    s = list(service) if service is not None else [0] * n

    # PRÉ-CALCUL de la matrice des distances (indispensable, cf. livrable 1)
    # Pour des milliers de clients, numpy est conseillé (voir plus bas).
    dist = [[math.dist(coords[i], coords[j]) for j in range(n)] for i in range(n)]


# =============================================================================
# 2. FONCTIONS DE BASE (équivalent de poids_contenu / valeur_contenu)
# =============================================================================

def cout_tournee(tournee):
    """Distance totale d'une tournée (dépôt → clients → dépôt)."""
    if not tournee:
        return 0.0
    c = dist[0][tournee[0]] + dist[tournee[-1]][0]
    for i in range(len(tournee) - 1):
        c += dist[tournee[i]][tournee[i + 1]]
    return c


def cout_solution(solution):
    """Coût total = somme des coûts des tournées (fonction objectif Z)."""
    return sum(cout_tournee(t) for t in solution)


def tournee_valide(tournee):
    """
    Vérifie capacité ET fenêtres de temps (avec attente autorisée).
    C'est l'équivalent de 'poids_contenu(sac) <= capacite' du workshop.
    """
    # 1) Capacité
    if sum(q[i] for i in tournee) > Q:
        return False

    # 2) Fenêtres de temps : on simule le trajet du camion
    t = 0.0          # heure de départ du dépôt
    prec = 0         # on part du dépôt
    for i in tournee:
        t = t + s[prec] + dist[prec][i]   # arrivée chez i
        t = max(t, tw[i][0])              # attente si on arrive trop tôt
        if t > tw[i][1]:                  # trop tard => interdit
            return False
        prec = i

    # 3) Retour au dépôt avant sa fermeture
    t = t + s[prec] + dist[prec][0]
    return t <= tw[0][1]


# =============================================================================
# 3. CONSTRUCTION GRASP (remplace random_solution() du workshop)
# =============================================================================

def grasp_construction(alpha=0.3):
    """
    Construit une solution tournée par tournée.
    À chaque étape :
      1. on liste les clients qu'on peut ajouter à la fin de la tournée courante
         sans violer capacité / fenêtres
      2. on les classe par 'distance' depuis le dernier client
      3. RCL (Restricted Candidate List) : on garde les meilleurs
         (ceux dont le score <= min + alpha * (max - min))
      4. on en tire un AU HASARD dans la RCL  => c'est le côté "randomisé"
    alpha = 0 : glouton pur (plus proche voisin)  /  alpha = 1 : aléatoire pur
    """
    non_visites = set(range(1, n))
    solution = []

    while non_visites:
        tournee = []
        while True:
            dernier = tournee[-1] if tournee else 0

            # 1. candidats réalisables
            candidats = [j for j in non_visites if tournee_valide(tournee + [j])]
            if not candidats:
                break  # plus rien ne rentre => on ferme la tournée

            # 2. score = distance + un peu d'urgence (fermeture de fenêtre)
            #    => on privilégie les clients proches ET pressés
            score = {j: dist[dernier][j] + 0.1 * tw[j][1] if tw[j][1] != float("inf")
                     else dist[dernier][j] for j in candidats}

            # 3. RCL
            smin, smax = min(score.values()), max(score.values())
            seuil = smin + alpha * (smax - smin)
            rcl = [j for j in candidats if score[j] <= seuil]

            # 4. choix aléatoire dans la RCL
            choisi = random.choice(rcl)
            tournee.append(choisi)
            non_visites.remove(choisi)

        if not tournee:
            # un client ne rentre même pas seul dans un camion : instance infaisable
            raise ValueError(f"Clients impossibles à servir : {non_visites}")
        solution.append(tournee)

    return solution


# =============================================================================
# 4. VOISINAGE (équivalent de voisinage(sac) du workshop)
# =============================================================================
# Workshop : un voisin = on inverse UN objet du sac.
# Ici      : un voisin = on DÉPLACE UN client (relocate)
#            ou on ÉCHANGE deux clients (swap).
# On renvoie aussi le "mouvement" pour la liste tabou.

def voisinage(solution, taille_echantillon=None):
    """
    Générateur de voisins valides : (voisin, mouvement).
    mouvement = client déplacé (c'est lui qu'on rendra tabou).
    taille_echantillon : pour les grandes instances, on ne teste qu'un
    échantillon aléatoire de clients (sinon le voisinage est énorme).
    """
    tous_clients = [(r, p) for r, t in enumerate(solution) for p in range(len(t))]
    if taille_echantillon and len(tous_clients) > taille_echantillon:
        tous_clients = random.sample(tous_clients, taille_echantillon)

    for (r1, p1) in tous_clients:
        client = solution[r1][p1]

        # ----- RELOCATE : on retire 'client' et on le remet ailleurs -----
        for r2 in range(len(solution) + 1):          # +1 = ouvrir un nouveau camion
            if r2 == len(solution) and len(solution[r1]) == 1:
                continue                             # inutile : même solution
            dest = solution[r2] if r2 < len(solution) else []
            for p2 in range(len(dest) + 1):
                if r1 == r2 and (p2 == p1 or p2 == p1 + 1):
                    continue                         # même position
                # copie légère : on ne recopie que les tournées modifiées
                voisin = [t[:] for t in solution] + ([[]] if r2 == len(solution) else [])
                voisin[r1].pop(p1)
                p2_ajuste = p2 - 1 if (r1 == r2 and p2 > p1) else p2
                voisin[r2].insert(p2_ajuste, client)
                if tournee_valide(voisin[r1]) and tournee_valide(voisin[r2]):
                    yield [t for t in voisin if t], client

        # ----- SWAP : on échange 'client' avec un client d'une autre tournée -----
        for r2 in range(r1 + 1, len(solution)):
            for p2 in range(len(solution[r2])):
                voisin = [t[:] for t in solution]
                voisin[r1][p1], voisin[r2][p2] = voisin[r2][p2], voisin[r1][p1]
                if tournee_valide(voisin[r1]) and tournee_valide(voisin[r2]):
                    yield voisin, client


# =============================================================================
# 5. RECHERCHE TABOU (copie quasi conforme du workshop)
# =============================================================================

def recherche_tabou(solution_initiale, taille_tabou=10, iter_max=50,
                    taille_echantillon=None):
    """
    1. On part de la solution GRASP
    2. On prend le meilleur voisin dont le mouvement n'est pas tabou
       (même s'il est moins bon : c'est ce qui permet de sortir des optimums locaux)
    3. On rend tabou le client déplacé
    4. On s'arrête après iter_max itérations SANS amélioration
    Différence avec le workshop : on rend tabou un MOUVEMENT (le client déplacé)
    au lieu de la solution entière -> plus efficace pour le VRP.
    """
    liste_tabou = deque(maxlen=taille_tabou)

    solution_courante = solution_initiale
    meilleure_globale = solution_initiale
    cout_meilleure_globale = cout_solution(solution_initiale)

    nb_iter = 0
    while nb_iter < iter_max:
        meilleur_voisin, cout_meilleur, mouvement = None, float("inf"), None

        for voisin, client in voisinage(solution_courante, taille_echantillon):
            c = cout_solution(voisin)
            # Critère d'ASPIRATION : un mouvement tabou est accepté s'il bat le record
            autorise = client not in liste_tabou or c < cout_meilleure_globale
            if autorise and c < cout_meilleur:
                meilleur_voisin, cout_meilleur, mouvement = voisin, c, client

        if meilleur_voisin is None:      # aucun voisin possible
            break

        # on passe au meilleur voisin non tabou
        solution_courante = meilleur_voisin
        liste_tabou.append(mouvement)

        # mise à jour du record
        if cout_meilleur < cout_meilleure_globale - 1e-9:
            meilleure_globale = meilleur_voisin
            cout_meilleure_globale = cout_meilleur
            nb_iter = 0
        else:
            nb_iter += 1

    return meilleure_globale


# =============================================================================
# 6. GRASP COMPLET = MULTI-START (construction + tabou), comme au workshop
# =============================================================================

def grasp_tabou(nb_starts=10, alpha=0.3, taille_tabou=10, iter_max=50,
                taille_echantillon=None, temps_max=None, verbose=True):
    """Répète (construction GRASP -> recherche tabou) et garde la meilleure."""
    meilleure, cout_meilleure = None, float("inf")
    debut = time.time()

    for k in range(nb_starts):
        sol = grasp_construction(alpha)
        sol = recherche_tabou(sol, taille_tabou, iter_max, taille_echantillon)
        c = cout_solution(sol)
        if verbose:
            print(f"start {k + 1:3d} : coût = {c:9.1f}  ({len(sol)} camions)")
        if c < cout_meilleure:
            meilleure, cout_meilleure = sol, c
        if temps_max and time.time() - debut > temps_max:
            break

    return meilleure, cout_meilleure


def verifier_solution(solution):
    """Contrôle final : chaque client visité 1 fois + toutes tournées valides."""
    clients = sorted(c for t in solution for c in t)
    return clients == list(range(1, n)) and all(tournee_valide(t) for t in solution)


# =============================================================================
# 7. TESTS
# =============================================================================
if __name__ == "__main__":
    random.seed(42)

    # ---- Test 1 : l'instance du livrable 1 (optimum PuLP = 33.9) ----
    print("=== Instance d'exemple (6 clients) ===")
    coords = [(0, 0), (-4, 3), (-2, 6), (1, 7), (4, 5), (5, 2), (2, 2.5)]
    demandes = [0, 4, 3, 5, 2, 4, 3]
    fenetres = [(0, 1000), (0, 10), (5, 15), (10, 20), (5, 15), (0, 10), (10, 20)]
    service = [0, 1, 1, 1, 1, 1, 1]
    charger_instance(coords, demandes, 12, fenetres, service)

    sol, c = grasp_tabou(nb_starts=5, verbose=False)
    print("Solution :", [[0] + t + [0] for t in sol])
    print(f"Coût = {c:.1f}  (optimum PuLP : 33.9)  valide : {verifier_solution(sol)}\n")

    # ---- Test 2 : instance aléatoire de 100 clients (CVRP) ----
    print("=== Instance aléatoire 100 clients ===")
    coords = [(50, 50)] + [(random.uniform(0, 100), random.uniform(0, 100)) for _ in range(100)]
    demandes = [0] + [random.randint(1, 10) for _ in range(100)]
    charger_instance(coords, demandes, 50)
    t0 = time.time()
    sol, c = grasp_tabou(nb_starts=3, iter_max=30, taille_echantillon=30)
    print(f"Meilleur coût = {c:.1f}, valide : {verifier_solution(sol)}, "
          f"temps = {time.time() - t0:.1f} s")