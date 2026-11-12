# Guide du code

Ce guide sert à **se retrouver dans le code** et à **répondre aux questions** du jury sur
n'importe quel fichier. Il suit l'ordre des fichiers dans l'explorateur de VS Code, puis
déroule ce qui se passe quand on utilise l'interface, du lancement jusqu'au résultat.

| Partie | Contenu |
|---|---|
| [0. Comment lire ce guide dans VS Code](#0-comment-lire-ce-guide-dans-vs-code) | les raccourcis, et comment ouvrir une ligne citée |
| [1. Les 4 idées à connaître avant d'ouvrir le code](#1-les-4-idées-à-connaître-avant-douvrir-le-code) | le problème, l'instance, la solution, le principe du projet |
| [2. La carte du projet](#2-la-carte-du-projet) | tous les dossiers et fichiers, dans l'ordre de VS Code |
| [3. Fichier par fichier](#3-fichier-par-fichier) | ce que contient chaque fichier, ligne par ligne, et les questions possibles |
| [4. Le parcours dans l'interface](#4-le-parcours-dans-linterface-étape-par-étape) | chaque clic, et le code qui s'exécute derrière |
| [5. Les chiffres à connaître](#5-les-chiffres-à-connaître) | les résultats, et pourquoi ils peuvent varier d'un PC à l'autre |
| [6. Questions générales](#6-questions-générales) | les questions qui ne concernent pas un seul fichier |
| [7. Index de toutes les fonctions](#7-index-de-toutes-les-fonctions) | retrouver une fonction par son nom |

---

## 0. Comment lire ce guide dans VS Code

**Ouvrir le guide en mode lecture :** ouvrir `GUIDE_DU_CODE.md`, puis **Ctrl + Shift + V**
(ou clic droit sur l'onglet > *Ouvrir l'aperçu*). Les tableaux et les liens deviennent lisibles.

**Les liens vers le code.** Chaque fois que le guide cite du code, il donne un lien de la forme
📍 [`grasp_construction`, l. 150](algorithmes/grasp_tabou_cvrptw.py#L150). Dans l'aperçu,
**un clic ouvre le fichier directement à cette ligne** (ça marche aussi sur GitHub).

**Les raccourcis utiles pendant la soutenance :**

| Pour… | Raccourci |
|---|---|
| ouvrir un fichier par son nom | **Ctrl + P**, puis taper le nom (ex. `plne`) |
| aller à une ligne du fichier ouvert | **Ctrl + G**, puis le numéro de ligne |
| voir la liste des fonctions du fichier ouvert | **Ctrl + Shift + O** |
| sauter à la définition d'une fonction | clic sur son nom puis **F12** (ou Ctrl + clic) |
| revenir où on était | **Alt + ←** |
| chercher un mot dans tout le projet | **Ctrl + Shift + F** |
| replier / déplier toutes les fonctions | **Ctrl + K** puis **Ctrl + 0** / **Ctrl + K** puis **Ctrl + J** |

**Les symboles du guide :**
★ fichier à bien connaître · ○ fichier à savoir expliquer en une phrase ·
💬 question que le jury peut poser · ⚠️ point délicat.

---

## 1. Les 4 idées à connaître avant d'ouvrir le code

### Idée 1 : le problème
Des camions **identiques** (capacité Q) partent d'un **dépôt**, livrent des **clients**, puis
reviennent au dépôt. Chaque client a une **demande** q_i, une **fenêtre de temps** [a_i, b_i]
(le créneau où il accepte la livraison) et un **temps de livraison** s_i. Un camion en avance
**attend** l'ouverture ; un camion en retard est **interdit**. On cherche les tournées qui
**minimisent la distance totale** (qui est aussi la durée totale de trajet). C'est le **CVRPTW** ;
sans fenêtres de temps, c'est le **CVRP**.

### Idée 2 : une instance = un dictionnaire
Une instance, ce sont toutes les données d'un problème. Dans tout le projet, c'est un
dictionnaire Python construit par 📍 [`construire_instance`, l. 48](probleme/instances.py#L48).
Le **sommet 0 est toujours le dépôt**, les clients vont de 1 à n.

| Clé | Contenu |
|---|---|
| `n` | nombre de clients |
| `coords` | coordonnées (x, y) de chaque sommet |
| `demande` | `demande[i]` = quantité à livrer au client i (0 pour le dépôt) |
| `capacite` | Q, la capacité d'un camion |
| `nb_vehicules` | K, le nombre de camions disponibles (`None` = illimité) |
| `distance` | matrice `distance[i, j]` = distance = durée du trajet i → j |
| `fenetres` | `fenetres[i] = [a_i, b_i]`, ou `None` en CVRP |
| `service` | s_i, le temps de livraison chez i (0 au dépôt) |
| `horizon` | fin de la journée (fermeture du dépôt) |
| `trafic` | profil de trafic, ou `None` s'il est désactivé |
| `bks` | coût de la meilleure solution connue (*Best Known Solution*), ou `None` |
| `nom`, `famille`, `type` | pour l'affichage (« CVRP » ou « CVRPTW ») |

### Idée 3 : une solution = une liste de tournées
Une **tournée** est la liste des clients d'un camion, **sans le dépôt** (il est sous-entendu au
début et à la fin). Une **solution** est une liste de tournées :

```
[[1, 2, 3], [5, 4, 6]]   =   camion 1 : 0 → 1 → 2 → 3 → 0     et     camion 2 : 0 → 5 → 4 → 6 → 0
```

### Idée 4 : on sépare le calcul et la vérification

```
  instance ──►  méthode (GRASP + Tabou, ou PLNE)  ──►  tournées  ──►  evaluer() : coût, contraintes, horaires  ──►  gap
              algorithmes/                                         probleme/contraintes.py
```

Les méthodes ne font que **proposer des tournées**. Une fonction à part,
📍 [`evaluer`, l. 56](probleme/contraintes.py#L56), **revérifie toutes les contraintes**, de la
même façon pour les deux méthodes. On ne fait pas confiance à l'algorithme, et la comparaison
est équitable.

**Qui appelle qui :**

```
app.py  (l'interface)
 ├── probleme/instances.py     → lire l'instance choisie (et probleme/lorraine.py pour la Moselle)
 ├── algorithmes/methodes.py   → lancer la méthode choisie et la chronométrer
 │     ├── algorithmes/grasp_tabou_cvrptw.py   → la métaheuristique
 │     └── algorithmes/plne.py                 → la méthode exacte
 ├── probleme/contraintes.py   → vérifier la solution, le trafic, le gap
 └── bonus_3d/suivi_3d.py      → l'onglet 3D (bonus, affichage seulement)

benchmark_vrplib.py, etude_statistique.py  (les expériences du notebook)
 └── algorithmes/grasp_tabou_cvrptw.py
```

---

## 2. La carte du projet

Dans l'ordre où VS Code les affiche (les dossiers d'abord, puis les fichiers).

```
projet-smart/
├── __pycache__/                    ✗  créé tout seul par Python (fichiers compilés), à ignorer
├── algorithmes/                        LES DEUX MÉTHODES DE RÉSOLUTION
│   ├── grasp_tabou_cvrptw.py      ★  la métaheuristique GRASP + recherche tabou
│   ├── methodes.py                ★  le lien entre l'interface et les deux méthodes
│   └── plne.py                    ★  la méthode exacte (PLNE résolue par CBC)
├── bonus_3d/                       ✗  BONUS : l'onglet « Suivi 3D » (affichage seulement)
├── images/                         ○  la capture de l'interface (pour le README)
├── instances/                      ○  LES DONNÉES : fichiers .vrp (instance) et .sol (meilleure solution connue)
├── probleme/                           LES DONNÉES ET LES RÈGLES DU PROBLÈME
│   ├── contraintes.py             ★  vérifier une solution, le trafic, le gap
│   ├── instances.py               ★  lire, créer et lister les instances
│   └── lorraine.py                ○  2 instances inventées sur de vraies communes de Moselle
├── resultats/                      ○  les CSV et graphiques produits par les expériences
├── .gitignore                      ✗  les fichiers que git ne doit pas enregistrer
├── app.py                         ★  l'interface Streamlit
├── benchmark_vrplib.py            ★  le gap sur 20 instances de référence
├── etude_statistique.py           ○  les 4 expériences : robustesse, convergence, taille, sensibilité
├── GUIDE_DU_CODE.md                   ce guide
├── lancer_interface.bat           ○  double-clic = ouvrir l'interface
├── Projet_Smart.ipynb             ★  le livrable : modélisation, méthode, étude expérimentale
├── README.md                      ○  présentation du projet, installation, lancement
└── requirements.txt               ○  les bibliothèques à installer
```

**Le code en chiffres :** 887 lignes de code (1 484 avec les commentaires et les lignes vides),
sans compter le bonus 3D.

| Fichier | Lignes de code | Lignes en tout |
|---|---|---|
| `algorithmes/grasp_tabou_cvrptw.py` | 253 | 493 |
| `probleme/instances.py` | 122 | 187 |
| `etude_statistique.py` | 113 | 172 |
| `app.py` | 90 | 121 |
| `benchmark_vrplib.py` | 83 | 148 |
| `probleme/contraintes.py` | 77 | 130 |
| `probleme/lorraine.py` | 72 | 111 |
| `algorithmes/plne.py` | 44 | 64 |
| `algorithmes/methodes.py` | 33 | 58 |

---

## 3. Fichier par fichier

### 📁 `algorithmes/` : les deux méthodes de résolution

---

#### 📄 ★ `algorithmes/grasp_tabou_cvrptw.py` : la métaheuristique GRASP + Tabou

**À quoi il sert.** C'est le cœur du projet : il cherche de très bonnes tournées, sans garantie
d'optimalité, en un temps limité. Il est construit comme le workshop du sac à dos (mêmes
étapes : solution de départ, voisinage, recherche tabou), adapté aux tournées.

**Le principe en 3 étapes**, répétées jusqu'à la fin du temps :
1. **Construction GRASP** : on remplit les tournées client par client ; le suivant est **tiré au
   hasard parmi les meilleurs candidats** (proches et pressés). Ça donne des points de départ variés.
2. **Recherche tabou** : on améliore la solution en déplaçant ou en échangeant des clients ; on
   va toujours au **meilleur voisin, même s'il est moins bon**, pour sortir des optimums locaux.
3. **Multi-start** : on recommence avec une nouvelle construction et on garde la meilleure solution.

**Il est utilisé par :** `algorithmes/methodes.py` (l'interface), `benchmark_vrplib.py` et
`etude_statistique.py` (le notebook). Le notebook en contient une copie (cellule `%%writefile`,
Livrable 2, partie 1).

⚠️ **Variables globales.** Comme au workshop, les données de l'instance (`n`, `q`, `Q`, `tw`,
`s`, `dist`, `proches`) sont des variables **globales** du fichier, remplies par
`charger_instance`. Il faut donc charger l'instance avant chaque résolution.

**Ce qu'il y a dedans, dans l'ordre du fichier** (Ctrl + Shift + O pour la liste) :

| Lignes | Nom | Rôle |
|---|---|---|
| [1-16](algorithmes/grasp_tabou_cvrptw.py#L1) | en-tête | explication générale, format d'une solution |
| [25-28](algorithmes/grasp_tabou_cvrptw.py#L25) | `UTILISER_2OPT` | interrupteur du mouvement 2-opt (désactivé) |
| [30-37](algorithmes/grasp_tabou_cvrptw.py#L30) | `K_VOISINS`, `SEUIL_KNN` | au-delà de 500 clients, on ne teste que les 30 plus proches voisins |
| [39-42](algorithmes/grasp_tabou_cvrptw.py#L39) | `depart`, `k_max` | ajout pour l'interface : heure de départ, nombre de camions |
| [45](algorithmes/grasp_tabou_cvrptw.py#L45) | `trajet(i, j, heure)` | durée d'un trajet (remplacée quand le trafic est activé) |
| **Partie 1** [l. 52](algorithmes/grasp_tabou_cvrptw.py#L52) | | **Les données** |
| [57](algorithmes/grasp_tabou_cvrptw.py#L57) | `charger_instance(...)` | remplit les variables globales, calcule les distances et les plus proches voisins |
| **Partie 2** [l. 102](algorithmes/grasp_tabou_cvrptw.py#L102) | | **Les fonctions de base** |
| [105](algorithmes/grasp_tabou_cvrptw.py#L105) | `cout_tournee(tournee)` | distance d'une tournée, dépôt compris |
| [115](algorithmes/grasp_tabou_cvrptw.py#L115) | `cout_solution(solution)` | somme des tournées = la fonction objectif |
| [120](algorithmes/grasp_tabou_cvrptw.py#L120) | `tournee_valide(tournee)` | vrai / faux : capacité, fenêtres, retour au dépôt |
| **Partie 3** [l. 147](algorithmes/grasp_tabou_cvrptw.py#L147) | | **La construction GRASP** |
| [150](algorithmes/grasp_tabou_cvrptw.py#L150) | `grasp_construction(alpha)` | construit une solution de départ |
| **Partie 4** [l. 214](algorithmes/grasp_tabou_cvrptw.py#L214) | | **Le voisinage** |
| [231](algorithmes/grasp_tabou_cvrptw.py#L231) | `autour(tournee, p)` | le client d'avant et celui d'après |
| [238](algorithmes/grasp_tabou_cvrptw.py#L238) | `voisinage(solution, ...)` | produit les mouvements possibles et leur coût |
| [312](algorithmes/grasp_tabou_cvrptw.py#L312) | `tournees_modifiees(...)` | construit seulement les tournées changées par un mouvement |
| [340](algorithmes/grasp_tabou_cvrptw.py#L340) | `clients_touches(...)` | les clients à rendre tabous |
| [354](algorithmes/grasp_tabou_cvrptw.py#L354) | `mouvement_valide(...)` | le mouvement respecte-t-il les contraintes ? |
| [359](algorithmes/grasp_tabou_cvrptw.py#L359) | `appliquer_mouvement(...)` | renvoie la nouvelle solution |
| **Partie 5** [l. 368](algorithmes/grasp_tabou_cvrptw.py#L368) | | **La recherche tabou** |
| [371](algorithmes/grasp_tabou_cvrptw.py#L371) | `recherche_tabou(...)` | améliore une solution |
| **Partie 6** [l. 435](algorithmes/grasp_tabou_cvrptw.py#L435) | | **Le multi-start** |
| [438](algorithmes/grasp_tabou_cvrptw.py#L438) | `grasp_tabou(...)` | répète construction + tabou, garde la meilleure |
| [461](algorithmes/grasp_tabou_cvrptw.py#L461) | `verifier_solution(solution)` | contrôle final : chaque client une fois, tournées valides |
| **Partie 7** [l. 468](algorithmes/grasp_tabou_cvrptw.py#L468) | | **Les tests** (quand on lance le fichier seul) |

##### Les passages importants

**`charger_instance`** 📍 [l. 57](algorithmes/grasp_tabou_cvrptw.py#L57)
- [l. 79-80](algorithmes/grasp_tabou_cvrptw.py#L79) : toutes les distances calculées **d'un coup** avec numpy (au lieu d'une double boucle).
- [l. 81-84](algorithmes/grasp_tabou_cvrptw.py#L81) : l'arrondi des instances de référence (« dixieme » pour Solomon, « entier » pour X).
- [l. 87](algorithmes/grasp_tabou_cvrptw.py#L87) : on repasse en liste Python, plus rapide pour lire une case à la fois.
- [l. 89-98](algorithmes/grasp_tabou_cvrptw.py#L89) : pour chaque client, la liste de ses plus proches voisins (`proches`), triés par distance.

**`tournee_valide`** 📍 [l. 120](algorithmes/grasp_tabou_cvrptw.py#L120) : on simule le trajet du camion.
- [l. 126](algorithmes/grasp_tabou_cvrptw.py#L126) : capacité ;
- [l. 133-134](algorithmes/grasp_tabou_cvrptw.py#L133) : fin de la livraison précédente, puis trajet ;
- [l. 135](algorithmes/grasp_tabou_cvrptw.py#L135) : `max(t, a_i)` = **attente** si on arrive trop tôt ;
- [l. 136](algorithmes/grasp_tabou_cvrptw.py#L136) : trop tard = interdit ;
- [l. 140-143](algorithmes/grasp_tabou_cvrptw.py#L140) : retour au dépôt avant sa fermeture.

**`grasp_construction`** 📍 [l. 150](algorithmes/grasp_tabou_cvrptw.py#L150)
- [l. 162](algorithmes/grasp_tabou_cvrptw.py#L162) : au départ, tous les clients sont à livrer.
- [l. 167](algorithmes/grasp_tabou_cvrptw.py#L167) : on ouvre un camion, et on garde sa **charge** et son **heure** au fil de la tournée.
- [l. 173-183](algorithmes/grasp_tabou_cvrptw.py#L173) : les **candidats**, c'est-à-dire les clients qu'on peut ajouter à la fin de la tournée sans rien violer. Chacun est testé en O(1) grâce à la charge et à l'heure gardées : [l. 175](algorithmes/grasp_tabou_cvrptw.py#L175) capacité, [l. 178-179](algorithmes/grasp_tabou_cvrptw.py#L178) fenêtre, [l. 181](algorithmes/grasp_tabou_cvrptw.py#L181) retour au dépôt.
- [l. 184](algorithmes/grasp_tabou_cvrptw.py#L184) : plus aucun candidat, donc on ferme la tournée et on ouvre un nouveau camion.
- [l. 189](algorithmes/grasp_tabou_cvrptw.py#L189) : le **score** = distance + 0,1 × fin du créneau. On préfère les clients **proches et pressés**.
- [l. 193-195](algorithmes/grasp_tabou_cvrptw.py#L193) : la **RCL** (liste restreinte de candidats) = ceux dont le score est sous `min + alpha × (max − min)`.
- [l. 198](algorithmes/grasp_tabou_cvrptw.py#L198) : on en tire un **au hasard** : c'est le côté « randomisé » du GRASP.
- [l. 207](algorithmes/grasp_tabou_cvrptw.py#L207) : si un client ne rentre même pas seul dans un camion, l'instance n'a pas de solution, donc erreur.

**`voisinage`** 📍 [l. 238](algorithmes/grasp_tabou_cvrptw.py#L238) : c'est un **générateur** (`yield`). Il produit les mouvements un par un, avec leur variation de coût `delta`, sans jamais construire la nouvelle solution.
- [l. 248-251](algorithmes/grasp_tabou_cvrptw.py#L248) : `position[client]` = (numéro de tournée, rang) ;
- [l. 254-255](algorithmes/grasp_tabou_cvrptw.py#L254) : on ne regarde qu'un **échantillon** de 25 clients au hasard à chaque itération ;
- [l. 262](algorithmes/grasp_tabou_cvrptw.py#L262) : ce qu'on gagne en retirant le client c (a → c → b devient a → b) ;
- [l. 264-286](algorithmes/grasp_tabou_cvrptw.py#L264) : **relocate** = déplacer c juste avant ou juste après un de ses proches voisins, ou dans un nouveau camion s'il en reste ([l. 266](algorithmes/grasp_tabou_cvrptw.py#L266)) ;
- [l. 288-297](algorithmes/grasp_tabou_cvrptw.py#L288) : **swap** = échanger c avec un proche voisin d'une autre tournée ;
- [l. 299-309](algorithmes/grasp_tabou_cvrptw.py#L299) : **2-opt** = inverser un morceau de tournée (désactivé par `UTILISER_2OPT`).

**`recherche_tabou`** 📍 [l. 371](algorithmes/grasp_tabou_cvrptw.py#L371)
- [l. 384](algorithmes/grasp_tabou_cvrptw.py#L384) : la **liste tabou** = `deque(maxlen=10)`, les 10 derniers clients déplacés (le plus ancien sort tout seul).
- [l. 393](algorithmes/grasp_tabou_cvrptw.py#L393) : on s'arrête après `iter_max` (30) itérations **sans amélioration** du record…
- [l. 396](algorithmes/grasp_tabou_cvrptw.py#L396) : … ou quand le temps total est écoulé.
- [l. 400-411](algorithmes/grasp_tabou_cvrptw.py#L400) : on cherche le **meilleur mouvement autorisé** :
  - [l. 402](algorithmes/grasp_tabou_cvrptw.py#L402) : le coût est testé en premier (rapide) ;
  - [l. 404-408](algorithmes/grasp_tabou_cvrptw.py#L404) : le **critère d'aspiration** autorise un mouvement tabou s'il bat le record ;
  - [l. 410](algorithmes/grasp_tabou_cvrptw.py#L410) : la validité (capacité, fenêtres) n'est vérifiée qu'en dernier, car c'est le plus cher.
- [l. 417-419](algorithmes/grasp_tabou_cvrptw.py#L417) : on applique le mouvement **même s'il est moins bon**, on rend les clients tabous, et on met le coût à jour par différence.
- [l. 422-429](algorithmes/grasp_tabou_cvrptw.py#L422) : nouveau record → on remet le compteur à 0 ; sinon on l'augmente.

**`grasp_tabou`** 📍 [l. 438](algorithmes/grasp_tabou_cvrptw.py#L438) : la boucle multi-start.
- [l. 445](algorithmes/grasp_tabou_cvrptw.py#L445) : construction ;
- [l. 447](algorithmes/grasp_tabou_cvrptw.py#L447) : recherche tabou ;
- [l. 451-452](algorithmes/grasp_tabou_cvrptw.py#L451) : on garde la meilleure ;
- [l. 455](algorithmes/grasp_tabou_cvrptw.py#L455) : on s'arrête quand le temps est écoulé.

##### 💬 Si on te demande…

**Que fait alpha ?** Il règle la taille de la RCL : 0 = glouton pur (toujours le meilleur
candidat), 1 = hasard pur. Avec 0,1, on tire au hasard parmi les tout meilleurs. L'interface
utilise 0,1 jusqu'à 500 clients et 0 au-delà ([`methodes.py` l. 43](algorithmes/methodes.py#L43)).

**Pourquoi accepter une solution moins bonne ?** Pour sortir des optimums locaux. Sans ça, on
s'arrêterait au premier « creux ».

**À quoi sert la liste tabou ?** À ne pas annuler tout de suite un mouvement (re-déplacer le même
client), ce qui ferait tourner en rond.

**Qu'est-ce que le critère d'aspiration ?** Une exception : un mouvement tabou est autorisé s'il
donne la meilleure solution jamais vue.

**Pourquoi calculer le coût « par différence » (delta) ?** Un mouvement ne change que 3 ou 4 arcs :
on calcule la variation en O(1) au lieu de recalculer toute la solution en O(n). C'est ce qui
permet de tester des milliers de voisins.

**Pourquoi seulement les 30 plus proches voisins ?** Insérer un client loin de tout n'est jamais
intéressant, et sur 1 000 clients tester toutes les positions serait trop lent. On ne l'active
qu'au-delà de 500 clients : sur les petites instances à fenêtres larges, la bonne place d'un client
n'est pas toujours à côté de ses voisins géographiques (RC2 passait de 5,2 % à 8,4 %).

**Pourquoi un échantillon de 25 clients ?** Tester tous les clients à chaque itération serait trop
lent sur les grandes instances, et le hasard de l'échantillon ajoute de la diversité.

**Pourquoi le 2-opt est-il désactivé ?** Sur nos tests, il n'améliorait pas le coût. Il reste
disponible en option (Livrable 2, partie 3 du notebook).

**Pourquoi le swap ne regarde-t-il que d'autres tournées ?** À l'intérieur d'une tournée, le
relocate permet déjà de changer l'ordre.

**Comment le nombre de camions peut-il baisser ?** Quand un relocate déplace le dernier client
d'une tournée, celle-ci devient vide et `appliquer_mouvement` la supprime
([l. 364](algorithmes/grasp_tabou_cvrptw.py#L364)).

**Quelle différence entre `iter_max` et l'heure de fin ?** `iter_max` termine **une** recherche
tabou (on repart d'une nouvelle construction) ; l'heure de fin termine **tout**.

**Pourquoi `1e-9` dans les comparaisons ?** Les nombres à virgule ont des erreurs d'arrondi
(0,1 + 0,2 ne fait pas exactement 0,3). La petite marge évite de compter comme record une
solution égale.

**Pourquoi `tournee_valide` ET `evaluer` ?** `tournee_valide` est interne à l'algorithme : rapide,
elle répond vrai / faux pour décider des mouvements. `evaluer` est le juge indépendant : il donne
les messages d'erreur et les horaires. Les deux appliquent la même règle.

**Comment tester l'algorithme seul ?** `python algorithmes/grasp_tabou_cvrptw.py` résout
l'exemple du livrable 1 et une instance aléatoire de 100 clients. Il affiche 33,8 et non 33,9 pour
l'exemple, car ce test utilise les distances exactes ; l'interface (distances arrondies au
dixième) trouve bien 33,9.

**Quelle complexité ?** Une construction : O(n²) (pour chaque client ajouté, on teste tous les
restants). Une itération tabou : 25 clients × environ 90 mouvements, chacun en O(1), et la
validité seulement pour les meilleurs.

---

#### 📄 ★ `algorithmes/methodes.py` : le lien entre l'interface et les deux méthodes

**À quoi il sert.** L'interface ne parle qu'à ce fichier. Il donne aux deux méthodes la même
forme, `methode(instance, temps_max, graine) → tournées`, et les chronomètre.

| Lignes | Nom | Rôle |
|---|---|---|
| [19-20](algorithmes/methodes.py#L19) | `GRASP_TABOU`, `PLNE` | les noms affichés dans l'interface |
| [23](algorithmes/methodes.py#L23) | `preparer(instance)` | charge l'instance dans le code GRASP + Tabou, avec les réglages de l'interface |
| [38](algorithmes/methodes.py#L38) | `grasp_tabou(instance, temps_max, graine)` | lance GRASP + Tabou avec les réglages du benchmark |
| [49](algorithmes/methodes.py#L49) | `METHODES` | dictionnaire nom → fonction |
| [52](algorithmes/methodes.py#L52) | `lancer(nom, instance, temps_max, graine)` | appelle la méthode choisie, chronomètre, renvoie (tournées, temps) |

##### Les passages importants
- **`preparer`** 📍 [l. 23](algorithmes/methodes.py#L23) :
  - [l. 26-28](algorithmes/methodes.py#L26) : appelle `charger_instance` de l'algorithme ;
  - [l. 29](algorithmes/methodes.py#L29) : **remplace les distances** par celles de l'instance, pour que tout le projet utilise exactement la même matrice ;
  - [l. 30-31](algorithmes/methodes.py#L30) : fixe l'heure de départ et le nombre de camions ;
  - [l. 32-35](algorithmes/methodes.py#L32) : avec le trafic, la fonction `trajet` de l'algorithme est **remplacée** par `temps_trajet` de `contraintes.py`.
- **`grasp_tabou`** 📍 [l. 38](algorithmes/methodes.py#L38) :
  - [l. 41](algorithmes/methodes.py#L41) : `random.seed(graine)`, même graine = même hasard ;
  - [l. 43](algorithmes/methodes.py#L43) : alpha automatique ;
  - [l. 44-45](algorithmes/methodes.py#L44) : les réglages, à savoir par cœur :

  | Réglage | Valeur | Sens |
  |---|---|---|
  | `nb_starts` | `10**9` | un « infini » : c'est le temps qui arrête |
  | `alpha` | 0,1 (0 au-delà de 500 clients) | taille de la RCL |
  | `taille_tabou` | 10 | les 10 derniers clients déplacés sont tabous |
  | `iter_max` | 30 | itérations sans amélioration avant de recommencer |
  | `taille_echantillon` | 25 | clients testés à chaque itération |

- **`lancer`** 📍 [l. 52](algorithmes/methodes.py#L52) :
  - [l. 55](algorithmes/methodes.py#L55) : convertit les tournées en listes d'entiers et retire les tournées vides ;
  - [l. 56-57](algorithmes/methodes.py#L56) : si aucune tournée (PLNE arrêtée sans solution), erreur « essayez avec plus de temps ».

##### 💬 Si on te demande…
**Comment le trafic arrive-t-il dans l'algorithme ?** `preparer` remplace la fonction `trajet`
de l'algorithme par `temps_trajet`. La construction et `tournee_valide` appellent
`trajet(i, j, heure)`, donc elles tiennent compte de l'heure. Le coût minimisé reste la distance.

**Pourquoi ne pas appeler l'algorithme directement depuis l'interface ?** Pour que l'interface
traite les deux méthodes de la même façon, et pour ne toucher au code de l'algorithme que par
quelques lignes marquées « AJOUT interface ».

---

#### 📄 ★ `algorithmes/plne.py` : la méthode exacte

**À quoi il sert.** Il écrit le **programme linéaire en nombres entiers** du livrable 1 et le fait
résoudre par le solveur **CBC** (via la bibliothèque **PuLP**). Il donne la solution **optimale
prouvée**, mais seulement sur de petites instances (le temps explose : problème NP-difficile).
Il sert de **référence** pour vérifier que GRASP + Tabou retrouve l'optimum.

**Une seule fonction :** 📍 [`plne_exacte`, l. 12](algorithmes/plne.py#L12). Le modèle, dans l'ordre du code :

| Lignes | Élément du modèle | Formule |
|---|---|---|
| [19-20](algorithmes/plne.py#L19) | limite | plus de 15 clients → refus |
| [26](algorithmes/plne.py#L26) | variables de trajet | x_ij ∈ {0, 1} : un camion va de i à j |
| [27](algorithmes/plne.py#L27) | variables de charge | q_i ≤ u_i ≤ Q : charge à l'arrivée en i (impose aussi la **capacité**) |
| [29](algorithmes/plne.py#L29) | **objectif** | min Σ c_ij · x_ij |
| [30-32](algorithmes/plne.py#L30) | visite unique | chaque client : une arrivée, un départ |
| [33](algorithmes/plne.py#L33) | dépôt | autant de départs que de retours |
| [34-35](algorithmes/plne.py#L34) | flotte | au plus K départs du dépôt |
| [36-39](algorithmes/plne.py#L36) | **MTZ** (sous-tours) | u_i − u_j + Q·x_ij ≤ Q − q_j |
| [41](algorithmes/plne.py#L41) | variables d'heure | a_i ≤ T_i ≤ b_i : début de livraison dans le créneau |
| [42](algorithmes/plne.py#L42) | big-M | M assez grand pour « désactiver » une contrainte |
| [44](algorithmes/plne.py#L44) | départ du dépôt | T_j ≥ a_0 + c_0j − M(1 − x_0j) |
| [47](algorithmes/plne.py#L47) | enchaînement des heures | T_i + s_i + c_ij − T_j ≤ M(1 − x_ij) |
| [48](algorithmes/plne.py#L48) | retour avant fermeture | T_j + s_j + c_j0 ≤ b_0 + M(1 − x_j0) |
| [50](algorithmes/plne.py#L50) | résolution | CBC, avec une limite de temps |
| [51-52](algorithmes/plne.py#L51) | statut | on accepte « Optimal » et « Not Solved » (arrêté au temps, avec une solution) |
| [54-64](algorithmes/plne.py#L54) | reconstruction | on suit les arcs x_ij = 1 depuis le dépôt |

##### 💬 Si on te demande…
**Comment la PLNE évite-t-elle les sous-tours ?** Avec **MTZ** : quand on va de i à j, la charge
augmente (u_j ≥ u_i + q_j). Un cycle qui ne passe pas par le dépôt ferait augmenter la charge
sans fin : impossible. Quand x_ij = 0, la contrainte devient u_i − u_j ≤ Q − q_j, toujours vraie.

**À quoi sert le big-M ?** À activer une contrainte de temps seulement si l'arc est utilisé :
x_ij = 1 donne T_j ≥ T_i + s_i + c_ij ; x_ij = 0 retire M, et la contrainte ne gêne plus.

**Comment l'attente est-elle autorisée ?** Par l'inégalité (≥) : le camion peut commencer plus
tard que son arrivée, tant qu'il reste dans [a_i, b_i].

**Pourquoi 2 indices (x_ij) et pas 3 (x_ijk) comme au livrable 1 ?** Les camions sont identiques :
savoir *quel* camion fait une tournée n'apporte rien, et l'indice k multiplie les solutions
symétriques, ce qui ralentit le solveur. La flotte est limitée par la contrainte des départs.

**Qu'est-ce qui a changé depuis le livrable 1 ?** 2 indices, le départ du dépôt ([l. 44](algorithmes/plne.py#L44))
et le retour avant la fermeture ([l. 48](algorithmes/plne.py#L48)), qui manquait (notebook,
Livrable 2, partie 9).

**Que se passe-t-il si CBC n'a pas fini ?** PuLP rend la meilleure solution trouvée, pas
forcément optimale (statut « Not Solved »). Elle est quand même revérifiée par `evaluer`.
⚠️ Comme pour GRASP + Tabou, ce résultat dépend de la vitesse du PC : sur LOR-Moselle-Est
(15 clients), la PLNE arrêtée à 60 s donne 489,0 dans le notebook mais 525,2 sur un PC plus lent.

**Pourquoi le trafic n'est-il pas dans la PLNE ?** La durée dépendrait de l'heure, donc d'une
variable : le modèle ne serait plus linéaire. ⚠️ Ne pas lancer la PLNE avec le trafic dans
l'interface ([l. 16](algorithmes/plne.py#L16)).

---

### 📁 `bonus_3d/` : l'onglet « Suivi 3D » (bonus, hors programme)

**À quoi il sert.** Une **option d'affichage** : il met en scène en 3D, dans une ville générée,
les tournées **déjà calculées et vérifiées** par `evaluer()` (mêmes heures que le suivi 2D). Il
ne calcule rien, et il n'est pas compté dans les 887 lignes. Il n'y a rien à en connaître pour
expliquer la méthode.

| Fichier | Rôle |
|---|---|
| `suivi_3d.py` | prépare les données de la scène (📍 [`donnees_scene`, l. 22](bonus_3d/suivi_3d.py#L22)) et affiche la page (📍 [`afficher_suivi_3d`, l. 60](bonus_3d/suivi_3d.py#L60)) |
| `scene.html` | la scène 3D (moteur three.js) |
| `lib/` | le moteur three.js, embarqué pour marcher sans internet |
| `LISEZMOI.md` | description du bonus |

💬 **« C'est vous qui l'avez fait ? À quoi ça sert ? »** C'est un bonus voté par le groupe pour
rendre le suivi plus parlant. Il est volontairement séparé du reste : `app.py` ne fait que
l'appeler ([l. 110-112](app.py#L110)).

---

### 📁 `images/`
`interface.png` : la capture de l'interface affichée dans le README.

---

### 📁 `instances/` : les données

Chaque instance a **deux fichiers** au format VRPLIB (texte, s'ouvre dans VS Code) :
- **`.vrp`** : l'instance. Un en-tête (`NAME`, `TYPE`, `DIMENSION` = nombre de sommets, dépôt
  compris, `CAPACITY`…), puis des sections : `NODE_COORD_SECTION` (coordonnées),
  `DEMAND_SECTION` (demandes), et pour le CVRPTW `TIME_WINDOW_SECTION` (fenêtres) et
  `SERVICE_TIME_SECTION` (temps de livraison).
- **`.sol`** : la **meilleure solution connue** (BKS). On ne lit que sa ligne `Cost`, qui sert au gap.

| Famille | Fichiers | Ce qu'elle représente |
|---|---|---|
| Solomon C1 / C2 | C101, C102, C105 / C201, C202, C205 | clients **regroupés**, fenêtres serrées (1) / larges (2) |
| Solomon R1 / R2 | R101, R102, R105 / R201, R202, R205 | clients **aléatoires** |
| Solomon RC1 / RC2 | RC101, RC102, RC105 / RC201, RC202, RC205 | **mélange** des deux |
| X (Uchoa) | X-n101-k25, X-n110-k13, X-n200-k36, X-n502-k39, X-n1001-k43 | CVRP sans fenêtres, 100 à 1 000 clients (`k` = nombre de camions) |
| XXL | Leuven1 | CVRP, 3 000 clients |
| Générée | GEN-uniforme-centre-serrees-n8-g1 | 8 clients, générée par nous, optimum calculé par la PLNE |

Les instances VRPLIB viennent du dépôt public PyVRP/Instances (CVRPLIB). Le sous-dossier
`instances/CVRP`, s'il apparaît, est vide : il n'est pas utilisé.

💬 **Pourquoi l'arrondi des distances compte-t-il ?** Les coûts de référence sont calculés avec un
arrondi précis (entier pour X, troncature au dixième pour Solomon). Avec le même arrondi, notre
code retrouve exactement les coûts publiés (C101 : 827,3 ; X-n101-k25 : 27 591). Sans lui, le gap
serait faux de plusieurs pour cent.

---

### 📁 `probleme/` : les données et les règles du problème

---

#### 📄 ★ `probleme/contraintes.py` : vérifier une solution, le trafic, le gap

**À quoi il sert.** C'est le **juge** : il recalcule chaque tournée et liste toutes les contraintes
non respectées. Il contient aussi le trafic et le calcul du gap.

| Lignes | Nom | Rôle |
|---|---|---|
| [15-23](probleme/contraintes.py#L15) | `PROFIL_TRAFIC_DEFAUT` | la journée type découpée en tranches, avec un coefficient chacune |
| [30](probleme/contraintes.py#L30) | `coefficient_trafic(inst, heure)` | le coefficient de la tranche qui contient l'heure |
| [39](probleme/contraintes.py#L39) | `temps_trajet(inst, i, j, depart)` | durée du trajet = distance × coefficient |
| [56](probleme/contraintes.py#L56) | `evaluer(inst, routes)` | vérifie **toutes** les contraintes et calcule les horaires |
| [126](probleme/contraintes.py#L126) | `gap(cout, reference)` | 100 × (coût − référence) / référence |

##### Les passages importants
**Le trafic.** Une journée est découpée en tranches exprimées en **% de la journée**
([l. 15-23](probleme/contraintes.py#L15)), car les instances n'ont pas la même échelle de temps.
Exemple : coefficient 1,6 à l'heure de pointe = le trajet dure 60 % plus longtemps.
`coefficient_trafic` ([l. 32](probleme/contraintes.py#L32)) calcule 100 × heure / horizon et
cherche la tranche. Le coefficient est celui de **l'heure de départ** du trajet.

**`evaluer`** 📍 [l. 56](probleme/contraintes.py#L56), dans l'ordre :
1. [l. 69-78](probleme/contraintes.py#L69) : chaque client est livré **exactement une fois** (ni oublié, ni en double, ni inconnu) ;
2. [l. 80-84](probleme/contraintes.py#L80) : pas plus de camions que disponibles ;
3. [l. 88-111](probleme/contraintes.py#L88) : pour chaque camion, on simule la journée :
   - [l. 91](probleme/contraintes.py#L91) : heure d'arrivée (avec le trafic) ;
   - [l. 94](probleme/contraintes.py#L94) : **début = max(arrivée, ouverture)**, l'attente est autorisée ;
   - [l. 95-97](probleme/contraintes.py#L95) : livrer après la fermeture = violation ;
   - [l. 98-100](probleme/contraintes.py#L98) : fin de la livraison, et on garde les horaires de chaque arrêt (pour le suivi) ;
   - [l. 104-106](probleme/contraintes.py#L104) : **capacité** ;
   - [l. 107-108](probleme/contraintes.py#L107) : **retour au dépôt avant sa fermeture**.
4. [l. 113-119](probleme/contraintes.py#L113) : renvoie la distance totale, le nombre de camions, `realisable` (vrai si aucune violation), la liste des violations et le détail des tournées.

##### 💬 Si on te demande…
**Comment savez-vous que vos solutions sont valides ?** `evaluer` les revérifie toutes,
indépendamment de l'algorithme. Dans l'interface, c'est le message « ✅ Toutes les contraintes
sont respectées ».

**Pourquoi `1e-6` dans `evaluer` ?** Pour ne pas déclarer en retard, à cause d'une erreur
d'arrondi, un camion qui arrive pile à l'heure.

**Pourquoi le gap n'est-il pas affiché avec le trafic ?** Les meilleures solutions connues sont
calculées **sans trafic** : comparer ne serait pas juste. Le trafic rend même parfois un client
impossible à livrer : sur R101, le client 25 ne peut être servi qu'entre 172 et 182 ; son retour
part en heure de pointe (× 1,6) et arrive à 235,6, après la fermeture du dépôt (230).
L'interface l'explique au lieu de planter ([`app.py` l. 35-38](app.py#L35)).

---

#### 📄 ★ `probleme/instances.py` : lire, créer et lister les instances

**À quoi il sert.** Il transforme un fichier de `instances/` en **dictionnaire instance**
(voir l'[idée 2](#idée-2--une-instance--un-dictionnaire)), et donne la liste des instances de l'interface.

| Lignes | Nom | Rôle |
|---|---|---|
| [17](probleme/instances.py#L17) | `DOSSIER_INSTANCES` | le chemin du dossier `instances/` |
| [25](probleme/instances.py#L25) | `matrice_distances(coords, arrondi)` | distances euclidiennes + l'arrondi des références |
| [48](probleme/instances.py#L48) | `construire_instance(...)` | range toutes les données dans le dictionnaire |
| [84](probleme/instances.py#L84) | `famille_instance(nom)` | déduit la famille du nom (C, R, RC, X…) |
| [113](probleme/instances.py#L113) | `charger_instance(chemin)` | lit un `.vrp` (et son `.sol` pour la BKS) |
| [146](probleme/instances.py#L146) | `INSTANCES_INTERFACE` | les 18 fichiers proposés dans l'interface |
| [156](probleme/instances.py#L156) | `lister_instances()` | la liste de l'interface (18 fichiers + 2 de Lorraine) |
| [179](probleme/instances.py#L179) | `exemple_livrable1()` | l'exemple à 6 clients du livrable 1 (optimum 33,9) |

##### Les passages importants
- **`matrice_distances`** [l. 33-41](probleme/instances.py#L33) : `np.hypot` calcule toutes les distances d'un coup ; puis « entier » (X), « troncature » au dixième (Solomon) ou « 0.1 » (exemple du livrable 1).
- **`construire_instance`** [l. 63-65](probleme/instances.py#L63) : un CVRP n'a pas d'horaires, donc on suppose une journée de 4 × la distance du client le plus lointain (utile seulement pour le trafic).
- **`charger_instance`** :
  - [l. 115-117](probleme/instances.py#L115) : un chemin `lorraine:NOM` mène à `lorraine.py` ;
  - [l. 120](probleme/instances.py#L120) : lecture avec la bibliothèque `vrplib` ;
  - [l. 127-128](probleme/instances.py#L127) : le coût de référence vient du `.sol` ;
  - [l. 138](probleme/instances.py#L138) : arrondi « troncature » s'il y a des fenêtres, sinon « entier ».
- **`lister_instances`** [l. 162-169](probleme/instances.py#L162) : on ne lit que l'**en-tête** des fichiers (rapide, même pour 3 000 clients) ; [l. 172](probleme/instances.py#L172) : tri par type, puis par taille.

##### 💬 Si on te demande…
**Pourquoi ces 20 instances dans l'interface ?** Elles couvrent ce que le sujet demande
d'analyser : la **taille** (8 à 3 000 clients), la **répartition** des clients (regroupés,
aléatoires, mixtes) et les **contraintes** (sans fenêtres, serrées, larges). Les autres fichiers
(C102, R102, X-n110-k13…) complètent le benchmark du notebook.

**Pourquoi deux façons de charger une instance ?** Le benchmark (`benchmark_vrplib.py`) appelle
directement l'algorithme, pour pouvoir tourner seul (Colab). L'interface passe par ce fichier
(un dictionnaire, utile pour l'affichage et `evaluer`). Les arrondis sont les mêmes, donc les
distances sont identiques.

---

#### 📄 ○ `probleme/lorraine.py` : 2 instances sur de vraies communes de Moselle

**À quoi il sert.** Montrer le problème sur un cas concret, avec de **vrais horaires** et le
**trafic**, et comparer la PLNE et GRASP + Tabou sur de petites instances (notebook, partie 9).

| Lignes | Nom | Rôle |
|---|---|---|
| [23](probleme/lorraine.py#L23) | `COMMUNES` | 25 communes avec leur latitude et longitude réelles |
| [42](probleme/lorraine.py#L42) | `SCENARIOS` | LOR-Metz-agglo (10 clients, créneaux) et LOR-Moselle-Est (15 clients, sans créneaux) |
| [61](probleme/lorraine.py#L61) | `OPTIMUM_CONNU` | 113,2 min pour Metz-agglo (prouvé par la PLNE) |
| [64](probleme/lorraine.py#L64) | `TRAFIC_LORRAINE` | bouchons 7h-9h et 16h30-19h (× 1,5), midi (× 1,2) |
| [70](probleme/lorraine.py#L70) | `CRENEAUX` | matin 8h-12h, après-midi 14h-18h, journée 8h-18h |
| [73](probleme/lorraine.py#L73) | `creer_instance_lorraine(nom)` | construit l'instance |
| [107](probleme/lorraine.py#L107) | `lister_instances_lorraine()` | les 2 instances, au format de `lister_instances` |

**Les hypothèses** (en-tête, [l. 4-13](probleme/lorraine.py#L4)) :
- les heures sont en **minutes depuis minuit** (480 = 8h00) ;
- durée d'un trajet = distance à vol d'oiseau × 1,3 ([l. 98](probleme/lorraine.py#L98)) : 30 % de détours, à 60 km/h (1 km = 1 min) ;
- entrepôt ouvert de 6h à 20h, 15 min par livraison ;
- demandes et créneaux tirés au hasard avec une **graine fixe** ([l. 84](probleme/lorraine.py#L84)), donc toujours la même instance.

---

### 📁 `resultats/` : ce que produisent les expériences

| Fichier | Produit par | Contenu |
|---|---|---|
| `resultats_20s.csv` / `gap_par_instance_20s.png` | `benchmark_vrplib.py` | **le benchmark final** : 20 instances, 20 s, graine 0 |
| `resultats_20s_alpha02.csv`, `_alpha01.csv` (+ `.png`) | `benchmark_vrplib.py` | les versions précédentes (avant les améliorations), gardées pour le test de Wilcoxon |
| `1_robustesse.csv` / `.png` | `etude_statistique.py` | 6 instances × 5 graines, 10 s |
| `2_convergence.csv` / `.png` | `etude_statistique.py` | gap à 2, 5, 10 et 30 s |
| `3_taille.csv` / `.png` | `etude_statistique.py` | de 100 à 3 000 clients, 60 s |
| `4_sensibilite.csv` / `.png` | `etude_statistique.py` | effet de alpha et de la taille de la liste tabou |

Colonnes des CSV : `instance`, `graine`, `n` (clients), `camions`, `cout`, `bks`, `gap_%`,
`temps_s`, `valide` (toutes les contraintes respectées), plus les paramètres testés.

⚠️ Relancer un script **écrase** son CSV avec des chiffres un peu différents (voir la
[partie 5](#5-les-chiffres-à-connaître)). Les chiffres du notebook sont ceux de la version
enregistrée sur GitHub.

---

### 📄 Les fichiers à la racine

---

#### 📄 ✗ `.gitignore`
La liste des fichiers que git ne doit pas enregistrer (fichiers temporaires de Python, etc.).
Une exception, `!bonus_3d/lib/`, garde le moteur 3D dans le dépôt.

---

#### 📄 ★ `app.py` : l'interface

**À quoi il sert.** Une page web (bibliothèque **Streamlit**) pour **démontrer** la méthode :
choisir une instance et une méthode, lancer, voir le résultat et suivre les camions. Il ne
contient **aucun calcul de tournée** : il appelle les fonctions des autres fichiers.

⚠️ **Comment marche Streamlit :** à chaque clic, **tout le fichier est relu de haut en bas**.
C'est pour ça que le code se lit comme une suite d'étapes, sans boucle d'événements.

| Lignes | Partie | Ce qui se passe |
|---|---|---|
| [6-13](app.py#L6) | imports | les bibliothèques, et nos fonctions (`lancer`, `evaluer`, `gap`, `charger_instance`…) |
| [15-16](app.py#L15) | page | titre et mise en page |
| [18-30](app.py#L18) | **1. Les choix, à gauche** | instance, trafic, méthode, temps, bouton ▶ Lancer |
| [32-39](app.py#L32) | **2. La résolution** | `lancer(...)` puis `evaluer(...)` |
| [41-51](app.py#L41) | **3. Le résultat** | les 4 indicateurs et le message sur les contraintes |
| [53-109](app.py#L53) | **4. Le suivi 2D** | la carte animée des camions |
| [110-112](app.py#L110) | onglet 3D | appel du bonus (3 lignes) |
| [114-121](app.py#L114) | **5. Le détail** | le tableau des tournées |

Le détail de chaque ligne est dans la [partie 4](#4-le-parcours-dans-linterface-étape-par-étape),
qui suit l'interface clic par clic.

##### 💬 Si on te demande…
**Comment marche le suivi 2D ?** Pour chaque camion, on connaît ses points de passage : départ
du dépôt, puis pour chaque client l'arrivée et la fin de la livraison (deux fois le même lieu :
le camion reste sur place pendant l'attente et la livraison), puis le retour.
`np.interp(h, heures, x)` donne la position à l'heure h, en ligne droite entre deux passages
([l. 83](app.py#L83)). On le fait à 100 moments, et plotly en fait une animation.

**Pourquoi l'heure est-elle en % hors Lorraine ?** Dans les instances de référence, le temps
n'est pas une heure : c'est une unité égale à la distance. On l'affiche donc en % de la journée
(0 % = ouverture du dépôt, 100 % = fermeture). Pour la Lorraine, ce sont de vraies minutes
([`moment`, l. 62](app.py#L62)).

---

#### 📄 ★ `benchmark_vrplib.py` : le gap sur 20 instances de référence

**À quoi il sert.** Mesurer la qualité de GRASP + Tabou : on le lance sur 20 instances dont on
connaît la meilleure solution, et on calcule le **gap**. Il est recopié dans le notebook
(Livrable 2, partie 4). Lancement : `python benchmark_vrplib.py 20` (20 = secondes par instance).

| Lignes | Nom | Rôle |
|---|---|---|
| [29](benchmark_vrplib.py#L29) | `telecharger(nom)` | télécharge l'instance si elle manque (utile sur Colab) |
| [48](benchmark_vrplib.py#L48) | `charger_vrplib(nom)` | lit le `.vrp` et le `.sol`, prépare l'algorithme, renvoie la BKS |
| [80](benchmark_vrplib.py#L80) | `tester(nom, graine, temps_max, …)` | lance GRASP + Tabou, renvoie une ligne de résultats |
| [107](benchmark_vrplib.py#L107) | programme principal | les 20 instances, le CSV, le gap moyen par famille, le graphique |

- [l. 71](benchmark_vrplib.py#L71) : le même arrondi que les références.
- [l. 88-89](benchmark_vrplib.py#L88) : alpha automatique, comme dans l'interface.
- [l. 92-94](benchmark_vrplib.py#L92) : les mêmes réglages que l'interface.
- [l. 97](benchmark_vrplib.py#L97) : le gap.
- [l. 101](benchmark_vrplib.py#L101) : `valide` = `verifier_solution`.
- [l. 115-123](benchmark_vrplib.py#L115) : les 20 instances : 18 Solomon (3 par famille) + 2 X.

---

#### 📄 ○ `etude_statistique.py` : les 4 expériences de l'étude

**À quoi il sert.** Les expériences de la partie 5 du notebook. Chacune enregistre un CSV et un
graphique dans `resultats/`. Lancement : `python etude_statistique.py` (les 4, environ 25 min),
ou `python etude_statistique.py 1 3` (seulement la 1 et la 3).

| Lignes | Expérience | Question posée |
|---|---|---|
| [33](etude_statistique.py#L33) | `INSTANCES` | une instance par famille : C101, C201, R101, R201, RC101, RC201 |
| [36](etude_statistique.py#L36) | `lancer(...)` | lance une liste d'essais et enregistre le CSV |
| [52](etude_statistique.py#L52) | 1. **Robustesse** | le hasard change-t-il beaucoup le résultat ? (5 graines, 10 s) |
| [76](etude_statistique.py#L76) | 2. **Convergence** | plus de temps donne-t-il un meilleur gap ? (2, 5, 10, 30 s) |
| [99](etude_statistique.py#L99) | 3. **Taille** | que se passe-t-il de 100 à 3 000 clients ? (60 s) |
| [135](etude_statistique.py#L135) | 4. **Sensibilité** | quel alpha, quelle taille de liste tabou ? (un paramètre à la fois) |

⚠️ La robustesse, la convergence et la sensibilité ont été mesurées **avant** le réglage final
(alpha = 0,2, 10 s). C'est justement la sensibilité qui a mené à alpha = 0,1 (notebook, parties 5.4 et 6).

---

#### 📄 `GUIDE_DU_CODE.md`
Ce guide.

---

#### 📄 ○ `lancer_interface.bat`
Un double-clic ouvre l'interface : il se place dans le dossier du projet
([l. 3](lancer_interface.bat#L3)) et lance `python -m streamlit run app.py` ([l. 4](lancer_interface.bat#L4)).

---

#### 📄 ★ `Projet_Smart.ipynb` : le livrable

Le notebook rendu. Son **sommaire** (2e cellule) indique où se trouve chaque attendu du sujet.

| Partie | Contenu |
|---|---|
| **Livrable 1** | 1. le problème · 2. la complexité (NP-difficile) · 3. la PLNE · 4. la méthode · 5. l'exemple · 6. la PLNE en PuLP |
| **Livrable 2, 0-3** | la méthode GRASP + Tabou formalisée, le code, le coût par différence, le 2-opt |
| **Livrable 2, 4-5** | le benchmark VRPLIB, puis l'étude statistique (robustesse, convergence, taille, sensibilité) |
| **Livrable 2, 6-8** | les deux améliorations (alpha, passage à l'échelle) et le test de Wilcoxon |
| **Livrable 2, 9-11** | PLNE contre GRASP + Tabou, l'interface, les limites et la conclusion |

⚠️ Trois cellules `%%writefile` recopient `grasp_tabou_cvrptw.py`, `benchmark_vrplib.py` et
`etude_statistique.py` : si on modifie un de ces fichiers, il faut modifier la cellule aussi.

---

#### 📄 ○ `README.md`
La présentation du projet : installation, lancement, résultats principaux.

#### 📄 ○ `requirements.txt`
Les bibliothèques : numpy, pandas, scipy (Wilcoxon), matplotlib, plotly (suivi 2D), streamlit
(interface), vrplib (lecture des instances), pulp **2.9.0** (PLNE). Installation :
`pip install -r requirements.txt`.

💬 **Pourquoi PuLP 2.9.0 exactement ?** La version 4 a changé la façon de déclarer les variables
(`LpVariable(cat=...)`) et cassait notre code : on a fixé la version.

---

## 4. Le parcours dans l'interface, étape par étape

Ce qui se passe à l'écran, et le code qui s'exécute derrière, dans l'ordre.

```
 Lancement ─► choix de l'instance ─► trafic ─► méthode ─► temps ─► ▶ Lancer
                                                                     │
          ┌──────────────────────────────────────────────────────────┘
          ▼
   lancer() ─► preparer() ─► grasp_tabou() ─► [ construction ─► recherche tabou ] × N ─► meilleure solution
          │                       (ou plne_exacte())
          ▼
   evaluer() ─► gap() ─► indicateurs ─► suivi 2D ─► (suivi 3D) ─► tableau des tournées
```

### Étape 1 : lancer l'interface
**À l'écran :** double-clic sur `lancer_interface.bat` (ou `streamlit run app.py` dans un
terminal). Le navigateur s'ouvre sur la page « 🚚 Tournées de livraison ».

**Dans le code :**
- 📍 [`app.py` l. 15-16](app.py#L15) : titre et mise en page.
- 📍 [`app.py` l. 19](app.py#L19) : `lister_instances()` ([`instances.py` l. 156](probleme/instances.py#L156)) lit l'en-tête des 18 fichiers ; [`lorraine.py` l. 107](probleme/lorraine.py#L107) ajoute les 2 de Lorraine.

### Étape 2 : choisir l'instance
**À l'écran :** menu « Instance », à gauche. En premier, « Exemple du livrable 1 », puis les
instances triées par type (CVRP, puis CVRPTW) et par taille. Sous le titre s'affichent le type,
le nombre de clients, la capacité et la meilleure solution connue.

**Dans le code :**
- 📍 [`app.py` l. 20-21](app.py#L20) : `charger_instance(chemin)` ([`instances.py` l. 113](probleme/instances.py#L113)) ou `exemple_livrable1()` ([l. 179](probleme/instances.py#L179)).
- Les deux passent par `construire_instance` ([l. 48](probleme/instances.py#L48)) et `matrice_distances` ([l. 25](probleme/instances.py#L25)). Pour la Lorraine : `creer_instance_lorraine` ([`lorraine.py` l. 73](probleme/lorraine.py#L73)).
- 📍 [`app.py` l. 26-27](app.py#L26) : la ligne d'information sous le titre.

### Étape 3 : activer ou non le trafic
**À l'écran :** interrupteur « Trafic selon l'heure ».

**Dans le code :** 📍 [`app.py` l. 22-23](app.py#L22) : `inst["trafic"]` reçoit le profil de la
Lorraine ([`TRAFIC_LORRAINE`](probleme/lorraine.py#L64)) ou le profil par défaut
([`PROFIL_TRAFIC_DEFAUT`](probleme/contraintes.py#L15)).

⚠️ Avec le trafic : pas de gap affiché, et ne pas choisir la PLNE.

### Étape 4 : choisir la méthode
**À l'écran :** « GRASP + Tabou », et « PLNE exacte (≤ 15 clients) » seulement pour les petites instances.

**Dans le code :** 📍 [`app.py` l. 24](app.py#L24) : la PLNE n'est proposée que si `n ≤ 15`.

### Étape 5 : choisir le temps de calcul
**À l'écran :** curseur de 1 à 120 s, **20 s par défaut** (comme le benchmark).

**Dans le code :** 📍 [`app.py` l. 25](app.py#L25).

### Étape 6 : cliquer sur ▶ Lancer
**Avant le clic :** 📍 [`app.py` l. 28-30](app.py#L28) : tant que le bouton n'est pas cliqué,
la page affiche un message et `st.stop()` arrête le script.

**Après le clic :** 📍 [`app.py` l. 34](app.py#L34) : `lancer(methode, inst, temps_max)`.
Pendant le calcul, Streamlit affiche « Running… ». Voici ce qui s'exécute :

1. [`methodes.py` l. 52](algorithmes/methodes.py#L52) `lancer` démarre le chronomètre et appelle la méthode choisie.
2. **Si GRASP + Tabou :** [`methodes.py` l. 38](algorithmes/methodes.py#L38) `grasp_tabou` :
   1. `random.seed(0)` ([l. 41](algorithmes/methodes.py#L41)) ;
   2. `preparer(instance)` ([l. 23](algorithmes/methodes.py#L23)) charge l'instance dans l'algorithme ([`charger_instance` l. 57](algorithmes/grasp_tabou_cvrptw.py#L57)), avec les distances, le départ, le nombre de camions et le trafic ;
   3. `equipe.grasp_tabou(...)` ([l. 438](algorithmes/grasp_tabou_cvrptw.py#L438)) répète, jusqu'à la fin du temps :
      - `grasp_construction` ([l. 150](algorithmes/grasp_tabou_cvrptw.py#L150)) : une solution de départ ;
      - `recherche_tabou` ([l. 371](algorithmes/grasp_tabou_cvrptw.py#L371)) : à chaque itération, `voisinage` ([l. 238](algorithmes/grasp_tabou_cvrptw.py#L238)) propose des mouvements, `mouvement_valide` ([l. 354](algorithmes/grasp_tabou_cvrptw.py#L354)) vérifie les meilleurs avec `tournee_valide` ([l. 120](algorithmes/grasp_tabou_cvrptw.py#L120)), et `appliquer_mouvement` ([l. 359](algorithmes/grasp_tabou_cvrptw.py#L359)) passe au voisin choisi ;
      - on garde la meilleure solution.
3. **Si PLNE :** [`plne.py` l. 12](algorithmes/plne.py#L12) `plne_exacte` écrit le modèle, CBC le résout, et on reconstruit les tournées.
4. `lancer` renvoie les tournées et le temps de calcul.

**Si c'est impossible :** 📍 [`app.py` l. 35-38](app.py#L35) : message « ❌ Aucune solution
possible » (par exemple avec le trafic, quand un client ne peut plus être livré à temps).

### Étape 7 : la vérification
**Dans le code :** 📍 [`app.py` l. 39](app.py#L39) : `evaluer(inst, routes)`
([`contraintes.py` l. 56](probleme/contraintes.py#L56)) revérifie toutes les contraintes et
calcule les horaires de chaque arrêt.

### Étape 8 : lire le résultat
**À l'écran :** 4 indicateurs, puis un message vert ou rouge.

| Indicateur | Ce que c'est | Code |
|---|---|---|
| Distance totale | la somme des tournées (le coût minimisé) | `ev["distance"]`, [l. 44](app.py#L44) |
| Gap | écart à la meilleure solution connue, « — » avec le trafic ou sans référence | `gap(...)`, [l. 42](app.py#L42) et [l. 45](app.py#L45) |
| Camions | nombre de tournées | [l. 46](app.py#L46) |
| Temps de calcul | mesuré par `lancer` | [l. 47](app.py#L47) |

📍 [`app.py` l. 48-51](app.py#L48) : « ✅ Toutes les contraintes sont respectées », ou la liste
des violations trouvées par `evaluer`.

### Étape 9 : suivre les camions (onglet « Suivi 2D »)
**À l'écran :** la carte : le dépôt (carré noir), les tournées (un trait par camion) et les
camions (gros points). Le bouton ▶ sous la carte fait avancer la journée.

**Dans le code :** 📍 [`app.py` l. 53-109](app.py#L53) :
- [l. 59](app.py#L59) : ouverture et fermeture du dépôt ;
- [l. 62-65](app.py#L62) : `moment(h)` écrit l'heure (« 7h29 » en Lorraine, « 42,0 % » ailleurs) ;
- [l. 71-72](app.py#L71) : 100 moments entre le premier départ et le dernier retour ;
- [l. 74-83](app.py#L74) : pour chaque camion, ses points de passage, puis sa position à chaque moment avec `np.interp` ;
- [l. 87-100](app.py#L87) : la figure plotly (positions animées, tournées, dépôt) ;
- [l. 103-104](app.py#L103) : 0,1 s par image, sans glissement (sinon les points laissent une traînée).

### Étape 10 : l'onglet « Suivi 3D (bonus) »
📍 [`app.py` l. 110-112](app.py#L110) : appelle `afficher_suivi_3d` ([`bonus_3d/suivi_3d.py` l. 60](bonus_3d/suivi_3d.py#L60)) avec
les mêmes tournées et les mêmes horaires. Affichage seulement.

### Étape 11 : le détail des tournées
**À l'écran :** un tableau, une ligne par camion : charge / capacité, distance, parcours
(« Dépôt → Client 5 → … → Dépôt », ou les noms des communes en Lorraine).

**Dans le code :** 📍 [`app.py` l. 115-121](app.py#L115).

**Pour relancer :** changer un réglage puis cliquer à nouveau sur ▶ Lancer. Tout le fichier est
relu depuis le début (étape 1).

---

## 5. Les chiffres à connaître

| Mesure | Résultat | Où le montrer |
|---|---|---|
| Benchmark (20 instances, 20 s, graine 0) | gap moyen **3,50 %**, **19 / 20 sous 7 %**, toutes valides | `resultats/resultats_20s.csv` · notebook 4.1 et 7.2 |
| Clients regroupés (C1, C2) | gap ≈ 0 % (C101, C105, C205 : meilleure solution retrouvée) | idem |
| Plus difficile | fenêtres larges (R2, RC2) | idem |
| Réglage alpha 0,2 → 0,1 | 4,98 % → 3,34 %, **significatif** (Wilcoxon, p = 0,022) | notebook 6 et 8 |
| Accélérations (100 clients) | 3,34 % → 3,50 %, non significatif (p = 0,50) | notebook 8 |
| Passage à l'échelle (60 s) | X-n1001 : 37 % → **7,8 %** ; Leuven1 (3 000 clients) : **6,8 %** | `resultats/3_taille.csv` · notebook 5.3 et 7.1 |
| Construction sur 1 000 clients | 4,14 s → 0,22 s | notebook 7 |
| PLNE | optimum prouvé jusqu'à 10 clients, **retrouvé par GRASP + Tabou** ; à 15 clients, pas de preuve en 60 s | notebook 9 |

⚠️ **Pourquoi un chiffre peut changer d'un PC à l'autre.** GRASP + Tabou s'arrête au bout d'un
**temps**, pas d'un nombre d'essais. Un PC plus lent ou occupé fait moins d'essais dans le même
temps, et trouve parfois une solution un peu moins bonne. Sur le PC de démonstration, à 20 s,
l'interface redonne **exactement** les chiffres du benchmark sur C101, C105, C201, C205, R105,
R205 et RC101 : ce sont celles à montrer en direct. Les petites instances donnent toujours le
même résultat (exemple du livrable 1 : 33,9 ; LOR-Metz-agglo : 113,2).

💬 **« Je ne retrouve pas votre chiffre. »** L'arrêt se fait au temps, donc le résultat dépend de
la machine. Sur la même machine, on retrouve les mêmes chiffres, par exemple C101 ou RC101. Un
arrêt sur un nombre d'itérations rendrait les résultats identiques partout : c'est une piste
d'amélioration.

---

## 6. Questions générales

**Pourquoi ne pas tout résoudre avec la PLNE ?** Le problème est NP-difficile : le temps de
résolution exacte explose. Mesuré : optimum en quelques secondes à 10 clients, pas de preuve en
60 s à 15 clients. Les vraies instances ont des centaines ou des milliers de clients.

**Qu'est-ce qu'une métaheuristique ?** Une méthode générale qui cherche une **très bonne**
solution en temps limité, **sans garantie** d'optimalité. On mesure sa qualité par le gap.

**Pourquoi GRASP + Tabou ?** Le GRASP donne des départs variés (diversification), la tabou les
améliore sans rester bloquée dans un optimum local (intensification). Les deux sont simples à
expliquer et à régler, et la méthode gère les fenêtres de temps.

**Pourquoi seulement des solutions réalisables ?** Un mouvement qui viole une contrainte est
refusé ; on n'utilise pas de pénalité dans le coût. Toute solution gardée est donc utilisable.

**Pourquoi utilisez-vous parfois plus de camions que la meilleure solution connue ?** Nous
minimisons la distance seulement ; les références Solomon minimisent d'abord le nombre de
camions, puis la distance.

**Pourquoi l'algorithme est-il moins bon sur les fenêtres larges ?** Les tournées sont longues
et les combinaisons très nombreuses ; nos mouvements simples (déplacer ou échanger un client)
explorent moins bien cet espace. Piste : des mouvements plus forts (Or-opt, 2-opt\*,
destruction / reconstruction).

**Comment avez-vous montré que les améliorations sont réelles ?** Avec un **test de Wilcoxon
apparié** sur les 20 instances : il compare les deux versions instance par instance, sans
supposer une loi normale. p < 0,05 = différence significative.

**À quoi sert `random.seed(graine)` ?** Avec la même graine, le hasard tire les mêmes nombres.
Sur la même machine, le même lancement donne le même résultat.

**Que se passe-t-il au-delà de 3 000 clients ?** La construction en O(n²) et la matrice des
distances (n² cases) deviennent limitantes. Il faudrait ne garder que les plus proches voisins
au lieu de toute la matrice.

---

## 7. Index de toutes les fonctions

Par ordre alphabétique. Un clic ouvre la fonction.

| Fonction | Fichier | Ce qu'elle fait |
|---|---|---|
| [`afficher_suivi_3d`](bonus_3d/suivi_3d.py#L60) | `bonus_3d/suivi_3d.py` | affiche l'onglet 3D (bonus) |
| [`appliquer_mouvement`](algorithmes/grasp_tabou_cvrptw.py#L359) | `algorithmes/grasp_tabou_cvrptw.py` | renvoie la solution après un mouvement |
| [`autour`](algorithmes/grasp_tabou_cvrptw.py#L231) | `algorithmes/grasp_tabou_cvrptw.py` | le client d'avant et celui d'après |
| [`charger_instance`](algorithmes/grasp_tabou_cvrptw.py#L57) | `algorithmes/grasp_tabou_cvrptw.py` | charge une instance dans l'algorithme (variables globales) |
| [`charger_instance`](probleme/instances.py#L113) | `probleme/instances.py` | lit un fichier `.vrp` en dictionnaire instance |
| [`charger_vrplib`](benchmark_vrplib.py#L48) | `benchmark_vrplib.py` | lit une instance pour le benchmark, renvoie la BKS |
| [`clients_touches`](algorithmes/grasp_tabou_cvrptw.py#L340) | `algorithmes/grasp_tabou_cvrptw.py` | les clients à rendre tabous |
| [`coefficient_trafic`](probleme/contraintes.py#L30) | `probleme/contraintes.py` | coefficient de la tranche horaire |
| [`construire_instance`](probleme/instances.py#L48) | `probleme/instances.py` | crée le dictionnaire instance |
| [`cout_solution`](algorithmes/grasp_tabou_cvrptw.py#L115) | `algorithmes/grasp_tabou_cvrptw.py` | coût total (fonction objectif) |
| [`cout_tournee`](algorithmes/grasp_tabou_cvrptw.py#L105) | `algorithmes/grasp_tabou_cvrptw.py` | distance d'une tournée |
| [`creer_instance_lorraine`](probleme/lorraine.py#L73) | `probleme/lorraine.py` | construit une instance de Moselle |
| [`donnees_scene`](bonus_3d/suivi_3d.py#L22) | `bonus_3d/suivi_3d.py` | prépare les données de la scène 3D (bonus) |
| [`evaluer`](probleme/contraintes.py#L56) | `probleme/contraintes.py` | **vérifie toutes les contraintes**, calcule les horaires |
| [`exemple_livrable1`](probleme/instances.py#L179) | `probleme/instances.py` | l'exemple à 6 clients |
| [`experience_convergence`](etude_statistique.py#L76) | `etude_statistique.py` | gap selon le temps |
| [`experience_robustesse`](etude_statistique.py#L52) | `etude_statistique.py` | 5 graines par instance |
| [`experience_sensibilite`](etude_statistique.py#L135) | `etude_statistique.py` | effet de alpha et de la liste tabou |
| [`experience_taille`](etude_statistique.py#L99) | `etude_statistique.py` | de 100 à 3 000 clients |
| [`famille_instance`](probleme/instances.py#L84) | `probleme/instances.py` | famille déduite du nom |
| [`gap`](probleme/contraintes.py#L126) | `probleme/contraintes.py` | écart en % à la référence |
| [`grasp_construction`](algorithmes/grasp_tabou_cvrptw.py#L150) | `algorithmes/grasp_tabou_cvrptw.py` | **construction GRASP** |
| [`grasp_tabou`](algorithmes/grasp_tabou_cvrptw.py#L438) | `algorithmes/grasp_tabou_cvrptw.py` | **multi-start** construction + tabou |
| [`grasp_tabou`](algorithmes/methodes.py#L38) | `algorithmes/methodes.py` | lance GRASP + Tabou depuis l'interface |
| [`lancer`](algorithmes/methodes.py#L52) | `algorithmes/methodes.py` | lance et chronomètre une méthode |
| [`lancer`](etude_statistique.py#L36) | `etude_statistique.py` | lance une série d'essais, enregistre le CSV |
| [`lister_instances`](probleme/instances.py#L156) | `probleme/instances.py` | les 20 instances de l'interface |
| [`lister_instances_lorraine`](probleme/lorraine.py#L107) | `probleme/lorraine.py` | les 2 instances de Moselle |
| [`matrice_distances`](probleme/instances.py#L25) | `probleme/instances.py` | distances + arrondi des références |
| [`moment`](app.py#L62) | `app.py` | écrit une heure du suivi 2D |
| [`mouvement_valide`](algorithmes/grasp_tabou_cvrptw.py#L354) | `algorithmes/grasp_tabou_cvrptw.py` | un mouvement respecte-t-il les contraintes ? |
| [`plne_exacte`](algorithmes/plne.py#L12) | `algorithmes/plne.py` | **la PLNE** |
| [`preparer`](algorithmes/methodes.py#L23) | `algorithmes/methodes.py` | charge l'instance dans l'algorithme, avec le trafic |
| [`recherche_tabou`](algorithmes/grasp_tabou_cvrptw.py#L371) | `algorithmes/grasp_tabou_cvrptw.py` | **recherche tabou** |
| [`telecharger`](benchmark_vrplib.py#L29) | `benchmark_vrplib.py` | télécharge une instance manquante |
| [`temps_trajet`](probleme/contraintes.py#L39) | `probleme/contraintes.py` | durée d'un trajet avec le trafic |
| [`tester`](benchmark_vrplib.py#L80) | `benchmark_vrplib.py` | une instance → une ligne de résultats |
| [`tournee_valide`](algorithmes/grasp_tabou_cvrptw.py#L120) | `algorithmes/grasp_tabou_cvrptw.py` | capacité, fenêtres, retour : vrai / faux |
| [`tournees_modifiees`](algorithmes/grasp_tabou_cvrptw.py#L312) | `algorithmes/grasp_tabou_cvrptw.py` | les tournées changées par un mouvement |
| [`trajet`](algorithmes/grasp_tabou_cvrptw.py#L45) | `algorithmes/grasp_tabou_cvrptw.py` | durée d'un trajet (remplacée avec le trafic) |
| [`verifier_solution`](algorithmes/grasp_tabou_cvrptw.py#L461) | `algorithmes/grasp_tabou_cvrptw.py` | contrôle final d'une solution |
| [`voisinage`](algorithmes/grasp_tabou_cvrptw.py#L238) | `algorithmes/grasp_tabou_cvrptw.py` | **les mouvements possibles et leur coût** |
