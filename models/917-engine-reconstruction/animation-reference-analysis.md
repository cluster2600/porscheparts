# Analyse de l'animation mécanique 917

Analyse du 12 octobre 2026 de la [deuxième vidéo fournie](https://www.youtube.com/watch?v=j3CkVwtOPX4),
complémentaire de l'[analyse du moteur filmé](video-reference-analysis.md).
Cette référence apporte une lecture du mécanisme en coupe et une différence
importante avec notre montage : les grandes roues des arbres à cames visibles
sont situées vers leur milieu, tandis que notre [distribution candidate](cam-drive/README.md)
place ses trains dans les plans X = 400 et 424 mm, en bout de moteur.
Cette différence doit être instruite avant de figer l'architecture des carters.

## Nature de la source

- Titre : « PORSCHE 917 ENGINE ANIMATION » ; auteur indiqué : `mwp917` ;
  publication indiquée par YouTube : 7 août 2009.
- L'auteur décrit un modèle SolidWorks rendu avec PhotoView 360 et une séquence
  répétée. Il s'agit d'une visualisation de CAO, sans preuve fournie ici que les
  formes, le calage et les interfaces reproduisent une variante Porsche exacte.
- Copie examinée : 900 × 720 pixels, 24 images/s, durée de 30 s.
  SHA-256 : `fb40259ed5f666dde5027bc3944fe4ea4647400dc5bb0dfecaad837bac9ebd42`.
- Une planche de repérage puis neuf images ponctuelles à 1, 3, 5, 7, 10, 15, 20,
  25 et 29 s ont été examinées. La caméra conserve le même point de vue ; ces
  images donnent des positions différentes du mécanisme, pas des vues de faces
  supplémentaires. Aucun régime réel ni diagramme de distribution n'est déduit.
- Extraction : `ffmpeg -ss 3 -i video.mp4 -frames:v 1 frame-003.png`, en
  remplaçant la seconde. Les fichiers de consultation restent dans `/tmp/`.
- Licence du modèle, droits de dérivation géométrique et de republication des
  images inconnus. Aucun modèle SolidWorks, maillage ou pixel externe n'est
  ajouté au dépôt. L'analyse n'extrait aucune cote de cette animation.

## Ce que montrent les images

| Repères | Observation | Apport pour notre reconstruction ; limite |
|---|---|---|
| [00:01](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=1s), [00:03](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=3s), [00:05](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=5s) | Sur le côté ouvert, pistons, bielles et parties du vilebrequin sont dégagés. Les positions des pistons et bielles changent entre les images. Les pistons comportent des gorges périphériques ; les arbres montrent des masses et des raccordements profilés. | La lecture mécanique repose sur les interfaces entre pièces et leurs mouvements, et exige plus que des cylindres et disques génériques. Revoir les volumes de bielles, masses de vilebrequin, paliers et logements à partir des sources mesurées. La perspective ne permet pas de compter tous les manetons, de mesurer les congés ou de confirmer l'appariement des bielles de l'autre banc. |
| [00:03](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=3s), [00:07](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=7s) | Deux arbres longs et parallèles sont visibles à l'extérieur du banc ouvert. Ils portent des lobes répétés et de grandes roues proches de leur milieu ; plusieurs roues intermédiaires sont regroupées dans la même région. | Étudier une distribution alimentée dans la région centrale, compatible avec nos axes de cames 4V. L'animation ne prouve ni la topologie complète du train, ni ses rapports, ni la position axiale mesurée, ni l'engrènement sans collision. Les arbres sont présentés hors de leur enveloppe : ne pas copier leur écart apparent comme une cote de montage. |
| [00:01](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=1s), [00:15](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=15s), [00:29](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=29s) | Des organes à tiges et ressorts se trouvent près des deux lignes de cames. Leur position et celle des lobes évoluent. | Identifier explicitement came, élément de transmission, soupape, guide, ressort et siège dans notre modèle. Une image ne permet pas de valider les contacts, les levées ou le nombre total de soupapes par cylindre. Cette référence ne valide pas nos 48 soupapes ni les lois déjà choisies sous hypothèses. |
| Toutes les images | Une rangée de six trompettes verticales à lèvres arrondies est visible sur le côté conservé. Aucun ensemble turbo ni conduit de suralimentation n'est montré. | Référence utile pour l'organisation répétée des admissions et leurs bases. Elle ne définit pas un circuit biturbo ; nos collecteurs fermés devront garder leurs interfaces et faire l'objet de contrôles de débit et de pression. L'autre rangée et la variante exacte ne peuvent pas être déduites de ce seul côté. |
| [00:01](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=1s), [00:07](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=7s), [00:25](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=25s) | Une roue à pales de plan horizontal occupe la partie haute centrale et change de position angulaire. Elle est entourée d'un volume profilé ; deux corps à têtes orange, semblables à des distributeurs, sont également visibles. | Concevoir le ventilateur avec son enveloppe, ses réserves, son entraînement et sa fixation. Les deux organes orange donnent une référence d'implantation de l'allumage, sans identifier leurs internes. Débit d'air, rapport d'entraînement, refroidissement et commandes électriques restent inconnus. |
| Toutes les images | Sur le côté conservé : carter profilé longitudinal, corps à fines ailettes et petits raccords en façade ; sur le côté ouvert : enveloppes absentes pour rendre le mécanisme lisible. | Les trous et parties ouvertes de la coupe servent à expliquer le mécanisme ; ils ne doivent pas devenir des ouvertures de nos solides imprimables. Le corps à ailettes ne peut pas être qualifié comme échangeur fonctionnel par son apparence. |

## Différences à instruire dans PicoGK

1. **Architecture de distribution avant l'habillage.** Comparer l'alimentation
   centrale suggérée par l'animation avec les quatre trains actuels en bout.
   Notre modèle possède déjà une pièce nommée `central_output_gear` dans
   l'[assemblage](assembly/README.md) : la sortie centrale de puissance et
   l'entraînement des cames sont deux questions distinctes. La présence de cette
   pièce ne valide pas nos nouveaux trains de distribution. Relever la position
   et le rôle des roues sur une source mécanique indépendante, puis reconstruire
   les trajets avec les axes des culasses 4V conservés.
2. **Mécanisme inspectable.** Produire à partir de nos propres solides une vue
   complète et une vue en coupe cohérentes, aux mêmes poses. Une coupe virtuelle
   du rendu doit conserver les solides de fabrication intacts. Les phases de
   vilebrequin, de bielles, de cames et de soupapes doivent venir de notre contrat,
   avec contrôle des jeux sur le cycle ; la vidéo ne fournit pas ce contrat.
3. **Carters et entraînements intégrés.** Définir volumes des paliers, logements,
   accès et réserves autour du mécanisme retenu, avant de remplacer les capots
   cubiques. Le raccordement du ventilateur, des accessoires et des circuits de
   lubrification reste à compléter avec des interfaces identifiées.
4. **Bionique avec fonction explicite.** Les supports et transitions de canaux
   peuvent réutiliser les fonctions PicoGK existantes. Les arbres, bielles et
   dentures demandent des calculs de fatigue, lubrification et finition avant
   tout allègement. Les roues percées de cette CAO ne constituent pas une preuve
   d'optimisation ni d'aptitude à l'impression métallique.

## Relation avec la première vidéo

| Première référence : moteur filmé | Deuxième référence : animation |
|---|---|
| Encombrement extérieur, habillage longitudinal, raccords, accessoires et implantation dans le châssis | Lecture du mécanisme ouvert, répétition des organes et implantation centrale apparente de la distribution |
| Des parties cachées restent inconnues | Des carters sont retirés et des pièces dégagées pour la visualisation |
| Ne révèle pas nos quatre soupapes par cylindre | Ne démontre pas non plus leur compatibilité ni leur calage |

Les deux vidéos ne sont pas deux relevés complémentaires garantis d'un même
moteur : variante, échelle, équipement et fidélité de la CAO restent à établir.
Notre reconstruction 4V biturbo reste une conception hybride sous hypothèses.
Les sources et reçus des étapes exécutées ne sont pas modifiés par cette analyse.
