# Interface de tournées de livraison : projet ADEME / CesiCDP

Ce document explique **tout ce qui a été fait** pour l'interface : à quoi sert chaque
fichier, comment le code fonctionne, comment brancher la Recherche tabou et le GRASP, et
comment chaque exigence du sujet est couverte. Il est écrit pour être relu avant la
soutenance.

---

## 1. En bref

L'interface (une page web créée avec **Streamlit**) permet de :

1. **choisir une instance** parmi les 20 de la bibliothèque, ou l'exemple du livrable 1 ;
2. **choisir un algorithme** (Recherche tabou, GRASP, glouton de référence ou PLNE exacte),
   puis le lancer ;
3. **vérifier la solution** : chaque contrainte est contrôlée par notre propre code, pas
   par l'algorithme ;
4. **voir les tournées** : carte (vraie carte pour la Lorraine), planning de chaque camion,
   **suivi animé en 3D et en 2D** ;
5. **comparer** tabou et GRASP sur la même instance ;
6. calculer le **gap** par rapport aux meilleures solutions connues (VRPLIB), avec la
   formule du sujet ;
7. réaliser l'**étude expérimentale** : qualité, temps de calcul selon la taille,
   robustesse, sensibilité aux paramètres et tests statistiques.

**Principe clé : les métaheuristiques ne font que calculer des tournées.** Tout le reste
(vérification, affichage, statistiques) est fait par l'interface. Les deux camarades n'ont
qu'une fonction à écrire (voir la partie 5).

---

## 2. Lancer l'interface

```bash
pip install -r requirements.txt     # une seule fois (déjà fait sur le PC de Yanis)
streamlit run app.py                # ou double-clic sur lancer_interface.bat
```

Le navigateur s'ouvre sur http://localhost:8501. La fenêtre noire doit rester ouverte, et
**Ctrl + C** arrête le serveur. Le fond de carte de la Lorraine (OpenStreetMap) demande une
connexion internet.

Bibliothèques utilisées (`requirements.txt`) :

| Bibliothèque | Pourquoi |
|---|---|
| `streamlit` | crée l'interface web en Python, sans HTML ni JavaScript |
| `plotly` | graphiques interactifs : cartes, 3D, animations |
| `numpy`, `pandas` | calculs (matrice des distances) et tableaux de résultats |
| `vrplib` | lit les fichiers d'instances et de solutions du format VRPLIB (lien du sujet) |
| `pulp` (version **2.9.0**) | écrit et résout la PLNE avec le solveur CBC. La version 4 casse le code |
| `scipy` | test statistique de Wilcoxon |

---

## 3. Organisation du code

```
            app.py  (l'interface : choix à gauche + 4 onglets)
               │
   ┌───────────┼──────────────┬─────────────────┐
   ▼           ▼              ▼                 ▼
solveurs.py  vrp_commun.py  visualisation.py  benchmark.py
 (algos)     (le cœur)      (graphiques)      (étude expérimentale)
   │            ▲
   ▼            │
adaptateur.py          instances_lorraine.py
   │                   instances/ (fichiers .vrp + .sol)
   ▼
grasp_tabou_cvrptw.py  (le code de l'équipe)
```

Le trajet d'une résolution :

```
charger_instance()  →  lancer(algo)  →  routes  →  evaluer()  →  affichage / gap / stats
 (vrp_commun)          (solveurs)                  (vrp_commun)   (visualisation, benchmark)
```

### Le dictionnaire `instance`

Toutes les fonctions se passent **le même dictionnaire**. C'est le seul objet à connaître :

| Clé | Contenu |
|---|---|
| `nom`, `famille`, `type` | nom, famille (X, Solomon, Lorraine…), « CVRP » ou « CVRPTW » |
| `n` | nombre de clients. Le dépôt porte le numéro 0, les clients vont de 1 à n |
| `coords` | coordonnées (x, y) de chaque point |
| `demande` | `demande[i]` = quantité à livrer au client i (0 pour le dépôt) |
| `capacite` | capacité Q, identique pour tous les camions |
| `nb_vehicules` | nombre k de camions disponibles |
| `distance` | **matrice des distances / temps** : `distance[i, j]` |
| `fenetres` | `fenetres[i] = [ouverture, fermeture]`, ou `None` en CVRP |
| `service` | temps passé chez chaque client (livraison) |
| `horizon` | fin de la journée (fermeture du dépôt) |
| `trafic` | profil de trafic, ou `None` s'il est désactivé |
| `bks` | coût de la meilleure solution connue (*Best Known Solution*), ou `None` |

