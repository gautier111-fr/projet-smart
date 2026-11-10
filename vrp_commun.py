"""
vrp_commun.py - Briques communes à TOUT le projet (interface + métaheuristiques).

Ce fichier contient :
    1. le chargement d'une instance (fichier VRPLIB) dans un dictionnaire simple ;
    2. le calcul de la matrice des distances (avec la bonne convention d'arrondi) ;
    3. le modèle de trafic (durée d'un trajet selon la tranche horaire) ;
    4. l'évaluation / vérification d'une solution (capacité, fenêtres, attente...) ;
    5. le calcul du gap par rapport à la meilleure solution connue (BKS) ;
    6. la création d'instances : exemple du livrable 1 et générateur de scénarios.

Règle importante : l'interface ET les métaheuristiques utilisent la MÊME matrice
inst["distance"]. Sinon le gap calculé n'a aucun sens.
"""

import os
from collections import Counter

import numpy as np
import vrplib

INFINI = float("inf")

# Profil de trafic par défaut : une "journée type" découpée en tranches.
# debut / fin sont en % de l'horizon de la journée, coef multiplie la durée :
# coef = 1.6 veut dire que le trajet dure 60 % plus longtemps qu'à vide.
PROFIL_TRAFIC_DEFAUT = [
    {"tranche": "Début de journée", "debut": 0, "fin": 10, "coef": 1.0},
    {"tranche": "Heure de pointe du matin", "debut": 10, "fin": 25, "coef": 1.6},
    {"tranche": "Matinée", "debut": 25, "fin": 50, "coef": 1.1},
    {"tranche": "Pause de midi", "debut": 50, "fin": 60, "coef": 1.3},
    {"tranche": "Après-midi", "debut": 60, "fin": 75, "coef": 1.1},
    {"tranche": "Heure de pointe du soir", "debut": 75, "fin": 90, "coef": 1.6},
    {"tranche": "Fin de journée", "debut": 90, "fin": 100, "coef": 1.0},
]


# ---------------------------------------------------------------------------
# 1. Distances
# ---------------------------------------------------------------------------
def matrice_distances(coords, arrondi):
    """Distance euclidienne entre chaque paire de points, puis arrondi.

    Conventions de la littérature (indispensables pour comparer aux BKS) :
      - "entier"     : arrondi à l'entier le plus proche (instances CVRP X) ;
      - "troncature" : tronqué à 1 décimale (instances VRPTW Solomon / Homberger) ;
      - "0.1"        : arrondi à 0,1 (exemple du livrable 1).
    """
    x, y = coords[:, 0], coords[:, 1]
    d = np.hypot(x[:, None] - x[None, :], y[:, None] - y[None, :])
    if arrondi == "entier":
        return np.floor(d + 0.5)
    if arrondi == "troncature":
        return np.floor(d * 10) / 10
    if arrondi == "0.1":
        return np.round(d, 1)
    return d


# ---------------------------------------------------------------------------
# 2. Chargement d'une instance
# ---------------------------------------------------------------------------
def construire_instance(nom, coords, demande, capacite, fenetres=None, service=None,
                        nb_vehicules=None, arrondi="entier", famille="",
                        bks=None, bks_routes=None):
    """Range toutes les données dans un dictionnaire unique (format du projet).

    Le sommet 0 est TOUJOURS le dépôt, les clients sont numérotés 1..n.
    """
    coords = np.asarray(coords, dtype=float)
    n = len(coords) - 1
    service = np.zeros(n + 1) if service is None else np.asarray(service, dtype=float)
    service[0] = 0.0                                    # pas de service au dépôt
    distance = matrice_distances(coords, arrondi)
    if fenetres is not None:
        fenetres = np.asarray(fenetres, dtype=float)
        horizon = fenetres[0, 1]                        # fermeture du dépôt
    else:
        # Pas d'horaires dans un CVRP : on suppose une journée assez longue
        # pour faire deux fois l'aller-retour le plus lointain (hypothèse).
        horizon = 4 * distance[0].max()
    return {
        "nom": nom,
        "famille": famille,
        "type": "CVRPTW" if fenetres is not None else "CVRP",
        "n": n,                                         # nombre de clients
        "coords": coords,                               # (n+1, 2)
        "demande": np.asarray(demande, dtype=float),    # (n+1,), demande[0] = 0
        "capacite": float(capacite),                    # Q
        "nb_vehicules": nb_vehicules,                   # K (None = illimité)
        "fenetres": fenetres,                           # (n+1, 2) [a_i, b_i] ou None
        "service": service,                             # (n+1,) temps de service s_i
        "distance": distance,                           # (n+1, n+1) c_ij
        "arrondi": arrondi,
        "horizon": float(horizon),
        "trafic": None,                                 # profil de trafic (ou None)
        "bks": bks,                                     # coût de la meilleure solution connue
        "bks_routes": bks_routes,
    }


