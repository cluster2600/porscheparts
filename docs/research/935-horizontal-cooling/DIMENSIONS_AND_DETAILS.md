# Cotes et détails : 993 verticale et système 935 horizontal

Relevé documentaire du 3 octobre 2026. Le [registre des cotes](dimensions.json)
sépare les données Porsche, les champs commerciaux et les inconnues. Aucune
valeur publiée ci-dessous ne calibre actuellement les deux scans 935.

## Recherche allemande, anglaise et française

Les recherches utilisent `Gebläserad`, `Flachgebläse`, `Gebläseantrieb`,
`liegendes Kühlgebläse`, `Luftführung`, `flat fan`, `fan drive`, `air guide`,
« ventilateur horizontal », « entraînement », « renvoi d'angle » et
« fiche d'homologation ». On décrit toujours séparément le plan du rotor et
son axe : pour notre projet 935, plan horizontal et axe vertical. Un mot
« vertical » isolé dans une annonce n'identifie pas cette orientation.

Le corpus [993 existant](../../../twins/993-engine-cooling-fan-system-f0/program/research/README.md)
contient déjà les recherches OEM et fournisseurs. Ses fichiers de provenance
restent intacts. Les références utiles sont revérifiées dans leurs sources
primaires ; les dimensions d'une 993 ne sont pas transférées à une 935.

## Ce que la FIA fournit effectivement