Les instances Lorraine ont en plus `villes` (noms des communes), `latlon` (vraie position),
`heure_depart` (6h00) et `description`.

---

## 4. Ce que fait chaque fichier

### `vrp_commun.py` : le cœur

C'est le fichier le plus important : tout le monde l'utilise.

* **`matrice_distances(coords, arrondi)`** calcule la distance euclidienne entre tous les
  points. L'arrondi suit la convention de chaque famille d'instances, sinon on ne retrouve
  pas les coûts de référence :
  * instances X (CVRP) : arrondi à l'entier ;
  * Solomon / Homberger (VRPTW) : troncature à 1 décimale.
* **`charger_instance(chemin)`** lit un fichier `.vrp` ou `.txt` avec `vrplib`, puis la
  solution de référence `.sol` si elle existe. Il construit enfin le dictionnaire.
* **`evaluer(instance, routes)`** est **le juge**. Il recalcule tout et liste les
  contraintes violées (voir la partie 6).
* **`temps_trajet(instance, i, j, depart)`** donne la durée d'un trajet, en tenant compte du
  trafic s'il est activé (voir la partie 7).
* **`gap(cout, reference)`** applique la formule du sujet : `100 × (coût − opt) / opt`.
* **`exemple_livrable1()`** recrée l'exemple du livrable 1 (6 clients, Q = 12, K = 2,
  optimum 33,9 min).
* **`generer_instance(...)`** crée une instance au hasard (utilisé par
  `creer_instances_generees.py`). On choisit le nombre de clients,
  leur répartition (uniforme, en grappes, mixte), la position de l'entrepôt et le type de
  fenêtres.

### `solveurs.py` : les algorithmes

* **`plus_proche_voisin`** est un **glouton de référence**. Le camion va toujours au client
  le plus proche qui reste possible (capacité, fenêtre, retour au dépôt). Quand plus aucun
  client n'est possible, il rentre et un autre camion part. Il sert :
  * à tester l'interface tant que le tabou et le GRASP ne sont pas branchés ;
  * de **point de comparaison** : une métaheuristique doit faire mieux que lui ;
  * c'est aussi la **construction gloutonne** sur laquelle reposent le GRASP (en version
    randomisée) et la solution initiale du tabou.
* **`plne_exacte`** reprend le **PLNE du livrable 1**, résolu par CBC via PuLP. On utilise
  une version à 2 indices (`x_ij`) au lieu de 3 (`x_ijk`) : les camions sont identiques,
  donc l'indice k n'apporte rien et ralentit le solveur. Le modèle contient :
  * les contraintes MTZ pour la capacité et l'élimination des sous-tours ;
  * des contraintes big-M pour les temps.

  La PLNE est limitée à **15 clients**, car le temps de calcul explose au-delà (le problème
  est NP-difficile, comme montré dans le livrable 1). Elle sert à **prouver l'optimum** des
  petites instances.
* **`ALGORITHMES`** est la liste des algorithmes affichés dans l'interface. La Recherche
  tabou et le GRASP y sont ajoutés depuis `adaptateur.py` (voir la partie 5).
* **`lancer(nom_algo, instance, ...)`** lance un algorithme et chronomètre le temps de
  calcul. Il récupère la courbe de convergence et nettoie la sortie : il retire les 0 du
  dépôt et accepte une liste, un tuple ou un dict.

### `visualisation.py` : les graphiques (Plotly)

* `carte_tournees` affiche la carte des tournées, une couleur par camion.
* `carte_reelle` affiche la tournée sur un fond **OpenStreetMap** (instances Lorraine) ; le
  nom des villes apparaît au survol.
* `gantt` montre le planning de chaque camion : trajet en gris, attente en jaune, livraison
  en vert.
* `suivi` anime les camions, en 3D ou en 2D, avec la même fonction. Le trajet se dessine
  au fur et à mesure que le camion avance. En 3D, le plan est un plateau et chaque trajet
  est un arc au-dessus du sol (`en_arcs`) ; en 2D, c'est le même plan vu de dessus. Le plan
  a des limites fixes pour que l'image ne bouge pas pendant la lecture.
