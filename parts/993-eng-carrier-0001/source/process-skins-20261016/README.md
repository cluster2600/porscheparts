# Préparation des supports de la révision ad12

Cette branche conserve le moteur de couches de pièce `process-coverage-20261016/build_pyslm.py` inchangé. Elle remplace la construction des enveloppes, des grilles et des peaux ; les anciens passages refusés restent des preuves historiques distinctes.

Le magasin mixte à sept enveloppes est maintenant lisible et transportable. Les checkpoints de surfaces et leurs graphes restent distincts de l’admission globale : un graphe accepté peut encore conserver une matière native que le contrôle exact de bande refuse. Les nouvelles générations v2 vérifient aussi ce prédicat avant réemploi. Le tranchage complet et l’audit des expositions doivent porter sur leurs résultats effectivement admis.

## Parcours courant

La [recette v5](../../../../manufacturing/workflows/993-carrier-lpbf-v5.json)
enchaîne 37 étapes avec 285 entrées épinglées. Sa
[revue](cold-v5-recipe-evidence/assessment.json) porte sur les identités et les
commandes ; les résultats de la campagne réelle restent séparés.
Les CLI courantes sont `generate_prism_region_v6.py` et
`generate_legacy_region_v6.py`, puis `build_cached_v5.py` avec les six contrôles
de `admissions_v3.py`. Les arguments restent ceux des variantes détaillées
ci-dessous.

La [construction combinatoire](README-combinatorial.md) garde le domaine libre
entier et ajoute uniquement des bandes de bord attestées. L’
[assemblage incrémental exact](README-incremental.md) conserve les mêmes
contours, décisions et reçus, en évitant les reconstructions complètes
répétées. Le générateur et l’admission chargent cette version depuis des
modules privés épinglés. Les tests et le benchmark de grande surface ne
remplacent pas les admissions et audits des sept régions effectivement livrées.

La [variante à bandes redondantes](redundant_strip_interfaces.py) traite le
cas d’une interface attestée qui borde une rentrée : elle omet son extension
uniquement si le quadrilatère entier est déjà contenu dans le domaine, avec
preuve exacte. Elle conserve les coordonnées, les rôles et le domaine source.
Les [tests dédiés](../../../../tests/test_carrier_redundant_strip_interfaces.py)
gardent aussi les refus de bandes partiellement extérieures. Le
[journal par surface](chart_progress.py) conserve les géométries d’entrée et de
sortie avec leurs reçus complets. Le préparateur choisit l’autorité enregistrée
dans chaque reçu ; les résultats antérieurs ne sont pas réétiquetés.

Les détails suivants conservent aussi les versions v1/v2 et leurs témoins
historiques ; la recette ci-dessus désigne les variantes à utiliser.

## Environnement

L’installateur versionné `../process-coverage-20261016/setup_pyslm.py` reconstruit un environnement isolé à partir des versions et du correctif épinglés. Les modules de ce dossier utilisent cet environnement sans modifier le code PySLM installé. Une réinstallation indépendante du même état a été exécutée dans `work/part-workflow/runtimes/pyslm-coverage-reproduced-012` ; le reçu `work/part-workflow/pyslm-reinstall-012-validation.json` compare les 37 versions et les 775 fichiers pertinents pour les couches de pièce.

Les installateurs natifs séparés sont `../native-pymesh-20261016/setup.py`, `../native-cgal-20261016/setup.py` et `../native-cgal-distance-20261016-v3/setup.py`. Ils produisent leurs reçus d’installation propres. Le calcul booléen garde les coordonnées exactes entre les opérations du même arbre CSG ; l’export final IEEE est ensuite contrôlé séparément. Les différences de versions, paramètres, entrées ou reçus sont des motifs de refus.

## Entrées et admissions

`prepare_exact_envelopes_v2.py STL OUTPUT --identity-receipt MESHING.json --reduce-horizontal` exporte le corps dans sa pose de fabrication, chaque chaîne de prismes, chaque toit positif original et chaque masque XY requis. `--sha256 SHA` est l’alternative exclusive pour une entrée déjà gelée. Le manifeste nouveau est `inputs-v2.json` ; le manifeste historique `inputs.json` reste séparé. La réduction des nappes strictement horizontales conserve les frontières et les coordonnées sources. La soustraction porte sur le corps complet ; les intervalles libres superposés ne sont pas remplacés par une hauteur maximale.

