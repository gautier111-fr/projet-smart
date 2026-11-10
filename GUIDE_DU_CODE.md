# Guide du code

Ce guide explique le code du projet pour pouvoir **répondre aux questions** à l'oral : les
données, la vérification des contraintes, la PLNE, la métaheuristique GRASP + Tabou, les
scripts d'expérience et les résultats. Les questions probables et leurs réponses sont à la
fin (partie 9). Pour installer et lancer le projet, voir le [README](README.md).

L'interface (`app.py`) n'est qu'un affichage : elle appelle les fonctions décrites ici
(partie 10).

---

## 1. Vue d'ensemble

### Le problème
Des camions **identiques** (capacité Q) partent d'un **dépôt**, livrent des **clients** (chacun
a une demande q_i, une fenêtre de temps [a_i, b_i] et un temps de livraison s_i), puis
reviennent au dépôt. On cherche les tournées qui **minimisent la distance totale**. C'est le
**CVRPTW** (niveau A du sujet) ; sans fenêtres de temps, c'est le **CVRP** (niveau B).

### Comment on représente une solution
Une **tournée** est la liste des clients d'un camion, **sans le dépôt** ; une **solution** est
une liste de tournées :

```
[[1, 2, 3], [5, 4, 6]]   <=>   camion 1 : 0 → 1 → 2 → 3 → 0      camion 2 : 0 → 5 → 4 → 6 → 0
```

Le sommet **0 est toujours le dépôt**, les clients sont numérotés de 1 à n.

### Le trajet d'une résolution

```
 instance ──► méthode (GRASP + Tabou, ou PLNE) ──► tournées ──► vérification (coût, contraintes, gap)
```

| Étape | Fichier |
|---|---|
| les données (instances) | `probleme/instances.py`, `probleme/lorraine.py` |
| la vérification, le trafic, le gap | `probleme/contraintes.py` |
| la méthode exacte | `algorithmes/plne.py` |
| la métaheuristique | `algorithmes/grasp_tabou_cvrptw.py` |
| le lien entre les deux | `algorithmes/methodes.py` |
| les expériences du notebook | `benchmark_vrplib.py`, `etude_statistique.py` |

**Principe important :** les méthodes ne font que **calculer des tournées**. La vérification
est faite **à part** (`evaluer`), de la même façon pour toutes : on ne fait pas confiance à
l'algorithme, et la comparaison est équitable.

---

## 2. Les données : `probleme/instances.py` et `probleme/lorraine.py`

### Une instance = un dictionnaire

| Clé | Contenu |
|---|---|
| `nom`, `famille`, `type` | nom, famille (« VRPTW R (aléatoires), fenêtres serrées »…), « CVRP » ou « CVRPTW » |
| `n` | nombre de clients |
| `coords` | coordonnées (x, y) de chaque sommet |
| `demande` | `demande[i]` = quantité à livrer au client i (0 pour le dépôt) |
| `capacite` | Q, la capacité d'un camion |
| `nb_vehicules` | K, le nombre de camions disponibles (`None` = illimité) |
| `distance` | matrice `distance[i, j]` = distance = durée du trajet i → j |
| `fenetres` | `fenetres[i] = [a_i, b_i]`, ou `None` en CVRP |
| `service` | s_i, le temps de livraison chez i (0 au dépôt) |
| `horizon` | fin de la journée (fermeture du dépôt), utile pour le trafic |
| `trafic` | profil de trafic, ou `None` s'il est désactivé |
| `bks` | coût de la meilleure solution connue (*Best Known Solution*), ou `None` |

### Les fonctions
* **`matrice_distances(coords, arrondi)`** : distances euclidiennes entre tous les points,
  calculées d'un coup avec numpy, puis **arrondies comme dans la littérature** :
  * instances X (CVRP) : à l'entier le plus proche ;
  * Solomon et Homberger (VRPTW) : **tronquées** à 1 décimale ;
  * exemple du livrable 1 : arrondies à 0,1.

  C'est indispensable : avec un autre arrondi, on ne retrouve pas le coût des solutions de
  référence et le gap est faux de plusieurs pour cent.
