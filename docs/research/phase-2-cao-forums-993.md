# Phase 2 — Fichiers CAO et 3D du 993 trouvés dans les communautés

Date de consultation : 29 août 2026. Requêtes menées en allemand, anglais et
français autour de `993 CAD`, `CAO`, `STEP`, `STL`, `3D scan`, `SolidWorks`,
`FreeCAD`, `Rennlist`, `PFF`, `GrabCAD`, `Thingiverse` et `Printables`.

## Conclusion

Des propriétaires ont bien travaillé sur des fichiers 3D fonctionnels du 993.
Le corpus public porte surtout sur des petites pièces, accessoires, gabarits
d'atelier et maillages visuels. Aucun assemblage CAO paramétrique complet et
métrologique de la voiture n'a été trouvé.

Les quatre pistes nouvelles les plus utiles au jumeau sont :

1. trois gabarits CAO de profondeur de pose du pare-brise, issus de gabarits
   physiques puis repris dans SolidWorks ;
2. un scan de Carrera complet annoncé à l'échelle réelle et à 2 mm de précision.
3. un second scan, cette fois d'une Turbo 1996, vendu en OBJ et annoncé à
   1,76 mm de précision extérieure ;
4. une étude de cas industrielle portant sur le scan métrologique et la
   rétro-ingénierie d'une 993 Coupé 1995 chez Juliá Automobile.

Les gabarits peuvent documenter une interface caisse-vitrage ; les deux scans
commerciaux peuvent fournir des enveloppes de carrosserie ; l'étude de cas
identifie un détenteur de données professionnelles. Aucun ne doit être présenté
comme géométrie certifiée avant contrôle des fichiers, de l'échelle, de la
variante et des droits.

## Deuxième vague de recherche

La recherche a été étendue aux dépôts GitHub et GitLab, à Carpokes, Pelican
Parts, PFF, Cults, Thingiverse, 3D Warehouse, aux prestataires de scan et aux
ateliers de restauration. Aucun dépôt Git public identifiable ne contient à ce
jour un assemblage ou une pièce 993 sous un nom explicite en STEP, FreeCAD,
OpenSCAD ou STL. Les résultats réellement exploitables sont dispersés sur les
forums et places de marché.

| Source nouvelle | Géométrie ou information | Intérêt pour le jumeau | Statut et garde-fou |
|---|---|---|---|
| Wolfe Classics | scan extérieur OBJ d'une Turbo 1996, précision annoncée 1,76 mm | seconde enveloppe complète, utile pour comparaison croisée | achat requis ; ligne de toit signalée faible ; licence et métrologie à demander |
| SHINING 3D / Juliá Automobile | scan et rétro-ingénierie d'une Coupé 1995 | détenteur identifié d'une géométrie professionnelle de caisse et carrosserie | fichiers privés ; 0,02 mm décrit le scanner, pas l'incertitude du modèle complet |
| Cults / formfactorperformance | cabochon de roue `993361303.11` en STEP et STL | première petite pièce trouvée avec un format CAO éditable | licence privée, aucune preuve de rétention ni de montage |
| Cults / ITMonkey | renforts gauche/droite de vide-poche non-HiFi en STL | géométrie locale avec enveloppe déclarée et fonction claire | payant, usage privé, aucune cote d'interface publiée |
| Carpokes | insert de réparation de bouton de climatisation 944/964/993 | communauté spécialisée et fil ancien avec retours | URL du fichier et licence à relever en session authentifiée |
| PFF / 1.AVM | composants de toit ouvrant 993 reconstruits en polymère renforcé | preuve d'une CAO fonctionnelle existante en Allemagne | aucun fichier, cote ou référence publique ; contact à établir |
| Denk3D | kits de réparation des attaches de platines d'interrupteurs 964/993 | deux familles de petites interfaces intérieures candidates | produit commercial, CAO fermée ; mesurer une pièce réelle |
| Thingiverse / LimeyBoy | bague d'avertisseur Momo RS : 52 mm intérieur, 59 mm extérieur, saillie 3 mm | petite géométrie bornée par trois dimensions déclarées | licence exacte et fonctionnement électrique à vérifier |
| Pelican Parts / gmorat | inserts de suppression de bumperettes, plusieurs itérations | révèle la variabilité réelle de la découpe du bouclier | pas de fichier ; concevoir paramétrique et mesurer chaque voiture |

Cette vague ajoute donc surtout deux détenteurs de scans complets, six familles
de petites pièces et une contrainte de conception importante. Elle ne change
pas la conclusion centrale : aucun fichier public ne constitue encore un
jumeau numérique métrique assemblé et réutilisable.

## Résultats classés

