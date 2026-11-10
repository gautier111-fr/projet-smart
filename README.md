# Projet Smart : tournées de livraison (ADEME / CesiCDP) - Groupe 3

Une entreprise doit livrer des clients avec plusieurs camions identiques partant d'un même
dépôt. Il faut construire les tournées qui **minimisent la distance totale** en respectant :

* la **capacité** des camions (identique pour tous) et le **nombre de camions** disponibles ;
* les **fenêtres de temps** des clients : on peut attendre si on arrive trop tôt, mais pas
  livrer en retard ;
* le retour au dépôt avant sa fermeture, et en option le **trafic** selon l'heure.

C'est le problème **CVRPTW** (niveau A du sujet), qui contient le CVRP (niveau B).
Il est NP-difficile : on utilise une **méthode exacte (PLNE)** pour les petites instances
et une **métaheuristique, GRASP + recherche tabou**, pour les grandes : le GRASP construit
des solutions, la recherche tabou les améliore, et on recommence tant qu'il reste du temps.

## Ce que contient le dépôt

| Quoi | Où |
|---|---|
| Le livrable : modélisation, PLNE, complexité, métaheuristique, benchmark, étude statistique | `Projet_Smart.ipynb` |
| La métaheuristique GRASP + Tabou | `algorithmes/grasp_tabou_cvrptw.py` |
| La PLNE du livrable 1, résolue par CBC | `algorithmes/plne.py` |
| Le benchmark sur les instances de référence VRPLIB (gap) | `benchmark_vrplib.py` |
| L'étude statistique (robustesse, convergence, taille, sensibilité) | `etude_statistique.py` |
| Une interface web simple pour lancer une méthode, voir les tournées et suivre les camions en 2D | `app.py` |
| L'explication de chaque partie du code | **[`GUIDE_DU_CODE.md`](GUIDE_DU_CODE.md)** |

## Installation

```bash
pip install -r requirements.txt
```

Python 3.10 ou plus. `pulp` est fixé à la version 2.9.0 (la version 4 change l'écriture du modèle).

## Lancer

| Pour… | Commande |
|---|---|
| ouvrir l'interface | `streamlit run app.py` (ou double-clic sur `lancer_interface.bat`) |
| le benchmark VRPLIB (20 instances, 20 s chacune) | `python benchmark_vrplib.py 20` |
| l'étude statistique (environ 25 min) | `python etude_statistique.py` (ou `python etude_statistique.py 1 3` pour certaines expériences) |
| tester le GRASP + Tabou seul | `python algorithmes/grasp_tabou_cvrptw.py` |

Toutes les commandes se lancent **depuis le dossier du projet**. Les résultats (CSV et
graphiques) sont enregistrés dans `resultats/`.

## Organisation

```
projet-smart/
├── README.md                 ce fichier
├── GUIDE_DU_CODE.md          l'explication de chaque fichier et de chaque partie du code
├── Projet_Smart.ipynb        le notebook du livrable
├── app.py                    ▶ l'interface
├── benchmark_vrplib.py       ▶ le benchmark VRPLIB
├── etude_statistique.py      ▶ l'étude statistique
├── requirements.txt          les bibliothèques à installer
├── lancer_interface.bat      lance l'interface d'un double-clic (Windows)
│
├── probleme/                 les données et les règles du problème
│   ├── instances.py          lire et lister les instances ; matrice des distances
│   ├── lorraine.py           5 instances sur de vraies villes autour de Metz et Nancy
│   └── contraintes.py        vérifier une solution, trafic, gap
├── algorithmes/              les méthodes de résolution
│   ├── grasp_tabou_cvrptw.py GRASP + Tabou (le code de l'équipe)
│   ├── plne.py               PLNE (méthode exacte)
│   └── methodes.py           les 2 méthodes de l'interface et leur lancement chronométré
│
├── instances/                toutes les instances (.vrp) et leurs meilleures solutions connues (.sol)
├── resultats/                les CSV et graphiques produits
└── images/                   la capture de l'interface (notebook, partie 10)
```

Règle de rangement : **à la racine, ce qu'on lance ; dans les dossiers, le code rangé par thème.**

## Résultats en bref

* **Benchmark VRPLIB** (20 instances Solomon et X, 20 s, une graine) : gap moyen **3,50 %**,
  **19 instances sur 20 sous 7 %**, toutes les solutions valides (notebook, partie 7).
* **Réglage alpha = 0,1** : gap moyen 4,98 % → 3,34 %, amélioration significative
  (test de Wilcoxon, p = 0,022).
* **Passage à l'échelle** (numpy, construction incrémentale, 30 plus proches voisins) :
  X-n1001-k43 (1 000 clients, 60 s) passe de 37 % à **7,8 %**, Leuven1 (3 000 clients) **6,8 %**.
* **PLNE** : optimum prouvé jusqu'à 10 clients, retrouvé par GRASP + Tabou ; à 15 clients, la
  PLNE ne prouve plus l'optimum en 60 s, GRASP + Tabou fait presque aussi bien en 5 s.
* **Point faible** : les fenêtres larges (RC205 reste à 7,95 %).

## Références

* Solomon (1987), instances VRPTW ; Uchoa et al. (2017), instances CVRP X ;
  Gehring & Homberger (1999) ; Arnold, Gendreau & Sörensen (2019), instances Leuven.
* Glover (1986), recherche tabou ; Feo & Resende (1995), GRASP.
* Instances : [PyVRP/Instances](https://github.com/PyVRP/Instances), lues avec
  [vrplib](https://github.com/PyVRP/VRPLIB).
