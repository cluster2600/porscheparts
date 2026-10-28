# Support moteur 993 Turbo — reprise avec la chaîne de contrôle, 16 octobre 2026

La géométrie provisoire **V6f est conservée**. Le nouveau bilan énergétique passe
sur ses douze cas linéaires archivés ; le contrôle géométrique DfAM strict la
rejette. **La pièce n'est pas livrable pour fabrication fonctionnelle** : ses
interfaces Porsche restent non mesurées, la convergence mécanique n'est pas
établie et aucun procédé d'impression complet n'est qualifié pour elle.

Le livrable de cette reprise est un dossier numérique reproductible :
[résultats et empreintes](../../parts/993-eng-carrier-0001/source/revalidation-20261016/results.json),
[audit énergétique](../../parts/993-eng-carrier-0001/source/revalidation-20261016/audit_energy.py),
[contrôle DfAM](../../parts/993-eng-carrier-0001/source/revalidation-20261016/dfam/assessment.json),
et le [STEP V6f inchangé](../../parts/993-eng-carrier-0001/derived/correction-20261013/carrier.step).
Le maître F0 du catalogue n'est pas remplacé par cette étude.

## Identité et périmètre

Référence **993 115 021 53, 993 Turbo**, distincte du support intermédiaire
993 115 103 52. Le STEP sélectionné a l'empreinte SHA-256
`834cc01a69c8205d854c611f7a8b7c2b6192687d547191deabbd25fe5c74049f`.
Son volume intégré est de 268 853,113 mm³ et sa masse nominale de 1,188331 kg
avec la densité de référence 4,42 g/cm³. Les axes, l'entraxe central 100 × 40 mm
et la portée de 8 mm restent des **hypothèses d'étude**.

Les fichiers bruts du dernier calcul ont été retrouvés et leurs identités
recoupées avec l'inventaire déjà publié. Aucune nouvelle résolution mécanique,
réparation, suppression de face positive ou modification du STEP n'a été faite.
Le STL contrôlé conserve exactement les coordonnées et l'orientation des
33 634 triangles de la surface V6f archivée.

## Contrôles réellement exécutés sur V6f

| Contrôle | Résultat | Ce que cela établit |
| --- | --- | --- |
| Énergie interne solide + ressorts, comparée à ½ F·u | 12/12 cas ; écart relatif maximal 3,334 × 10⁻⁸, seuil fixé à 10⁻⁴ | Cohérence énergétique du modèle linéaire archivé |
| Topologie de surface | 1 composante ; 0 bord ouvert, arête non manifold, orientation incohérente ou triangle dégénéré | Surface fermée cohérente |
| Auto-intersections, libigl 2.6.3 | 0 paire détectée | Contrôle indépendant de cette surface triangulée |
| Triangles effilés, critère strict | **74**, contre 0 admis | Maillage rejeté par ce critère ; ce n'est pas une mesure de résistance |
| Épaisseur par rayons, seuil exploratoire 1,5 mm | **54,994 %** de l'aire sous le seuil ; p01 et p05 = **1,300 mm** | Échec du criblage choisi, pas d'un critère fournisseur qualifié |
| Cavités fermées, grille de parité 0,3 mm | Aucun volume enfermé détecté | Résultat limité à cette résolution ; évacuation réelle de poudre non démontrée |

L'audit énergétique réintègre σ:ε/2 aux quatre points de Gauss de chaque
tétraèdre C3D10 affine, avec les six composantes de contrainte, le E et le ν
du jeu de données. Il ajoute ½ k u² pour les ressorts et vérifie les identités
des éléments, points d'intégration, nœuds, chargements et fichiers.
Les [dix cas mesh-9](../../parts/993-eng-carrier-0001/source/revalidation-20261016/energy-mesh-9.json)
et [deux cas mesh-7](../../parts/993-eng-carrier-0001/source/revalidation-20261016/energy-mesh-7.json)
sont conservés séparément. Le seuil de 10⁻⁴ a été fixé avant l'évaluation ;
les contraintes et déplacements imprimés ont sept chiffres significatifs.
Les tétraèdres courbes, cas non linéaires et cas thermiques sont refusés.
Six tests couvrent des énergies analytiques, les ressorts et les entrées corrompues.

DfAM strict-v3 et son contrôle libigl ont exécuté leurs tests témoins avant le
support. Le calcul du support a duré 50,46 s, puis 0,71 s pour le contrôle
d'intersections, sans dépassement des plafonds de 4 Gio, deux CPU et 600 s.
Les [empreintes des logiciels](../../parts/993-eng-carrier-0001/source/revalidation-20261016/dfam/runtime-provenance.json)
et les sorties texte sont conservées. Le seuil de 1,5 mm doit être remplacé
par un critère justifié par le procédé retenu avant toute décision industrielle.

## Ce qui empêche encore la validation

Les [résultats structurels antérieurs](../../parts/993-eng-carrier-0001/source/bionic-20261011/correction-20261013/README.md)
restent rejetés : sous −4 kN suivant Z et 850 N·m autour de Y du modèle,
le raffinement fait passer le pic de 740,86 à 800,63 MPa. Avec les appuis
supposés de 1 000 N/mm par extrémité, le maillage fin atteint 2 082,84 MPa
dans le modèle élastique. Aucun admissible LPBF ni comportement après
plastification n'est établi. Le bilan énergétique réussi ne résout ni cette
sensibilité aux appuis ni l'absence de convergence, de contact ou de précharge.
Les chiffres de l'étude historique R9 utilisent d'autres charges et axes.

