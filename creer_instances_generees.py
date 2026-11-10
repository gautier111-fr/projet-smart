"""
creer_instances_generees.py - Crée les instances de scénarios d'usage
(à lancer une seule fois : python creer_instances_generees.py).

Elles complètent les instances VRPLIB avec des cas typiques du terrain :
livraison urbaine avec créneaux serrés, zone rurale, entrepôt en périphérie,
très grande instance (plusieurs milliers de clients)...
Pour les petites instances, la PLNE calcule l'optimum, qui est enregistré
comme solution de référence (.sol) : on obtient ainsi un vrai gap à l'optimum.
"""

import os

import vrplib

import solveurs
from vrp_commun import evaluer, generer_instance, sauvegarder_instance

DOSSIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instances", "GENERE")

SCENARIOS = [
    # (n, répartition, dépôt, fenêtres, description)
    (8, "uniforme", "centre", "serrées", "petite tournée de quartier (optimum par PLNE)"),
    (200, "clusters", "centre", "serrées", "centre-ville, quartiers denses, créneaux serrés"),
    (2000, "clusters", "coin", "aucune", "grande métropole : plusieurs milliers de clients"),
]

if __name__ == "__main__":
    os.makedirs(DOSSIER, exist_ok=True)
    for n, repartition, depot, fenetres, description in SCENARIOS:
        inst = generer_instance(n, repartition, depot, fenetres, graine=1)
        chemin = os.path.join(DOSSIER, inst["nom"] + ".vrp")
        sauvegarder_instance(inst, chemin)
        print(f"{inst['nom']:45s} {description}")
        if n <= 12:
            routes = solveurs.plne_exacte(inst, temps_max=300)
            if solveurs.DERNIER_STATUT_PLNE == "Optimal":
                cout = evaluer(inst, routes)["distance"]
                vrplib.write_solution(chemin[:-4] + ".sol", routes, {"Cost": round(cout, 1)})
                print(f"    optimum PLNE = {cout:.1f}")
