# M64 : matériaux conducteurs, résistance à chaud et données manquantes

Cette revue ciblée complète la [campagne matériau existante](../M64_700CH_MATERIAL_COOLING_LPBF.md). Elle ne sélectionne pas définitivement un alliage. Les sources ont été consultées jusqu'au **12 septembre 2026** ; publication scientifique, fiche fournisseur et piste non lue sont distinguées.

## Décision pour les premières comparaisons

Conserver **AlSi10Mg comme témoin procédé**, **CP1 comme candidat de diffusion thermique**, **HT1 comme candidat de résistance à chaud**. A20X reste une alternative dont les conditions d'essai et la conductivité doivent être complétées. Cette hiérarchie de travaux ne désigne pas le matériau gagnant. Les [points documentaires du dépôt](../../twins/m64-cylinder-head/targets/700ps-material-process-candidates.json) restent des observations attachées à un procédé et un état, pas des valeurs admissibles de calcul.

Pauzon et al. étudient directement le CP1, Al–1Fe–1Zr, fabriqué par LPBF. Ils relient précipitation et comportement mécanique après vieillissement et annoncent **330 MPa de limite d'écoulement et 27 MS/m de conductivité électrique**, après 400 °C pendant quatre heures. Ce sont des résultats de leur protocole ; **400 °C désigne le traitement, pas la température d'utilisation sous charge**. La conductivité électrique ne devient pas une carte thermique sans relation et calibration justifiées.[^1]

La fiche Constellium fournit **182–189 W/(m·K)** selon la durée de traitement à 400 °C ; la température de mesure de cette colonne n'est pas précisée. Son tableau de traction ambiante ne garantit donc pas une résistance de 300 MPa dans un pont de soupapes à 200–300 °C. La [campagne existante](../M64_700CH_MATERIAL_COOLING_LPBF.md) conserve séparément les points à chaud et leur traitement différent.[^2]

La fiche EOS **M290, AlSi10Mg, 30 µm** donne une conductivité de 100/110 W/(m·K) en brut vertical/horizontal, 165/155 après T6 et 160/165 après détensionnement. Elle permet d'identifier un témoin reproductible, mais pas de transporter ces valeurs vers une autre machine, une surface interne rugueuse ou une autre histoire thermique. La page ne fournit pas ici une courbe complète k(T). Sa mention de paroi minimale imprimable n'est pas une épaisseur structurelle admissible de culasse.[^3]

Le gain de CP1 par rapport à AlSi10Mg dépend donc fortement de **l'état comparé**. Opposer CP1 vieilli à AlSi10Mg brut produirait un classement trompeur si le composant AlSi10Mg devait être traité. Les données actuellement disponibles ne permettent pas encore une comparaison complète à température de service et durée de vie identiques.

## Pourquoi la seule conductivité ne suffit pas

Dans un chemin thermique simplifié :

\[
R_{cond}=\frac{L}{kA},\qquad
R_{conv}=\frac{1}{\eta_f h A_f},\qquad
\dot Q=\frac{\Delta T}{R_{cond}+R_{contact}+R_{conv}}.
\]

Ce réseau est un contre-calcul de premier ordre, pas un remplacement de la CHT tridimensionnelle. Doubler k ne double pas nécessairement la chaleur extraite : le contact siège–culasse, le débit entre ailettes, les carénages et l'échangeur d'huile peuvent dominer. Une galerie augmente localement l'échange mais retire aussi de la matière porteuse ; une ailette très fine peut devenir peu efficace et difficile à fabriquer.

La décision finale doit comparer, sur la même géométrie et les mêmes charges, température des ponts échappement/bougie, gradient près des sièges, déformation des logements, relaxation du serrage, fatigue thermomécanique, masse et puissance auxiliaire. **Le matériau transmettant le mieux la chaleur n'est pas automatiquement celui donnant la meilleure culasse.**

La brochure A20X distingue traitements ambiants et tableau à chaud. Pour ce dernier, les paramètres manquants empêchent d'attribuer un état T7 par simple proximité éditoriale. Ses chiffres restent utiles pour demander des essais comparables, pas pour remplir une carte de fatigue.[^4] Les comparaisons 2618 et INCONEL 718 sont déjà sourcées dans la campagne : le premier est un benchmark conventionnel, le second une comparaison masse/conduction et un candidat possible pour certains composants, pas une proposition de corps complet.

## Ce que les publications récentes changent

Mani et al. caractérisent en trois dimensions les phases d'Al–1Fe–1Zr par nanotomographie et fluorescence. La résolution annoncée atteint 57 nm pour une des techniques. Cette étude aide à comprendre les réseaux intermétalliques et la répartition de Fe/Zr ; **elle n'est pas une nouvelle campagne de fatigue à chaud sur CP1**. Ses données ouvertes peuvent soutenir une étude de microstructure ultérieure, sans retarder le premier calcul macroscopique à propriétés mesurées.[^5]

