# M64 biturbo 700 ch — campagne matériau, refroidissement et procédé

État documentaire du 7 septembre 2026. Cette note définit des **branches de calcul**,
pas un alliage gagnant, une recette fournisseur libérée ou une culasse validée.
Le [jeu de données associé](../twins/m64-cylinder-head/targets/700ps-material-process-candidates.json)
sépare température d'essai, traitement, orientation et inconnues. Aucune courbe
interpolée n'est transférée à une carte solveur.

## Décision de campagne

1. **AlSi10Mg : témoin logiciel/procédé**, pour corriger le coupon AdditiveFOAM
   existant avec des données cohérentes, sans le présenter comme la culasse M64.
2. **CP1 : branche de diffusion thermique ; HT1 : branche de résistance à chaud.**
   Comparer des géométries identiques avant d'optimiser chacune. Les traitements
   et conditions d'essai diffèrent : les chiffres ci-dessous ne classent pas à
   eux seuls des culasses complètes.
3. **A20X et AlF357 : alternatives**, respectivement si les conditions des essais
   à chaud A20X sont obtenues, et comme autre route aluminium LPBF documentée.
4. **2618 usiné : benchmark conventionnel**, sans présumer une recette LPBF.
   **718 : comparaison masse/conduction**, pas proposition de culasse entière
   par défaut. Un matériau de soupape ou d'insert n'est pas automatiquement un
   bon matériau de corps de culasse.

Les 700 ch métriques au vilebrequin (PS) ne donnent ni la puissance thermique
transmise à la culasse, ni sa pression maximale. Les charges doivent venir de la campagne
moteur : pression cylindre en fonction de l'angle, flux locaux, température et
débit d'air, circuit d'huile, richesse, avance et scénarios transitoires.

## Ce qui est effectivement mesuré

`YS` désigne la limite d'écoulement ainsi intitulée par la source ; un décalage
de 0,2 % n'est pas inventé. Un traitement à 400 °C n'est pas un essai à 400 °C.

| Candidat | Données utiles et état exact | Limite pour notre calcul |
|---|---|---|
| AlSi10Mg | Une étude expérimentale sur M290, couches 60 µm, éprouvettes verticales à surface non usinée, après 350 °C/2 h, donne Rm 280,2 MPa à température ambiante, 162,8 à 250 °C et 34,4 à 450 °C. | Ces points ne sont **pas** ceux de la route EOS 30 µm/T6. Pas de transfert de courbe entre états. |
| Aheadd CP1 | À 200 °C : YS 126, Rm 149 MPa, allongement 17 %, après 400 °C/1 h, vertical, M290/60 µm. La fiche donne k = 187 W/(m·K) après 400 °C/4 h, mais sans préciser la température de cette mesure. | Le point à chaud 1 h ne qualifie pas l'état 4 h. Il manque une carte cohérente k(T), Cp(T), E(T), plasticité et fatigue du même état. |
| Aheadd HT1 | Traitement #2 : à 200 °C YS 270/Rm 293 MPa ; à 250 °C YS 216/Rm 265 MPa. Traitement #1 : respectivement 238/268 et 188/225 MPa. | Recettes #1/#2 non publiées. Pas de k(T), Cp(T), dilatation, fluage ou fatigue thermomécanique qualifiés ici. |
| A20X | Tableau à chaud : YS/Rm 311/331 MPa à 200 °C et 215/224 à 250 °C. Masse volumique annoncée 2,85 g/cm³. | Le tableau chaud ne précise pas traitement, orientation, maintien ou effectif. **Ne pas l'étiqueter T7** par voisinage avec un autre tableau. |
| AlF357 | Route EOS M290/30 µm : après T6, vertical, YS 265/Rm 330 MPa à température ambiante ; k annoncé 150 W/(m·K), température de mesure non explicitée. | Une bonne fiche ambiante ne constitue pas une loi à chaud. |
| 2618 | NASA : courbes de 2618-T6511 extrudé, dont essais à chaud après 100 h à la température d'essai. | Ni billet FVD identifié, ni 2618-T61 forgé, ni état LPBF. Ne pas convertir en allowables M64. |
| INCONEL 718 | Bulletin matériau : Cp 435 J/(kg·K) à 21 °C ; état recuit/vieilli, k ≈ 11,39 à 21,1 °C et 14,42 W/(m·K) à 204,4 °C ; densité ≈ 8,22 g/cm³. | Données conventionnelles, pas carte LPBF. À volume égal, environ trois fois la masse d'un aluminium à 2,73 g/cm³ ; conduction très inférieure dans ces états, pas résistance thermique d'une culasse calculée. |