def famille_instance(nom):
    """Déduit le 'scénario' d'une instance à partir de son nom."""
    if nom.startswith("X-"):
        return "CVRP X (Uchoa)"
    if nom.startswith(("Leuven", "Antwerp", "Brussels", "Ghent", "Flanders")):
        return "CVRP XXL (Belgique)"
    if nom.startswith("LOR-"):
        return "Lorraine (villes réelles)"
    if nom.startswith("GEN-"):
        morceaux = nom.split("-")                       # GEN-repartition-depot-fenetres-...
        fenetres = "sans fenêtres" if morceaux[3] == "aucune" else "fenêtres " + morceaux[3].replace("serrees", "serrées")
        return f"Généré ({morceaux[1]}, {fenetres})"
    if nom[:2] == "RC":
        lettre = "RC (mixte)"
    elif nom[0] == "C":
        lettre = "C (regroupés)"
    elif nom[0] == "R":
        lettre = "R (aléatoires)"
    else:
        return "Autre"
    serie = nom.lstrip("RC")[0]                         # '1' = horizon court, '2' = long
    fenetre = "fenêtres serrées" if serie == "1" else "fenêtres larges"
    return f"VRPTW {lettre}, {fenetre}"


def charger_instance(chemin):
    """Lit un fichier .vrp (et son .sol s'il existe) avec la bibliothèque vrplib."""
    if chemin.startswith("lorraine:"):                  # instances inventées (Metz / Nancy)
        from instances_lorraine import creer_instance_lorraine
        return creer_instance_lorraine(chemin[len("lorraine:"):])
    # Les fichiers Solomon d'origine (.txt) ont un format différent du format VRPLIB
    format_fichier = "solomon" if chemin.lower().endswith(".txt") else "vrplib"
    brut = vrplib.read_instance(chemin, instance_format=format_fichier, compute_edge_weights=False)
    fenetres = brut.get("time_window")
    service = brut.get("service_time", 0)
    if np.ndim(service) == 0:                           # une seule valeur pour tous
        service = np.full(len(brut["node_coord"]), float(service))
    nom = str(brut.get("name", os.path.basename(chemin))).strip()

    bks, bks_routes = None, None
    chemin_sol = os.path.splitext(chemin)[0] + ".sol"
    if os.path.exists(chemin_sol):
        sol = vrplib.read_solution(chemin_sol)
        bks, bks_routes = float(sol["cost"]), sol["routes"]

    return construire_instance(
        nom=nom,
        coords=brut["node_coord"],
        demande=brut["demand"],
        capacite=brut["capacity"],
        fenetres=fenetres,
        service=service,
        nb_vehicules=int(brut["vehicles"]) if "vehicles" in brut else None,
        arrondi="troncature" if fenetres is not None else "entier",
        famille=famille_instance(nom),
        bks=bks,
        bks_routes=bks_routes,
    )


# ---------------------------------------------------------------------------
# 3. Trafic : durée d'un trajet qui dépend de l'heure de départ
# ---------------------------------------------------------------------------
def coefficient_trafic(inst, heure):
    """Coefficient de la tranche horaire qui contient 'heure' (1.0 si aucune)."""
    pourcentage = 100 * heure / inst["horizon"]
    for tranche in inst["trafic"]:
        if tranche["debut"] <= pourcentage < tranche["fin"]:
            return tranche["coef"]
    return 1.0


def temps_trajet(inst, i, j, depart):
    """Durée du trajet i -> j quand on part à l'heure 'depart'.

    Sans trafic : durée = distance (convention des instances VRPLIB).
    Avec trafic : durée = distance x coefficient de la tranche horaire du départ
    (ex. 1.5 aux heures de pointe : le trajet dure 50 % plus longtemps).
    """
    duree = inst["distance"][i, j]
    if inst.get("trafic"):
        duree *= coefficient_trafic(inst, depart)
    return duree


