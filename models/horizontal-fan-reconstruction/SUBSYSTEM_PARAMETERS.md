# Sous-systèmes installés : dimensions et variables séparées

Le [contrat paramétrique](parameters/qualitative-subsystem-contract.json)
décrit le plénum installé, l'entraînement par poulies/courroie, le support
nervuré et l'enveloppe centrale relevée. L'inspection du
[film attribué à Patrick Motorsports](https://www.instagram.com/patrickmotorsports/reel/DeC4x04yjNP/)
est qualitative. Ses pixels restent locaux ; aucune image tierce n'est publiée.
La légende 935 3.5L Flat Fan / 993 6spd Transaxle ne démontre pas une base moteur
993, une culasse à quatre soupapes ou l'équivalence de deux ventilateurs.

**Aucune dimension installée documentée n'est disponible.** Les listes
`documented_dimensions` sont vides. Chaque variable possède un symbole,
une unité et une valeur/bornes nulles ; ses interfaces mesurées restent nulles.
Le diamètre analytique R0 de 275 mm, ses neuf pales et son jeu relatif 0,008
figurent séparément comme hypothèses d'étude. Ils n'alimentent aucune cote
documentée du montage filmé. Aucun nouveau CAD fonctionnel n'est généré.

| Sous-système | Variables de conception à renseigner | Dépendances mesurées requises |
| --- | --- | --- |
| Plénum installé | profil de lèvre, profondeur H, étendue R, sections Aᵢ, épaisseur t, jeu g | plans moteur, perçages, repères rotor, dégagements admission/commandes, débits et pertes par sortie |
| Poulies/courroie | diamètres primitifs D_driver / D_driven, entraxe C, spécification courroie, gorges, ratio, course tendeur | rôle de chaque poulie, axes et attaches, alignement, chemin de charge, paliers et tensions |
| Support nervuré | sections de nervures, épaisseurs, portée, motifs de vis, logements de palier, matériau/état | fixations moteur, réactions de courroie, masses, précharges, vibration et température |
| Enveloppe centrale | profil et hauteur, ajustement arbre/alésage, jeux axiaux, sections du voile | ajustement et retenue axiale, disposition des paliers, vitesse/couple et dilatation |

Les relations du contrat restent symboliques et conditionnelles :
Q_total = ΣQᵢ sans fuite dans un régime stationnaire incompressible ;
Aᵢ = Qᵢ/vᵢ et Δpᵢ = KᵢQᵢ² seulement après définition du régime et de Kᵢ.
Les résistances de screening existantes ne sont pas des mesures du plénum.

Pour une transmission par courroie établie, sans autre étage et avec diamètres
primitifs mesurés, n_driven/n_driver = D_driver/D_driven × (1 − slip).
Le glissement, le rôle des poulies et le renvoi interne ne sont pas connus.
La longueur de courroie ouverte idéale n'est valable que pour deux poulies
coplanaires sans tendeur ; aucune référence de courroie n'est sélectionnée.
T = (F_tight − F_slack) D_pitch/2 et P = Tω définissent un chemin de charge
possible, sans fournir les tensions ou charges de paliers réelles.

L'ordre de conception suit les interfaces : repères/attaches mesurés, axes et
plans d'assemblage, dégagements, sections, puis charges et tolérances. Les
reconstructions actuelles ne fournissent pas leur propre preuve de montage.
Les gardes logicielles refusent qu'une variable sans mesure devienne une cote
documentée, une pièce fonctionnellement complète ou une qualification physique.
