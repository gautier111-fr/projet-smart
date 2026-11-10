"""
lorraine.py - Instances inventées sur de vraies communes autour de Metz et Nancy.

Hypothèses simples (à rappeler à l'oral) :
    - position des communes : latitude / longitude réelles (approximatives) ;
    - durée d'un trajet (minutes) = distance à vol d'oiseau (km) x 1.3
      (les routes ne sont pas droites) / vitesse moyenne de 60 km/h ;
    - les heures sont en minutes depuis minuit (480 = 8h00) ;
    - entrepôt ouvert de 6h00 à 20h00, 15 minutes de livraison par client ;
    - chaque commerce a un créneau : matin (8h-12h), après-midi (14h-18h)
      ou journée (8h-18h) ;
    - trafic : bouchons le matin (7h-9h) et le soir (16h30-19h).
Les demandes et les créneaux sont tirés au hasard (graine fixe = toujours
la même instance).
"""

import math

import numpy as np

from probleme.instances import construire_instance

# (nom, latitude, longitude)
COMMUNES = [
    # Agglomération de Metz
    ("Metz", 49.1193, 6.1757), ("Woippy", 49.1500, 6.1500),
    ("Montigny-lès-Metz", 49.1000, 6.1500), ("Marly", 49.0650, 6.1500),
    ("Ars-sur-Moselle", 49.0794, 6.0731), ("Moulins-lès-Metz", 49.1039, 6.1067),
    ("Maizières-lès-Metz", 49.2117, 6.1600), ("Talange", 49.2361, 6.1711),
    ("Hagondange", 49.2536, 6.1683), ("Amnéville", 49.2581, 6.1417),
    ("Rombas", 49.2500, 6.1000), ("Gorze", 49.0519, 6.0003),
    ("Novéant-sur-Moselle", 49.0236, 6.0478), ("Pange", 49.0800, 6.3600),
    ("Courcelles-Chaussy", 49.1100, 6.4000),
    # Nord : Thionville, vallée de la Fensch, Pays-Haut
    ("Thionville", 49.3579, 6.1683), ("Yutz", 49.3580, 6.1890),
    ("Hayange", 49.3297, 6.0619), ("Fameck", 49.2989, 6.1097),
    ("Florange", 49.3214, 6.1208), ("Sierck-les-Bains", 49.4392, 6.3586),
    ("Briey", 49.2486, 5.9389), ("Jarny", 49.1583, 5.8783),
    ("Jœuf", 49.2297, 6.0122), ("Homécourt", 49.2222, 5.9931),
    ("Villerupt", 49.4672, 5.9289), ("Audun-le-Tiche", 49.4719, 5.9564),
    ("Longwy", 49.5197, 5.7661),
    # Est mosellan
    ("Boulay-Moselle", 49.1833, 6.4931), ("Bouzonville", 49.2917, 6.5333),
    ("Faulquemont", 49.0436, 6.5975), ("Saint-Avold", 49.1047, 6.7064),
    ("Creutzwald", 49.2056, 6.6956), ("Forbach", 49.1883, 6.8964),
    ("Sarreguemines", 49.1100, 7.0683), ("Morhange", 48.9233, 6.6408),
    ("Château-Salins", 48.8186, 6.5133), ("Dieuze", 48.8125, 6.7178),
    ("Vic-sur-Seille", 48.7833, 6.5333), ("Delme", 48.8869, 6.3944),
    ("Sarrebourg", 48.7353, 7.0539),
    # Entre Metz et Nancy
    ("Pont-à-Mousson", 48.9053, 6.0544), ("Dieulouard", 48.8433, 6.0700),
    ("Nomeny", 48.8894, 6.2272), ("Thiaucourt-Regniéville", 48.9564, 5.8611),
    # Agglomération de Nancy
    ("Nancy", 48.6921, 6.1844), ("Vandœuvre-lès-Nancy", 48.6575, 6.1700),
    ("Laxou", 48.6847, 6.1514), ("Villers-lès-Nancy", 48.6731, 6.1525),
    ("Malzéville", 48.7122, 6.1847), ("Saint-Max", 48.7017, 6.2061),
    ("Essey-lès-Nancy", 48.7069, 6.2236), ("Tomblaine", 48.6847, 6.2156),
    ("Jarville-la-Malgrange", 48.6703, 6.2025), ("Heillecourt", 48.6514, 6.1950),
    ("Ludres", 48.6211, 6.1683), ("Champigneulles", 48.7339, 6.1647),
    ("Frouard", 48.7597, 6.1336), ("Pompey", 48.7714, 6.1225),
    ("Liverdun", 48.7483, 6.0647), ("Neuves-Maisons", 48.6164, 6.1053),
    ("Saint-Nicolas-de-Port", 48.6283, 6.3008), ("Dombasle-sur-Meurthe", 48.6239, 6.3497),
    # Sud et ouest de la Meurthe-et-Moselle
    ("Toul", 48.6750, 5.8917), ("Colombey-les-Belles", 48.5297, 5.8964),
    ("Vézelise", 48.4872, 6.0919), ("Lunéville", 48.5894, 6.4964),
    ("Baccarat", 48.4497, 6.7392), ("Blâmont", 48.5900, 6.8442),
]

