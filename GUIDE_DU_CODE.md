# Guide du code

Ce guide explique chaque fichier et chaque partie du code, dans l'ordre où on les utilise.
Pour installer et lancer le projet, voir le [README](README.md).

---

## 1. Vue d'ensemble

Le trajet d'une résolution, quel que soit le point de départ (interface, benchmark, notebook) :

```
 instance         ──►  méthode de résolution  ──►  tournées          ──►  vérification
 (les données)         (GRASP, tabou, PLNE)        [[3, 7, 1], [5, 2]]     (contraintes, coût, gap)
```

* Une **tournée** est la liste des clients d'un camion, sans le dépôt : `[3, 7, 1]` veut
  dire dépôt → 3 → 7 → 1 → dépôt. Une **solution** est une liste de tournées.
* Le sommet **0 est toujours le dépôt** ; les clients sont numérotés de 1 à n.
* Les méthodes ne font que **calculer des tournées**. La vérification est faite à part, de
  la même façon pour toutes les méthodes : la comparaison est donc équitable.

Où se trouve chaque étape :

| Étape | Fichier |
|---|---|
| lire ou créer une instance | `probleme/instances.py`, `probleme/lorraine.py` |
| résoudre | `algorithmes/grasp_tabou_cvrptw.py`, `algorithmes/plne.py`, `algorithmes/methodes.py` |
| vérifier, trafic, gap | `probleme/contraintes.py` |
| afficher et étudier | `app.py`, `interface/graphiques.py`, `interface/etude.py` |
| benchmark et étude du notebook | `benchmark_vrplib.py`, `etude_statistique.py` |

---

## 2. Le dossier `probleme/` : les données et les règles

### `instances.py` : lire, créer et lister les instances

Une instance est un **dictionnaire**, le même partout dans le projet :

| Clé | Contenu |
|---|---|
| `nom`, `famille`, `type` | nom, famille (X, Solomon, Lorraine…), « CVRP » ou « CVRPTW » |
| `n` | nombre de clients |
| `coords` | coordonnées (x, y) de chaque sommet |
| `demande` | `demande[i]` = quantité à livrer au client i (0 pour le dépôt) |
| `capacite` | capacité Q d'un camion |
| `nb_vehicules` | nombre de camions disponibles (`None` = illimité) |
| `distance` | matrice des distances / durées : `distance[i, j]` |
| `fenetres` | `fenetres[i] = [ouverture, fermeture]`, ou `None` en CVRP |
| `service` | temps de livraison chez chaque client |
| `horizon` | fin de la journée (fermeture du dépôt) |
| `trafic` | profil de trafic, ou `None` s'il est désactivé |
| `bks` | coût de la meilleure solution connue, ou `None` |

Les fonctions, partie par partie :

1. **Distances** : `matrice_distances(coords, arrondi)` calcule toutes les distances
   euclidiennes, avec **l'arrondi des solutions de référence** : entier pour les instances
   X, troncature à 1 décimale pour Solomon et Homberger. Sans ça, le gap serait faux de
   plusieurs pour cent.
2. **Le dictionnaire** : `construire_instance(...)` range les données ; `famille_instance(nom)`
   déduit la famille du nom (« VRPTW R (aléatoires), fenêtres serrées »…).
3. **Lire** : `charger_instance(chemin)` lit un fichier `.vrp` avec `vrplib`, et son `.sol`
   s'il existe (la meilleure solution connue). `lister_instances()` donne les 20 instances
   de l'interface : les sous-dossiers `instances/CVRP`, `VRPTW`, `GENERE` et les 5 de Lorraine.
4. **Instances créées par nous** : `exemple_livrable1()` (6 clients, optimum 33,9) et
   `generer_instance(n, repartition, depot, fenetres)` (clients uniformes, en grappes ou
   mixtes ; dépôt au centre ou dans un coin ; fenêtres aucune, larges ou serrées).
