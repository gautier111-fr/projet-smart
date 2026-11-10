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

import numpy as np

# Active / désactive le mouvement 2-opt dans le voisinage.
# Sur nos tests (100 clients aléatoires) il n'améliorait pas le coût :
# on le laisse en OPTION pour le comparer sur les instances VRPLIB.
UTILISER_2OPT = False

# Voisinage restreint : pour chaque client, on ne regarde que ses K plus proches
# voisins (insertion à côté d'eux, échange avec eux) au lieu de TOUS les clients.
# Indispensable pour les grandes instances. None = voisinage complet.
# On ne l'active qu'au-delà de SEUIL_KNN clients : sur les petites instances
# avec fenêtres de temps, la bonne place d'un client n'est pas toujours à côté
# de ses voisins géographiques (testé : RC2 passait de 5,2 % à 8,4 % de gap).
K_VOISINS = 30
SEUIL_KNN = 500

# AJOUT interface : réglages remplis par l'interface (voir algorithmes/methodes.py).
# Avec ces valeurs par défaut, le code fonctionne exactement comme avant.
depart = 0.0      # heure de départ des camions (360 = 6h00 pour les instances de Lorraine)
k_max = None      # nombre de camions disponibles (None = illimité)


def trajet(i, j, heure):
    """AJOUT interface : durée du trajet i -> j en partant à 'heure'.
    Par défaut c'est la distance ; l'interface la remplace quand le trafic est activé."""
    return dist[i][j]


# =============================================================================
# 1. DONNÉES DE L'INSTANCE
# =============================================================================
# On stocke tout dans des variables globales, comme dans le workshop


def charger_instance(coords, demandes, Q_cap, fenetres=None, service=None,
                     arrondi=None):
    """
    Prépare l'instance.
    coords   : liste de (x, y), indice 0 = dépôt
    demandes : liste des demandes q_i (q_0 = 0)
    Q_cap    : capacité d'un camion
    fenetres : liste de (a_i, b_i)  (None => pas de fenêtres = CVRP)
    service  : liste des temps de service s_i (None => 0 partout)
    arrondi  : None (distance exacte), "dixieme" (tronquée à 0,1) ou "entier"
               -> conventions des instances de référence (voir benchmark)
    """
    global n, q, Q, tw, s, dist, proches

    n = len(coords)                      # nombre de sommets (dépôt compris)
    q = list(demandes)
    Q = Q_cap
    tw = list(fenetres) if fenetres is not None else [(0, float("inf"))] * n
    s = list(service) if service is not None else [0] * n

    # PRÉ-CALCUL de la matrice des distances avec numpy (calcul vectorisé :
    # toutes les distances d'un coup, bien plus rapide qu'une double boucle)
    c = np.array(coords, dtype=float)
    d = np.sqrt(((c[:, None, :] - c[None, :, :]) ** 2).sum(axis=2))
    if arrondi == "dixieme":
        d = np.floor(d * 10) / 10
    elif arrondi == "entier":
        d = np.rint(d)
    # on repasse en listes Python : lire dist[i][j] case par case est plus
    # rapide sur une liste que sur un tableau numpy
    dist = d.tolist()

    # Les K plus proches voisins de chaque client (le dépôt 0 est exclu)
    petite = n - 1 <= SEUIL_KNN
    k = n - 2 if (K_VOISINS is None or petite) else min(K_VOISINS, n - 2)
    d_clients = d.copy()
    d_clients[:, 0] = np.inf                 # on ne veut pas le dépôt
    np.fill_diagonal(d_clients, np.inf)      # ni le client lui-même
    if k > 0:
        proches = np.argsort(d_clients, axis=1)[:, :k].tolist()
    else:
        proches = [[] for _ in range(n)]


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
    t = depart       # heure de départ du dépôt (AJOUT interface : 0 avant)
    prec = 0         # on part du dépôt
    for i in tournee:
        t = t + s[prec]                   # fin du service chez le précédent
        t = t + trajet(prec, i, t)        # arrivée chez i (AJOUT interface : trajet() gère le trafic)
        t = max(t, tw[i][0])              # attente si on arrive trop tôt
        if t > tw[i][1]:                  # trop tard => interdit
            return False
        prec = i

    # 3) Retour au dépôt avant sa fermeture
    t = t + s[prec]
    t = t + trajet(prec, 0, t)
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
        charge, heure = 0, depart   # charge du camion et heure d'arrivée chez le dernier
        while True:
            dernier = tournee[-1] if tournee else 0

            # 1. candidats réalisables, testés en O(1) chacun : on ne re-simule
            #    PAS toute la tournée, on part de (charge, heure) du dernier client
            candidats = []
            for j in non_visites:
                if charge + q[j] > Q:
                    continue                                   # capacité
                fin = heure + s[dernier]                       # départ de chez le dernier
                arrivee = max(fin + trajet(dernier, j, fin), tw[j][0])
                if arrivee > tw[j][1]:
                    continue                                   # trop tard chez j
                if arrivee + s[j] + trajet(j, 0, arrivee + s[j]) > tw[0][1]:
                    continue                                   # retour au dépôt
                candidats.append(j)
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
            fin = heure + s[dernier]
            heure = max(fin + trajet(dernier, choisi, fin), tw[choisi][0])
            charge += q[choisi]
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
#            ou on ÉCHANGE deux clients (swap)
#            ou on INVERSE un morceau de tournée (2-opt).
#
# ACCÉLÉRATION (version 2) :
#   Avant, pour chaque voisin on recopiait TOUTE la solution puis on
#   recalculait TOUT le coût  => O(n) par voisin, beaucoup trop lent.
#   Maintenant, un voisin n'est plus une solution complète mais un MOUVEMENT
#   (quelques indices). Son coût se calcule par DIFFÉRENCE (delta) avec
#   seulement 3 ou 4 distances => O(1) par voisin.
#   On ne vérifie la validité (capacité / fenêtres) QUE si le mouvement est
#   intéressant, et on ne construit la nouvelle solution QUE pour le
#   mouvement finalement choisi.

