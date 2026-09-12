# Culasse M64 : procédé LPBF et refroidissement par huile

La littérature disponible au 12 septembre 2026 soutient une qualification progressive par coupons et secteurs de culasse. Elle ne démontre pas qu’une culasse M64 imprimée, turbo, quatre soupapes et refroidie uniquement par air/huile tiendra 700 ch. La référence du dépôt reste **700 PS au vilebrequin, soit 514,85 kW** ; 700 hp mécaniques correspondraient à environ 522 kW. Le régime, le carburant, le cycle d’utilisation et la chaleur réellement transférée à chaque culasse restent à définir.

## Références moteur et portée

Swindon documente un kit M64 quatre soupapes refroidi par air, utilisant la commande de distribution et la lubrification d’origine. Cette existence industrielle établit la plausibilité de l’architecture, sans fournir de validation publique d’une culasse LPBF à 700 PS turbo. Singer annonce pour son DLS Turbo Road 710 HP SAE net et quatre soupapes, mais **des culasses refroidies par eau**, avec cylindres refroidis par air.[^10][^11] Aucune affirmation historique sur l’impossibilité du quatre-soupapes dans les années 1960 n’est retenue faute de source primaire vérifiée.

## Simulation du procédé

AdditiveFOAM est adapté au transport thermique et à l’écoulement local du bain, avec source volumique, chaleur latente et effet Marangoni. Son article de 2025 situe explicitement ce modèle intermédiaire entre résolution détaillée du bain et calcul global de pièce.[^1] Knapp et al. montrent sur l’IN625 du benchmark NIST qu’un modèle thermique simplifié calibré peut reproduire certaines sorties aussi bien qu’un modèle avec écoulement.[^2] Ce résultat justifie une calibration économique ; il ne prouve pas que l’écoulement ou la vaporisation soient négligeables pour l’alliage et la recette M64.

Les essais F58 doivent rester distincts :

| Reçu et date | Physique et fenêtre | Limiteur / laser absorbé |
|---|---|---:|
| [Coupon corrigé du 8 septembre 2026](../M64_F58_CORRECTED_COUPON_20260908.md) | Écoulement couplé ; arrêt à 109,55 µs sur 120 µs | 8,406 % |
| [Quadrature q10 du 12 septembre 2026](../M64_QUADRATURE_EXECUTION_20260912.md) | Thermique seule ; 40 µs terminées | 9,8133 % |
| [Quadrature q20 du 12 septembre 2026](../M64_QUADRATURE_EXECUTION_20260912.md) | Thermique seule ; 40 µs terminées | 8,8675 % |

Tous atteignent le plafond numérique de 3 300 K. Les q10/q20 comparent uniquement la quadrature sur une même fenêtre ; ils ne complètent ni ne remplacent le coupon couplé du 8 septembre. Ces pourcentages sur des physiques et durées différentes ne décrivent pas une tendance d’amélioration. Une excellente fermeture comptable incluant ce puits artificiel ne constitue pas une validation physique. La priorité reste : propriétés distinctes poudre/solide, absorption et profil laser mesurés, conditions thermiques justifiées, puis sections métallographiques de pistes et coupons multicouches. La prépublication Kumar et al. (2026) couvre justement évaporation, recul de vapeur, réflexions laser et variation d’épaisseur de poudre ; son accord annoncé avec NIST mérite une reproduction ciblée, sans remplacer automatiquement le solveur existant.[^9]

Pour la culasse entière, il faut un modèle thermomécanique de construction : activation des couches, supports, bridage, plasticité dépendante de la température, refroidissement, traitement thermique, découpe du plateau et usinage. Les orientations documentaires divergent dans le temps : [la note du 8 septembre](../M64_MULTIPHYSICS_EXECUTION.md) retient MOOSE comme candidat, tandis que [le plan du 12 septembre](../M64_JOBS_234_20260912.md) donne la priorité à Adamantine après qualification du procédé. Les exemples DED de MOOSE/MALAMUTE ne qualifient pas le LPBF ; la version Adamantine 1.0 publiée en 2024 limite sa mécanique au CPU série et exige des maillages hexaédriques conformes.[^4][^12] La proposition est un **unique benchmark thermomécanique**, comparant la chaîne existante à Adamantine sur un même coupon, avec mêmes lois, charges, séquence de débridage et mesures de déformation. Le choix dépendra de cet écart aux mesures, de la faisabilité du maillage et du coût de calcul ; aucune intégration obligatoire des deux familles n’est proposée.

ExaCA v2 améliore le traitement des refusions et la prédiction de texture. ExaConstit calcule ensuite la réponse mécanique homogénéisée de polycristaux.[^3][^13] Leur ajout se justifie seulement si des mesures EBSD et des essais selon plusieurs orientations permettent de calibrer et vérifier ces modèles. Une couleur de grain simulée ne donne ni une courbe de fatigue à chaud ni une durée de vie de culasse.