| Priorité | Élément | Format ou procédé annoncé | Preuve disponible | Limite actuelle |
|---|---|---|---|---|
| haute | gabarits de pose du pare-brise | SolidWorks puis 3 fichiers imprimables, haut/bas/côté | fil de conception, corrections d'échelle, lien Printables et retours d'usage | licence, fichiers maîtres, cotes et incertitude à vérifier |
| haute | scan complet d'une Carrera « barn find » | maillage de scan, 1,6 M triangles | taille réelle et précision 2 mm déclarées par le vendeur | payant, variante et rapport de calibration absents, redistribution interdite |
| haute | scan extérieur d'une Turbo 1996 | OBJ, précision extérieure 1,76 mm déclarée | fiche du prestataire et défaut de toit explicitement signalé | payant, procédé, carte d'écart et licence non publiés |
| haute | rétro-ingénierie Juliá Automobile | système de scan métrologique et CAO professionnelle | étude de cas allemande, voiture et millésime identifiés | données privées ; précision instrumentale différente de l'incertitude globale |
| moyenne | cabochon de roue `993361303.11` | STEP et STL | référence OEM et formats maîtres déclarés | licence privée, aucune preuve de montage ou de rétention |
| moyenne | renforts de vide-poche non-HiFi | deux STL gauche/droite | enveloppe publiée et fonction documentée | payant, licence privée, tolérances et essai absents |
| moyenne | bague arrière de réglage de siège | STL dans une archive ZIP | auteur et utilisateur décrivent la fabrication et le montage | licence, dimensions, matière, masse et variante inconnues |
| moyenne | barre de grille arrière divisée | STL Thingiverse, CAO communautaire | journal de conception, photos de finition et montage | pièce custom, pas une reproduction OEM ; licence exacte à reconfirmer |
| moyenne | cadres de haut-parleurs, porte-gobelets, support téléphone, patte de purge | STL sur Thingiverse/Printables ou archive Renn3D | fichiers et quelques photos de montage | échelle, matière, masse, licence et ajustement encore incomplets selon la pièce |
| basse | carrosseries CGTrader/GrabCAD/3DModels.org | Blender, FBX, OBJ, STL ou conversion STEP | visuels détaillés, parfois dimensions globales annoncées | géométrie de rendu ou miniature, aucune métrologie locale démontrée |
| basse | scan GT2 par vidéogrammétrie | maillage Sketchfab CC BY | maillage libre et provenance décrite | aucune échelle ni précision, images vidéo tierces |

## Fils particulièrement utiles

- [index Rennlist des pièces 3D du 993](https://rennlist.com/forums/993-forum/1451330-thread-of-993-3d-printed-diy-bits.html) :
  haut-parleurs, gabarits de pare-brise, porte-gobelets, console et bagues de
  siège ;
- [développement des gabarits de pare-brise](https://rennlist.com/forums/993-forum/1401664-windshield-replacement-diy.html) :
  trois fichiers CAO pour régler la profondeur du vitrage ;
- [historique de numérisation des gabarits](https://rennlist.com/forums/993-forum/937323-f-s-993-windshield-back-glass-templates-5.html) :
  passage d'un tracé physique à SolidWorks et résolution de problèmes d'échelle ;
- [bague de glissière de siège](https://rennlist.com/forums/993-forum/958995-993-passenger-and-driver-side-seat-rail-replacement-alternative-2.html) :
  STL joint au forum et retour d'utilisation ;
- [barre de grille divisée](https://rennlist.com/forums/993-forum/1189086-993-custom-split-grill-3.html) :
  fichier Thingiverse `4349486` et journal de montage ;
- [demande de plans châssis et suspension](https://rennlist.com/forums/993-forum/1285117-993-chassis-and-suspension-blueprints-3d-models.html) :
  la réponse publique fournit un PDF de dimensions de caisse, pas un modèle 3D.
- [scan extérieur d'une 993 Turbo 1996](https://www.wolfeclassics.com/shop/p/1996-porsche-911-turbo-3d-scan) :
  OBJ annoncé à 1,76 mm, avec une limite connue au niveau du toit ;
- [étude de cas allemande SHINING 3D / Juliá Automobile](https://www.shining3d.com/de/juli%C3%A1-automobile-shining-3d-when-passion-meets-3d-scanning-technology-classic-porsche-rebor) :
  scan professionnel d'une 993 Coupé 1995 pour reconstruction ;
- [bibliothèque CAO Carpokes](https://www.carpokes.com/viewforum.php?f=20) :
  fil dédié à un insert de réparation de bouton de climatisation 993/964/944 ;
- [reconstruction allemande de pièces de toit ouvrant](https://www.pff.de/thread/2821329-3d-druck-mit-kohlefaser-cnc-fraesen-und-drehen-ersatzteile-besser-als-original/) :
  comparaison photographique entre pièces d'origine et reproductions ;
- [développement CAO d'inserts de bumperettes](https://forums.pelicanparts.com/porsche-964-993-technical-forum/905860-bumperette-delete-modification-ive-been-working.html) :
  documente les variations de découpe entre voitures.

Les recherches sur PFF, les forums FreeCAD et Autodesk n'ont pas produit de
fichier CAO 993 partageable et mieux documenté. Les résultats GrabCAD trouvés
concernent surtout des carrosseries RWB, des miniatures ou des maillages de
rendu.

## Prochaine action de qualification

1. demander à Wolfe Classics et 21 Design un échantillon, le repère, la méthode
   de mise à l'échelle, une carte d'écart et leurs conditions de licence ;
2. contacter Juliá Automobile pour savoir si des coupes, interfaces ou mesures
   ciblées peuvent être partagées sans divulguer leur modèle complet ;
3. ouvrir les pages Carpokes et Thingiverse dans une session authentifiée pour
   relever licence, auteur, formats et sommes de contrôle ;
4. demander aux auteurs des gabarits le fichier maître SolidWorks ou un STEP,
   les dimensions de référence et la variante de caisse testée ;
5. n'importer dans le dépôt qu'un fichier dont la licence autorise réellement la
   redistribution ; sinon conserver URL, métadonnées et empreinte locale sans le
   maillage.