* `convergence` trace la courbe du meilleur coût au fil des itérations.

### `benchmark.py` : l'étude expérimentale

* `executer(...)` lance chaque méthode sur chaque instance avec chaque graine : une ligne
  par essai. `sauvegarder` l'écrit dans `resultats/` au **même format CSV que le benchmark
  de l'équipe** : `instance, famille, n, algorithme, graine, cout, bks, gap_%, camions,
  temps_s, valide`, plus `temps_meilleure_s` (moment où la meilleure solution a été
  trouvée). Dans le notebook : `pd.read_csv("resultats/....csv")`.
* Une fonction par point du sujet :
  * `resume_par_methode` : qualité (gap moyen, gap max, instances ≤ 7 %) et robustesse
    (variation du coût d'une graine à l'autre) ;
  * `resume_par_famille` : gap moyen par type d'instance ;
  * `graphique_temps` et `pente_complexite` : temps selon la taille ;
  * `graphique_sensibilite` : effet d'un paramètre ;
  * `test_wilcoxon` : tabou contre GRASP.
* En ligne de commande, pour une longue campagne : `python benchmark.py --graines 5 --temps 60`.

### `app.py` : l'interface

Elle assemble tout : les choix à gauche, 4 onglets au centre (voir la partie 9). Les
résultats sont gardés en mémoire (`st.session_state`), ce qui permet de passer du tabou au
GRASP sans tout relancer.

### Les autres fichiers

| Fichier | Rôle |
|---|---|
| `instances_lorraine.py` | crée les 5 instances sur de vraies communes de Moselle et Meurthe-et-Moselle |
| `creer_instances_generees.py` | a créé les 3 instances de `instances/GENERE`. Déjà exécuté, inutile de le relancer |
| `grasp_tabou_cvrptw.py` | **le GRASP et la Recherche tabou de l'équipe** (voir la partie 5) |
| `adaptateur.py` | branche le code de l'équipe sur l'interface |
| `lancer_interface.bat` | lance l'interface d'un double-clic |
| `instances/` | l'interface lit les sous-dossiers `CVRP/`, `VRPTW/` et `GENERE/` : fichiers `.vrp` (instances) et `.sol` (meilleures solutions connues). Les fichiers posés directement dans `instances/` servent à `benchmark_vrplib.py` |
| `benchmark_vrplib.py`, `etude_statistique.py`, `Projet_Smart.ipynb` | (dépôt GitHub) le benchmark VRPLIB, l'étude statistique et le notebook de l'équipe |
| `resultats/` | les CSV produits par l'étude expérimentale |

---

## 5. Brancher la Recherche tabou et le GRASP

### Le code de l'équipe : `grasp_tabou_cvrptw.py`

Il contient tout : la vérification d'une tournée (`tournee_valide`), la construction GRASP
(`grasp_construction`), le voisinage (déplacer, échanger, 2-opt), la recherche tabou
(`recherche_tabou`) et le multi-start (`grasp_tabou`). Les données sont dans des variables
globales (`n`, `q`, `Q`, `tw`, `s`, `dist`), comme dans le workshop du sac à dos.

Pour l'interface, quelques lignes ont été ajoutées ; elles sont marquées `# AJOUT interface`
et ne changent rien quand on lance le fichier seul :

* `depart` : heure de départ des camions (6h00 pour la Lorraine, 0 avant) ;
* `trajet(i, j, heure)` : durée d'un trajet, pour tenir compte du **trafic** ;
* `k_max` : on n'ouvre pas de nouveau camion s'il n'en reste plus ;
* `fin` : le tabou s'arrête au **temps maximum** ;
* `suivi` : appelé à chaque record, pour la **courbe de convergence**.

Une amélioration est marquée `# AMÉLIORATION` : `proches[i]` contient les 40 clients les
plus proches de i (calculés par `adaptateur.py`). La construction regarde d'abord ces
clients, et le voisinage ne tente de déplacer un client que vers les tournées qui passent
près de lui. Sur les grandes instances, le gap moyen passe ainsi de 7,6 % à 5,7 % (tabou)
et de 44 % à 6,8 % (GRASP), en 10 s. Sans `proches` (fichier lancé seul), rien ne change.

