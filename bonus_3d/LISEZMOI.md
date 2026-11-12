# Bonus : suivi 3D (facultatif, hors programme)

Option d'affichage ajoutée à l'interface (onglet « Suivi 3D (bonus) »). **Elle ne calcule rien** :
elle reprend les tournées vérifiées par `evaluer()` et les met en scène dans une ville 3D.
Elle n'est pas nécessaire pour comprendre ou présenter la méthode.

| Fichier | Rôle |
|---|---|
| `suivi_3d.py` | prépare les données (lieux, tournées, horaires, distances) et affiche la scène dans Streamlit |
| `scene.html` | la scène 3D (three.js) |
| `lib/` | three.js r147, OrbitControls et Sky (licence MIT, voir `lib/LICENSE`), copiés ici pour fonctionner sans internet |

Ce qu'on y voit :
* **une ville générée** (toujours la même pour une instance) : commerces des clients avec vitrine,
  store et enseigne ; entrepôt avec quais et bureaux ; tours vitrées, immeubles, maisons ; trottoirs,
  lampadaires, arbres, champs ; voitures qui circulent ;
* **la journée** : ciel physique (lever et coucher du soleil, étoiles et lune), ombres, reflets du ciel
  sur les vitres ; la nuit, fenêtres, enseignes, lampadaires et phares s'allument ;
* **les camions** : ils accélèrent, roulent à droite, freinent (feux stop), clignotent dans les virages,
  se garent devant le commerce ; un livreur descend à l'arrière, porte le colis jusqu'à la porte,
  le pose (il y reste) et revient ; repère au-dessus de chaque client (à livrer, en cours, livré) ;
* **les vues** : vue d'ensemble, suivi d'un camion (clic sur le camion ou dans la liste) avec GPS et
  compteur de vitesse, vue depuis la cabine, mode cinéma (la caméra filme seule), plein écran ;
* **les commandes** : lecture, vitesse ×0,5 à ×8, frise de la journée, son (moteur, ville),
  qualité de l'image (baissée automatiquement si l'ordinateur peine).
