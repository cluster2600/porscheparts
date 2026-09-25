# Releve des interfaces — 964 puis verification 993

Statut au 2026-09-25 : **preparation de mesure, pas conception liberee**.
La [fiche CSV](derived/interface-measurements-20260925.csv) conserve les 18
identites du registre du manuel. Neuf ont un ecartement transversal documentaire,
sept seulement une hypothese XY projetable. **Aucun XYZ d'ancrage n'est valide.**
P8, P9 et P10 ne figurent pas dans ce registre ; aucun point n'est invente pour
completer la numerotation. Ce registre n'est pas l'inventaire complet d'une coque.

## Lire les vues sans leur faire dire plus que le scan

`source/interface_review.py` reutilise le contrat existant et les sommets recales.
Le [rapport](derived/interface-review-20260925.json) lie par SHA-256 ses entrees,
son code et la fiche CSV. Il produit localement une vue 3D et une vue en plan :

- bleu : X **relatif** documentaire P17/P18/P19 ; pas un XYZ mesure ;
- orange : X relatif derive, non verifie P3/P5/P12/P20 ;
- pointilles verticaux : Z inconnu, sans plage de tolerance ou volume d'ancrage ;
- plan graphique sous le scan : uniquement pour separer les hypotheses de la
  peau observee. Sa hauteur ne doit jamais entrer dans la CAO ;
- P6 sans X, P21 invalide et les neuf autres identites sans XY restent dans la
  fiche, mais ne sont pas projetes. La position rejetee de P21 n'est pas reutilisee.

Le rapprochement visuel d'un point et d'une peau ne prouve pas qu'il s'agit de
la bonne fixation. Aucun plus proche voisin ne complete automatiquement Z.
La translation globale de travail de P17 reste −506 mm, **non validee**.
P12 designe la traverse de boite, jamais la suspension arriere. Les tolerances
du manuel sont celles des ecartements de paires, pas de chaque Y symetrique.

Les images contiennent des donnees du scan : elles restent hors Git tant que les
droits de redistribution ne sont pas confirmes. La fiche CSV est un etat des
connaissances, pas un formulaire a remplir en ecrasant les anciennes valeurs.

## Ordre de releve propose

| Priorite | Zone / identites | Releve a obtenir | Ce que cela debloque |
|---|---|---|---|
| 0 | Vehicule et acquisition | 964 C2/C4, millesime, caisse large d'origine ou modifiee, boite, modifications de suspension ; unite, instrument, precision annoncee, traitements du scan, etat monte/demonte | Applicabilite du scan ; aucune transposition automatique a la 993 |
| 1 | Repere structurel ; P17/P18/P19 | Identifier physiquement les surfaces de reference G/D ; XYZ et incertitudes ; controles independants des ecartements et des distances R/S | Recalage sur la caisse au lieu d'un sol deduit des pneus |
| 2 | Avant P3/P4/P5/P6 | Centres et axes des fixations, plans d'appui, entraxes, diametres et geometrie des supports ; relever P6 sans lui attribuer un X par symetrie | Interfaces du train avant et des jambes de suspension |
| 2 | Arriere P13/P14, moteur P15/P21, boite P12 | Identification par photos et reperes ; XYZ, axes, faces d'appui, motifs de percage, limites des pieces voisines | Interfaces arriere reelles ; remplacement des hypotheses P12/P21 |
| 3 | Tunnel et tringlerie, par variante | Scan cote habitacle et dessous avec carenages identifies ; supports, axes, articulations, enveloppe balayee sur tous les rapports, acces de depose | Passage de commande et forme du tunnel ; pas seulement sa peau inferieure |
| 3 | Transmission C4 | Tube/arbre, brides et differentiel avant : geometrie, ligne d'axe, supports, mouvements du groupe et acces ; etats documentes | Reservation C4 ; aucun diametre ou jeu arbitraire |
| 4 | Coque superieure et ouvertures | Tablier, passages de roue, montants, pavillon, baies, portes, charnieres et serrures ; surfaces interieures/exterieures et epaisseurs accessibles | Coque complete, pas un plancher avec volumes inventes |
| 4 | Autres interfaces | Sieges, ceintures, pedalier/direction, reservoir, conduites, faisceau, chauffage/ventilation, pare-chocs P1/P16 et autres fixations P2/P7/P11/P20 | Retenue, services, montage et maintenance a integrer au modele |

Ce tableau est une liste de travail, pas une procedure de demontage ou de mise
en charge du vehicule. Le releve et son acces doivent etre prepares avec un
operateur competent. Les configurations dynamiques et les jeux requis doivent
etre definis avec l'ingenieur responsable ; aucune valeur n'est imposee ici.

## Donnees attendues pour chaque nouvelle mesure

Conserver un nouvel enregistrement, sans modifier les preuves historiques :

- identifiant du point **et du cote**, fonction et photo annotee sans identifiant
  personnel/vehicule ; definition de l'element mesure (axe de trou, plan d'appui, etc.) ;
- generation/variante, configuration du vehicule et etat de charge ;
- XYZ, unites, repere, transformation vers le scan et incertitude justifiee ;
- axes, diametres, surfaces et entraxes utiles ; les deux cotes mesures separement ;
- instrument, verification metrologique, date, operateur et methode conserves
  dans le dossier prive ; donnees publiques anonymisees et autorisees ;
- fichier natif, empreinte du fichier, droits et points de controle independants
  de ceux utilises pour le recalage.

La precision cible et le critere d'acceptation doivent etre fixes **avant**
l'acquisition en fonction des interfaces. La dispersion du sol de 55,1 mm ou le
residu de symetrie de 7,54 mm ne sont pas des incertitudes instrumentales.

## Passage a la CAO d'interface

La prochaine version pourra placer des surfaces et axes fonctionnels editables
quand leur identite, leur XYZ et leur repere seront etayes, avec verification
sur des controles independants et revue metrologique. Les inconnues restent
non renseignees (`null`, pas zero) ; un ancrage trouve ne valide pas tous les autres. Une campagne 964 ne
qualifie ni la 993 ni toutes les variantes C2/C4.

Le drapage, les inserts, les charges admissibles, les moules et la validation
route/circuit restent des etapes ulterieures. Aucun fichier de fabrication
n'est genere par cette revue.

## Reproduire

Depuis la racine du depot, avec l'environnement de recalage deja documente :

```sh
python twins/964-chassis/source/interface_review.py \
  --vertices /chemin/prive/verts_vehicle.npy \
  --output /chemin/prive/nouvelle-revue
python3 -m unittest discover -s tests -p 'test_964_interface_review.py'
```

Le dossier de sortie doit etre nouveau ; un tableau de sommets different du
recalage archive est refuse. Les PNG restent locaux. La fiche CSV et le rapport
publies sont des copies strictement identiques de cette execution, sans geometrie brute.