### Le branchement : `adaptateur.py`

* `preparer(instance)` remplit les variables globales du code de l'équipe à partir du
  dictionnaire `instance`, avec **les distances de l'interface** (mêmes arrondis que les BKS).
* Deux méthodes, pour pouvoir les comparer dans l'onglet Comparer et l'étude :
  * **Recherche tabou** (`tabou`) : une construction gloutonne (alpha = 0), puis la
    recherche tabou jusqu'au temps maximum ;
  * **GRASP** (`grasp`) : construction randomisée répétée (multi-start), chacune améliorée
    par un tabou court ; on garde la meilleure.
* Paramètres pour l'étude de sensibilité : `taille_tabou`, `taille_echantillon` (les deux),
  `alpha` et `iter_max` (GRASP). Valeurs par défaut : celles du benchmark de l'équipe.

### Brancher un autre algorithme

Il suffit d'un fichier avec **une seule fonction obligatoire** :

```python
def resoudre(instance, temps_max=30, graine=0, suivi=None, **parametres):
    random.seed(graine)               # pour pouvoir reproduire un résultat
    ...
    if suivi:                         # facultatif : à chaque amélioration
        suivi(iteration, meilleur_cout)
    ...
    return routes                     # ex. [[3, 7, 1], [5, 2]] : une liste par camion, sans le dépôt 0
```

