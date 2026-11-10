# Projet Smart : tournées de livraison (ADEME / CesiCDP) - Groupe 3

Une entreprise doit livrer des clients avec plusieurs camions identiques partant d'un même
dépôt. Il faut construire les tournées qui **minimisent la distance totale** en respectant :

* la **capacité** des camions (identique pour tous) et le **nombre de camions** disponibles ;
* les **fenêtres de temps** des clients : on peut attendre si on arrive trop tôt, mais pas
  livrer en retard ;
* le retour au dépôt avant sa fermeture, et en option le **trafic** selon l'heure.

C'est le problème **CVRPTW** (niveau A du sujet), qui contient le CVRP (niveau B).
Il est NP-difficile : on utilise une **méthode exacte (PLNE)** pour les petites instances
et des **métaheuristiques (GRASP et recherche tabou)** pour les grandes.

## Ce que contient le dépôt

| Quoi | Où |
|---|---|
| Le livrable : modélisation, PLNE, complexité, métaheuristique, benchmark, étude statistique | `Projet_Smart.ipynb` |
| Le GRASP et la recherche tabou | `algorithmes/grasp_tabou_cvrptw.py` |
| La PLNE du livrable 1, résolue par CBC | `algorithmes/plne.py` |
| Le benchmark sur les instances de référence VRPLIB (gap) | `benchmark_vrplib.py` |
| L'étude statistique (robustesse, convergence, taille, sensibilité) | `etude_statistique.py` |
| Une interface web pour lancer, vérifier, visualiser et comparer les méthodes | `app.py` |
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
| tester le GRASP + tabou seul | `python algorithmes/grasp_tabou_cvrptw.py` |
| recréer les instances générées (déjà fait) | `python -m probleme.instances` |

Toutes les commandes se lancent **depuis le dossier du projet**. Les résultats (CSV et
graphiques) sont enregistrés dans `resultats/`.

## Organisation

```
projet-smart/
├── README.md                 ce fichier
├── GUIDE_DU_CODE.md          l'explication de chaque fichier et de chaque partie du code
├── Projet_Smart.ipynb        le notebook du livrable
├── app.py                    ▶ l'interface (4 onglets)
├── benchmark_vrplib.py       ▶ le benchmark VRPLIB
├── etude_statistique.py      ▶ l'étude statistique
├── requirements.txt          les bibliothèques à installer
├── lancer_interface.bat      lance l'interface d'un double-clic (Windows)
│
├── probleme/                 les données et les règles du problème
│   ├── instances.py          lire, créer et lister les instances ; matrice des distances
│   ├── lorraine.py           5 instances sur de vraies villes autour de Metz et Nancy
│   └── contraintes.py        vérifier une solution, trafic, gap
├── algorithmes/              les méthodes de résolution
│   ├── grasp_tabou_cvrptw.py GRASP + recherche tabou
│   ├── plne.py               PLNE (méthode exacte)
│   └── methodes.py           les 3 méthodes de l'interface et leur lancement chronométré
├── interface/                ce qui ne sert qu'à l'interface
│   ├── graphiques.py         cartes, planning, suivi 3D / 2D, convergence
│   └── etude.py              l'onglet « Étude expérimentale »
│
├── instances/                les instances (.vrp) et leurs meilleures solutions connues (.sol)
└── resultats/                les CSV et graphiques produits
```

Règle de rangement : **à la racine, ce qu'on lance ; dans les dossiers, le code rangé par thème.**

## Résultats en bref

* **Benchmark VRPLIB du notebook** (20 instances Solomon et X, 20 s, une graine) :
  gap moyen **4,98 %**, 15 instances sur 20 sous 7 %, toutes les solutions valides.
* **Amélioration « 40 voisins les plus proches »** (12 instances de 100 à 3 000 clients,
  10 s) : gap moyen de la recherche tabou **7,6 % → 5,7 %**, du GRASP **43,7 % → 6,8 %**.
* **Points faibles** : fenêtres larges (familles R2 et RC2) et très grandes instances avec
  fenêtres serrées (R1_10_1, 1 000 clients : environ 19 %).

Le détail et l'analyse sont dans le notebook.

## Références

* Solomon (1987), instances VRPTW ; Uchoa et al. (2017), instances CVRP X ;
  Gehring & Homberger (1999) ; Arnold, Gendreau & Sörensen (2019), instances Leuven.
* Glover (1986), recherche tabou ; Feo & Resende (1995), GRASP.
* Instances : [PyVRP/Instances](https://github.com/PyVRP/Instances), lues avec
  [vrplib](https://github.com/PyVRP/VRPLIB).