5. **Création de `instances/GENERE`** (déjà faite) : `python -m probleme.instances` recrée les
   3 instances générées. Pour la petite, la PLNE calcule l'optimum, enregistré dans le `.sol`.

### `lorraine.py` : 5 instances sur de vraies villes

68 communes de Moselle et de Meurthe-et-Moselle avec leur vraie position. Hypothèses :

* durée (min) = distance à vol d'oiseau (km) × 1,3 (les routes ne sont pas droites), à 60 km/h ;
* départ des camions à 6h00, dépôt fermé à 20h00, 15 min de livraison par client ;
* créneaux : matin (8h-12h), après-midi (14h-18h) ou journée (8h-18h) ;
* trafic : bouchons de 7h à 9h et de 16h30 à 19h (× 1,5), midi (× 1,2) ;
* demandes et créneaux tirés au hasard avec une **graine fixe** : l'instance est toujours la même.

`SCENARIOS` décrit les 5 instances (entrepôt, communes, créneaux, camions, capacité) et
`creer_instance_lorraine(nom)` les construit.

### `contraintes.py` : vérifier une solution, trafic, gap

1. **Trafic** : la journée est découpée en tranches, chacune avec un coefficient.
   `temps_trajet(instance, i, j, depart)` = distance × coefficient de la tranche de l'heure
   de départ (sans trafic : la distance). Un trajet de 20 min qui part en heure de pointe
   (× 1,5) dure 30 min. Limite assumée : le coefficient ne change pas en cours de route.
2. **Vérifier** : `evaluer(instance, routes)` est **le juge**. Il simule la journée de chaque
   camion, arrêt par arrêt :

   ```
   heure = heure de départ du dépôt
   pour chaque client de la tournée :
       arrivée = heure + temps_trajet(position, client, heure)
       début   = max(arrivée, ouverture)        ← en avance : on attend
       si début > fermeture : violation         ← livrer en retard est interdit
       heure   = début + temps de service
   retour au dépôt : violation s'il est fermé
   ```

   Il contrôle aussi que chaque client est livré **une seule fois**, la **capacité** de
   chaque camion et le **nombre de camions**. Il renvoie la distance, la durée, l'attente,
   `realisable` (vrai / faux), la liste des violations en clair et le détail de chaque arrêt
   (utilisé par le planning et le suivi).
3. **Gap** : `gap(cout, reference)` = 100 × (coût − référence) / référence, la formule du sujet.

---

## 3. Le dossier `algorithmes/` : les méthodes de résolution

### `grasp_tabou_cvrptw.py` : GRASP + recherche tabou

Même logique que le workshop du sac à dos, adaptée au CVRPTW. Les données sont dans des
variables globales (`n`, `q`, `Q`, `tw`, `s`, `dist`), remplies par `charger_instance(...)`
ou par `methodes.preparer(...)`.