Sources originales : [Lehmhus et al., Materials 2022, 15, 7386, pp. 1, 5–6](https://mdpi-res.com/d_attachment/materials/materials-15-07386/article_deploy/materials-15-07386.pdf),
[Constellium CP1, fiche 2021, p. 2](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/product_sheet_aheadd_cp1_nov_2021docx.e81a7d073ebf.pdf),
[Constellium, présentation Formnext 2021, p. 9](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/2021-11-8_constellium_aheadd_formnext_final.a0a8c4307e76.pdf),
[Constellium HT1, p. 1](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/aheadd_ht1_fact_sheet_230620.ccac52e244fb.pdf),
[ECKART A20X, pp. 4–5](https://www.eckart.net/en/download/document/view/id/519),
[EOS AlF357 M290 30 µm](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-alf357-eos-m-290-30um),
[NASA CR-4517, figure 3, p. imprimée 64 / PDF 68](https://ntrs.nasa.gov/api/citations/19930022454/downloads/19930022454.pdf),
[Special Metals SMC-045, septembre 2007, pp. 1–2](https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-718.pdf).

Les figures/tableaux PDF retenus ont été inspectés visuellement ; aucune
illustration ni copie propriétaire n'est ajoutée au dépôt. Le bulletin 718
calcule k depuis la résistivité électrique ; sa conversion d'unités est
explicitée dans le JSON. La figure NASA sépare essais **à chaud** et essais
**à température ambiante après exposition** : ils ne sont pas interchangeables.
Les coefficients moyens de dilatation CP1 disponibles sont des moyennes sur
intervalles, pas une fonction locale alpha(T). Voir aussi les
[relevés matériaux antérieurs corrigés](M64_HOT_MATERIAL_SOURCE_REVIEW.md).

Pour HT1, les éprouvettes sont usinées, direction Z, M290/60 µm, NF EN ISO 6892,
avec vitesse d'essai chaud 5×10⁻³ min⁻¹. Les niveaux de déformation plastique
à chaud, fluage et fatigue ne sont donc pas déductibles d'une simple traction
ultime. Une fiche vendeur ne remplace pas les coupons du lot/procédé retenu.

## Machine moderne et recette : trois niveaux distincts

| Niveau | Référence documentaire | Ce qui reste à vérifier |
|---|---|---|
| Exemple coupon CP1 publié | 370 W, vitesse 1 400 mm/s, spot nominal 100 µm, hatch 0,13 mm, couche 60 µm, plateau 150 °C ; traitement 400 °C/4 h. | Définition optique du spot, atmosphère complète, séquence, contours, poudre/lot et validation sur la machine choisie. |
| Route EOS actuelle | M400-4, jeu `AlCP1_060_M404`, 60 µm, plateau 150 °C, argon, lame HSS, Aerospike Nozzle, EOSPRINT ≥ 2.13 ; traitement 400 °C/4 h ; TRL 3 indiqué. | Puissance, vitesse et hatch du jeu EOS non publiés sur cette page : **ne pas les remplacer silencieusement** par l'exemple 2021. |
| Machine chinoise représentative | Eplus3D EP-M400 : volume 400×400×450 mm, hauteur incluant le plateau ; options 1 à 6 lasers, 500 W notamment ; spot 70–120 µm, couches 20–120 µm, argon ou azote. | Le fournisseur ne publie pas ici une qualification CP1, une préchauffe garantie à 150 °C ou une recette équivalente EOS. |

Sources : [exemple Constellium](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/product_sheet_aheadd_cp1_nov_2021docx.e81a7d073ebf.pdf),
[route EOS M400-4](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-constellium-cp1-eos-m-400-4-60um),
[caractéristiques EP-M400](https://www.eplus3d.com/products/ep-m400-metal-3d-printer/).

**Choix pour la campagne virtuelle, pas commande :** enveloppe EP-M400 et un
laser actif pour les premiers coupons, avec l'exemple CP1 comme point de départ
documentaire. La simulation doit s'arrêter à « recette à transférer » tant que
préchauffe, profil réel, matériau et calibration ne sont pas disponibles.
L'emploi de plusieurs lasers et leurs recouvrements sera une variante ultérieure.
Ni achat, ni fourniture, ni paramètres usine n'ont été obtenus par cette étude.

## Refroidissement : air forcé, puis assistance huile mesurée

Conserver l'enveloppe extérieure de référence non ovale et les interfaces
prouvées. Évaluer à géométrie extérieure et charges identiques :

- **A — air forcé seul :** ailettes, déflecteurs et chemins de circulation ;
  calcul conjugué solide/air, pertes de charge, débit réellement fourni par la
  turbine, température des ponts échappement/bougie et gradients aux sièges.
- **B — air + huile localisée :** même base, avec passage accessible près des
  zones chaudes et retour drainable. Comparer gain thermique, masse, rigidité,
  débit, puissance de pompe, échauffement du réservoir et marge de lubrification.

Ce n'est pas une idée à imposer sans comparaison : la fiche fabricant actuelle
FVD 104 993 02 décrit déjà une poche et un perçage supérieurs pour refroidissement
par huile depuis le porte-arbres 993. Elle ne donne ni cotes ni débits. Elle
annonce **un aluminium série 7000**, contrairement au benchmark 930/2618 fourni
par l'utilisateur : ne pas confondre ces références. [FVD, culasse 993 GT2/Turbo](https://www.fvd.net/us-en/FVD10499302/billet-993gt2-993-turbo-cylinder-head.html).

L'intérêt géométrique de l'additif est démontré sur un autre organe par les
canaux internes des pistons Porsche/Mahle/Trumpf de GT2 RS. Les résultats
annoncés pour ces pistons ne sont pas transférables à notre culasse M64.
[Porsche, Christophorus 397](https://christophorus.porsche.com/fr/2020/397/technique-3d-print.html).

Bilan à renseigner, sans coefficient inventé :
`Q_huile = débit_massique × intégrale(Cp_huile(T) dT)` et
`P_pompe = perte_de_pression × débit_volumique / rendement`.
Mesurer dans le modèle la part rejetée par l'air, l'huile, les contacts et le
stockage transitoire ; ne pas compter deux fois une chaleur passée du solide
à l'huile. Les températures gaz ne deviennent pas automatiquement celles du
métal. Les conditions limites doivent inclure état chaud, démarrage, arrêt
après charge et perte partielle de ventilation/lubrification selon le plan
de sécurité. Aucun débit d'huile disponible n'est présumé.

Pour la CAO : préserver les chemins d'effort entre portée cylindre, sièges et
goujons ; imposer accès de nettoyage, inspection et bouchons mécaniquement
définis. Vérifier pression d'huile, dilatations différentielles, serrage des
inserts à chaud, étanchéité et absence de rétention. Une galerie qui refroidit
mais affaiblit un pont ou prive les paliers d'huile n'est pas une amélioration.

## Épaisseurs, supports et dépoudrage

Le seuil **1,5 mm reste un filtre DFAM provisoire du projet**, pas une limite
universelle ni une preuve de résistance. EOS annonce par exemple 0,4 mm de
paroi minimale pour une route AlSi10Mg/M290 donnée ; cette capacité procédé
ne libère pas une paroi moteur de 0,4 mm. [EOS AlSi10Mg 30 µm](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-alsi10mg-eos-m-290-30um).

Évaluer séparément ailettes, parois sous pression, ponts entre sièges, logements
guides et zones de fixation. L'épaisseur utile est celle **après usinage**,
défauts admissibles et tolérances, avec un minimum issu du calcul mécanique et
thermique en plus de la capacité LPBF. Une mesure par quelques rayons ne
qualifie pas tout un solide.

Chaque cavité doit avoir une sortie de poudre réellement connectée, des
sections franchissables et une séquence d'orientation/nettoyage. Interdire les
supports internes impossibles à retirer. Vérifier canaux au voisinage des
sièges, orifices de purge et accès d'outil. La simulation de connectivité et de
rotation n'est pas une preuve d'écoulement d'une poudre cohésive ; contrôle
résiduel, inspection et essais de nettoyage restent nécessaires avant
traitement thermique. [Solukon, FAQ dépoudrage](https://www.solukon.de/en/faq/),
[EOS/Solukon, conception et dépoudrage](https://www.eos.info/content/blog/2025/solukon-on-automated-depowdering-for-am-production).

## F58 : correction scientifique à exécuter ensuite

Le [reçu énergétique F58](../twins/reference-917-engine/evidence/f58-energy-diagnostic/energy-summary.json)
concerne **un coupon rectangulaire AlSi10Mg de 57 600 cellules**, ni l'ovale,
ni un STEP de culasse, ni CP1. Deux calculs réels de 120 µs utilisent 100 et
50 ns. Contre-calcul algébrique revérifié le 7 septembre, sans nouvelle simulation :

| Grandeur | 100 ns | 50 ns |
|---|---:|---:|
| Incident : 380 W × 120 µs | 45,600 mJ | 45,600 mJ |
| Laser absorbé intégré | 31,55219 mJ | 31,55755 mJ |
| Absorbé / incident | 69,1934 % | 69,2051 % |
| Puits artificiel du limiteur | 3,33700 mJ | 3,33147 mJ |
| Puits / laser absorbé | 10,5761 % | 10,5568 % |
| Pic plafonné | 3 300 K | 3 300 K |

Le recalcul de Kelly ne révèle pas une source qui crée plus que 380 W.
Le plancher `etaMin=0.35` n'est pas l'absorption constante ; l'isotherme
simulée rétroagit sur l'absorption. La fermeture précise de l'équation
**incluant le puits artificiel** ne valide ni température physique ni procédé.

Lecture des entrées exactes : T intérieure initiale 293,15 K, fond/côtés
imposés à 300 K ; le flux net entrant d'environ 3,8 mJ n'est donc pas, à lui
seul, une preuve d'erreur de signe. `nOuterCorrectors=0` ne résout pas la
convection complète du bain. La carte existante emploie les mêmes coefficients
k/Cp pour poudre et solide ; vérifier leur pertinence et la fraction poudre,
pas importer ces propriétés dans CP1. Aucun modèle complet de recul de vapeur
ou de surface libre n'a été ajouté au coupon.

Ordre des prochains essais, avec entrées et résultats témoins conservés :

1. **Laser éteint, seul changement puissance = 0** : mêmes IC/BC, durée,
   matériau, maillage, plafond ; intégrer stockage sensible/latent et flux.
   Cela isole l'effet des frontières dans un témoin, sans autoriser une
   soustraction linéaire des deux bains non linéaires.
2. **Troisième pas temporel et raffinement spatial distinct**, à physique
   inchangée : flux conservatifs, profil de source, volume fondu, températures
   non écrêtées là où elles existent, et énergie du limiteur. Des pics tous
   plafonnés ne sont pas une convergence physique.
3. **Corriger la physique, pas le verdict** : vérifier domaine de validité des
   propriétés et définition optique, puis convection/Marangoni si documentées.
   Si régime de vaporisation hors domaine du modèle, reconnaître ce manque et
   employer une formulation testée ; ne pas régler absorption ou Tmax pour
   faire passer la gate.
4. **Calibration indépendante** sur géométrie de bain mesurée et procédé
   comparable. L'outil ORNL `calibrateHeatSource` documenté vise le modèle
   `projected` et des profondeurs mesurées répétées ; ce n'est pas un calibrage
   direct sans mesure du SuperGaussian/Kelly actuellement utilisé.

### Témoin laser éteint effectivement exécuté

Après la revue documentaire, le témoin de l'étape 1 a été exécuté sur Kali le
7 septembre à 19:33–19:34 UTC : 2 CPU, 4 Gio, arrêt externe fixé à 300 s,
durée réelle 37,9 s. Le code de sortie zéro est vérifié par l'état final du
conteneur, séparément de la complétude du journal. Le conteneur a été supprimé
après récupération de son état ; aucun résultat ancien n'a été écrasé.

Seul `constant/scanPath` diffère du cas F58 100 ns : puissance 380 W → 0 W.
Les autres empreintes d'entrée sont identiques, notamment Tmax = 3 300 K,
les IC/BC, le modèle Kelly, le maillage et la carte AlSi10Mg. Les 1 200 pas
atteignent 120 µs. Les résultats avec le même bilan discret sont :

| Témoin sans laser | Résultat |
|---|---:|
| Maximum de température enregistré | 299,99702 K |
| Apport net des frontières | 4,040712916 mJ |
| Stockage sensible | 4,040712929 mJ |
| Laser / latent / advection / limiteur | 0 / 0 / 0 / 0 mJ |
| Intégrale du résidu absolu / apport net des frontières | 3,166×10⁻⁹ |

La normalisation par l'énergie laser est indéfinie dans ce témoin et n'est
pas utilisée. L'apport de chaleur par les frontières est ainsi confirmé sans
laser. **Ce témoin ne corrige pas le cas laser actif**, dont le limiteur
reste important ; on ne soustrait pas linéairement les deux réponses.
Le raffinement spatial et la calibration ne sont pas exécutés dans ce sous-lot.
Un troisième pas actif a ensuite été exécuté séparément, comme indiqué ci-dessous.

Empreintes du reçu privé rapatrié : résultat
`3acf16c293c77fb0aa7f5f89dbc98fe76613b5844c33c0346d8f679f57650c57`,
manifeste d'entrée
`b7218c6908e94e7bb72ed7ecb7435df901981fe0f10d4f36086f55ccc57ee222`,
preuve de sortie processus
`85f0f21987aeb682ec3c695187163f8603a92ab890e0c1c20a98224eb43ced79`.
Le JSON associé reprend uniquement les agrégats ; les journaux et champs
restent privés. Les empreintes de l'image et du binaire sont celles du reçu F58.

### Troisième pas laser actif : 25 ns

Une nouvelle copie du cas **100 ns actif** a été exécutée après libération du
créneau Kali par le travail géométrie. Seul `deltaT 1e-07` devient `2.5e-08`
dans `system/controlDict` ; puissance 380 W, Tmax 3 300 K, absorption, matériau,
IC/BC et maillage restent inchangés. Le reçu vérifie l'absence d'autre
différence, ainsi que l'intégrité des entrées originales après exécution.

Les 4 800 pas atteignent 120 µs en **131,7 s**, avec retour processus 0,
sans OOM ni timeout, sous 2 CPU/4 Gio et limite externe 300 s. Le conteneur est
supprimé après récupération des preuves ; les anciens résultats sont conservés.
Le [reçu numérique des trois niveaux](../twins/reference-917-engine/evidence/f58-energy-diagnostic/time-refinement-three-levels.json)
contient les intégrales complètes, empreintes et calculs de différences.
Dans sa version 3, le statut canonique du seul cas 25 ns est
`solver_exit_code=0`, `solver_exit_status_verified=true`, lié à la preuve
Docker ; les valeurs `null/false` du parseur seul sont conservées sous
`log_parser_process_status`. Les codes des anciens cas 100/50 ns restent
inconnus dans ce reçu. L'enrichissement ne modifie aucun bilan ni calcul
de différence. Empreinte du reçu enrichi :
`610465cc2a68bd81464d7e5d8f619a7102be791d11e052de92e4c52b90b83cbb`.
Le champ `strictly_monotonic_three_values` décrit une monotonie stricte :
il reste faux pour l'advection constante. Son renommage ne change aucun
critère, chiffre ni formule ; les reçus antérieurs sont conservés.

| Énergie sur 120 µs | 100 ns (mJ) | 50 ns (mJ) | 25 ns (mJ) |
|---|---:|---:|---:|
| Stockage sensible | 28,331056 | 28,340616 | 28,346910 |
| Stockage latent | 3,692310 | 3,692401 | 3,692608 |
| Frontières, net entrant | 3,808165 | 3,806926 | 3,806254 |
| Laser absorbé | 31,552192 | 31,557546 | 31,562272 |
| Limiteur artificiel | 3,336999 | 3,331473 | 3,329043 |

L'advection reste nulle. À 25 ns, le limiteur retire **10,5475 %** de l'énergie
laser absorbée. Les trois pics sont toujours plafonnés à 3 300 K : **aucun
ordre de convergence n'est calculé pour la température maximale**.

Pour les intégrales non directement plafonnées, le simple estimateur
`p = log2(abs((Q100-Q50)/(Q50-Q25)))` est évalué uniquement lorsque les
différences successives ont le même signe et diminuent. Il donne des ordres
**apparents du modèle discret toujours soumis au limiteur** : 0,603 pour le
sensible, 0,880 pour les frontières, 0,180 pour le laser et 1,186 pour le
puits numérique. Ce ne sont ni des ordres prouvés du solveur, ni une
extrapolation physique. L'écart du latent augmente entre les deux dernières
résolutions : aucun ordre positif n'est retenu pour cette grandeur ; le
transport advectif identiquement nul ne fournit pas d'ordre non plus.

L'écart relatif 50→25 ns vaut 0,0222 % pour le sensible et 0,0730 % pour le
limiteur. Malgré ces faibles différences, les ordres disparates et le latent
ne démontrent **pas de régime asymptotique commun**. L'intégrale du résidu
absolu normalisée par le laser passe de 3,77×10⁻⁷ à 7,67×10⁻⁷ puis
1,52×10⁻⁶ : elle n'est pas annoncée comme s'améliorant. Les colonnes sont
contre-vérifiées par la même somme indépendante que F58.

**Décision :** arrêter le raffinement temporel seul comme remède au plafond.
Les étapes encore utiles sont le contrôle spatial et la vérification/calibration
physique de la source et du bain. Ni la baisse du pas, ni le bon retour
processus ne libèrent la fabrication.

### Raffinement spatial exécuté ensuite : 460 800 cellules

Le 8 septembre, la grille a été divisée par deux dans chaque direction à
25 ns inchangés. Les 4 800 pas atteignent 120 µs en 1 282,135 s sur Kali,
sans location Vast. Le [rapport spatial et ses preuves](M64_F58_SPATIAL_REFINEMENT_20260908.md)
distinguent sortie native 0, refus strict du lanceur causé par quatre
métadonnées ajoutées, et contre-vérification séparée des entrées conservées.

Le puits artificiel passe de 3,329043 à 2,964055 mJ, soit de 10,54754 % à
9,30932 % de l'énergie absorbée. **Le plafond reste atteint : le raffinement
spatial seul n'a pas résolu le défaut physique.** Deux maillages ne donnent
pas un ordre de convergence ; deux parseurs des mêmes journaux ne sont pas
deux modèles physiques indépendants. La vérification des propriétés, de la
source et de la physique du bain, puis leur calibration, restent nécessaires.

Sources : [théorie AdditiveFOAM](https://ornl.github.io/AdditiveFOAM/docs/theory/),
[conditions aux limites](https://ornl.github.io/AdditiveFOAM/docs/boundary-conditions/),
[calibration ORNL](https://ornl.github.io/AdditiveFOAM/docs/heat-source-calibration/).

Le calcul global de construction vient **après** : histoire de dépôt, supports,
contacts plateau, plasticité/relaxation à chaud, détachement, traitement et
usinage. Il doit produire distorsion et contraintes avec convergence vérifiée.
Une animation de couches ou un rendu Omniverse ne démontre aucune de ces
propriétés. À cette date, aucune de ces branches ne libère fabrication ou
démarrage moteur.
