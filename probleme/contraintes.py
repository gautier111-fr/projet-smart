"""
contraintes.py - Les règles du problème : vérifier une solution, trafic, gap.

evaluer() est le juge : il recalcule chaque tournée et liste toutes les contraintes
non respectées (client oublié, capacité, fenêtre de temps, retour au dépôt, nombre de camions).
"""

from collections import Counter

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
# 1. Trafic : la durée d'un trajet dépend de l'heure de départ
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
# 2. Vérifier une solution
# ---------------------------------------------------------------------------

def evaluer(inst, routes):
    """Calcule le planning de chaque camion et vérifie TOUTES les contraintes.

    routes : liste de tournées, chaque tournée = liste de clients (sans le dépôt).
             Exemple : [[3, 7, 1], [5, 2]]
    Renvoie un dictionnaire avec la distance, le nombre de camions, les violations et le
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
            if debut > fermeture + 1e-6:               # interdit de livrer après la fermeture
                violations.append(f"Camion {k} : client {c} livré à {debut:.1f}, "
                                  f"fenêtre fermée à {fermeture:.0f}")
            fin = debut + s[c]
            arrets.append({"client": c, "arrivee": arrivee, "debut": debut,
                           "attente": debut - arrivee, "fin": fin})
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
                         "arrets": arrets})

    return {
        "distance": sum(t["distance"] for t in tournees),   # coût VRPLIB (pour le gap)
        "nb_vehicules": len(tournees),
        "realisable": not violations,
        "violations": violations,
        "tournees": tournees,
    }


# ---------------------------------------------------------------------------
# 3. Gap par rapport à la meilleure solution connue
# ---------------------------------------------------------------------------

def gap(cout, cout_reference):
    """gap (%) = 100 x (coût trouvé - coût optimal) / coût optimal  (formule du sujet)."""
    if not cout_reference:
        return None
    return 100 * (cout - cout_reference) / cout_reference