def autour(tournee, p):
    """Renvoie (précédent, suivant) du client en position p (0 = dépôt)."""
    prec = tournee[p - 1] if p > 0 else 0
    suiv = tournee[p + 1] if p < len(tournee) - 1 else 0
    return prec, suiv


def voisinage(solution, taille_echantillon=None):
    """
    Générateur de mouvements : (delta, mouvement).
      delta     = nouveau coût - coût actuel (négatif = amélioration)
      mouvement = ("relocate" | "swap" | "2opt", r1, p1, r2, p2)
    ATTENTION : la validité n'est PAS vérifiée ici (voir mouvement_valide).
    taille_echantillon : pour les grandes instances, on ne teste qu'un
    échantillon aléatoire de clients (sinon le voisinage est énorme).
    """
    # position de chaque client : position[client] = (tournée, rang)
    position = {}
    for r, t in enumerate(solution):
        for p, cl in enumerate(t):
            position[cl] = (r, p)

    tous_clients = list(position.values())
    if taille_echantillon and len(tous_clients) > taille_echantillon:
        tous_clients = random.sample(tous_clients, taille_echantillon)

    for (r1, p1) in tous_clients:
        t1 = solution[r1]
        c = t1[p1]
        a, b = autour(t1, p1)
        # gain obtenu en retirant c :  a -> c -> b  devient  a -> b
        delta_retrait = dist[a][b] - dist[a][c] - dist[c][b]

        # ----- RELOCATE : on retire c et on le remet entre x et y -----
        # ouvrir un nouveau camion : 0 -> c -> 0 (AJOUT interface : seulement s'il en reste un)
        if len(t1) > 1 and (k_max is None or len(solution) < k_max):
            yield delta_retrait + 2 * dist[0][c], ("relocate", r1, p1, len(solution), 0)

        # On n'essaie que les positions JUSTE AVANT ou JUSTE APRÈS un des K plus
        # proches voisins v de c : insérer c loin de tout n'est jamais intéressant.
        for v in proches[c]:
            r2, pv = position[v]
            t2 = solution[r2]
            for p2 in (pv, pv + 1):                  # insertion AVANT la position p2
                if r1 == r2 and (p2 == p1 or p2 == p1 + 1):
                    continue                         # même position
                x = t2[p2 - 1] if p2 > 0 else 0
                y = t2[p2] if p2 < len(t2) else 0
                if r1 == r2:                         # même tournée : c n'est plus là
                    if x == c:
                        x = a
                    if y == c:
                        y = b
                # coût ajouté en insérant c :  x -> y  devient  x -> c -> y
                delta_insert = dist[x][c] + dist[c][y] - dist[x][y]
                yield delta_retrait + delta_insert, ("relocate", r1, p1, r2, p2)

        # ----- SWAP : on échange c avec un proche voisin d d'une autre tournée -----
        for d in proches[c]:
            r2, p2 = position[d]
            if r2 == r1:
                continue
            t2 = solution[r2]
            e, f = autour(t2, p2)
            delta = (dist[a][d] + dist[d][b] - dist[a][c] - dist[c][b]
                     + dist[e][c] + dist[c][f] - dist[e][d] - dist[d][f])
            yield delta, ("swap", r1, p1, r2, p2)

        # ----- 2-OPT : on inverse le morceau t1[p1..p2] DANS la même tournée -----
        #   a -> [c ... e] -> f   devient   a -> [e ... c] -> f
        #   seuls 2 arcs changent : (a,c) et (e,f) sont remplacés par (a,e) et (c,f)
        #   (le morceau du milieu garde la même longueur car dist est symétrique)
        if not UTILISER_2OPT:
            continue
        for p2 in range(p1 + 1, len(t1)):
            e = t1[p2]
            f = t1[p2 + 1] if p2 < len(t1) - 1 else 0
            delta = dist[a][e] + dist[c][f] - dist[a][c] - dist[e][f]
            yield delta, ("2opt", r1, p1, r1, p2)


