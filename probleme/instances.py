"""
instances.py - Les données du problème : lire, créer et lister les instances.

Une instance est un dictionnaire (voir construire_instance). Le sommet 0 est le dépôt,
les clients vont de 1 à n. Tout le projet utilise la même matrice instance["distance"],
calculée avec l'arrondi des solutions de référence : sinon le gap serait faux.

Les instances de instances/GENERE ont été créées une fois (clients uniformes ou en grappes,
dépôt au centre ou dans un coin, fenêtres serrées ou aucune) ; l'optimum de la plus petite
a été calculé par la PLNE.
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
                        nb_vehicules=None, arrondi="entier", famille="", bks=None):
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
        "horizon": float(horizon),
        "trafic": None,                                 # profil de trafic (ou None)
        "bks": bks,                                     # coût de la meilleure solution connue
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

    chemin_sol = os.path.splitext(chemin)[0] + ".sol"
    bks = float(vrplib.read_solution(chemin_sol)["cost"]) if os.path.exists(chemin_sol) else None

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
        liste.append({"nom": entete.get("NAME", os.path.basename(chemin)[:-4]),
                      "type": "CVRPTW" if "TW" in entete.get("TYPE", "") else "CVRP",
                      "n": int(entete["DIMENSION"]) - 1, "chemin": chemin})
    from probleme.lorraine import lister_instances_lorraine
    liste += lister_instances_lorraine()                # villes de Metz / Nancy
    return sorted(liste, key=lambda i: (i["type"], i["n"], i["nom"]))


# ---------------------------------------------------------------------------
# 4. L'exemple du livrable 1
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