## Circuits d’huile imprimés

Une architecture de départ défendable associe des ailettes externes conservées à des galeries d’huile accessibles, courtes et dirigées vers les zones thermiquement critiques. Des branches parallèles limitent la longueur parcourue, mais exigent un contrôle de la répartition ; des serpentins très longs augmentent la difficulté de nettoyage et la sensibilité hydraulique. Ce choix reste une proposition d’ingénierie à comparer au refroidissement sans galerie supplémentaire.

Le dimensionnement doit coupler chaleur extraite et coût hydraulique :

\[
\dot Q_{huile}=\dot m\,c_p(T)\,(T_{sortie}-T_{entrée}),\qquad
\Delta p=\left(f\frac{L}{D_h}+\sum K\right)\frac{\rho U^2}{2},\qquad
P_{pompe}=\frac{\Delta p\,\dot V}{\eta}.
\]

Ces relations ne permettent pas d’assimiler les 514,85 kW mécaniques à la chaleur à extraire. Il faut mesurer ou calculer le partage air/huile/échappement, utiliser la viscosité réelle de l’huile froide et chaude, et vérifier le débit encore disponible pour la lubrification ainsi que le retour et la désaération.

Favero et al. associent essais hydrauliques, caractérisation de surface et tomographie de canaux LPBF CuCrZr selon leur orientation.[^5] La conséquence transférable est méthodologique : utiliser la section imprimée mesurée et calibrer la rugosité équivalente sur la perte de charge. Le matériau, le fluide et les corrélations expérimentales ne doivent pas être transférés directement à l’huile moteur. Un unique Ra et une géométrie CAO nominale sont insuffisants pour qualifier chaque galerie.

Le dépoudrage doit précéder tout traitement susceptible de fixer les résidus. Prévoir accès, rotations, évacuation et témoins reproduisant la pire branche ; vérifier par pesées répétées, filtrage des rinçages et inspection/CT selon leur sensibilité. Du et al. obtiennent un dépoudrage par combinaison de vortex et d’air comprimé, mais sur un échangeur **SiC en binder jetting**, pas en LPBF métal : leur protocole ne définit aucun diamètre minimal garanti pour cette culasse.[^6]

Juárez et al. étudient des dépôts d’une huile de turbine aérée jusqu’à 236 °C de paroi ; température et oxygène modifient leur apparition.[^8] **236 °C n’est pas une limite admissible d’huile moteur.** La boucle d’essai doit employer l’huile retenue, avec température de paroi, débit, temps de séjour, aération et arrêts à chaud représentatifs. Mesurer masse des dépôts, dérive de perte de charge, évolution du transfert thermique et particules relarguées, y compris après redémarrage.

## Critères proposés pour les prochains lots

Ces critères organisent les essais ; les limites de fabrication et de service doivent être approuvées avant leur exécution.

| Lot | Preuves attendues et condition d’acceptation |
|---|---|
| Coupon numérique | Fenêtre complète ; aucun plafond actif ; bilan de masse/énergie explicite ; raffinement spatial et temporel. Cibles initiales proposées : résidu énergétique inférieur à 1 %, variation des sorties utiles inférieure à 5 %, distinctes de la corrélation expérimentale. |
| Coupon LPBF | Lot poudre, machine, paramètres, orientation et traitements traçables ; bain mesuré ; porosité et défauts selon taille/localisation ; comparaison modèle/mesure avec incertitudes déclarées et validation sur coupons non utilisés pour calibrer. |
| Secteur de galerie | CT des passages et épaisseurs, propreté mesurée, courbes débit–pression froid/chaud, échange thermique et répartition entre branches ; limites fixées par budget pompe et température métal/huile. |
| Secteur mécanique | Déformation après découpe/usinage, étanchéité sous pression de calcul, tenue des sièges/guides et cycles thermiques ; seuils tirés des jeux, serrages et charges réellement définis. |

Van der Rest et al. montrent que rugosité et défauts proches de la surface gouvernent la fatigue d’AlSi10Mg ; leurs essais sont à température ambiante, en traction cyclique R = 0,1.[^7] Il faut donc tester le procédé final à chaud, après vieillissement, avec surfaces internes représentatives : traction, fatigue, cycles thermomécaniques et fluage/relaxation lorsque les durées de maintien le justifient. Des éprouvettes polies ou une densité moyenne élevée ne qualifient pas les ponts entre sièges et galeries. Le passage final reste un banc moteur instrumenté avec inspection après essais.

## Sources et niveau de lecture

Sources consultées le **12 septembre 2026**, publications retenues jusqu’à cette date. « Intégral » désigne le document complet lu ; « sections » une consultation ciblée du texte intégral ; « résumé » exclut toute prétention de lecture complète.