La [nouvelle vérification Adamantine](LPBF_NATIVE_VERIFICATION_20261015.md)
établit le bon export des contraintes et un témoin thermoélastique à un élément.
Elle ne fournit pas encore une simulation calibrée de dépôt, fusion,
plasticité, refroidissement, supports et découpe de ce support moteur.
Les anciens contours à 60 µm et le contrôle de contraction uniforme V6f
ne deviennent pas une telle simulation par transfert de ces résultats.

## Recherche publique vérifiée le 16 octobre 2026

Le [PET officiel Porsche](https://files.porsche.com/f/332100/cfbfd366e3/kat017-e-911-98-katalog.pdf),
groupe 109-00, pages PDF 115–116, confirme le berceau repère 17, le support
intermédiaire repère 18, quatre M10 × 20 et quatre écrous M10, deux silentblocs
et quatre M8 × 40 vers la caisse. Il ne cote pas les entraxes, axes, surfaces
de référence ou tolérances. La recherche ciblée sur les références 53/54,
plans, scans et STEP/STL n'a identifié aucun modèle exact avec métrologie et
licence réutilisable. C'est une recherche bornée, pas une preuve d'absence.

| Piste industrielle | Donnée publique | Point encore à confirmer |
| --- | --- | --- |
| [BLT S600](https://www.xa-blt.com/en/product/blt-s600/?solution=45) | 650 × 650 × 850 mm, alliages titane ; [fabrication BLT](https://www.xa-blt.com/en/aerospace/) avec Grade 5, usinage, traitements et essais | Procédé Grade 5 sur cette machine et acceptation de ce support |
| [Nikon NXG XII 600](https://nikon-slm-solutions.com/slm-systems/nxg-xii-600/) | 600 × 600 × 600 mm ; [fiche matière de novembre 2025](https://nikon-slm-solutions.com/wp-content/uploads/2025/11/mds5137.pdf), page 10, Ti6Al4V Grade 23 ELI à 60 µm | Route Grade 5 distincte ; les propriétés Grade 23 ne sont pas transférées |
| [AMEXCI](https://amexci.com/services/metal-3d-printing) | NXG XII 600 et Ti64 dans son offre | Association Ti64/NXG600 et Grade 5 non établie publiquement ; [communiqué Nikon](https://nikon-slm-solutions.com/newsroom/amexci-and-nikon-slm-solutions-strengthen-their-collaboration-in-the-nordics-with-am-technology/) attribuant explicitement le titane au SLM500 |

L'encombrement V6f à plat avec la rotation de 45° dans le plan et les marges
supposées demande un plateau carré d'au moins **471,134 mm**. Les grandes
machines ci-dessus sont des pistes d'enveloppe, sans réservation ni validation
du travail. Aucun fournisseur n'a été contacté, aucun fichier transmis.

## Suite nécessaire pour obtenir une pièce fonctionnelle livrable

1. Relever le berceau exact avec son support intermédiaire et ses silentblocs :
   centres, axes, portées, datums, tolérances, empilement des vis et encombrement.
   Le [plan de mesure existant](../../parts/993-eng-carrier-0001/evidence/measurement-plan.md)
   fournit le point de départ.
2. Figer les charges, la raideur des appuis et le modèle contact/précharge ;
   reprendre ensuite la géométrie et établir la convergence mécanique.
3. Choisir un fabricant et son procédé exact : alliage, orientation à plat,
   supports accessibles, dépoudrage, paramètres, traitements, surépaisseurs
   d'usinage et contrôle. Calibrer la simulation de construction sur ce procédé.
4. Faire approuver les critères et le plan d'essais, puis contrôler le prototype
   et réaliser les essais de charge/fatigue représentatifs avec revue compétente.

La remise actuelle est donc **une reprise vérifiée du dossier d'étude**.
Elle ne constitue ni un fichier machine, ni une autorisation de fabrication,
ni une validation de montage ou de durée de vie.

## Reproduction et vérification du dépôt

Avec les données brutes archivées et NumPy, le nouveau contrôle s'exécute ainsi,
en donnant un répertoire de sortie neuf pour chaque maillage :

```sh
python3 parts/993-eng-carrier-0001/source/revalidation-20261016/audit_energy.py "$RAW/v6f/mesh-9" "$NEW_OUTPUT"
```

Les **16 tests ciblés** de correction V6f et d'audit énergétique passent dans
le conteneur scientifique existant, avec les trois tests de surface exécutés.
Les dix tests de génération des pages passent également. Schémas, catalogue,
pages générées, index des rapports et liens stricts sont vérifiés.

Une réexécution supplémentaire de l'ancien inspecteur CAO sous émulation a été
arrêtée à 604,8 s après dépassement de son budget de 600 s, sans rapport final.
Ses sorties partielles restent dans le dossier de travail et n'apportent aucune
preuve nouvelle. Les résultats d'interface déjà archivés restent historiques.

Le lancement local de `make check` sur la base de cette reprise n'est **pas
vert** : 3 979 tests, deux échecs de comparaison exacte de flottants dans les
tests inchangés de turbine WE43/stator AlSi10Mg, 27 erreurs liées à SciPy
PROPACK/Python 3.10, et 254 tests ignorés. Ces problèmes ne sont pas corrigés
dans cette reprise. Aucune CI distante, fusion ou publication n'est revendiquée.