# ---------------------------------------------------------------------------
# 4. Évaluation et vérification d'une solution
# ---------------------------------------------------------------------------
def evaluer(inst, routes):
    """Calcule le planning de chaque camion et vérifie TOUTES les contraintes.

    routes : liste de tournées, chaque tournée = liste de clients (sans le dépôt).
             Exemple : [[3, 7, 1], [5, 2]]
    Renvoie un dictionnaire avec la distance, la durée, les violations et le
    détail de chaque arrêt (arrivée, attente, début de service, fin).
    """
    n, d, q = inst["n"], inst["distance"], inst["demande"]
    fen, s, Q = inst["fenetres"], inst["service"], inst["capacite"]
    violations = []

    # --- Contrainte 1 : chaque client est livré exactement une fois ---
    compte = Counter(c for r in routes for c in r)
    invalides = sorted(c for c in compte if not 1 <= c <= n)
    manquants = [c for c in range(1, n + 1) if compte[c] == 0]
    doublons = sorted(c for c, k in compte.items() if k > 1 and 1 <= c <= n)
    if invalides:
        violations.append(f"Numéros de clients invalides : {invalides[:10]}")
    if manquants:
        violations.append(f"{len(manquants)} client(s) jamais livré(s) : {manquants[:10]}")
    if doublons:
        violations.append(f"{len(doublons)} client(s) livré(s) plusieurs fois : {doublons[:10]}")

    # --- Contrainte 5 : nombre de camions disponibles ---
    routes = [[c for c in r if 1 <= c <= n] for r in routes]
    routes = [r for r in routes if r]
    if inst["nb_vehicules"] and len(routes) > inst["nb_vehicules"]:
        violations.append(f"{len(routes)} camions utilisés pour {inst['nb_vehicules']} disponibles")

    depart = inst.get("heure_depart", fen[0, 0] if fen is not None else 0.0)
    tournees = []
    for k, route in enumerate(routes, start=1):
        t, precedent, distance, arrets = depart, 0, 0.0, []
        for c in route:
            arrivee = t + temps_trajet(inst, precedent, c, t)
            distance += d[precedent, c]
            ouverture, fermeture = (fen[c] if fen is not None else (0.0, INFINI))
            debut = max(arrivee, ouverture)            # attente autorisée si on est en avance
            ok = debut <= fermeture + 1e-6             # interdit de livrer après la fermeture
            if not ok:
                violations.append(f"Camion {k} : client {c} livré à {debut:.1f}, "
                                  f"fenêtre fermée à {fermeture:.0f}")
            fin = debut + s[c]
            arrets.append({"client": c, "arrivee": arrivee, "debut": debut,
                           "attente": debut - arrivee, "fin": fin,
                           "ouverture": ouverture, "fermeture": fermeture, "ok": ok})
            t, precedent = fin, c
        retour = t + temps_trajet(inst, precedent, 0, t)
        distance += d[precedent, 0]
        charge = q[route].sum()
        if charge > Q + 1e-9:                          # contrainte 3 : capacité
            violations.append(f"Camion {k} : charge {charge:.0f} > capacité {Q:.0f}")
        if fen is not None and retour > fen[0, 1] + 1e-6:
            violations.append(f"Camion {k} : retour au dépôt à {retour:.1f} après sa fermeture")
        tournees.append({"numero": k, "clients": list(route), "charge": charge,
                         "distance": distance, "depart": depart, "retour": retour,
                         "duree": retour - depart,
                         "attente": sum(a["attente"] for a in arrets), "arrets": arrets})

    return {
        "distance": sum(t["distance"] for t in tournees),   # coût VRPLIB (pour le gap)
        "duree": sum(t["duree"] for t in tournees),         # durée totale (avec trafic)
        "attente": sum(t["attente"] for t in tournees),
        "nb_vehicules": len(tournees),
        "realisable": not violations,
        "violations": violations,
        "tournees": tournees,
    }


def gap(cout, cout_reference):
    """gap (%) = 100 x (coût trouvé - coût optimal) / coût optimal  (formule du sujet)."""
    if not cout_reference:
        return None
    return 100 * (cout - cout_reference) / cout_reference