[^1]: J. Coleman et al., [AdditiveFOAM: A Continuum Multiphysics Code for Additive Manufacturing](https://www.theoj.org/joss-papers/joss.07770/10.21105.joss.07770.pdf), JOSS, **23 mai 2025**. Article logiciel évalué ; **intégral, 4 pages**. [Code ORNL](https://github.com/ORNL/AdditiveFOAM).
[^2]: G. L. Knapp et al., [Calibrating uncertain parameters in melt pool simulations of additive manufacturing](https://doi.org/10.1016/j.commatsci.2022.111904), Computational Materials Science 218, **5 février 2023**. Évalué ; **résumé ORNL et extraits éditeur de méthode/conclusion**, pas intégral.
[^3]: M. Rolchigo et al., [ExaCA v2.0](https://doi.org/10.1016/j.commatsci.2025.113734), Computational Materials Science 251, **mars 2025**. Évalué ; **résumé ORNL et début du manuscrit auteur**, pas intégral. [Manuscrit OSTI](https://www.osti.gov/servlets/purl/2538332).
[^4]: B. Turcksin et S. DeWitt, [Adamantine 1.0: A Thermomechanical Simulator for Additive Manufacturing](https://www.theoj.org/joss-papers/joss.07017/10.21105.joss.07017.pdf), JOSS, **17 octobre 2024**. Article logiciel évalué ; **intégral, 5 pages**. [Code](https://github.com/adamantine-sim/adamantine).
[^5]: G. Favero et al., [Effect of the building orientation on additively manufactured copper alloy: Hydraulic performance of different surface roughness channels](https://doi.org/10.1016/j.ijft.2024.100790), International Journal of Thermofluids 23, **5 août 2024**. Évalué ; **résumé éditeur et extraits indexés du manuscrit institutionnel**, PDF direct inaccessible.
[^6]: W. Du, W. Yu, D. M. France et D. Singh, [Depowdering of an additively manufactured heat exchanger with narrow and turning channels](https://doi.org/10.1016/j.addlet.2024.100202), Additive Manufacturing Letters 9, **avril 2024**. Évalué ; **résumé et sections expérimentales indexées**, pas intégral. SiC/binder jetting.
[^7]: C. van der Rest et al., [Influence of roughness and subsurface porosity on the fatigue life of AlSi10Mg produced by Laser Powder Bed Fusion](https://doi.org/10.1016/j.msea.2025.148885), Materials Science and Engineering A 944, **en ligne 28 juillet 2025**, volume novembre 2025. Évalué ; **sections introduction, 2.4 et conclusions du PDF UCLouvain**.
[^8]: R. Juárez, B. Creighton et E. L. Petersen, [Temperature Dependence of Aerated Turbine Lubricating Oil Degradation From a Lab-Scale Test Rig](https://doi.org/10.1115/1.4066787), ASME Journal of Engineering for Gas Turbines and Power 147(7), **en ligne 20 janvier 2025**, numéro juillet 2025. Article de revue ; **résumé éditeur déposé dans Crossref**, PDF inaccessible.
[^9]: B. Kumar et al., [Laser Powder Bed Fusion Melt Pool Dynamics for Different Geometric Variations and Powder Layer Heights: High-Fidelity Multiphysics Modeling vs 2025 NIST Experiments](https://arxiv.org/abs/2604.07359v1), **soumission v1 le 29 mars 2026 à 02:53:32 UTC**, selon l’historique arXiv revérifié. L’identifiant appartient à la série 2026-04 ; la date d’annonce publique n’est pas établie ici. **Prépublication**, évaluation par les pairs non établie ; **résumé uniquement**.
[^10]: Swindon Powertrain, [M64 24V Cylinder Head Kit Product Sheet](https://swindonpowertrain.com/wp-content/uploads/2025/10/M64-24V-Cylinder-Head-Kit-Product-Sheet-0923.pdf), fiche référencée « 0923 », hébergée sous 2025/10. Source constructeur ; **section descriptive du PDF**. Date exacte de révision non établie.
[^11]: Singer Vehicle Design, [DLS Turbo Services — Road](https://singervehicledesign.com/singer-in-the-world/featured-restoration-3/), page non datée. Source constructeur ; **section Engine**, relevée au 12 septembre 2026.
[^12]: Idaho National Laboratory, [MALAMUTE System Design Description](https://malamute.inl.gov/sqa/malamute_sdd.html) et [présentation](https://malamute.inl.gov/), documentation officielle ; **sections procédé et architecture**. La page d’accueil indique une construction documentaire du 11 septembre 2026. Aucune exécution M64 établie.
[^13]: LLNL, [ExaConstit](https://github.com/LLNL/ExaConstit), code et README officiels, **sections applications, constitution et données d’entrée**, relevés au 12 septembre 2026 ; documentation logicielle, pas essai matériau.