def _communes_entre(lat_min, lat_max, lon_min, lon_max):
    """Les communes situées dans un rectangle (latitude, longitude)."""
    return [c[0] for c in COMMUNES
            if lat_min <= c[1] <= lat_max and lon_min <= c[2] <= lon_max]


# Nom du scénario -> entrepôt, communes livrées, créneaux ou non, nombre de camions, capacité
SCENARIOS = {
    "LOR-Metz-agglo": {
        "description": "Petite tournée dans l'agglomération de Metz (optimum calculé par PLNE)",
        "depot": "Metz",
        "clients": ["Woippy", "Montigny-lès-Metz", "Marly", "Ars-sur-Moselle",
                    "Moulins-lès-Metz", "Maizières-lès-Metz", "Talange", "Gorze",
                    "Pange", "Courcelles-Chaussy"],
        "creneaux": True, "camions": 3, "capacite": 100,
    },
    "LOR-Nancy-agglo": {
        "description": "Livraison de commerces dans l'agglomération de Nancy",
        "depot": "Nancy",
        "clients": [c for c in _communes_entre(48.55, 48.80, 5.85, 6.40) if c != "Nancy"][:20],
        "creneaux": True, "camions": 5, "capacite": 100,
    },
    "LOR-Moselle-Est": {
        "description": "Zone rurale de l'est mosellan, sans créneaux (CVRP)",
        "depot": "Metz",
        "clients": _communes_entre(48.70, 49.35, 6.35, 7.10),
        "creneaux": False, "camions": 4, "capacite": 120,
    },
    "LOR-Sillon-lorrain": {
        "description": "Axe Thionville - Metz - Nancy, entrepôt à Pont-à-Mousson",
        "depot": "Pont-à-Mousson",
        "clients": [c for c in _communes_entre(48.60, 49.40, 5.85, 6.30)
                    if c != "Pont-à-Mousson"][:40],
        "creneaux": True, "camions": 9, "capacite": 100,
    },
    "LOR-Lorraine-complete": {
        "description": "Toutes les communes, entrepôt à Metz, créneaux + bouchons",
        "depot": "Metz",
        "clients": [c[0] for c in COMMUNES if c[0] != "Metz"],
        "creneaux": True, "camions": 16, "capacite": 100,
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
    position = {c[0]: (c[1], c[2]) for c in COMMUNES}
    lieux = [scenario["depot"]] + scenario["clients"]
    lat = np.array([position[v][0] for v in lieux])
    lon = np.array([position[v][1] for v in lieux])

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
    # Distance en km -> durée en minutes : x 1.3 (détours) / 60 km/h x 60 min
    inst["distance"] = np.round(inst["distance"] * 1.3, 1)
    if not scenario["creneaux"]:
        inst["horizon"] = 1200.0
    inst["heure_depart"] = 360.0                      # les camions partent à 6h00
    inst["villes"] = lieux                            # pour afficher les noms
    inst["latlon"] = np.column_stack([lat, lon])      # pour la vraie carte
    inst["profil_trafic"] = TRAFIC_LORRAINE
    inst["description"] = scenario["description"]
    return inst


def lister_instances_lorraine():
    """Même format que instances.lister_instances()."""
    return [{"nom": nom, "type": "CVRPTW" if s["creneaux"] else "CVRP",
             "n": len(s["clients"]), "chemin": "lorraine:" + nom}
            for nom, s in SCENARIOS.items()]
