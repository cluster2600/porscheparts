# De l'originale à la culasse moderne d'étude

## Ce que montrent les sources

Les photographies de [Performance Developments, restauration de 962 C, partie 3](https://performancedevelopments.com/porsche-962c-race-engine-part-3/)
montrent des culasses individuelles, une face de chambre à quatre soupapes,
deux logements ouverts de ressorts par culasse et un port ovale latéral commun
à une paire. La vue de chambre examinée montre une ouverture centrale de
bougie. Le préparateur précise qu'il a séparé les chemises des culasses : ces
photos documentent donc aussi **sa modification**, sans établir une variante
d'usine exacte. La [partie 2](https://performancedevelopments.com/porsche-962c-race-engine-part-2/)
montre les ensembles démontés et les porte-arbres à cames séparés.

Vues examinées : [chambre](https://performancedevelopments.com/wp-content/uploads/2017/04/123_2399.jpg),
[dessus](https://performancedevelopments.com/wp-content/uploads/2017/04/124_2408.jpg),
[ports](https://performancedevelopments.com/wp-content/uploads/2017/04/124_2409.jpg),
[ensembles démontés](https://performancedevelopments.com/wp-content/uploads/2017/04/IMG_4108.jpg).
Les pixels ont été inspectés localement. Ils restent hors Git ; aucune licence
de réutilisation n'a été trouvée. Les [références et empreintes](source/architecture/references.json)
conservent leur provenance. Une photo sans échelle n'établit aucune cote.

Le dossier constructeur [40 Years Group C, pages 18–20](https://newsroom.porsche.com/dam/jcr:a6f33b52-c47d-47b4-98c1-7e963661f587/40%2520Years%2520Group%2520C.pdf)
décrit l'aluminium, des ensembles culasse/cylindre soudés par faisceau
d'électrons, la distribution à deux arbres à cames et deux circuits d'eau
indépendants avec une pompe par côté. Il ne fournit pas les coordonnées de
fixation ou les canaux internes nécessaires à notre CAO. Les archives FIA
du [dossier initial](README.md) concernent le règlement et ne remplacent pas
la métrologie. Ne pas mélanger la 962 IMSA initiale à air et cette direction
962 C à quatre soupapes et eau.

## Traduction dans le modèle

Le [générateur](source/architecture/Head962ArchitectureStudy.cs) reprend
l'organisation observée : deux poches de ressorts, corps chanfreiné et
ports communs par paire. Il ajoute quatre réservations de guides inclinés,
deux puits d'allumage et une chemise d'eau suivant la chambre et les conduits.
Le double allumage et les dimensions constituent **notre proposition**.
Ce modèle n'est pas une reconstruction cotée de la culasse photographiée.

La forme conforme vient d'offsets natifs, d'intersections et de soustractions.
Cette construction autorise des chemins proches des parois chaudes ; elle
ne démontre pas un meilleur débit ou transfert thermique. L'implantation des
deux terminaux représente une étude d'alimentation/retour, à confronter au
réseau complet de chaque banc. Le modèle ne complète ni paliers, ni goujons,
ni huile, ni sièges rapportés, ni commande de soupapes.

## PicoGK et ses bibliothèques

| Outil | Usage effectif ou entrée manquante |
| --- | --- |
| PicoGK 2.3.0 / natif 26.2 | Booléens, offsets, lissage du corps, poutres de raccordement, voxelisation à 0,5 mm et export STL exécutés. |
| [ShapeKernel](https://github.com/leap71/LEAP71_ShapeKernel) | `LocalFrame`, `BaseBox`, `BaseCylinder`, `LineModulation` et `SurfaceModulation` exécutés pour le corps variable et les lofts ovales. Sources installées à la révision déclarée `554bce4…`, empreintes enregistrées. Licence Apache-2.0. |
| [LatticeLibrary](https://github.com/leap71/LEAP71_LatticeLibrary) | `CuboidCell`, `BodyCentreLattice` et `ConstantBeamThickness` exécutés pour des nervures extérieures ouvertes. Cellules et diamètre sont des hypothèses, sans optimisation sous charges. Aucun treillis n'est placé dans l'eau. |
| [Fasteners](https://github.com/joshmelnykcroft/PicoGK-Fasteners) | Installée. Filetages et perçages attendent les interfaces mesurées du donneur. |
| [HelixHeatX](https://github.com/leap71/LEAP71_HelixHeatX) | Installée ; concerne l'échangeur du [module thermique](THERMAL_MODULE.md), pas une preuve de refroidissement de la culasse. |
| Échange natif OpenVDB | Trois domaines, un champ scalaire de distance et un champ vectoriel de gradient sauvegardés puis relus par nom ; contrôles de domaines et valeurs actifs dans les deux sens. |
| [SimulationExample](https://github.com/leap71/PicoGK_SimulationExample) | Disponible pour préparer une entrée de simulation. L'échange présent utilise directement `OpenVdbFile`, sans conditions physiques inventées ni solveur CFD/CHT. |

Utiliser toutes les fonctions sans besoin identifié ajouterait des formes
sans justification physique. La bibliothèque de formes sert ici la culasse ;
les autres restent liées à leur problème et aux données nécessaires.

La [variante à nervures](BIONIC_FIELDS.md) utilise effectivement ShapeKernel,
LatticeLibrary et les champs VDB sur les volumes de cette culasse. Elle ajoute
de la matière aux flancs : ce n'est pas une promesse d'allégement ni de gain
thermique. Les [vues de la variante](GALLERY.md) et son rapport restent au
statut d'étude non qualifiée.

## Contribution Qwen réellement exécutée

Le Qwen local est `Qwen2.5-Coder-1.5B-Instruct`, conversion MLX 4 bits à
révision figée. Les anciens poids de base manquaient : ils ont été restaurés
depuis la révision publique attendue et leur SHA-256 a été vérifié. Le
checkpoint spécialisé PicoGK **r3, étape 240** était intact. Aucune location
GPU ou modification du modèle par défaut n'a eu lieu.

Les [réponses et reçus](derived/qwen-assistance/review.json) conservent trois
exécutions : méthode complète avec r3, méthode complète avec le modèle de
base, puis expression de rayon elliptique avec le modèle de base. Les deux
méthodes étaient invalides et sont rejetées sans exécution. Seule l'expression
elliptique a été retenue après contrôle analytique ; le code d'intégration a
été corrigé et compilé séparément. Cette aide étroite n'établit aucune
expertise mécanique ou thermique du modèle.

## Étape vers le kit de 1 000 ch moteur

La [galerie](GALLERY.md) présente les vrais maillages. Le
[rapport](derived/architecture-report.json) décrit leur contrôle indépendant.
Le matériau reste à sélectionner et qualifier suivant le
[protocole existant](MATERIAL_QUALIFICATION.md) : la conductivité seule ne
choisit pas un alliage de culasse. Les mesures des
[interfaces donneur](DONOR_METROLOGY.md), la distribution, le cycle de charge,
le carburant, la CFD/CHT et la validation mécanique restent nécessaires au
kit banc/piste. Aucune compatibilité 964/993 ni puissance n'est validée.