# ---------------------------------------------------------------------------
# 5. Instances "maison"
# ---------------------------------------------------------------------------
def exemple_livrable1():
    """L'instance à 6 clients du livrable 1 (optimum connu : 33,9 min)."""
    coords = [(0, 0), (-4, 3), (-2, 6), (1, 7), (4, 5), (5, 2), (2, 2.5)]
    demande = [0, 4, 3, 5, 2, 4, 3]
    fenetres = [(0, 100), (0, 10), (5, 15), (10, 20), (5, 15), (0, 10), (10, 20)]
    service = [0, 1, 1, 1, 1, 1, 1]
    return construire_instance("Exemple livrable 1", coords, demande, 12, fenetres,
                               service, nb_vehicules=2, arrondi="0.1",
                               famille="Exemple pédagogique", bks=33.9)


def generer_instance(n=100, repartition="uniforme", position_depot="centre",
                     fenetres="aucune", graine=0):
    """Génère un scénario d'usage réaliste.

    repartition    : "uniforme" (zone rurale), "clusters" (quartiers urbains), "mixte"
    position_depot : "centre" (entrepôt en ville) ou "coin" (entrepôt en périphérie)
    fenetres       : "aucune" (CVRP), "larges" ou "serrées" (CVRPTW)
    """
    rng = np.random.default_rng(graine)
    # Même échelle que les instances de référence : 0-1000 (X) ou 0-100 (Solomon)
    taille = 1000.0 if fenetres == "aucune" else 100.0

    def uniformes(k):
        return rng.uniform(0, taille, (k, 2))

    def en_clusters(k):
        centres = rng.uniform(0.1 * taille, 0.9 * taille, (max(3, k // 30), 2))
        choix = rng.integers(0, len(centres), k)
        return np.clip(centres[choix] + rng.normal(0, 0.04 * taille, (k, 2)), 0, taille)

    if repartition == "uniforme":
        clients = uniformes(n)
    elif repartition == "clusters":
        clients = en_clusters(n)
    else:
        clients = np.vstack([uniformes(n // 2), en_clusters(n - n // 2)])
    depot = [taille / 2, taille / 2] if position_depot == "centre" else [0.0, 0.0]
    coords = np.round(np.vstack([depot, clients]), 1)   # arrondi pour pouvoir sauvegarder
    demande = np.concatenate([[0], rng.integers(1, 31, n)])
    capacite = 150                                       # ~10 clients par tournée

    nom = f"GEN-{repartition}-{position_depot}-{fenetres}-n{n}-g{graine}".replace("é", "e")
    if fenetres == "aucune":
        return construire_instance(nom, coords, demande, capacite, arrondi="entier",
                                   famille=famille_instance(nom))

    horizon, s = 1000.0, 10.0
    service = np.full(n + 1, s)
    d = matrice_distances(coords, "troncature")
    largeur = 60.0 if fenetres == "serrées" else 300.0
    tw = [(0.0, horizon)]
    for i in range(1, n + 1):
        plus_tot = d[0, i]                               # on ne peut pas arriver avant
        plus_tard = horizon - s - d[i, 0]                # il faut pouvoir rentrer au dépôt
        centre = rng.uniform(plus_tot, plus_tard)
        tw.append((max(0.0, centre - largeur / 2), min(plus_tard, centre + largeur / 2)))
    return construire_instance(nom, coords, demande, capacite, tw, service,
                               arrondi="troncature", famille=famille_instance(nom))


def sauvegarder_instance(inst, chemin):
    """Écrit une instance au format VRPLIB (pour la réutiliser dans le benchmark)."""
    donnees = {
        "NAME": inst["nom"],
        "TYPE": inst["type"],
        "DIMENSION": inst["n"] + 1,
        "CAPACITY": int(inst["capacite"]),
        "EDGE_WEIGHT_TYPE": "EUC_2D",
        "NODE_COORD_SECTION": [[round(x, 2), round(y, 2)] for x, y in inst["coords"]],
        "DEMAND_SECTION": [int(v) for v in inst["demande"]],
    }
    if inst["fenetres"] is not None:
        donnees["SERVICE_TIME_SECTION"] = [float(v) for v in inst["service"]]
        donnees["TIME_WINDOW_SECTION"] = [[float(a), float(b)] for a, b in inst["fenetres"]]
    donnees["DEPOT_SECTION"] = [1]
    vrplib.write_instance(chemin, donnees)