* **`construire_instance(...)`** range les données dans le dictionnaire. En CVRP (pas
  d'horaires), on fixe une journée égale à 4 fois la distance du client le plus lointain,
  soit deux allers-retours (hypothèse, utile seulement pour le trafic).
* **`famille_instance(nom)`** déduit la famille du nom : C = clients regroupés, R = aléatoires,
  RC = mixtes ; série 1 = fenêtres serrées, série 2 = fenêtres larges ; X = CVRP d'Uchoa…
* **`charger_instance(chemin)`** lit un fichier `.vrp` avec la bibliothèque `vrplib`, et le
  `.sol` du même nom s'il existe (coût de la meilleure solution connue).
* **`INSTANCES_INTERFACE`** et **`lister_instances()`** : les 20 instances étudiées (15 fichiers
  + 5 de Lorraine). Toutes les instances sont dans le dossier `instances/`, une seule fois.
* **`exemple_livrable1()`** : l'exemple à 6 clients du livrable 1 (Q = 12, K = 2, optimum 33,9).

### Les 20 instances

| Instances | Type | Clients | Origine | Référence pour le gap |
|---|---|---|---|---|
| C101, C201, R101, R201, RC101, RC201 | CVRPTW | 100 | Solomon : regroupés / aléatoires / mixtes ; fenêtres serrées (1) ou larges (2) | BKS |
| R1_10_1 | CVRPTW | 1 000 | Gehring & Homberger | BKS |
| X-n101-k25, X-n200-k36, X-n502-k39, X-n1001-k43 | CVRP | 100 à 1 000 | Uchoa et al. 2017 | BKS |
| Leuven1 | CVRP | 3 000 | Arnold et al. 2019 | BKS |
| GEN-uniforme-centre-serrees-n8-g1 | CVRPTW | 8 | générée par nous | optimum PLNE 342,4 |
| GEN-clusters-centre-serrees-n200-g1 | CVRPTW | 200 | générée (centre-ville, créneaux serrés) | — |
| GEN-clusters-coin-aucune-n2000-g1 | CVRP | 2 000 | générée (métropole, dépôt excentré) | — |
| LOR-Metz-agglo | CVRPTW | 10 | Lorraine (villes réelles) | optimum PLNE 113,2 |
| LOR-Moselle-Est, LOR-Nancy-agglo, LOR-Sillon-lorrain, LOR-Lorraine-complete | CVRP / CVRPTW | 15 à 68 | Lorraine | — |

Elles couvrent ce que le sujet demande d'analyser : la **taille** (8 à 3 000 clients), la
**répartition** des clients (regroupés, aléatoires, mixtes, en grappes) et les **contraintes**
(sans fenêtres, fenêtres serrées, fenêtres larges). Les autres fichiers de `instances/`
(C102, R205, X-n110-k13…) servent au benchmark du notebook.

**Pourquoi le gap est fiable :** en recalculant avec notre code le coût des meilleures
solutions publiées, on retrouve exactement les valeurs publiées (C101 : 827,3 ; X-n101-k25 :
27 591 ; R1_10_1 : 53 026,1 ; Leuven1 : 192 848).

### Les instances de Lorraine (`lorraine.py`)
68 communes de Moselle et de Meurthe-et-Moselle, avec leur vraie position. Hypothèses :
* **durée (min) = distance à vol d'oiseau (km) × 1,3** : les routes font environ 30 % de
  détours, et à 60 km/h, 1 km de route prend 1 minute ;
* dépôt ouvert de 6h00 à 20h00 (360 à 1200 minutes depuis minuit), 15 min par livraison ;
* créneaux tirés au hasard : matin (8h-12h), après-midi (14h-18h) ou journée (8h-18h) ;
* demandes de 5 à 30 colis, camions de 100 colis (120 pour la Moselle-Est) ;
* tirages avec une **graine fixe** (2026) : l'instance est toujours la même ;
* trafic : bouchons de 7h à 9h et de 16h30 à 19h (× 1,5), midi (× 1,2).

---

## 3. La vérification et le trafic : `probleme/contraintes.py`

### `evaluer(instance, routes)` : le juge
Elle simule la journée de chaque camion, arrêt par arrêt :

```
heure = heure de départ du dépôt
pour chaque client de la tournée :
    arrivée = heure + durée du trajet (avec le trafic s'il est activé)
    début   = max(arrivée, a_client)          ← en avance : on ATTEND l'ouverture
    si début > b_client : violation           ← livrer en retard est INTERDIT
    heure   = début + s_client                ← fin de la livraison
retour au dépôt : violation s'il arrive après sa fermeture
```

Elle contrôle **toutes** les contraintes du sujet et du livrable 1 :

| Contrainte | Comment |
|---|---|
| chaque client est livré **une et une seule fois** | aucun client oublié, en double ou inconnu |
| **capacité** Q identique pour tous | somme des demandes de chaque tournée ≤ Q |
| **fenêtres de temps**, attente autorisée | `début = max(arrivée, a_i)` et `début ≤ b_i` |
| retour au dépôt avant sa fermeture | heure de retour ≤ b_0 |
| **nombre de camions** | nombre de tournées ≤ K |

Elle renvoie la distance totale (le coût, celui des solutions de référence), le nombre de
camions, `realisable` (vrai / faux), la liste des violations en clair et le détail de chaque
arrêt (arrivée, début, attente, fin).

### Le trafic
La journée est découpée en tranches ; chacune a un coefficient :

```
durée du trajet = distance × coefficient de la tranche de l'heure de DÉPART
```

Exemple : un trajet de 20 min qui part à 8h, en heure de pointe (× 1,5), dure 30 min.
`coefficient_trafic` trouve la tranche, `temps_trajet` calcule la durée. Limite assumée : le
coefficient ne change pas en cours de trajet. Avec le trafic, une solution optimale « sur le
papier » peut devenir irréalisable (c'est le cas de la meilleure solution connue de C101).

### Le gap
```
gap (%) = 100 × (coût trouvé − coût de référence) / coût de référence
```
C'est la formule du sujet. Au-delà de 7-10 %, la note est limitée à B. Les références sont
calculées sans trafic : on ne calcule le gap que sans trafic.

---

## 4. La méthode exacte : `algorithmes/plne.py`

`plne_exacte(instance, temps_max)` écrit le **PLNE du livrable 1** avec PuLP et le fait
résoudre par le solveur **CBC**.

### Variables
* **x_ij** ∈ {0, 1} : vaut 1 si un camion va directement de i à j.
* **u_i** ∈ [q_i, Q] : charge du camion **après** avoir livré i (contraintes MTZ).
* **T_i** ∈ [a_i, b_i] : heure de début de livraison chez i (seulement avec fenêtres). Le
  domaine de T_i impose déjà la fenêtre de temps.

### Objectif
minimiser  Σ c_ij · x_ij  (la distance totale).

### Contraintes (dans l'ordre du code)
| Contrainte | Formule | Sens |
|---|---|---|
| visite unique | Σ_i x_ij = 1 pour chaque client j | on arrive une fois chez chaque client |
| continuité | Σ_l x_jl = 1 pour chaque client j | on repart une fois de chaque client |
| dépôt | Σ_j x_0j = Σ_i x_i0 | autant de camions partent que reviennent |
| flotte | Σ_j x_0j ≤ K | pas plus de K camions |
| capacité + sous-tours (MTZ) | u_i − u_j + Q·x_ij ≤ Q − q_j | si on va de i à j, u_j ≥ u_i + q_j : la charge augmente, donc pas de cycle sans dépôt, et u ≤ Q |
| départ du dépôt | T_j ≥ a_0 + c_0j − M(1 − x_0j) | si j est le premier client, il ne peut pas être servi avant d'être atteint |
| enchaînement | T_i + s_i + c_ij − T_j ≤ M(1 − x_ij) | si on va de i à j, j commence après la fin de i plus le trajet |
| retour | T_j + s_j + c_j0 ≤ b_0 + M(1 − x_j0) | le dernier client laisse le temps de rentrer |

**Big-M :** M = b_0 + max(s) + max(c). Quand x_ij = 0, M rend la contrainte toujours vraie ;
quand x_ij = 1, elle s'applique. L'attente est autorisée car on écrit « ≥ », pas « = ».

### Pourquoi 2 indices (x_ij) au lieu de 3 (x_ijk) comme au livrable 1
Les camions sont **identiques** : savoir *quel* camion fait une tournée n'apporte rien. Le
modèle à 2 indices est équivalent, avec K fois moins de variables, et il évite les solutions
symétriques (les mêmes tournées avec les camions numérotés autrement), qui ralentissent CBC.

### Après la résolution
On reconstruit les tournées en suivant les arcs x_ij = 1 depuis le dépôt : chaque arc qui
part du dépôt est un camion. Le solveur a une **limite de temps** : passé ce délai, il rend la
meilleure solution trouvée, **sans preuve d'optimalité**.

### Limite
Le temps explose avec n (problème NP-difficile) : la PLNE est réservée à **15 clients**. Mesuré
(notebook, partie 9) : l'optimum est prouvé en moins de 3 s jusqu'à 10 clients ; à 15 clients,
CBC atteint la limite de 60 s sans preuve. Le trafic n'est pas modélisé dans la PLNE.

---

## 5. La métaheuristique : `algorithmes/grasp_tabou_cvrptw.py`

C'est **une seule méthode** en deux temps, répétée (multi-start) :
* le **GRASP** (*Greedy Randomized Adaptive Search Procedure*) **construit** une solution avec
  un glouton un peu aléatoire : c'est la **diversification** (chaque départ est différent) ;
* la **recherche tabou** l'**améliore** en se déplaçant de voisin en voisin : c'est
  l'**intensification**.

La logique suit le workshop du sac à dos. Les données sont dans des **variables globales**
(`n` sommets dépôt compris, `q`, `Q`, `tw` fenêtres, `s` service, `dist`, `proches`).

### 5.1 Les données : `charger_instance(...)`
* calcule la matrice `dist` avec numpy (avec l'arrondi des références si demandé), puis la
  convertit en listes Python : lire `dist[i][j]` case par case est plus rapide sur une liste ;
* calcule `proches[i]`, la liste des clients **du plus proche au plus loin** de i (le dépôt et
  i lui-même exclus). **Au-delà de 500 clients** (`SEUIL_KNN`), on ne garde que les
  **30 plus proches** (`K_VOISINS`) ; en dessous, on les garde tous.

### 5.2 Les fonctions de base
* `cout_tournee(t)` : dépôt → clients → dépôt ; `cout_solution(S)` : somme sur les tournées
  (la fonction objectif).
* `tournee_valide(t)` : capacité, puis simulation des horaires (même logique que `evaluer` :
  attente si trop tôt, refus si trop tard, retour avant la fermeture du dépôt).

### 5.3 La construction GRASP : `grasp_construction(alpha)`
On construit les tournées une par une, en ajoutant les clients à la fin :
1. **Candidats** : les clients non livrés qui respectent la capacité, leur fenêtre et le
   retour au dépôt. Le test est en **O(1)** par client : on garde la charge et l'heure du
   camion après le dernier client, au lieu de re-simuler toute la tournée.
2. **Score** de chaque candidat j depuis le dernier client i :
   `score(j) = d_ij + 0,1 × b_j` → on préfère les clients **proches** et **pressés** (fenêtre
   qui ferme tôt). Sans fenêtres, le score est la distance.
3. **Liste restreinte (RCL)** : les candidats tels que
   `score ≤ s_min + alpha × (s_max − s_min)`.
4. On tire **au hasard** un client de la RCL et on l'ajoute.
5. Quand plus aucun client ne rentre, on ferme la tournée et on en ouvre une autre.

**Rôle d'alpha :** alpha = 0 → seul le meilleur score est gardé, c'est le plus proche voisin
(aucun hasard) ; alpha = 1 → tous les candidats, c'est le hasard pur. Nous utilisons
**alpha = 0,1** (meilleur réglage mesuré, partie 6 du notebook), et **0 au-delà de 500 clients**
(sur une grande carte, l'écart s_max − s_min est si grand que même 0,1 laisse entrer des
clients lointains).

*Exemple :* scores 10, 12, 15, 30 et alpha = 0,1 → seuil = 10 + 0,1 × 20 = 12 → RCL = {10, 12},
on tire l'un des deux.

### 5.4 Le voisinage : `voisinage(solution, taille_echantillon)`
Un **voisin** est la solution obtenue par **un mouvement** :

| Mouvement | Effet | Variation du coût (delta) |
|---|---|---|
| **relocate** | retirer le client c (entre a et b) et l'insérer entre x et y | (d_ab − d_ac − d_cb) + (d_xc + d_cy − d_xy) |
| relocate vers un **nouveau camion** | 0 → c → 0 | (d_ab − d_ac − d_cb) + 2 d_0c |
| **swap** | échanger c (entre a et b) et d (entre e et f) de deux tournées | d_ad + d_db − d_ac − d_cb + d_ec + d_cf − d_ed − d_df |
| **2-opt** (désactivé, `UTILISER_2OPT`) | inverser le morceau c … e d'une tournée | d_ae + d_cf − d_ac − d_ef |

Points clés :
* **Coût par différence (delta) :** seules 3 ou 4 distances changent, donc on calcule le coût
  d'un voisin en **O(1)** au lieu de recopier et recalculer toute la solution en O(n).
* **Échantillon :** à chaque itération, on ne déplace que **25 clients tirés au hasard**
  (`taille_echantillon`), sinon le voisinage serait énorme.
* **Positions utiles seulement :** un client n'est inséré que **juste avant ou juste après
  un de ses voisins** (`proches`), et échangé qu'avec eux : insérer un client loin de tout
  n'est jamais intéressant.
* Le générateur renvoie des **mouvements** (`(type, r1, p1, r2, p2)`), pas des solutions :
  on ne construit la nouvelle solution que pour le mouvement choisi
  (`tournees_modifiees`, `appliquer_mouvement`).
* La validité (capacité, fenêtres) n'est **pas** vérifiée dans le voisinage, mais seulement
  pour les mouvements intéressants (`mouvement_valide`), car elle coûte plus cher.
* Un nouveau camion n'est ouvert que s'il en reste un (`k_max`).

### 5.5 La recherche tabou : `recherche_tabou(...)`
```
courante = solution GRASP ; meilleure = courante
tant que moins de iter_max itérations sans amélioration (et qu'il reste du temps) :
    parmi les voisins, prendre le MEILLEUR mouvement qui est :
        - réalisable (capacité, fenêtres),
        - non tabou, SAUF s'il bat le record (critère d'aspiration)
    l'appliquer, MÊME S'IL DÉGRADE le coût
    rendre tabous les clients déplacés
    si la nouvelle solution bat le record : la garder, remettre le compteur à 0
renvoyer la meilleure solution rencontrée
```
* **Accepter un voisin moins bon** permet de sortir d'un **optimum local** (une descente
  simple s'arrêterait au premier).
* **La liste tabou** (`deque(maxlen=10)`) contient les **10 derniers clients déplacés** : on ne
  peut pas les re-déplacer tout de suite, sinon on reviendrait en arrière et on tournerait
  en rond. Différence avec le workshop : on rend tabou un **mouvement** (le client déplacé),
  pas la solution entière, ce qui est plus simple et plus efficace pour le VRP.
* **Aspiration :** un mouvement tabou reste permis s'il donne un coût meilleur que le record.
* Le coût courant est mis à jour **par différence** (`cout_courant += delta`).
* **Arrêt :** `iter_max = 30` itérations sans amélioration, ou fin du temps (`heure_fin`).

### 5.6 Le multi-start : `grasp_tabou(...)`
Répète **construction GRASP → recherche tabou** jusqu'au temps maximum et garde la meilleure
solution. Comme la construction est aléatoire, chaque départ explore une autre région.

### 5.7 Le reste du fichier
* `verifier_solution(S)` : contrôle final (chaque client une fois, toutes les tournées valides).
* Lancé seul (`python algorithmes/grasp_tabou_cvrptw.py`), le fichier teste l'exemple du
  livrable 1 et une instance aléatoire de 100 clients.
* Les lignes **`# AJOUT interface`** (`depart`, `trajet()`, `k_max`) servent à
  l'interface : heure de départ des camions, trafic, nombre de camions. Avec leurs valeurs
  par défaut, elles ne changent rien au benchmark. (Le paramètre `suivi` de
  `recherche_tabou` et `grasp_tabou` permet de suivre la convergence ; il n'est pas utilisé.)

### 5.8 Paramètres

| Paramètre | Valeur | Rôle |
|---|---|---|
| `alpha` | 0,1 (0 au-delà de 500 clients) | part de hasard dans la construction |
| `taille_tabou` | 10 | nombre de clients tabous |
| `iter_max` | 30 | itérations sans amélioration avant de recommencer une construction |
| `taille_echantillon` | 25 | clients testés à chaque itération |
| `K_VOISINS`, `SEUIL_KNN` | 30, 500 | voisinage restreint aux 30 plus proches au-delà de 500 clients |
| temps maximum | 20 s (benchmark) | critère d'arrêt global |

### 5.9 Complexité
* **Construction :** à chaque ajout, on parcourt les clients restants (test en O(1)) → **O(n²)**
  par construction (0,22 s à 1 000 clients, 2,2 s à 3 000).
* **Une itération tabou :** 25 clients × leurs voisins (2 positions par voisin pour relocate,
  1 pour swap) → O(25 × K) deltas en O(1), plus quelques tests de validité en O(longueur de
  tournée). Au-delà de 500 clients, cela ne dépend plus de n.
* **Mémoire :** la matrice des distances fait n² cases (9 millions à 3 000 clients).

### 5.10 Le lien avec l'interface : `algorithmes/methodes.py`
`preparer(instance)` appelle `charger_instance` de ce fichier, puis lui donne les distances de
l'instance (avec les bons arrondis), l'heure de départ, le nombre de camions et le trafic.
`grasp_tabou(...)` lance la méthode avec les paramètres ci-dessus, et `lancer(...)` la
chronomètre et renvoie les tournées et le temps de calcul. `METHODES` contient les deux méthodes : GRASP + Tabou et PLNE.

---

## 6. Les scripts du notebook

### `benchmark_vrplib.py` : le gap sur les instances de référence
* `telecharger(nom)` : récupère l'instance et sa solution sur PyVRP/Instances si elles
  manquent dans `instances/` (utile sur Colab).
* `charger_vrplib(nom)` : lit l'instance avec `vrplib`, la charge dans le GRASP + Tabou avec
  **l'arrondi des BKS** (dixième pour Solomon, entier pour X) et renvoie le coût de référence.
* `tester(nom, graine, temps_max, …)` : lance GRASP + Tabou (alpha automatique) et renvoie
  coût, référence, **gap**, nombre de camions, temps, validité.
* `python benchmark_vrplib.py 20` : 20 instances (18 Solomon, 2 X), 20 s chacune, graine 0 ;
  écrit `resultats/resultats_20s.csv` et `resultats/gap_par_instance_20s.png`.

### `etude_statistique.py` : 4 expériences
| # | Expérience | Plan | Fichiers |
|---|---|---|---|
| 1 | Robustesse | 6 instances (C101, C201, R101, R201, RC101, RC201) × 5 graines, 10 s | `1_robustesse.*` |
| 2 | Convergence | 4 instances × 2, 5, 10, 30 s | `2_convergence.*` |
| 3 | Taille | X-n101 à X-n1001 et Leuven1, 60 s ; temps d'une construction | `3_taille.*` |
| 4 | Sensibilité | alpha (0 à 0,7) puis taille tabou (3 à 40), 3 instances, 10 s | `4_sensibilite.*` |

`python etude_statistique.py` (environ 25 min) ou `python etude_statistique.py 1 3`.

### Le dossier `resultats/`
* `resultats_20s.csv` / `.png` : benchmark final ; `_alpha02` et `_alpha01` : les versions
  précédentes (avant les améliorations 1 et 2), gardées pour la comparaison et le test de
  Wilcoxon (partie 8 du notebook).
* `1_` à `4_` : les 4 expériences de l'étude statistique.

---

## 7. Les résultats à connaître

| Mesure | Résultat |
|---|---|
| Benchmark (20 instances Solomon et X, 20 s) | gap moyen **3,50 %**, **19 / 20 sous 7 %** (seule RC205 : 7,95 %), toutes valides |
| Meilleures familles | clients regroupés (C1, C2) : gap ≈ 0 % |
| Plus difficile | fenêtres larges (R2, RC2) |
| Réglage alpha 0,2 → 0,1 | 4,98 % → 3,34 % ; **significatif** (Wilcoxon, p = 0,022) |
| Passage à l'échelle (60 s) | X-n1001 : 37 % → **7,8 %** ; Leuven1 (3 000 clients) : **6,8 %** |
| PLNE | optimum prouvé jusqu'à 10 clients et **retrouvé par GRASP + Tabou** ; à 15 clients, pas de preuve en 60 s |

---

## 8. Les choix et leurs raisons

* **GRASP + Tabou :** le GRASP donne des départs variés, la tabou les améliore sans rester
  bloquée dans un optimum local ; les deux sont simples à expliquer et à régler.
* **Séparer calcul et vérification :** `evaluer()` juge toutes les solutions de la même façon.
* **Seulement des solutions réalisables :** un mouvement qui viole une contrainte est refusé
  (pas de pénalité dans le coût).
* **Coût par différence, construction incrémentale, plus proches voisins :** ce sont les trois
  accélérations qui permettent de traiter des milliers de clients.
* **Voisinage restreint seulement au-delà de 500 clients :** sur les petites instances à
  fenêtres larges, la bonne place d'un client n'est pas toujours à côté de ses voisins
  géographiques (RC2 passait de 5,2 % à 8,4 %).
* **Arrêt au temps :** c'est la contrainte réelle d'un utilisateur ; contrepartie, une machine
  plus rapide fait plus d'itérations, donc les résultats varient un peu d'un PC à l'autre.
* **PLNE à 2 indices :** équivalente au modèle du livrable 1, plus rapide.
* **Trafic par tranche horaire au départ :** simple, suffisant pour montrer l'effet des heures
  de pointe.

---

## 9. Questions probables et réponses

**Pourquoi ne pas résoudre tout avec la PLNE ?**
Le problème est NP-difficile : le temps de résolution exacte explose. Mesuré : optimum en
moins de 3 s à 10 clients, pas de preuve d'optimalité en 60 s à 15 clients. Les instances
réelles ont des centaines ou des milliers de clients.

**Qu'est-ce qu'une métaheuristique ?**
Une méthode générale qui cherche une **très bonne** solution en temps limité, **sans garantie**
d'optimalité. On mesure sa qualité par le gap aux meilleures solutions connues.

**Comment la PLNE évite-t-elle les sous-tours ?**
Avec les contraintes **MTZ** : u_j ≥ u_i + q_j quand on va de i à j. La charge ne fait
qu'augmenter le long d'une tournée, donc un cycle qui ne passe pas par le dépôt est
impossible. Les mêmes variables imposent u ≤ Q, c'est-à-dire la capacité.

**À quoi sert le M (big-M) ?**
À « désactiver » une contrainte de temps quand l'arc n'est pas utilisé (x_ij = 0). Quand
x_ij = 1, la contrainte T_j ≥ T_i + s_i + c_ij s'applique.

**Comment l'attente est-elle autorisée ?**
Dans la PLNE, par une inégalité (≥) et le domaine T_i ∈ [a_i, b_i]. Dans le code, par
`début = max(arrivée, a_i)` : si le camion arrive tôt, il attend l'ouverture.

**Que fait alpha ?**
Il règle la taille de la liste restreinte (RCL) : 0 = glouton pur, 1 = hasard pur. Avec 0,1,
on choisit au hasard parmi les tout meilleurs candidats.

**Pourquoi la recherche tabou accepte-t-elle des solutions moins bonnes ?**
Pour sortir des optimums locaux. Sans ça, on s'arrêterait au premier « creux ».

**À quoi sert la liste tabou ?**
À ne pas annuler tout de suite un mouvement (re-déplacer le même client), ce qui ferait
tourner en rond. Elle garde les 10 derniers clients déplacés.

**Qu'est-ce que le critère d'aspiration ?**
Une exception : un mouvement tabou est autorisé s'il donne la meilleure solution jamais vue.

**Pourquoi calculer le coût « par différence » ?**
Un mouvement ne change que 3 ou 4 arcs : on calcule la variation en O(1) au lieu de
recalculer toute la solution en O(n). C'est ce qui permet de tester des milliers de voisins.

**Pourquoi un échantillon de 25 clients ?**
Tester tous les clients à chaque itération serait trop lent sur les grandes instances. Le
hasard de l'échantillon ajoute aussi de la diversité.

**Pourquoi le 2-opt est-il désactivé ?**
Sur nos tests, il n'améliorait pas le coût ; il reste disponible en option (`UTILISER_2OPT`).

**Pourquoi utilisez-vous parfois plus de camions que la BKS ?**
Nous minimisons la distance seulement ; les références de Solomon minimisent d'abord le nombre
de camions, puis la distance.

**Comment savez-vous que vos solutions sont valides ?**
`evaluer()` les revérifie toutes, indépendamment de l'algorithme, et le benchmark utilise
aussi `verifier_solution`. Toutes les solutions du benchmark sont valides.

**Pourquoi l'arrondi des distances est-il important ?**
Les coûts de référence sont calculés avec un arrondi précis (entier pour X, troncature au
dixième pour Solomon). Sans le même arrondi, le gap serait faux de plusieurs pour cent.

**Vos résultats sont-ils reproductibles ?**
Avec la même graine et la même machine, presque : l'arrêt se fait au temps, donc une machine
plus rapide fait plus d'itérations. Les conclusions restent les mêmes (notebook, 5.5).

**Comment avez-vous montré que les améliorations sont réelles ?**
Avec un **test de Wilcoxon apparié** sur les 20 instances : il compare les deux versions
instance par instance, sans supposer une loi normale. p < 0,05 : différence significative
(alpha 0,1 : p = 0,022).

**Pourquoi l'algorithme est-il moins bon sur les fenêtres larges ?**
Les tournées sont longues et les combinaisons très nombreuses ; nos mouvements simples
(déplacer ou échanger un client) explorent moins bien cet espace. Piste : des mouvements
plus forts (or-opt, 2-opt\*, destruction / reconstruction de type ALNS).

**Que se passe-t-il au-delà de 3 000 clients ?**
La construction en O(n²) et la matrice des distances en n² cases deviennent limitantes. Il
faudrait ne garder que les plus proches voisins au lieu de toute la matrice.

**Comment le trafic est-il pris en compte ?**
La durée d'un trajet est multipliée par le coefficient de la tranche horaire du départ.
L'algorithme l'utilise pour vérifier les fenêtres de temps (`trajet()`), et `evaluer()` aussi.

---

## 10. L'interface (en bref)

`streamlit run app.py` ouvre une page web pour **démontrer** la méthode. À gauche : l'instance,
le trafic, la méthode (GRASP + Tabou, ou PLNE jusqu'à 15 clients) et le temps de calcul. Après
▶ Lancer, `app.py` appelle `lancer(...)` puis `evaluer(...)`, et affiche la distance, le gap,
le nombre de camions, le temps, les contraintes respectées ou non, la carte des tournées et
le parcours de chaque camion. La carte est aussi un **suivi 2D** : à 100 moments de la journée (affichés en vrai horaire, « 7h29 », pour la Lorraine, et en % de la journée pour les autres instances, dont le temps est une unité abstraite égale à la distance),
on calcule la position de chaque camion avec `np.interp` (il va en ligne droite d'un lieu au
suivant et reste sur place pendant l'attente et la livraison), et le bouton ▶ fait défiler ces
heures. Tout tient dans `app.py` (environ 90 lignes, sans logique de calcul) : il n'y a rien à
connaître de plus pour répondre sur la méthode.
