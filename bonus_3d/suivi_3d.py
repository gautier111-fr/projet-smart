"""
BONUS (hors programme) - Suivi 3D d'une journée de livraison.

Option ajoutée pour l'affichage seulement : rien ici ne calcule de tournée. On reprend les
tournées déjà vérifiées par evaluer() (heure d'arrivée et de fin de chaque livraison) et on
les met en scène en 3D dans une ville générée (moteur three.js, dans scene.html).
Ce dossier n'est pas nécessaire pour comprendre ou présenter la méthode.
"""

import json
import os

import numpy as np
import streamlit as st

DOSSIER = os.path.dirname(os.path.abspath(__file__))
# Les mêmes couleurs que le suivi 2D (plotly), pour reconnaître les camions
COULEURS = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
            "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52"]


def donnees_scene(inst, ev):
    """Tout ce dont la scène 3D a besoin, en coordonnées de la scène."""
    xy = np.asarray(inst["coords"], dtype=float)
    # Échelle : deux lieux voisins sont à environ 22 unités (la place d'un pâté de maisons)
    echantillon = np.random.default_rng(0).choice(len(xy), size=min(len(xy), 400), replace=False)
    d = np.sqrt(((xy[echantillon, None, :] - xy[None, :, :]) ** 2).sum(axis=2))
    d[d == 0] = np.inf
    voisin = np.median(d.min(axis=1))
    k = 22 / voisin if np.isfinite(voisin) and voisin > 0 else 1.0
    centre = (xy.min(axis=0) + xy.max(axis=0)) / 2

    noms = inst.get("villes") or ["Entrepôt"] + [f"Client {i}" for i in range(1, inst["n"] + 1)]
    fen = inst["fenetres"]
    ouverture, fermeture = fen[0] if fen is not None else (0, inst["horizon"])
    lieux = [{"x": round(float((xy[i, 0] - centre[0]) * k), 2),
              "z": round(float(-(xy[i, 1] - centre[1]) * k), 2),
              "nom": noms[i], "demande": float(inst["demande"][i]),
              "fenetre": None if fen is None else [float(fen[i, 0]), float(fen[i, 1])]}
             for i in range(len(xy))]
    dist = inst["distance"]

    def arrets(t):                       # d = longueur du trajet qui mène à ce client (compteur de vitesse)
        lieux_tournee = [0] + [int(a["client"]) for a in t["arrets"]]
        return [{"client": int(a["client"]), "arrivee": float(a["arrivee"]), "debut": float(a["debut"]),
                 "fin": float(a["fin"]), "d": float(dist[lieux_tournee[k], lieux_tournee[k + 1]])}
                for k, a in enumerate(t["arrets"])]

    camions = [{"numero": t["numero"], "couleur": COULEURS[i % len(COULEURS)],
                "charge": float(t["charge"]), "depart": float(t["depart"]), "retour": float(t["retour"]),
                "arrets": arrets(t), "d_retour": float(dist[t["arrets"][-1]["client"], 0])}
               for i, t in enumerate(ev["tournees"])]
    return {"nom": inst["nom"], "lorraine": "villes" in inst, "capacite": float(inst["capacite"]),
            "ouverture": float(ouverture), "fermeture": float(fermeture),
            "horizon": float(inst["horizon"]), "trafic": inst.get("trafic"),
            "km_par_unite": 1 / 1.3 if "villes" in inst else 1.0,     # Lorraine : durée (min) = km x 1,3
            "lieux": lieux, "camions": camions}


def afficher_suivi_3d(inst, ev, hauteur=780):
    """Affiche la scène 3D dans la page Streamlit (three.js est embarqué : pas besoin d'internet)."""
    def lire(nom):
        with open(os.path.join(DOSSIER, nom), encoding="utf-8") as f:
            return f.read()

    donnees = json.dumps(donnees_scene(inst, ev), ensure_ascii=False).replace("</", "<\\/")
    page = lire("scene.html").replace("__DONNEES__", donnees)
    moteur = "\n".join(lire("lib/" + f) for f in ("three.min.js", "OrbitControls.js", "Sky.js"))
    page = page.replace("/*THREE*/", moteur)
    st.iframe(page, height=hauteur)
