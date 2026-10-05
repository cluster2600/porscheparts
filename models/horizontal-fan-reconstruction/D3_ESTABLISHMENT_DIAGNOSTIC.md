# Établissement de D2 et essai discriminant D3

Le [diagnostic des champs et journaux conservés](results/cfd/D2-establishment-diagnostic.json)
est terminé sans nouveau solveur, modification de maillage ou changement des
critères. Les fichiers initiaux960 téléchargés en lecture seule sont identiques
aux empreintes de la préparation D2 exécutée. Les états1000/1020, tables et logs
proviennent des archives natives déjà vérifiées ; ils restent privés.

## Ce qui explique le prochain essai

Au démarrage960, les cinquante couches ajoutées répètent la vitesse des cellules
de sortie, avec une pression nulle partout dans le prolongement. Les flux des
51 plans sont identiques. Cette initialisation conserve le débit ; elle
n'établit pas l'équilibre de quantité de mouvement du domaine ajouté.

De960 à1000, la variation RMS de pression vaut38,34 Pa dans le cœur et86,63 Pa
dans le prolongement ; de1000 à1020 elle vaut encore10,35 /14,40 Pa. La variation
RMS de vitesse1000→1020 vaut0,382 /3,056 m/s. Ces résultats indiquent un
établissement encore actif, sans isoler causalement l'effet de l'initialisation.

Le premier résidu initial p décroît de0,241 à0,00538 sur les60 itérations
complètes ; sur les20 dernières, il est divisé par1,985. Les180 résolutions
linéaires de pression respectent leur `relTol=0.01` : leur maximum
final/initial vaut0,009979. Les extrema de pression commune diminuent au fil
des itérations, mais la [stationnarité et l'admission D2 échouent](D2_COMPLETION_EXECUTION.md).
Le résidu de matrice n'est pas une erreur de pression physique.

À1020, le reflux brut représente9,27 % du flux net au plan commun,
environ11,8 % au milieu du prolongement et10,82 % à la sortie. L'allongement
seul n'a donc pas supprimé le reflux. Les parois latérales glissantes et la
section constante de ce tampon ne représentent pas un plénum installé.

## Pourquoi ne pas lancer directement un transitoire

Le volume ajouté divisé par le débit net vaut14,35 ms, soit1,435 tour à6000 rpm.
C'est un temps de traversée nominal ; le reflux empêche d'en faire une borne
du temps de séjour. Les itérations SIMPLE n'ont aucune durée physique.
Le solveur contient un terme temporel dont le rôle dépend du schéma sélectionné ;
le calcul actuel emploie `steadyState`.
[Source du solveur OpenFOAM13](https://github.com/OpenFOAM/OpenFOAM-13/blob/master/applications/modules/incompressibleFluid/momentumPredictor.C).

Le diagnostic reconstruit indépendamment les volumes par les faces natives :
680596 volumes positifs, différence absolue maximale dans le cœur de
3,31×10⁻²² m³ par rapport aux volumes déjà contrôlés. Pour le flux MRF natif,
`Co=dt Σ|phi_face|/(2V)` donne un taux maximal de3,15×10⁷ s⁻¹ et un pas
indicatif `Co≤0.5` de1,59×10⁻⁸ s. Cela représente630014 pas par tour.
La cellule limitante a un volume de1,37×10⁻¹⁵ m³ ; le percentile99 du taux
est aussi élevé, à1,15×10⁷ s⁻¹. Le passage du contrôle de maillage ne garantit
donc pas son coût ou sa qualité pour un transitoire. Cette estimation n'est
ni un pas choisi, ni une preuve d'instationnarité physique. Un transitoire
pertinent nécessiterait d'abord une étude des petites cellules, du schéma
temporel et du coût, puis assez de tours pour mesurer l'établissement.

## D3 : vingt itérations par branche, même état1020

Les [deux cas privés sont préparés et vérifiés](parameters/D3-prepared-relaxation-protocol.json).
Chaque branche reprend les mêmes28 champs natifs et quatre marqueurs temporels,
sur les quatre partitions d'origine. Aucun remaillage, décomposition ou
reconstruction n'a été lancé. Les champs, géométrie, conditions aux limites,
MRF6000 rpm, turbulence, schémas et solveurs restent identiques.

| Branche | Relaxation p | Travail prévu |
| --- | --- | --- |
| `control015` | 0,15, inchangée | 20 itérations1021–1040 |
| `candidate005` | 0,05 | 20 itérations1021–1040 |

Seul `system/fvSolution` diffère entre les branches, et seulement sur cette
valeur. Leur contrôle temporel identique demande exactement20 pas et les
tables natives à chaque pas. L'identité1020 n'est pas réécrite à0.

Comparer à travail égal : décroissance du premier résidu p et maxima de tous
les résidus, moyenne/écart-type de la pression commune, variations volumiques
de p/U depuis1020, débit, couple, reflux et extrema. Une variance plus faible
avec un résidu ou une dérive plus élevés traduit seulement une évolution
ralentie ; elle ne justifie aucune admission. Une modification de la phase
ou de l'amplitude avec α renseignerait sur la sensibilité numérique, sans
prouver un phénomène transitoire réel. Les critères numériques et les seuils
de stationnarité originaux sont conservés. Un résultat encore inconclusif
sera archivé sans prolongation automatique ni répétition aveugle.

**Budget à coordonner avant lancement :** deux solveurs séquentiels, quatre
CPU au maximum, RAM+swap5 Gio, réseau désactivé, image OpenFOAM13 déjà disponible.
Plafond global360 s comprenant préparation30 s, solveurs90 s chacun,
reconstruction40 s, analyse45 s, sauvegarde60 s et libération5 s. Le dernier
lot20 pas a consommé110,5 s tout compris, dont67 s de solveur ; le budget est
une borne, pas une garantie de terminer. Les limites de phases partagent une
seule échéance globale. Un superviseur D3 contrôlé reste à assembler/admettre
avant toute exécution ; les commandes de solveur du protocole ne sont pas un
lanceur autorisé. Aucun job D3 n'est lancé et aucun créneau serveur n'est réservé.

## Reproduire les préparations sans lancer de calcul

Les entrées privées sont les archives natives D2/D2-completion, le checkpoint960
et les sélections communes. `PRIVATE_FAN_WORKSPACE` désigne un répertoire privé
externe au contenu publié. Avec les dépendances déjà présentes :

```sh
python3 source/diagnose_d2_establishment.py "$PRIVATE_D2_CASES" "$PRIVATE_D2_COMPLETION/extended" "$PRIVATE_D2_SELECTIONS" "$PRIVATE_FAN_WORKSPACE/diagnostic.json" "$PRIVATE_FAN_WORKSPACE/centers.npz"
python3 source/prepare_d3_relaxation_pair.py . "$PRIVATE_D2_COMPLETION" "$PRIVATE_FAN_WORKSPACE/D3-pair"
```

Le [code du diagnostic](source/diagnose_d2_establishment.py) et le
[préparateur D3](source/prepare_d3_relaxation_pair.py) consignent les empreintes.
Le scan brut, les champs natifs et les coordonnées CFD restent privés.
[Assemblage et fabrication, poursuivis indépendamment](ASSEMBLY_MANUFACTURING_S1.md).