Nagalingam et al. comparent LPBF AlSi10Mg mono- et multilasers. Leurs essais associent positions dans le plateau, épaisseur de couche et circulation du gaz. Une stratégie multilasers optimisée peut rejoindre les performances en fatigue du témoin ; un débit de gaz réduit augmente les défauts pénalisants. Les éprouvettes de fatigue sont usinées puis rectifiées, à amplitude de déformation de 0,5 %. L'application pratique est de prévoir des témoins dans les zones de recouvrement et en aval du gaz, et des surfaces représentatives des galeries. Ces résultats ne fournissent pas une loi de fatigue thermomécanique de culasse.[^6]

Une publication du **11 mars 2026**, *Computational design of ultra-high thermal conductivity, crack-free aluminum alloys for additive manufacturing*, constitue une piste de conception d'alliage. La notice et l'identité ont été retrouvées, mais l'accès au PDF a été refusé. **Aucun gain chiffré ni choix de matériau n'en est déduit** ; son analyse détaillée appartient aux missions déléguées, avec ce niveau d'accès explicitement signalé.[^7]

## Paquet d'essais matériau à préparer

Pour chaque combinaison alliage–machine–poudre–orientation–traitement retenue :

1. **Transport thermique :** k(T), Cp(T), masse volumique et dilatation ; distinguer conductivité mesurée, calculée et supposée. Vérifier les effets d'anisotropie et de vieillissement.
2. **Mécanique à chaud :** E(T), courbes contrainte–déformation, relaxation/fluage aux maintiens pertinents ; essais ambiants après exposition séparés des essais directement à chaud.
3. **Durabilité :** fatigue LCF/HCF et thermomécanique avec températures et phases correspondant aux scénarios calculés ; surfaces usinées et internes représentatives, défauts caractérisés, dispersion et effectifs conservés.
4. **Assemblage :** frettage/relaxation des sièges et guides, étanchéité, dilatation différentielle ; matériaux des inserts et lubrification explicitement définis.
5. **Procédé :** coupons fabriqués avec la recette réelle, position et recouvrements laser ; métrologie après traitement, découpe, usinage et nettoyage. Les jeux de calibration et de validation doivent être distincts.

Les températures, durées et nombres d'éprouvettes définitifs découleront des charges et d'un plan de qualification approuvé. Aucun tableau fournisseur ne remplace ces essais. Il n'existe pas encore de matériau affecté et qualifié pour la fabrication moteur.

## Sources et lecture

[^1]: C. Pauzon et al., [Direct ageing of LPBF Al-1Fe-1Zr for high conductivity and mechanical performance](https://doi.org/10.1016/j.actamat.2023.119199), *Acta Materialia* 258, 119199, **1er octobre 2023**. Article évalué ; résumé, extraits méthode/résultats/conclusion de l'éditeur consultés, pas texte intégral.
[^2]: Constellium, [Aheadd CP1 — Product Sheet](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/product_sheet_aheadd_cp1_nov_2021docx.e81a7d073ebf.pdf), **novembre 2021**, 2 pages. Fiche fournisseur, pas article ; document relu, valeurs rattachées à leur état dans le registre existant.
[^3]: EOS, [AlSi10Mg, EOS M290, 30 µm](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-alsi10mg-eos-m-290-30um) ; [tableaux du portail matériaux](https://www.eos.info/metal-solutions/data-sheets/all-processes-and-materials?id=eos-aluminium-alsi10mg). Fiche procédé consultée le 12 septembre 2026. La date d'état du portail n'est pas une date de publication scientifique.
[^4]: ECKART, [Metal Powders for Additive Manufacturing, A20X, pp. 4–5](https://www.eckart.net/en/download/document/view/id/519). Brochure fournisseur, section A20X consultée ; conditions manquantes conservées dans le [registre](../../twins/m64-cylinder-head/documentary-material-points-20260907.json).
[^5]: D. Mani et al., [Nanoscale 3D characterization of an Al-1Fe-1Zr alloy for additive manufacturing](https://doi.org/10.1016/j.matchar.2025.115109), *Materials Characterization* 225, 115109, en ligne **2 mai 2025**. Article évalué ; méthodes, résultats et conclusions du [PDF institutionnel](https://publications.rwth-aachen.de/record/1012561/files/1012561.pdf?version=1) consultés, pas reproduction des données.
[^6]: A. P. Nagalingam et al., [Impact of Multiple-Laser Processing on the Low-Cycle Fatigue Behaviour of Laser-Powder Bed Fused AlSi10Mg Alloy](https://doi.org/10.3390/met15070807), *Metals* 15(7), 807, **18 juillet 2025**. Article évalué ; résumé et sections méthodes 2–3 du [PDF institutionnel](https://eprints.whiterose.ac.uk/id/eprint/230301/1/metals-15-00807.pdf) consultés ; pas lecture exhaustive des 22 pages d'article.
[^7]: Y. He et al., [Computational design of ultra-high thermal conductivity, crack-free aluminum alloys for additive manufacturing](https://doi.org/10.1080/17452759.2026.2638103), *Virtual and Physical Prototyping* 21(1), e2638103, **11 mars 2026**. **Notice seulement ; PDF inaccessible.** Piste bibliographique, exclue des preuves de sélection.