def tournees_modifiees(solution, mouvement):
    """
    Construit UNIQUEMENT les tournées touchées par le mouvement.
    Renvoie un dict {indice_tournee: nouvelle_tournee}.
    """
    type_mvt, r1, p1, r2, p2 = mouvement
    if type_mvt == "swap":
        t1, t2 = solution[r1][:], solution[r2][:]
        t1[p1], t2[p2] = t2[p2], t1[p1]
        return {r1: t1, r2: t2}

    if type_mvt == "2opt":
        t = solution[r1]
        # on garde le début, on inverse le morceau [p1..p2], on garde la fin
        return {r1: t[:p1] + t[p1:p2 + 1][::-1] + t[p2 + 1:]}

    # relocate
    c = solution[r1][p1]
    t1 = solution[r1][:p1] + solution[r1][p1 + 1:]
    if r1 == r2:
        p2 = p2 - 1 if p2 > p1 else p2   # les positions ont glissé d'un cran
        t1.insert(p2, c)
        return {r1: t1}
    t2 = solution[r2][:] if r2 < len(solution) else []
    t2.insert(p2, c)
    return {r1: t1, r2: t2}


def clients_touches(solution, mouvement):
    """
    Clients concernés par le mouvement (ce sont eux qu'on rend tabou).
      relocate : le client déplacé
      swap     : les 2 clients échangés
      2-opt    : les 2 extrémités du morceau inversé
    Sans ça, le 2-opt pourrait ré-inverser le morceau juste après => boucle.
    """
    type_mvt, r1, p1, r2, p2 = mouvement
    if type_mvt == "relocate":
        return (solution[r1][p1],)
    return (solution[r1][p1], solution[r2][p2])


def mouvement_valide(solution, mouvement):
    """Vérifie capacité + fenêtres sur les seules tournées modifiées."""
    return all(tournee_valide(t) for t in tournees_modifiees(solution, mouvement).values())


def appliquer_mouvement(solution, mouvement):
    """Renvoie la nouvelle solution (on ne recopie que les tournées touchées)."""
    nouvelle = solution[:] + [[]]        # [[]] : place pour un éventuel nouveau camion
    for r, t in tournees_modifiees(solution, mouvement).items():
        nouvelle[r] = t
    return [t for t in nouvelle if t]    # on retire les tournées vides