La CLI native par région est `run_native_envelope_case.py INPUTS/inputs-v2.json CASES/source-NNN --source-index N --runtime NATIVE_RUNTIME.json`. Elle distingue les deux cas à prismes positifs 0/2 et les cinq arbres CSG historiques 1/3/8/9/10, avec leurs ordres d’opérations explicites. Son terminal `case.json` n’a le statut `executed` que si les gates propres au cas et la fermeture des scopes sont acquises. `seal_envelopes_v2.py INPUTS/inputs-v2.json CASES CASES STORE` consomme ces terminaux et conserve les preuves natives avec des noms uniques et des références relatives. Le troisième argument peut aussi être un manifeste historique explicite des deux cas à prismes.

Après les calculs natifs, `audit_envelope_case.py` contrôle le maillage IEEE final avec le détecteur indépendant puis le classifieur rationnel des contacts. `seal_envelopes.py INPUTS.json CASES OUTPUT` réunit les entrées, les sept résultats et leurs preuves dans un magasin autonome. Un champ `status: passed` sans reçus liés au hash exact du maillage ne suffit pas.

Le prototype local non versionné `run_native_envelopes.py` n’est pas une entrée de la recette. Celle-ci utilise les sept étapes bornées de `run_native_envelope_case.py`, puis un scellement distinct. La variante `../native-pymesh-clip-20261016/setup.py` soustrait le corps intersecté avec une boîte strictement englobante de la chaîne ; l’identité ensembliste est justifiée dans son reçu et les coordonnées exactes restent dans le même arbre. Ce préfiltrage ne découpe aucune portion utile du corps. Un échec conserve le journal et interdit le scellement final.

La [recette v2](../../../../manufacturing/workflows/993-carrier-lpbf-v2.json) contient 37 étapes et 211 entrées versionnées épinglées. Le [reçu de revue](cold-recipe-evidence/assessment.json) conserve le contrôle des empreintes, des 25 commandes après le préfixe CAO/calcul et de l’immuabilité des sorties. Les douze premiers objets d’étape et les 45 entrées de la recette initiale sont identiques. Cette revue ne prétend pas avoir exécuté les 37 étapes sur le carrier : les générations et les audits réels conservent leurs propres reçus. Le magasin réel complet à sept enveloppes existe ; il ne constitue pas à lui seul une admission des surfaces et trajectoires de supports.

Le magasin doit passer, pour chaque région : topologie fermée et orientée, zéro intersection hors du simplexe partagé, retour du noyau exact, filiation des faces complète et dérive bidirectionnelle sous la borne déclarée. La précision de réparation est fixée à 51 bits et cinq itérations ; la borne est calculée depuis les trois pas de grille natifs, sans marge supplémentaire. Un résultat partiel ou un retour `false` reste refusé.

## Feuilles et trajectoires

`peripheral_skins.py` utilise les vraies parois verticales des enveloppes. Le dépliage sépare les jonctions des chemins XY avant l’infill et la denture natifs, puis remappe chaque morceau sans raccourcir les coins. `grid_intervals.py` contrôle les triangles entiers des grilles dans les vraies sections libres et dans la bande de pénétration verticale déclarée des dents. Les supports sont des feuilles et des trajectoires ; aucun volume plein n’est attribué à ces surfaces ouvertes.

Chaque composante de matière possède un identifiant, un intervalle de faces, sa WKB et ses interfaces sources. `../process-scanpath-audit-20261016/exact_contacts_both.py` calcule l’intersection des interfaces sources avec le domaine libre et la matière, en arithmétique rationnelle sur les coordonnées IEEE. Les fractions restent exactes jusqu’à un encodage final unique. Les WKB et SHA du domaine libre et du matériau accompagnent chaque contact et groupe de faces. Les diagnostics GEOS sont conservés séparément. Une composante sans contact propre doit obtenir une preuve de liaison réelle en 3D ; une projection, une boîte englobante ou un point de contact ne l’établit pas.

L’option `--solid-sheets` de `diagnose_support.py` et `build_cached.py` demande le mode natif PySLM `generateTrussGrid=False` : feuilles sans perforations de treillis, avec la préparation native des dents. Le petit adaptateur `solid_sheets.py` convertit les chemins renvoyés par ce mode en son objet PolyTree natif. Il ne remplit pas les espaces entre feuilles et ne leur attribue aucune épaisseur volumique. Les mêmes contrôles de contacts, de connexion 3D et d’exposition restent obligatoires. Le témoin boîte passe. Le deuxième essai réel sur la grande région droite a généré 105 712 faces et 946 groupes en 321 s ; son graphe refuse encore quatorze groupes isolés, représentant 1,028245 mm² intrinsèques. Tous les quatorze ont une exposition positive sur le calendrier réel et restent donc requis. Le contre natif sans dents sert seulement à diagnostiquer la fragmentation ; aucune nouvelle stratégie n’est admise par ce résultat.

