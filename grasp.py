import os, random, time                            # fichiers, hasard, chronomètre
import vrplib                                      # bibliothèque imposée par le sujet

OPTIMUM = 27591                                    # coût optimal de X-n101-k25 (donné par VRPLIB)
if not os.path.exists("instance.vrp"):             # si le fichier de l'instance est absent
    raise SystemExit("Enregistre X-n101-k25.vrp (CVRPLIB) sous le nom instance.vrp, à côté de ce fichier")
inst = vrplib.read_instance("instance.vrp")        # lit le problème
dist = inst["edge_weight"].round()                 # distances entre tous les points, calculées une seule fois
demande = inst["demand"]                           # demande de chaque client (le dépôt 0 a 0)
Q = inst["capacity"]                               # capacité maximale d'un camion
n = len(demande) - 1                               # nombre de clients


def cout(routes):                                  # durée totale (= distance, vitesse 1)
    return int(sum(dist[a][b] for r in routes for a, b in zip([0] + r, r + [0])))  # dépôt -> clients -> dépôt


def charge(route):                                 # quantité transportée par un camion
    return sum(demande[c] for c in route)


# ---------- ÉTAPE A : CONSTRUIRE (méthode des économies + un peu de hasard) ----------
def construire(alpha):                             # alpha = part de hasard
    route_de = {c: [c] for c in range(1, n + 1)}   # au départ, un camion par client
    liste = []                                     # les fusions possibles de deux camions
    for i in range(1, n + 1):
        for j in range(i + 1, n + 1):
            gain = dist[0][i] + dist[0][j] - dist[i][j]    # km économisés si i et j partagent un camion
            liste.append((gain * random.uniform(1 - alpha, 1 + alpha), i, j))  # gain un peu bousculé
    liste.sort(reverse=True)                       # les plus grosses économies d'abord
    for gain, i, j in liste:
        ri, rj = route_de[i], route_de[j]          # camions de i et de j
        if ri is rj or charge(ri) + charge(rj) > Q:    # même camion ou trop chargé : on ignore
            continue
        if ri[-1] == i and rj[0] == j:             # i au bout de ri, j au début de rj
            nouveau = ri + rj
        elif ri[0] == i and rj[-1] == j:           # i au début de ri, j au bout de rj
            nouveau = rj + ri
        elif ri[0] == i and rj[0] == j:            # i et j au début : on retourne ri
            nouveau = ri[::-1] + rj
        elif ri[-1] == i and rj[-1] == j:          # i et j au bout : on retourne rj
            nouveau = ri + rj[::-1]
        else:                                      # i ou j est au milieu d'un camion
            continue
        for c in nouveau:                          # tous les clients du nouveau camion...
            route_de[c] = nouveau                  # ...savent dans quel camion ils sont
    return list({id(r): r for r in route_de.values()}.values())    # liste des camions, sans doublon


# ---------- ÉTAPE B : AMÉLIORER (déplacer un client, ou échanger deux clients) ----------
def essais(routes):                                # propose des changements sur 2 camions (a et b)
    for a in range(len(routes)):
        for b in range(len(routes)):
            for i, c in enumerate(routes[a]):      # c = client qu'on veut bouger
                sans = routes[a][:i] + routes[a][i + 1:]       # camion a sans le client c
                base = sans if a == b else routes[b]           # camion b de départ
                for p in range(len(base) + 1):     # DÉPLACER c à la place p du camion b
                    rb = base[:p] + [c] + base[p:]
                    yield a, b, (rb if a == b else sans), rb
                if a < b:                          # ÉCHANGER c avec chaque client d du camion b
                    for j, d in enumerate(routes[b]):
                        yield a, b, routes[a][:i] + [d] + routes[a][i + 1:], routes[b][:j] + [c] + routes[b][j + 1:]


def ameliorer(routes):                             # applique des changements tant que ça raccourcit
    trouve = True
    while trouve:
        trouve = False
        for a, b, ra, rb in essais(routes):
            if charge(ra) <= Q and charge(rb) <= Q and cout([ra, rb]) < cout([routes[a], routes[b]]):
                routes = list(routes)              # permis ET plus court : on garde !
                routes[a], routes[b] = ra, rb      # on remplace les deux camions
                routes = [r for r in routes if r]  # on enlève un éventuel camion vide
                trouve = True                      # on a gagné : on recommence
                break
    return routes


# ---------- GRASP : répéter (construire + améliorer) ----------
def grasp(nb_iterations, alpha):
    debut = time.time()                            # heure de départ
    meilleure, meilleur_cout, t_best = None, float("inf"), 0
    for _ in range(nb_iterations):
        routes = ameliorer(construire(alpha))      # étape A puis étape B
        if cout(routes) < meilleur_cout:           # meilleure solution jusqu'ici ?
            meilleure, meilleur_cout, t_best = routes, cout(routes), time.time() - debut
    return meilleure, meilleur_cout, t_best, time.time() - debut


# ---------- RÉSULTATS ----------
random.seed(0)                                     # même résultat à chaque lancement
routes, c, t_best, t_total = grasp(nb_iterations=20, alpha=0.05)
for k, r in enumerate(routes, start=1):            # un affichage par camion
    print(f"Camion {k:2d} : {' -> '.join(map(str, [0] + r + [0]))} | charge {charge(r)}/{Q} | durée {cout([r])}")
gap = 100 * (c - OPTIMUM) / OPTIMUM                # formule du gap du sujet
print(f"Camions : {len(routes)} | Durée totale : {c} | Optimum : {OPTIMUM}")
print(f"Temps de calcul : {t_total:.1f} s ({t_best:.1f} s pour trouver la meilleure)")
print(f"Gap : {gap:.2f} %", "-> VERTE" if gap <= 7 else "-> ORANGE" if gap <= 10 else "-> ROUGE")