# =============================================================================
# 5. RECHERCHE TABOU (copie quasi conforme du workshop)
# =============================================================================

def recherche_tabou(solution_initiale, taille_tabou=10, iter_max=50,
                    taille_echantillon=None, heure_fin=None, suivi=None):
    """
    1. On part de la solution GRASP
    2. On prend le meilleur voisin dont le mouvement n'est pas tabou
       (même s'il est moins bon : c'est ce qui permet de sortir des optimums locaux)
    3. On rend tabou le client déplacé
    4. On s'arrête après iter_max itérations SANS amélioration
    Différence avec le workshop : on rend tabou un MOUVEMENT (le client déplacé)
    au lieu de la solution entière -> plus efficace pour le VRP.
    AJOUT interface : suivi(iteration, cout) est appelé à chaque nouveau record
                      (courbe de convergence de l'interface).
    """
    liste_tabou = deque(maxlen=taille_tabou)

    solution_courante = solution_initiale
    cout_courant = cout_solution(solution_initiale)   # calculé UNE seule fois
    meilleure_globale = solution_initiale
    cout_meilleure_globale = cout_courant

    nb_iter = 0
    iteration = 0                    # AJOUT interface (pour suivi)
    while nb_iter < iter_max:
        iteration += 1
        # arrêt forcé si le temps total est dépassé (grandes instances)
        if heure_fin and time.time() > heure_fin:
            break
        meilleur_mvt, delta_meilleur = None, float("inf")

        for delta, mvt in voisinage(solution_courante, taille_echantillon):
            # 1) test rapide sur le coût AVANT le test de validité (plus cher)
            if delta >= delta_meilleur:
                continue
            # 2) Critère d'ASPIRATION : un mouvement tabou est accepté s'il bat le record
            est_tabou = any(cl in liste_tabou
                            for cl in clients_touches(solution_courante, mvt))
            autorise = (not est_tabou
                        or cout_courant + delta < cout_meilleure_globale - 1e-9)
            # 3) seulement maintenant on vérifie capacité / fenêtres
            if autorise and mouvement_valide(solution_courante, mvt):
                meilleur_mvt, delta_meilleur = mvt, delta

        if meilleur_mvt is None:         # aucun voisin possible
            break

        # on passe au meilleur voisin non tabou (et on rend tabou les clients touchés)
        liste_tabou.extend(clients_touches(solution_courante, meilleur_mvt))
        solution_courante = appliquer_mouvement(solution_courante, meilleur_mvt)
        cout_courant += delta_meilleur   # mise à jour du coût par différence

        # mise à jour du record
        if cout_courant < cout_meilleure_globale - 1e-9:
            meilleure_globale = solution_courante
            cout_meilleure_globale = cout_courant
            nb_iter = 0
            if suivi:                    # AJOUT interface : courbe de convergence
                suivi(iteration, cout_meilleure_globale)
        else:
            nb_iter += 1

    return meilleure_globale


# =============================================================================
# 6. GRASP COMPLET = MULTI-START (construction + tabou), comme au workshop
# =============================================================================

def grasp_tabou(nb_starts=10, alpha=0.3, taille_tabou=10, iter_max=50,
                taille_echantillon=None, temps_max=None, verbose=True, suivi=None):
    """Répète (construction GRASP -> recherche tabou) et garde la meilleure."""
    meilleure, cout_meilleure = None, float("inf")
    debut = time.time()

    for k in range(nb_starts):
        sol = grasp_construction(alpha)
        fin = debut + temps_max if temps_max else None
        sol = recherche_tabou(sol, taille_tabou, iter_max, taille_echantillon, fin)
        c = cout_solution(sol)
        if verbose:
            print(f"start {k + 1:3d} : coût = {c:9.1f}  ({len(sol)} camions)")
        if c < cout_meilleure:
            meilleure, cout_meilleure = sol, c
            if suivi:                    # AJOUT interface : courbe de convergence
                suivi(k + 1, c)
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