La [fiche n°645, Groupe 4](https://historicdb.fia.com/sites/default/files/car_attachment/1613059201/homologation_form_number_645_group_4.pdf)
de la Porsche Turbo a été téléchargée et ses **neuf pages examinées**.
La rubrique 10 indique le refroidissement par air. Les photos moteur H–J
de la page PDF 6 montrent le ventilateur de base dans un plan vertical.
L'extension 1/1V, pages 8–9, concerne notamment tableau de bord, freinage,
moyeux, guidages d'essieux et réservoir. Aucun plan coté du rotor horizontal,
du support ou du renvoi d'angle 935 n'a été trouvé dans ces neuf pages.
Le PDF indique une validité au 1 janvier 1976 ; l'index web affiche le
2 janvier. Pour une date historique précise, conserver cette divergence.

Le [PDF n°3076, Groupe 3](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf)
a été téléchargé, ses 28 pages et huit extensions examinées le 6 octobre.
La page PDF 9, rubriques 148–149, donne **245 mm, 11 pales et alliage léger**.
Les photos I–J de la page 6 montrent le ventilateur vertical de base.
Cette donnée ne calibre pas notre rotor horizontal à neuf régions de pales.
Les extensions, pages 17–28, ne contiennent pas de plan de fabrication du
renvoi horizontal dans cet exemplaire. Son SHA-256 et les localisateurs sont
conservés dans le registre des sources ; le PDF reste dans le cache privé.
Ce contrôle ne prouve pas l'absence de documents utiles dans le reste de
l'archive FIA. L'exemplaire transféré en Groupe B reste une autre source.

L'[Annexe J 1976, articles 268–269](https://argent.fia.com/web/fia-public.nsf/ABCF4550D7659360C12574A5003C6CA0/$FILE/Hist_App_J_76_Art_269_a.pdf)
définit le Groupe 5 à partir des voitures reconnues en Groupes 1–4 et laisse
libres les autres éléments mécaniques selon l'article 269(d), sous ses
conditions. **Inférence documentaire :** une fiche de la voiture de base
peut donc être utile sans contenir les plans de fabrication du montage
935 utilisé en course. Ces documents réglementaires ne spécifient ni nos
cotes d'interface ni les performances de notre pièce.

La recherche interactive FIA a rencontré une erreur HTTP 403. Les pages
indexées et le téléchargement direct du PDF 645 sont accessibles ; l'archive
complète n'a pas été parcourue. Ce résultat ne prouve pas l'absence de toute
autre documentation FIA pertinente.

## 993 : premières cotes et références recoupées

Le [PET Porsche allemand](https://files.porsche.com/f/332100/db8e7dba1c/kat017-d-911-98-katalog.pdf),
planche 105-00, pages PDF 78–79, distingue notamment :

| Élément | Variante/référence | Donnée documentaire |
|---|---|---|
| Rotor Turbo M64.60 | `96410601521` / `96410601522` | Application PET ; dessin non coté |
| Rotor Carrera standard | `96410601531` | Application distincte de la Turbo |
| Rotor RS M64.20 | `96410601540` | Application distincte ; moyeu `99310605180` |
| Carter Turbo M64.60 | `99310666750` | Ne pas substituer le carter Carrera sans vérifier |
| Courroie position 13, Turbo | `99919234350` | Désignation nominale 9,5 × 760 mm |
| Courroies position 14, Turbo | `99919237350` / `99919237250` | 9,5 × 753 / 9,5 × 757 mm ; renvoi TI 7/97 pour `.37350`, contenu non lu |
| Courroie position 13, Carrera | `99919233850` | 9,5 × 776 mm |
| Cales position 16 | `96410626830` / `96410626832` | Épaisseurs 0,5 / 0,7 mm, selon application PET |

Pour le rotor `96410601522`, [FVD](https://www.fvd.net/en-us/shop/engine-cooling-fan-alternator-impeller-965-993-turbo-993-gt2-96410601522~p252068)
publie **245 × 245 × 87 mm et 0,9 kg** dans ses champs commerciaux.
C'est un ordre de grandeur documenté pour cette référence Turbo/GT2,
sans datum, tolérance ou méthode de pesée. Ce n'est pas une mesure du
diamètre de pointe, de la masse du rotor nu ou d'une pièce 935.

## 935 : détails constructifs et cotes encore manquantes

Le [relevé des matières](MATERIALS.md) complète cette section : Jim Torres
décrit les carters métalliques usine en magnésium, puis ses reproductions en
aluminium. Cette observation concerne les carters d'entraînement ; elle ne
donne pas la matière du rotor 935 du propriétaire.

[Jim Torres Racing](https://jimtorresracing.com/for-sale/reproduction-flat-fan)
décrit sa reproduction avec carters coulés en aluminium, rotor usiné en
aluminium 7075, arbre de distribution d'huile, boulon banjo long et conduite
d'alimentation. Alternateur et courroie sont exclus de l'ensemble annoncé.
Le fabricant rapporte un rodage/essai de 60–90 minutes, entre 2 000 et
8 500 tr/min ; l'arbre auquel cette vitesse se rapporte n'est pas explicité.
Ce protocole annoncé ne définit pas une vitesse maximale admissible.
Le diamètre, les tolérances, l'état métallurgique du 7075 et les plans de
dentures ne sont pas publiés. Ces informations ne qualifient pas la matière
de notre scan ni la compatibilité revendiquée avec toutes les pièces usine.

[EB Motorsport](https://eb-motorsport.com/shop/flat-fan-guibo/) catalogue
l'accouplement souple `0701403`, sans cotes ni raideur torsionnelle publiées.
Son emplacement exact sur le spécimen scanné reste à identifier.
Ses poulies de vilebrequin sont destinées aux configurations avec
alternateur séparé :

| Reproduction EB | Matière/finition annoncée | Champs commerciaux |
|---|---|---|
| [`0701504`](https://eb-motorsport.com/shop/rsr-turbo-to-935-crank-shaft-pulley/) | Usinée, passivation zinc jaune ; nuance non précisée | 0,58 kg ; 20 × 12 × 3 cm |
| [`0701505`](https://eb-motorsport.com/shop/rsr-turbo-to-935-crank-shaft-pulley-titanium/) | Titane grade 5 annoncé | 0,34 kg ; 20 × 12 × 3 cm |

Les tailles sont des champs commerciaux sans définition géométrique :
**20 cm n'est pas un diamètre primitif établi**. Les masses sont indicatives
selon le fabricant. Ces fiches ne fournissent pas le dossier de qualification
du titane, ni les interfaces exactes, ni la masse du système complet.

L'ensemble [Design911 `93510610300R/1`](https://www.design911.co.uk/p/fan-housing-with-fan-blades-porsche-935/)
associe un entonnoir/carter GRP à un ventilateur aluminium. Son diamètre
n'est pas annoncé sur la fiche lue. Le **225 mm** visible à proximité dans
une liste de produits concerne le `90110610300R/1` RSR/906/914, une autre
pièce : il ne faut pas l'affecter au rotor horizontal 935.

Pour notre système 935, restent inconnus : diamètre et hauteur du rotor,
géométrie des pales, alésage/moyeu, entraxes de fixation, axes et faces
d'appui du support, portées d'arbres/roulements, dentures/rapport, diamètre
primitif des poulies, jeux carter/rotor et détails de lubrification.
Le [contrat d'interfaces](../../../twins/935-horizontal-cooling-system-f0/interface-contract.json)
énumère les preuves à obtenir pour chacune de ces liaisons.

## Passage des documents aux cotes exploitables

Pour calibrer un OBJ, il faut une dimension de la **même pièce**, sur un
élément identifiable, avec unité, datum, tolérance et provenance. Une deuxième
dimension indépendante, dans une autre direction, vérifiera l'échelle et
les déformations du scan. Les raccordements doivent ensuite être mesurés
indépendamment : axe, portée, face, perçages et empilage. On ne calibre pas
un rotor par un diamètre pris sur une photo ou sur une autre référence.

Les prochaines sources à examiner sont les extensions FIA pertinentes,
les instructions/catalogues de la variante 935 identifiée et les documents
de fabrication ou relevés métrologiques du rotor et de l'entraînement.
Les pistes d'acquisition restent documentées ; aucun document payant n'a
été acheté et aucun fournisseur n'a été contacté.