La stratégie distincte `--solid-sheets --continuous-interfaces` reconstruit un intervalle lorsque sa denture native fragmente la matière ou manque un contact requis. Elle conserve son domaine libre connecté D entier et ajoute seulement des balayages verticaux de ses interfaces attestées, limités à la pénétration déclarée de 0,2 mm et à Z ≥ 0. Un recouvrement qui joindrait deux intervalles libres distincts est refusé. C’est une **nouvelle construction**, avec les aires natives ajoutées et retirées déclarées ; ce n’est pas une normalisation identique à la matière dentée. Des fragments natifs hors des vraies bandes peuvent ainsi disparaître. Les contacts continus augmentent la surface à détacher et restent identifiés dans chaque reçu. Le témoin natif de toit horizontal passe aux plans réels de 60 µm, avec contact exposé à Z = 1,05 mm grâce à la pénétration jusqu’à Z = 1,2 mm. La région réelle conserve son statut de diagnostic jusqu’aux mêmes admissions et à l’audit complet d’exposition.

Les arêtes horizontales plus courtes qu’un cycle, que PySLM conserve sans dents, peuvent perdre leur contact après quantification Clipper. `quantized_contacts.py` restaure uniquement une arête existante à son Z source identifié, sous la demi-maille native mesurée ; il conserve le déplacement et les coordonnées avant/après dans le reçu. Les contours que le mode natif de bord plein efface sous sa maille sont conservés dans leurs coordonnées sources exactes, avec décision explicite.

Une carte n’est exclue du support que si `layer_schedule.py` démontre une section vide ou ponctuelle sur chaque vrai plan d’exposition concerné. Il n’existe aucun seuil d’aire ou de hauteur pour cette décision. Le reçu conserve les faces, l’aire, les bornes, le SHA du calendrier et les couches voisines ; l’enveloppe source reste entière. Le compte vérifié est `expected = generated + explicit_excluded`, et l’admission recalcule ces preuves depuis le maillage source. Les groupes effectivement générés doivent ensuite tous apparaître dans l’audit d’exposition.

Un triangle encodé d’aire rationnelle exactement nulle ne peut être retiré qu’après preuve de couverture de son segment ou de son point entier par les triangles non nuls de la même composante. `exact_zero_face_coverage.py` conserve les témoins rationnels ; aucun triangle d’aire 3D positive n’est retiré. Cette normalisation de l’ensemble IEEE ne constitue pas une preuve de conservation d’une aire intrinsèque qui se serait déjà effondrée au remappage.

La construction continue prouve l’inclusion fermée D ⊆ matière ⊆ bande sur les coordonnées IEEE traitées comme fractions exactes. Un trou produit par l’overlay n’est retiré que si son domaine entier est certifié dans l’union intentionnelle D + balayages et dans la bande autorisée ; ses coordonnées extérieures et les autres trous restent identiques. Le prévol de 33 unités modifiées passe ces inclusions. Le contrôle des 662 résultats finaux retrouve exactement les frontières normalisées des composantes individuelles, sans nouveau pont. Les reçus compacts versionnés sont `continuous-verification.json` et `continuous-union-verification.json` ; ils ne constituent pas une admission de la pièce entière.

Le contrôle nouveau de `continuous_prism_interfaces.py` utilise `exact_band_union_v2.py`, les primitives du helper gelé `exact_band_union.py` et la soustraction convexe rationnelle `exact_convex_union.py`. Il certifie la même union intentionnelle des triangles balayés verticalement, avant son overlay GEOS. Les triangles orientés positifs doivent reproduire exactement la chaîne de frontière et l’aire source. Chaque triangle de matière doit ensuite être couvert par l’union fermée ; le premier reste positif donne un témoin de refus, jamais un PASS partiel. Les primitives, la pénétration de 0,2 mm et le clipping Z ≥ 0 restent explicites.

