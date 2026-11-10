# Bonus : suivi 3D (facultatif, hors programme)

Option d'affichage ajoutée à l'interface (onglet « Suivi 3D (bonus) »). **Elle ne calcule rien** :
elle reprend les tournées vérifiées par `evaluer()` et les met en scène dans une ville 3D.
Elle n'est pas nécessaire pour comprendre ou présenter la méthode.

| Fichier | Rôle |
|---|---|
| `suivi_3d.py` | prépare les données (lieux, tournées, horaires) et affiche la scène dans Streamlit |
| `scene.html` | la scène 3D (three.js) : ville générée, entrepôt, routes, camions animés, jour et nuit, trafic, panneaux |
| `lib/` | three.js r147 et OrbitControls (licence MIT, voir `lib/LICENSE`), copiés ici pour fonctionner sans internet |

Dans la scène : lecture / pause et vitesse (×0,5 à ×8), frise pour avancer dans la journée,
vue d'ensemble ou suivi d'un camion (clic sur un camion de la liste), vue depuis la cabine,
infobulle au survol d'un commerce ou de l'entrepôt, journal des livraisons. La ville
(immeubles, maisons, champs, arbres) est générée au hasard avec une graine fixe : elle est
toujours la même pour une instance donnée.
