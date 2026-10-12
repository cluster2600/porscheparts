# Analyse du moteur 917 exposé en vue éclatée

Analyse du 12 octobre 2026 de la [troisième vidéo fournie](https://www.youtube.com/watch?v=bIT1i03EZWM).
Elle complète le [moteur installé](video-reference-analysis.md) et
l'[animation en coupe](animation-reference-analysis.md) par des gros plans
d'organes physiques. Son apport principal est la construction des pièces :
chapeaux de paliers, logements, ailettes, brides, raccords et fixations.

## Source examinée

- Titre : « 917 Engine Display Porsche Museum » ; auteur indiqué : BreitWerks ;
  publication indiquée par YouTube : 9 juillet 2017. La description situe cette
  exposition au musée Porsche à Stuttgart ; la variante exacte du moteur n'est
  pas établie par cette analyse.
- Copie effectivement examinée : 1280 × 720 pixels, 30 images/s, durée
  124,6 s. SHA-256 :
  `c4301e525f4113a68f0846bbb5365d55b0b4e79be61a09d088a837c10f690eb0`.
- Une planche de repérage et quinze images ponctuelles ont été examinées :
  4, 12, 20, 28, 36, 44, 52, 68, 76, 84, 92, 100, 108, 116 et 122 s.
  Extraction reproductible : `ffmpeg -ss 36 -i video.mp4 -frames:v 1 frame-036.png`.
- Les pièces sont présentées écartées sur des supports : le déplacement
  muséographique ne fournit ni entraxes de montage ni jeux de fonctionnement.
  Le pas du plateau perforé est inconnu et ne constitue pas une échelle.
- Licence et droits de reproduction/dérivation inconnus. Vidéo et images restent
  dans `/tmp/`, hors Git. Aucun pixel, plaque ou identifiant du véhicule n'est
  publié dans ce document. Aucun son ou commentaire n'est employé comme mesure.

## Observations exploitables

| Repère | Pièces et détails visibles | Conséquence pour PicoGK ; limite |
|---|---|---|
| [00:12](https://www.youtube.com/watch?v=bIT1i03EZWM&t=12s), [00:20](https://www.youtube.com/watch?v=bIT1i03EZWM&t=20s) | Demi-carter ouvert avec logements de paliers et cloisons répétées ; pistons séparés avec gorges et logement d'axe ; rangée de six cylindres individuels à ailettes extérieures. | Séparer cylindre, piston, axe, paliers et carter avec leurs faces d'appui et fixations. Recaler leurs interfaces sur le scan et les cotes sourcées. Ni la répétition ni les supports de présentation ne donnent les cotes. Les ailettes ne doivent pas être copiées automatiquement sur une culasse dont le refroidissement serait différent. |
| [00:28](https://www.youtube.com/watch?v=bIT1i03EZWM&t=28s) | Longs éléments de fixation retirés, rangés à côté du banc ; surfaces de culasses partiellement visibles et image en mouvement. | Les attaches traversantes et accès aux écrous doivent figurer dans le contrat d'assemblage. La vue est trop floue et masquée pour établir le filetage, la précharge, un nombre complet de fixations ou le nombre de soupapes par cylindre. |
| [00:36](https://www.youtube.com/watch?v=bIT1i03EZWM&t=36s), [00:44](https://www.youtube.com/watch?v=bIT1i03EZWM&t=44s), [00:52](https://www.youtube.com/watch?v=bIT1i03EZWM&t=52s) | Arbre à cames dans un carter longitudinal ouvert : portées, lobes, chapeaux de paliers boulonnés, bossages et organes de transmission près des lobes. Une roue dentée apparaît dans la région intermédiaire à 44 s ; l'extrémité visible à 36 s comporte un profil axial régulier. | Remplacer les supports génériques par des logements et chapeaux démontables, avec réserves de mouvement, fixations et lubrification. La région dentée constitue un indice physique supplémentaire pour examiner la distribution centrale suggérée par l'animation. Le profil terminal peut correspondre à des cannelures : ne pas l'assimiler à un pignon sans vue complémentaire. Le train complet, ses rapports et ses retenues ne sont pas établis. |
| [01:08](https://www.youtube.com/watch?v=bIT1i03EZWM&t=68s), [01:16](https://www.youtube.com/watch?v=bIT1i03EZWM&t=76s), [01:24](https://www.youtube.com/watch?v=bIT1i03EZWM&t=84s) | Deux ensembles à volutes noires et conduits métalliques coudés ; organe central à corps noir haut ; assemblage tenu par des platines et pattes percées. | Référence physique utile pour nos turbos : brides, orientations des raccords, rayons de courbure et supports doivent former un assemblage démontable. L'organe central est compatible visuellement avec une commande de dérivation/régulation, mais son identité et son circuit doivent être confirmés. Les poses d'exposition ne fixent pas celles des turbos dans le moteur. |
| [01:32](https://www.youtube.com/watch?v=bIT1i03EZWM&t=92s), [01:40](https://www.youtube.com/watch?v=bIT1i03EZWM&t=100s) | Manchon noir serré par colliers, embout métallique à bourrelet, jonctions soudées, bride boulonnée inférieure, pattes de support et plusieurs sorties distinctes. | Distinguer parties chaudes/froides après identification du circuit ; créer les raccords réels autour de nos ports candidats, plutôt qu'un unique tube continu. Les déformations thermiques, efforts sur les volutes, étanchéité et maintenance doivent être contrôlés. Ni alliage, épaisseur, type de joint, débit ni pression ne sont mesurables ici. Aucun échangeur n'est identifié dans ces gros plans. |
| [01:48](https://www.youtube.com/watch?v=bIT1i03EZWM&t=108s) | Couvercle longitudinal profilé avec bosses et fixations périphériques ; plusieurs organes détachés et alignés sous le banc. | Confirme la priorité d'un habillage longitudinal cohérent face aux six boîtes de notre rendu actuel. Nos culasses 4V demandent leur propre enveloppe, plan de joint et accès : ce couvercle historique ne prouve pas leur compatibilité. |
| [01:56](https://www.youtube.com/watch?v=bIT1i03EZWM&t=116s), [02:02](https://www.youtube.com/watch?v=bIT1i03EZWM&t=122s) | Vilebrequin, bielles et grandes masses profilées, arbre longitudinal voisin, engrenages sous la zone centrale, ventilateur horizontal avec enveloppe jaune ; embrayage et transmission séparés à l'arrière-plan. | Documenter chaque liaison en couple et distinguer entraînement des cames, sortie de puissance, ventilateur et accessoires. Les éléments centraux renforcent l'intérêt d'une revue de cette architecture ; ils ne permettent pas d'attribuer tous les engrenages à une fonction précise. Les bielles déplacées pour l'exposition ne donnent pas les phases cinématiques. |

## Suite de reconstruction fondée sur les trois références

1. **Revoir le chemin de distribution.** Croiser les engrenages visibles du
   musée avec l'animation et les données mécaniques de la variante retenue.
   Les trains actuels en bout restent une solution candidate ; un nouvel axe ou
   une nouvelle denture demeure une hypothèse de conception tant que ses
   interfaces ne sont pas sourcées. Conserver les axes des culasses 4V, puis vérifier les rapports,
   sens de rotation, réserves et interfaces du nouveau trajet étudié.
2. **Reconstruire les enveloppes avec leurs attaches.** Priorité aux carters
   longitudinaux et chapeaux de paliers, aux plans de joint, aux vis accessibles,
   aux portées et aux canaux. Les tiges transparentes de musée et les perçages du
   plateau ne sont pas des pièces moteur ; ne pas les inclure dans l'assemblage.
3. **Intégrer les turbos.** Garder nos prototypes, identifier les circuits et
   compléter supports, brides, manchons et dispositif de régulation. Revoir les
   longues boucles à partir des ports et des volumes interdits, puis contrôler
   jeux, contacts, circulation, étanchéité et dilatation.
4. **Employer la bionique aux endroits justifiés.** Réutiliser les fonctions
   PicoGK de branches, poutres et champs implicites pour les supports et
   transitions internes, en conservant ancrages et zones interdites. Ces images
   ne montrent pas une construction bionique à copier. Une baisse de volume
   seule ne qualifie ni les chapeaux de paliers ni les bielles ni les dentures.

La référence de musée apporte des formes physiques plus détaillées que
l'animation, sans fournir la métrologie nécessaire. Les couleurs noires,
métalliques et jaunes n'identifient pas les matériaux. Les quatre soupapes,
dimensions, tolérances, circuits internes, charges, traitements et procédés
doivent garder leurs preuves propres. Aucune pièce n'est déclarée fonctionnelle
ou imprimable pour service moteur par cette analyse.

Les sources PicoGK et reçus d'exécution déjà publiés restent inchangés ; cette
étape ajoute des observations et des critères de reconstruction.