| Partie | Fonctions | Rôle |
|---|---|---|
| 1. Données | `charger_instance` | remplit les variables globales et la matrice des distances |
| 2. Fonctions de base | `cout_tournee`, `cout_solution`, `tournee_valide` | coût d'une tournée ; capacité et fenêtres de temps (attente autorisée) |
| 3. Construction GRASP | `grasp_construction(alpha)` | construit les tournées une par une. À chaque étape : les clients possibles sont classés par distance (+ un peu d'urgence de fenêtre) ; on garde les meilleurs dans une liste restreinte (RCL : score ≤ min + alpha × (max − min)) et on en tire un au hasard. alpha = 0 : glouton pur ; alpha = 1 : hasard pur |
| 4. Voisinage | `voisinage`, `tournees_modifiees`, `mouvement_valide`, `appliquer_mouvement` | un voisin = **déplacer** un client (relocate), **échanger** deux clients (swap) ou **inverser** un morceau de tournée (2-opt, en option). Le coût d'un voisin se calcule **par différence** avec 3 ou 4 distances, sans recalculer toute la solution |
| 5. Recherche tabou | `recherche_tabou` | va au meilleur voisin non tabou, même s'il est moins bon (pour sortir des optimums locaux). Les clients déplacés deviennent tabous ; un mouvement tabou reste permis s'il bat le record (**critère d'aspiration**). Arrêt après `iter_max` itérations sans amélioration ou à `heure_fin` |
| 6. Multi-start | `grasp_tabou` | répète construction GRASP + tabou jusqu'au temps maximum et garde la meilleure solution |
| Contrôle | `verifier_solution` | chaque client visité une fois et toutes les tournées valides |

Deux séries de lignes ont été ajoutées pour l'interface. Elles ne changent rien quand le
fichier est utilisé seul (notebook, benchmark) :

* **`# AJOUT interface`** : `depart` (heure de départ des camions), `trajet()` (durée avec
  trafic), `k_max` (pas de nouveau camion s'il n'en reste plus), `suivi` (courbe de convergence).
* **`# AMÉLIORATION`** : `proches[i]` = les 40 clients les plus proches de i. La construction
  les regarde en premier, et le voisinage ne déplace un client que vers les tournées qui
  passent près de lui. C'est la piste « voisinage aux k plus proches voisins » du bilan du
  notebook : sur 12 instances (10 s), le gap moyen passe de 7,6 % à 5,7 % (tabou) et de
  43,7 % à 6,8 % (GRASP).

### `plne.py` : la méthode exacte

Le PLNE du livrable 1, résolu par CBC via PuLP. Version à 2 indices (`x_ij`) au lieu de 3
(`x_ijk`) : les camions sont identiques, l'indice du camion n'apporte rien et ralentit le
solveur. Contraintes : visite unique, continuité, nombre de camions, **MTZ** (capacité et
pas de sous-tour), **big-M** pour les fenêtres de temps. Limitée à 15 clients : au-delà, le
temps de calcul explose (problème NP-difficile). Elle sert à **prouver l'optimum** des
petites instances et à vérifier que les métaheuristiques le retrouvent.

### `methodes.py` : les méthodes de l'interface

1. `preparer(instance)` remplit les variables globales de `grasp_tabou_cvrptw.py` à partir
   du dictionnaire `instance` : mêmes distances, heure de départ, nombre de camions, trafic
   et les 40 voisins les plus proches.
2. Deux métaheuristiques, pour pouvoir les **comparer** :
   * `tabou` : une seule construction gloutonne (alpha = 0), puis la recherche tabou jusqu'au
     temps maximum ;
   * `grasp` : construction randomisée + tabou court, répétés jusqu'au temps maximum.
3. `METHODES` liste les 3 méthodes (tabou, GRASP, PLNE) ; `lancer(...)` en lance une, la
   chronomètre et garde la courbe de convergence.

Toutes ont la même forme : `methode(instance, temps_max, graine, suivi) → routes`. Les
paramètres (`alpha`, `taille_tabou`, `iter_max`, `taille_echantillon`) ont les valeurs par
défaut du benchmark de l'équipe et peuvent varier dans l'étude de sensibilité.

---

## 4. L'interface : `app.py` et le dossier `interface/`

`streamlit run app.py` ouvre une page web. **À gauche** : l'instance, le trafic, la méthode,
le temps maximum et le bouton ▶ Lancer. **Au centre**, 4 onglets :

| Onglet | Contenu |
|---|---|
| 🚚 Tournées | distance, gap (🟢 ≤ 7 %, 🟠 7-10 %, 🔴 > 10 %), camions, temps de calcul, contraintes respectées ou non, carte, parcours de chaque camion, planning |
| 🗺️ Suivi 3D / 2D | les camions roulent et leur trajet se dessine (▶ Lecture) |
| ⚖️ Comparer | toutes les méthodes sur la même instance, et leur courbe de convergence |
| 📊 Étude expérimentale | plusieurs instances, plusieurs graines : qualité, robustesse, familles, temps, sensibilité, Wilcoxon |

Les résultats sont gardés en mémoire (`st.session_state`) : on passe du tabou au GRASP sans
tout relancer. Le gap n'apparaît que pour les instances qui ont une solution de référence,
et pas avec le trafic (les références sont calculées sans trafic).

### `graphiques.py`

* `carte_instance`, `carte_tournees` : les clients et les tournées, une couleur par camion ;
  `carte_reelle` : la même chose sur un fond OpenStreetMap pour la Lorraine.
* `gantt` : le planning de chaque camion (trajet en gris, attente en jaune, livraison en vert).
* `suivi` : l'animation. Pour chaque camion, on liste ses **points clés** (heure, position) :
  départ, arrivée et fin de livraison chez chaque client, retour. Entre deux points on
  avance en ligne droite, ce qui donne la position à toute heure. En 3D, chaque trajet est
  un arc au-dessus d'un plateau (`en_arcs`) ; en 2D, c'est le même plan vu de dessus.
* `convergence` : le meilleur coût trouvé au fil du temps.

### `etude.py` : l'onglet Étude expérimentale

`executer(...)` lance chaque méthode sur chaque instance avec chaque graine et `sauvegarder`
écrit un CSV dans `resultats/`, avec les mêmes colonnes que `benchmark_vrplib.py`
(`instance, famille, n, algorithme, graine, cout, bks, gap_%, camions, temps_s, valide`),
plus `temps_meilleure_s`, le moment où la meilleure solution a été trouvée. Une fonction par
point du sujet :

| Demande du sujet | Fonction |
|---|---|
| qualité des solutions (gap) | `resume_par_methode`, `graphique_gap` |
| robustesse | `resume_par_methode` (variation du coût d'une graine à l'autre) |
| comportement selon le type d'instance | `resume_par_famille` |
| temps de calcul selon la taille | `graphique_temps`, `pente_complexite` (temps ≈ a·nᵇ) |
| sensibilité aux paramètres | `graphique_sensibilite` |
| analyse statistique | `test_wilcoxon` (tabou contre GRASP ; p < 0,05 : différence significative) |

Les méthodes utilisent tout le temps donné : le temps étudié est donc celui où la meilleure
solution a été trouvée.

---

## 5. Les scripts du notebook

### `benchmark_vrplib.py`

* `telecharger(nom)` récupère l'instance et sa solution depuis PyVRP/Instances si elles
  manquent dans `instances/` (utile sur Colab).
* `charger_vrplib(nom)` charge l'instance dans `grasp_tabou_cvrptw.py` avec les conventions
  d'arrondi des BKS, et renvoie le coût de la meilleure solution connue.
* `tester(nom, graine, temps_max, …)` lance GRASP + tabou et renvoie une ligne de résultat
  (coût, BKS, gap, temps, validité).
* `python benchmark_vrplib.py 20` : les 20 instances (18 Solomon, 2 X), 20 s chacune ;
  écrit `resultats/resultats_20s.csv` et `resultats/gap_par_instance_20s.png`.

### `etude_statistique.py`

Quatre expériences, chacune avec un CSV et un graphique dans `resultats/` :

1. **Robustesse** : 6 instances × 5 graines (moyenne, écart-type, min, max) ;
2. **Convergence** : le gap selon le temps accordé (2, 5, 10, 30 s) ;
3. **Taille** : instances X de 100 à 1 000 clients, gap et temps d'une construction ;
4. **Sensibilité** : `alpha` puis la taille de la liste tabou.

Les fichiers du dossier `instances/` (sans sous-dossier) servent à ces deux scripts ;
ceux des sous-dossiers servent à l'interface.

---

## 6. Les 20 instances de l'interface

| Instance | Type | Clients | Origine | Référence pour le gap |
|---|---|---|---|---|
| LOR-Metz-agglo | CVRPTW | 10 | Lorraine (inventée) | optimum PLNE 113,2 |
| LOR-Moselle-Est | CVRP | 15 | Lorraine (inventée) | — |
| LOR-Nancy-agglo | CVRPTW | 18 | Lorraine (inventée) | — |
| LOR-Sillon-lorrain | CVRPTW | 40 | Lorraine (inventée) | — |
| LOR-Lorraine-complete | CVRPTW | 68 | Lorraine (inventée) | — |
| GEN-uniforme-centre-serrees-n8-g1 | CVRPTW | 8 | générée | optimum PLNE 342,4 |
| GEN-clusters-centre-serrees-n200-g1 | CVRPTW | 200 | générée (centre-ville, créneaux serrés) | — |
| GEN-clusters-coin-aucune-n2000-g1 | CVRP | 2 000 | générée (métropole, dépôt excentré) | — |
| X-n101-k25, X-n200-k36, X-n502-k39, X-n1001-k43 | CVRP | 100 à 1 000 | VRPLIB, Uchoa 2017 | BKS |
| Leuven1 | CVRP | 3 000 | VRPLIB, Arnold 2019 | BKS |
| C101, C201, R101, R201, RC101, RC201 | CVRPTW | 100 | Solomon (grappes, aléatoires, mixtes ; fenêtres serrées 1 ou larges 2) | BKS |
| R1_10_1 | CVRPTW | 1 000 | Gehring & Homberger | BKS |

Les instances inventées sans référence n'ont pas de gap : on compare alors les méthodes
entre elles (coût, nombre de camions).

**Pourquoi le gap est fiable :** en recalculant le coût des meilleures solutions connues avec
notre propre code, on retrouve exactement les valeurs publiées (C101 : 827,3 ;
X-n101-k25 : 27 591 ; R1_10_1 : 53 026,1 ; Leuven1 : 192 848), et la PLNE retrouve 33,9 sur
l'exemple du livrable 1.

---

## 7. Choix à justifier à l'oral

* **Séparer calcul et vérification** : les méthodes renvoient des tournées, `evaluer()` les
  juge toutes de la même façon.
* **PLNE à 2 indices** : équivalente au modèle du livrable 1 car les camions sont identiques,
  et plus rapide.
* **Coût par différence et 40 plus proches voisins** : ce sont les deux accélérations qui
  permettent de traiter des milliers de clients.
* **Arrêt au temps** plutôt qu'au nombre d'itérations : c'est la contrainte réelle d'un
  utilisateur, mais une machine plus rapide fait plus d'itérations, donc les résultats
  varient un peu d'un PC à l'autre (voir la remarque du notebook).
* **Trafic par tranche horaire, appliqué au départ** : simple à expliquer, suffisant pour
  montrer l'effet des heures de pointe. Exemple : avec le trafic, la meilleure solution
  connue de C101 n'est plus réalisable (deux fenêtres dépassées).
* **20 instances** couvrant CVRP et CVRPTW, des fenêtres serrées et larges, des clients
  aléatoires, en grappes ou mixtes, et de 8 à 3 000 clients.

---

## 8. Ajouter une méthode

1. Écrire une fonction `ma_methode(instance, temps_max=30, graine=0, suivi=None, **parametres)`
   qui renvoie les tournées, par exemple `[[3, 7, 1], [5, 2]]`. Utiliser
   `instance["distance"]` (ne pas recalculer les distances) et, avec le trafic,
   `temps_trajet(...)`. Appeler `suivi(iteration, meilleur_cout)` à chaque record pour la
   courbe de convergence.
2. L'ajouter au dictionnaire `METHODES` de `algorithmes/methodes.py`, et à la liste `algos`
   de `app.py`.

La vérification, le gap, les graphiques et l'étude fonctionnent alors sans autre modification.