| Paramètre | Rôle |
|---|---|
| `instance` | le dictionnaire décrit dans la partie 3 |
| `temps_max` | temps de calcul autorisé en secondes : c'est le critère d'arrêt |
| `graine` | graine aléatoire. Même graine = même résultat (exigé pour l'étude statistique) |
| `suivi` | fonction à appeler quand on trouve mieux. Elle trace la courbe de convergence |
| `**parametres` | réglages testés dans l'étude de sensibilité, ex. `taille_tabou=15` ou `alpha=0.3`. Il faut leur donner une valeur par défaut, car l'interface ne les passe que pour cette étude |

puis une ligne dans `FICHIERS_METAHEURISTIQUES` (`solveurs.py`) : nom affiché →
(fichier, fonction). Si le fichier contient une erreur, l'interface l'affiche dans la barre
latérale au lieu de planter. Le glouton n'apparaît que si le tabou ou le GRASP manque.

> ⚠️ **Règle importante :** utiliser `instance["distance"][i, j]` et **ne pas recalculer
> les distances soi-même**. Avec une autre convention d'arrondi, le gap est faux de
> plusieurs pour cent. Pour la durée d'un trajet avec le trafic, utiliser
> `temps_trajet(instance, i, j, heure_de_depart)` de `vrp_commun.py`.

---

## 6. Comment une solution est vérifiée : `evaluer()`

L'interface ne fait **jamais confiance** à l'algorithme : elle refait tous les calculs.
Pour chaque camion, on simule sa journée arrêt par arrêt :

```
heure = heure de départ du dépôt
pour chaque client de la tournée :
    arrivée = heure + temps_trajet(position, client, heure)
    début   = max(arrivée, ouverture)      ← s'il arrive trop tôt, il attend
    si début > fermeture  → violation     ← interdit de livrer hors fenêtre
    heure   = début + temps de service
retour au dépôt : violation s'il rentre après la fermeture
```

Les contraintes contrôlées sont les suivantes :

| Contrainte (sujet / livrable 1) | Contrôle |
|---|---|
| Chaque client est livré **une et une seule fois** | aucun client manquant, en double ou inconnu |
| **Flotte de k camions** | nombre de tournées ≤ `nb_vehicules` |
| **Capacité Q identique** | somme des demandes de chaque tournée ≤ Q |
| **Fenêtres de temps**, livraison hors fenêtre interdite | `début ≤ fermeture` |
| **Attente autorisée** | `début = max(arrivée, ouverture)` |
| Temps de service, retour au dépôt avant sa fermeture | simulé |
| **Trafic selon l'heure** | `temps_trajet()` |

`evaluer()` renvoie :

* la distance totale, la durée et le temps d'attente ;
* le nombre de camions ;
* `realisable` (vrai ou faux) et la **liste des violations en clair** ;
* pour chaque tournée, le détail des arrêts (heure d'arrivée, d'attente, de livraison).

C'est ce détail qu'utilisent le Gantt et la 3D.

---

## 7. Le trafic (volontairement simple)

La journée est découpée en **tranches horaires**, chacune avec un coefficient :

```
durée du trajet = distance × coefficient de la tranche de l'heure de départ
```

Par exemple, un trajet de 20 min qui part à 8h, en heure de pointe (coefficient 1,5), dure
**30 min**.

* Un interrupteur à gauche active ou coupe le trafic. Les tranches sont définies dans le
  code : `PROFIL_TRAFIC_DEFAUT` (`vrp_commun.py`) et `TRAFIC_LORRAINE`
  (`instances_lorraine.py`).
* Pour la Lorraine, il y a des bouchons de 7h à 9h et de 16h30 à 19h (×1,5), et un
  ralentissement le midi (×1,2).
* La limite (à dire à l'oral) : on ne change pas de coefficient en cours de route. On a
  choisi la simplicité.
* Les meilleures solutions VRPLIB sont calculées **sans trafic**. Le gap se mesure donc
  avec le trafic désactivé.
* Un argument pour la soutenance : avec le trafic, la meilleure solution connue de C101
  **devient irréalisable** (2 fenêtres violées). Une tournée optimale « sur le papier »
  peut donc ne plus tenir dans la vraie vie, d'où l'intérêt du trafic dans le modèle.

---

## 8. Les 20 instances

Le sujet demande **au moins 20 instances** avec des scénarios variés. Nous en avons 20 :
CVRP et CVRPTW, de 8 à 3000 clients, avec des clients aléatoires, en grappes ou mixtes, et
un entrepôt central ou excentré.

| # | Instance | Type | Clients | Origine | Référence pour le gap |
|---|---|---|---|---|---|
| 1 | LOR-Metz-agglo | CVRPTW | 10 | Lorraine (inventée) | optimum PLNE = 113,2 min |
| 2 | LOR-Nancy-agglo | CVRPTW | 18 | Lorraine (inventée) | meilleur trouvé |
| 3 | LOR-Moselle-Est | CVRP | 15 | Lorraine (inventée) | meilleur trouvé |
| 4 | LOR-Sillon-lorrain | CVRPTW | 40 | Lorraine (inventée) | meilleur trouvé |
| 5 | LOR-Lorraine-complete | CVRPTW | 68 | Lorraine (inventée) | meilleur trouvé |
| 6 | GEN-uniforme-centre-serrees-n8-g1 | CVRPTW | 8 | générée | optimum PLNE = 342,4 |
| 7 | GEN-clusters-centre-serrees-n200-g1 | CVRPTW | 200 | générée (centre-ville, créneaux serrés) | meilleur trouvé |
| 8 | GEN-clusters-coin-aucune-n2000-g1 | CVRP | 2000 | générée (métropole, entrepôt en périphérie) | meilleur trouvé |
| 9 | X-n101-k25 | CVRP | 100 | VRPLIB, Uchoa 2017 | BKS 27 591 |
| 10 | X-n200-k36 | CVRP | 199 | VRPLIB, Uchoa 2017 | BKS |
| 11 | X-n502-k39 | CVRP | 501 | VRPLIB, Uchoa 2017 | BKS |
| 12 | X-n1001-k43 | CVRP | 1000 | VRPLIB, Uchoa 2017 | BKS |
| 13 | Leuven1 | CVRP | 3000 | VRPLIB, Arnold 2019 | BKS 192 848 |
| 14 | C101 | CVRPTW | 100 | Solomon : grappes, fenêtres serrées | BKS 827,3 |
| 15 | C201 | CVRPTW | 100 | Solomon : grappes, fenêtres larges | BKS |
| 16 | R101 | CVRPTW | 100 | Solomon : aléatoire, fenêtres serrées | BKS |
| 17 | R201 | CVRPTW | 100 | Solomon : aléatoire, fenêtres larges | BKS |
| 18 | RC101 | CVRPTW | 100 | Solomon : mixte, fenêtres serrées | BKS |
| 19 | RC201 | CVRPTW | 100 | Solomon : mixte, fenêtres larges | BKS |
| 20 | R1_10_1 | CVRPTW | 1000 | Gehring & Homberger | BKS 53 026,1 |

En plus de ces 20 instances, l'**exemple du livrable 1** est disponible dans la barre
latérale (6 clients, optimum 33,9 min).

### Les instances Lorraine (inventées, villes réelles)

68 communes de Moselle et de Meurthe-et-Moselle, avec leur vraie latitude et longitude. Les
hypothèses sont simples :

* durée (min) = distance à vol d'oiseau (km) × 1,3 (les routes ne sont pas droites), à
  une vitesse moyenne de 60 km/h ;
* entrepôt ouvert de 6h à 20h, 15 min de livraison par client ;
* créneaux : matin (8h-12h), après-midi (14h-18h) ou journée (8h-18h) ;
* demandes de 5 à 30 colis, camions de 100 colis ;
* tirages au hasard avec une **graine fixe** : l'instance est toujours la même.

### Pourquoi le gap est fiable

Pour vérifier notre calcul des distances, on recalcule le coût des meilleures solutions
connues avec notre propre code. On retrouve **exactement** les valeurs publiées :

| Instance | Coût publié | Coût recalculé |
|---|---|---|
| C101 | 827,3 | 827,3 |
| X-n101-k25 | 27 591 | 27 591 |
| R1_10_1 | 53 026,1 | 53 026,1 |
| Leuven1 | 192 848 | 192 848 |

La PLNE retrouve aussi **33,9** sur l'exemple du livrable 1.

Les instances sans BKS (Lorraine, générées) sont comparées au **meilleur coût trouvé par nos
algorithmes**. Cette colonne s'appelle « écart à la référence » dans l'étude.

---

## 9. L'interface, écran par écran

### À gauche : 4 réglages et un bouton

1. **Instance** : les 20 de la bibliothèque, ou l'exemple du livrable 1.
2. **Trafic selon l'heure** : interrupteur.
3. **Algorithme** : Recherche tabou ou GRASP. La PLNE s'ajoute pour les instances de
   15 clients ou moins.
4. **Temps de calcul maximum**.
5. Le bouton **▶ Lancer**.

Pour **passer du tabou au GRASP**, il suffit de changer l'algorithme à gauche : les onglets
affichent la solution de l'algorithme sélectionné, si elle a déjà été calculée.

### Les 4 onglets

| Onglet | Contenu |
|---|---|
| 🚚 **Tournées** | distance, gap (🟢 ≤ 7 % / 🟠 7-10 % / 🔴 > 10 %, seuils du sujet), camions, temps de calcul, contraintes respectées ou non, carte, parcours de chaque camion, planning |
| 🗺️ **Suivi 3D / 2D** | les camions roulent et leur trajet se dessine (▶ Lecture), en 3D ou en 2D |
| ⚖️ **Comparer** | lance toutes les méthodes sur l'instance : tableau (distance, gap, camions, temps, contraintes) et courbe de convergence. Jusqu'à 15 clients, la PLNE donne l'optimum pour vérifier les métaheuristiques |
| 📊 **Étude expérimentale** | qualité et robustesse, résultats par type d'instance, temps selon la taille, sensibilité, test de Wilcoxon |

**Le gap :** dès qu'on choisit une instance, l'en-tête affiche sa meilleure solution
connue ; le gap apparaît après ▶ Lancer. Les instances inventées (Lorraine, générées) n'ont
pas de référence, donc pas de gap, sauf les plus petites dont l'optimum a été prouvé par la
PLNE. Le gap ne s'affiche pas non plus avec le trafic, car les références sont sans trafic.

**Lire le suivi :** en 3D, les clients sont posés sur un plateau, chaque trajet est un arc
(plus il est long, plus il monte) et le mât foncé est l'entrepôt d'où partent tous les
camions. On fait tourner le plateau à la souris. Le trait pâle est la tournée prévue, le trait épais ce qui a déjà
été parcouru. Le curseur donne l'heure. Un double-clic sur un camion dans la légende
n'affiche que lui. L'affichage est limité aux 30 premiers camions, pour rester lisible.

---

## 10. L'étude expérimentale (ce que demande le sujet)

Dans l'onglet 📊, on choisit les instances, le nombre de répétitions et le temps maximum,
puis on lance l'étude. Le tableau suivant montre ce que l'onglet produit pour chaque
question du sujet.

| Question du sujet | Ce que produit l'interface |
|---|---|
| Au moins 20 instances | les 20 sont cochées par défaut |
| Qualité des solutions (gap VRPLIB) | 1. gap moyen, gap max, nombre d'instances ≤ 7 %, gap par instance avec la ligne des 7 % |
| Robustesse | 1. variation du coût d'une graine à l'autre |
| Selon le scénario (taille, répartition, fenêtres) | 2. gap moyen par famille d'instances |
| Temps de calcul selon la taille | 3. temps pour trouver la meilleure solution, en log-log, et **pente** : une pente de 2 signifie que le temps est multiplié par 4 quand n double, soit environ O(n²) |
| Sensibilité aux paramètres | 4. on choisit un paramètre (ex. `alpha`) et plusieurs valeurs, puis on compare les gaps |
| Analyse statistique | **test de Wilcoxon apparié** (tabou contre GRASP, sur les mêmes instances) : si p < 0,05, la différence n'est pas due au hasard |

Les méthodes utilisent tout le temps donné ; c'est pourquoi le temps étudié est celui où
la meilleure solution a été trouvée. Les résultats sont enregistrés en CSV dans
`resultats/` (voir `benchmark.py`), lisibles dans le notebook avec `pd.read_csv`.

---

## 11. Tester rapidement

1. **Exemple du livrable 1** avec **PLNE exacte**, puis ▶ Lancer : on doit obtenir 33,9 avec
   un gap de 0 %.
2. **LOR-Sillon-lorrain**, trafic activé, ▶ Lancer : vraie carte dans Tournées, puis l'onglet Suivi 3D / 2D
   avec ▶ Lecture, dans les deux vues.
3. **C101** sans trafic, ▶ Lancer : le gap s'affiche par rapport à la référence 827,3.
4. Onglet **Étude expérimentale** : 3-4 petites instances, 1 répétition, 5 s.

Ce qui est normal :

* Sur les très grandes instances (1 000 clients et plus), le calcul peut dépasser le temps
  maximum : la construction de la première solution n'est pas interruptible.

---

## 12. Choix faits (à justifier à l'oral)

* **Séparer calcul et vérification.** Les métaheuristiques renvoient seulement des
  tournées, et `evaluer()` les juge toutes de la même façon. La comparaison entre tabou et
  GRASP est donc équitable.
* **Un contrat unique `resoudre(...)`.** Chacun code de son côté, et le branchement se fait
  sans toucher à l'interface.
* **PLNE à 2 indices.** Elle équivaut au modèle à 3 indices du livrable 1 puisque les
  camions sont identiques, et elle est plus rapide. Elle sert à prouver l'optimum des
  petites instances.
* **Trafic par tranche horaire, appliqué au départ.** Ce modèle est simple à expliquer et
  suffit à montrer l'effet des heures de pointe.
* **Instances Lorraine.** Elles placent le problème dans un contexte concret (Metz, Nancy,
  sillon lorrain) et s'affichent sur une vraie carte.
* **20 instances.** C'est le minimum demandé. Elles couvrent CVRP et CVRPTW, des fenêtres
  serrées et larges, des clients aléatoires, en grappes ou mixtes, et des tailles de 8 à
  3000 clients (« plusieurs milliers de villes »).

## 13. Références

* Solomon, M. (1987). Algorithms for the vehicle routing and scheduling problems with time
  window constraints. *Operations Research*, 35(2), 254-265.
* Uchoa, E. et al. (2017). New benchmark instances for the CVRP. *EJOR*, 257(3), 845-858.
* Gehring, H. & Homberger, J. (1999). A parallel hybrid evolutionary metaheuristic for the
  VRPTW. *Proceedings of EUROGEN99*.
* Arnold, F., Gendreau, M. & Sörensen, K. (2019). Efficiently solving very large-scale
  routing problems. *Computers & Operations Research*, 107, 32-42.
* Glover, F. (1986). Future paths for integer programming and links to artificial
  intelligence. *Computers & Operations Research*, 13(5), 533-549. (Recherche tabou)
* Feo, T. & Resende, M. (1995). Greedy randomized adaptive search procedures. *Journal of
  Global Optimization*, 6, 109-133. (GRASP)
* Instances : [PyVRP/Instances](https://github.com/PyVRP/Instances) (reprise de CVRPLIB),
  lues avec [vrplib](https://github.com/PyVRP/VRPLIB).