Cette version reconstruit également un natif dont cette preuve de confinement échoue, avec la raison `native_material_not_confined_to_intended_band`. Le nom hérité de la stratégie contient encore `only_for_native_fragmented_intervals` ; les raisons et les preuves par intervalle décrivent sa portée étendue. Les écarts GEOS restent des diagnostics, sans seuil d’aire utilisé pour accepter un résidu. Les domaines, la matière exportée et les reçus rationnels sont liés par WKB et SHA ; l’admission recalcule la preuve depuis ces polygones. Les six autres critères et l’audit des couches restent indépendants.

`region_checkpoints.py` conserve une région réussie avec les identités de la pièce posée, de l’enveloppe, des interfaces attestées, des paramètres, du calendrier, des sources et du runtime avant/après. Le chargeur `PreparedRegion(directory).geometry(block)` refuse une différence et contrôle à nouveau les trois fichiers et le reçu avant/après chargement et réutilisation. Le statut `region_geometry_completed_no_global_admission` ne remplace aucun des six contrôles globaux.

`collect_prepared_regions.py STORE REGIONS PREPARED.json` exige les sept `REGIONS/source-NNN/region-checkpoint.json` réussis et lie leur ordre au SHA du magasin. Les chemins relatifs sont résolus depuis le manifeste. `build_cached.py STL OUTPUT --identity-receipt MESHING.json --envelopes STORE --part-cache CACHE --region-checkpoints PREPARED.json --solid-sheets --continuous-interfaces` assemble les régions, puis produit six reçus séparés : enveloppes, régions, peaux, grilles, contacts et collisions. `--supports-only` sépare ce scellement du calcul des couches ; un nouvel appel avec `--reuse-support-stage SUPPORTS` vérifie ce checkpoint et son manifeste préparé exact avant de trancher. `admissions_v2.py` ajoute les inclusions rationnelles, leur liaison aux matériaux réellement exportés et le refus d’une région sans stratégie continue explicite. Le cache de pièce doit être complet et compatible avec les mêmes paramètres, pose et sources ; ses tableaux sont relus sans recalcul de hachures.

Le hook de coupe exact des supports reste distinct du moteur de pièce. L’audit indépendant complet `../process-scanpath-audit-20261016/audit_complete_supports_hybrid.py PROCESS AUDIT --source-stl STL --part-cache CACHE` doit ensuite contrôler toutes les couches enregistrées, le confinement des segments entiers et les contacts effectivement exposés, avec les intersections de contact rationnelles jusqu’à la section réelle de pièce. Il charge le magasin hybride depuis les sources exactes du résultat. Son reçu et le sous-reçu de trajectoires doivent porter `rational_part_contact_intersections=true` et `hybrid_envelope_store_verified=true` ; la couverture doit aussi porter `every_material_group_exposed=true`. Les six admissions géométriques ne remplacent pas ce dernier reçu.

## Diagnostics et témoins

`diagnose_support.py PART.npz VOLUME.npz INPUTS.json OUTPUT --source-index N --solid-sheets --continuous-interfaces` fige ses sources et génère une seule région réelle. Son statut conserve explicitement les contacts non prouvés ; cette commande ne crée pas une admission de fabrication. Elle scelle un checkpoint réutilisable uniquement si le graphe matériel réel est accepté et si toutes les identités sont restées inchangées. Cette CLI actuelle décode les anciens cas CSGTree ; l’adaptateur des deux nouveaux cas à prismes positifs est distinct.

Les nouveaux générateurs sont `generate_legacy_region_v2.py PART VOLUME INPUTS OUTPUT --source-index N --solid-sheets --continuous-interfaces` pour les cas CSGTree et `generate_prism_region_v2.py PART NATIVE_AUDIT ROOFS INPUTS OUTPUT --source-index N` pour les prismes. Le second reçoit le paquet natif original, où `local-evidence-map.json` est le frère du reçu ; les neuf faces réparées de la gauche conservent leur statut d’interface inconnue. Les deux CLI figent les sources supplémentaires et leur hook, contrôlent leurs hashes avant/après, et retournent un échec sans checkpoint réellement réussi. Les sorties sont compactées par sérialisation seulement, sans suppression de champs mathématiques.

Les témoins comprennent une boîte, une ouverture intérieure, deux intervalles Z séparés, une surface à plusieurs hauteurs au même XY, un segment traversant un trou et un îlot de matériau flottant. Les tests se trouvent dans `tests/test_carrier_skin_geometry_20261016.py`. Chaque refus réel est conservé dans un nouveau dossier ; aucun reçu refusé n’est réécrit pour prendre le statut d’un passage ultérieur.
