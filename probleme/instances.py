"""
instances.py - Les données du problème : lire, créer et lister les instances.

Une instance est un dictionnaire (voir construire_instance). Le sommet 0 est le dépôt,
les clients vont de 1 à n. Tout le projet utilise la même matrice instance["distance"],
calculée avec l'arrondi des solutions de référence : sinon le gap serait faux.

Lancé seul (python -m probleme.instances), ce fichier recrée les instances de instances/GENERE.
"""

import glob
import os

import numpy as np
import vrplib

DOSSIER_INSTANCES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "instances")


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
# 2. Le dictionnaire instance
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


# ---------------------------------------------------------------------------
# 3. Lire les instances
# ---------------------------------------------------------------------------

def charger_instance(chemin):
    """Lit un fichier .vrp (et son .sol s'il existe) avec la bibliothèque vrplib."""
    if chemin.startswith("lorraine:"):                  # instances inventées (Metz / Nancy)
        from probleme.lorraine import creer_instance_lorraine
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


def lister_instances():
    """Parcourt les sous-dossiers de instances/ (CVRP, VRPTW, GENERE) et lit juste l'en-tête
    de chaque fichier. Les fichiers posés directement dans instances/ servent au
    benchmark_vrplib.py de l'équipe : on ne les compte pas deux fois."""
    liste = []
    for chemin in glob.glob(os.path.join(DOSSIER_INSTANCES, "*", "*.vrp")):
        entete = {}
        with open(chemin, encoding="utf-8", errors="replace") as f:
            for ligne in f:
                if "SECTION" in ligne:
                    break
                if ":" in ligne:
                    cle, valeur = ligne.split(":", 1)
                    entete[cle.strip()] = valeur.strip()
        nom = entete.get("NAME", os.path.basename(chemin)[:-4])
        liste.append({
            "nom": nom,
            "famille": famille_instance(nom),
            "type": "CVRPTW" if "TW" in entete.get("TYPE", "") else "CVRP",
            "n": int(entete["DIMENSION"]) - 1,
            "bks connue": os.path.exists(chemin[:-4] + ".sol"),
            "chemin": chemin,
        })
    from probleme.lorraine import lister_instances_lorraine
    liste += lister_instances_lorraine()                # villes de Metz / Nancy
    return sorted(liste, key=lambda i: (i["type"], i["n"], i["nom"]))


# ---------------------------------------------------------------------------
# 4. Instances créées par nous
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


# ---------------------------------------------------------------------------
# 5. Création des instances de instances/GENERE (déjà faite)
# ---------------------------------------------------------------------------

# Pour les petites, la PLNE calcule l'optimum, enregistré comme référence (.sol).
SCENARIOS_GENERES = [
    # (n, répartition, dépôt, fenêtres, description)
    (8, "uniforme", "centre", "serrées", "petite tournée de quartier (optimum par PLNE)"),
    (200, "clusters", "centre", "serrées", "centre-ville, quartiers denses, créneaux serrés"),
    (2000, "clusters", "coin", "aucune", "grande métropole : plusieurs milliers de clients"),
]


if __name__ == "__main__":
    from algorithmes import plne
    from probleme.contraintes import evaluer

    DOSSIER = os.path.join(DOSSIER_INSTANCES, "GENERE")
    os.makedirs(DOSSIER, exist_ok=True)
    for n, repartition, depot, fenetres, description in SCENARIOS_GENERES:
        inst = generer_instance(n, repartition, depot, fenetres, graine=1)
        chemin = os.path.join(DOSSIER, inst["nom"] + ".vrp")
        sauvegarder_instance(inst, chemin)
        print(f"{inst['nom']:45s} {description}")
        if n <= 12:
            routes = plne.plne_exacte(inst, temps_max=300)
            if plne.DERNIER_STATUT == "Optimal":
                cout = evaluer(inst, routes)["distance"]
                vrplib.write_solution(chemin[:-4] + ".sol", routes, {"Cost": round(cout, 1)})
                print(f"    optimum PLNE = {cout:.1f}")
