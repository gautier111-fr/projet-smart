"""
lorraine.py - Deux petites instances inventées sur de vraies communes de Moselle.

Elles servent à comparer la PLNE et GRASP + Tabou (notebook, partie 9) et à montrer de
vrais horaires et le trafic dans l'interface. Hypothèses simples (à rappeler à l'oral) :
    - position des communes : latitude / longitude réelles (approximatives) ;
    - durée d'un trajet (minutes) = distance à vol d'oiseau (km) x 1,3 : les routes font
      environ 30 % de détours, et à 60 km/h, 1 km de route prend 1 minute ;
    - les heures sont en minutes depuis minuit (480 = 8h00) ;
    - entrepôt ouvert de 6h00 à 20h00, 15 minutes de livraison par client ;
    - chaque commerce a un créneau : matin (8h-12h), après-midi (14h-18h) ou journée (8h-18h) ;
    - trafic : bouchons le matin (7h-9h) et le soir (16h30-19h).
Les demandes et les créneaux sont tirés au hasard (graine fixe = toujours la même instance).
"""

import math

import numpy as np

from probleme.instances import construire_instance

# Nom de la commune -> (latitude, longitude)
COMMUNES = {
    # Metz et son agglomération
    "Metz": (49.1193, 6.1757), "Woippy": (49.1500, 6.1500),
    "Montigny-lès-Metz": (49.1000, 6.1500), "Marly": (49.0650, 6.1500),
    "Ars-sur-Moselle": (49.0794, 6.0731), "Moulins-lès-Metz": (49.1039, 6.1067),
    "Maizières-lès-Metz": (49.2117, 6.1600), "Talange": (49.2361, 6.1711),
    "Gorze": (49.0519, 6.0003), "Pange": (49.0800, 6.3600),
    "Courcelles-Chaussy": (49.1100, 6.4000),
    # Est mosellan
    "Boulay-Moselle": (49.1833, 6.4931), "Bouzonville": (49.2917, 6.5333),
    "Faulquemont": (49.0436, 6.5975), "Saint-Avold": (49.1047, 6.7064),
    "Creutzwald": (49.2056, 6.6956), "Forbach": (49.1883, 6.8964),
    "Sarreguemines": (49.1100, 7.0683), "Morhange": (48.9233, 6.6408),
    "Château-Salins": (48.8186, 6.5133), "Dieuze": (48.8125, 6.7178),
    "Vic-sur-Seille": (48.7833, 6.5333), "Delme": (48.8869, 6.3944),
    "Sarrebourg": (48.7353, 7.0539),
}

# Nom du scénario -> entrepôt, communes livrées, créneaux ou non, nombre de camions, capacité
SCENARIOS = {
    "LOR-Metz-agglo": {         # 10 clients, avec créneaux (optimum calculé par la PLNE)
        "depot": "Metz",
        "clients": ["Woippy", "Montigny-lès-Metz", "Marly", "Ars-sur-Moselle",
                    "Moulins-lès-Metz", "Maizières-lès-Metz", "Talange", "Gorze",
                    "Pange", "Courcelles-Chaussy"],
        "creneaux": True, "camions": 3, "capacite": 100,
    },
    "LOR-Moselle-Est": {        # 15 clients, zone rurale, sans créneaux (CVRP)
        "depot": "Metz",
        "clients": ["Pange", "Courcelles-Chaussy", "Boulay-Moselle", "Bouzonville",
                    "Faulquemont", "Saint-Avold", "Creutzwald", "Forbach", "Sarreguemines",
                    "Morhange", "Château-Salins", "Dieuze", "Vic-sur-Seille", "Delme",
                    "Sarrebourg"],
        "creneaux": False, "camions": 4, "capacite": 120,
    },
}

# Optimum prouvé par la PLNE (algorithmes/plne.py) pour la petite instance
OPTIMUM_CONNU = {"LOR-Metz-agglo": 113.2}   # minutes de trajet

# Bouchons en % de la journée [0h ; 20h] : 7h = 35 %, 9h = 45 %, etc.
TRAFIC_LORRAINE = [
    {"tranche": "Bouchons du matin (7h-9h)", "debut": 35, "fin": 45, "coef": 1.5},
    {"tranche": "Midi (12h-14h)", "debut": 60, "fin": 70, "coef": 1.2},
    {"tranche": "Bouchons du soir (16h30-19h)", "debut": 82.5, "fin": 95, "coef": 1.5},
]

CRENEAUX = [(480, 720), (840, 1080), (480, 1080)]   # matin, après-midi, journée (minutes)


def creer_instance_lorraine(nom):
    """Construit l'instance d'un scénario (toujours la même grâce à la graine fixe)."""
    scenario = SCENARIOS[nom]
    lieux = [scenario["depot"]] + scenario["clients"]
    lat = np.array([COMMUNES[v][0] for v in lieux])
    lon = np.array([COMMUNES[v][1] for v in lieux])

    # Coordonnées en km (projection simple, suffisante à l'échelle d'une région)
    km_par_degre_lon = 111.32 * math.cos(math.radians(49))
    coords = np.column_stack([(lon - lon.min()) * km_par_degre_lon, (lat - lat.min()) * 111.32])

    rng = np.random.default_rng(2026)                 # graine fixe
    n = len(lieux) - 1
    demande = np.concatenate([[0], rng.integers(5, 31, n)])          # colis
    fenetres, service = None, None
    if scenario["creneaux"]:
        choix = rng.integers(0, len(CRENEAUX), n)
        fenetres = [(360, 1200)] + [CRENEAUX[k] for k in choix]       # dépôt 6h-20h
        service = [0] + [15] * n                                      # 15 min par livraison

    inst = construire_instance(nom, coords, demande, scenario["capacite"], fenetres, service,
                               nb_vehicules=scenario["camions"], arrondi="aucun",
                               famille="Lorraine (villes réelles)",
                               bks=OPTIMUM_CONNU.get(nom))
    # Distance en km -> durée en minutes : x 1,3 (détours), à 60 km/h
    inst["distance"] = np.round(inst["distance"] * 1.3, 1)
    if not scenario["creneaux"]:
        inst["horizon"] = 1200.0
    inst["heure_depart"] = 360.0                      # les camions partent à 6h00
    inst["villes"] = lieux                            # pour afficher les noms
    inst["profil_trafic"] = TRAFIC_LORRAINE
    return inst


def lister_instances_lorraine():
    """Même format que instances.lister_instances()."""
    return [{"nom": nom, "type": "CVRPTW" if s["creneaux"] else "CVRP",
             "n": len(s["clients"]), "chemin": "lorraine:" + nom}
            for nom, s in SCENARIOS.items()]
