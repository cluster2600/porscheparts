# Registre de références visuelles 917 — F30

## Objet

Le fichier `twins/reference-917-engine/visual-reference-registry-f30.json`
catalogue exactement les dix captures fournies par l'utilisateur et huit médias
complémentaires publiés par Canepa. Il s'agit d'un registre documentaire
**link-only** : aucune image, miniature, vidéo ou autre charge utile distante
n'est copiée dans le dépôt.

F30 autorise uniquement :

- l'identification de la page source et de ses identifiants publics ;
- l'enregistrement du détenteur ou du régime de droits lorsqu'il est publié ;
- des observations topologiques visibles ou explicitement décrites par la
  source ;
- l'enregistrement des limites de chaque observation.

F30 n'autorise ni relevé dimensionnel, ni transfert d'échelle, ni
reconstruction CAO, ni simulation, ni fabrication, ni démarrage moteur.

## Séparation stricte des variantes

Les étiquettes ci-dessous sont des compartiments documentaires. Elles ne
permettent jamais de transférer une géométrie d'une variante à une autre.

| Variante documentaire | Captures |
| --- | --- |
| Type 912, 4,5 L atmosphérique | `photo_03` |
| 917 K | `photo_05` |
| 917/10 | `photo_08`, `photo_09`, `photo_10` |
| 917/30 | `photo_01`, `photo_02` |
| Variante inconnue | `photo_04`, `photo_06`, `photo_07` |

La catégorie « variante inconnue » est volontaire : une légende de republication,
une miniature ou une photographie en coupe ne suffit pas à établir la variante
physique du moteur grandeur réelle.

## Couverture des médias Canepa

Les huit entrées complémentaires sont elles aussi uniquement des liens :

- quatre actifs distants de la page de démontage 917/10 :
  `canepa_917_10_image_007` à `canepa_917_10_image_010` ;
- la page de remontage 917/30 et son image de présentation ;
- la page d'attachement « 917-30 Spare Engine 10 » ;
- la page de la vidéo accélérée du remontage 917/30.

Les quantités explicitement publiées par Canepa — douze bielles, vingt-quatre
soupapes, vingt-quatre ressorts et dix couches par filtre — sont conservées
comme observations de nomenclature ou de topologie. Elles ne sont pas des cotes
et ne constituent aucune métrologie.

## Métrologie et droits

Chaque capture et chaque média complémentaire porte un objet `metrology` dont
`metric_values` reste vide. Une perspective photographique, un support de
musée, une miniature, une illustration ou un éclaté d'exposition ne fournit pas
de datum d'assemblage ni d'échelle fiable.

Les pages Alamy sont indiquées comme « rights managed » ; Suber Factory, Canepa
et les autres éditeurs sans licence ouverte restent link-only. La photographie
Wikimedia Commons est publiée sous CC BY-SA 2.0, mais la politique F30 conserve
également uniquement son lien. L'image relayée par Reddit/Tumblr garde des
droits inconnus et ne doit pas être importée.

## Critère de sortie

Tous les champs de `release_gates` restent à `false`. Le registre ne peut être
utilisé comme preuve de fidélité géométrique, d'identité physique, de
performance, de corrélation, de sécurité ou d'autorisation de fabrication.
