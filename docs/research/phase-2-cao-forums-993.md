# Phase 2 — Fichiers CAO et 3D du 993 trouvés dans les communautés

Date de consultation : 29 août 2026. Requêtes menées en allemand, anglais et
français autour de `993 CAD`, `CAO`, `STEP`, `STL`, `3D scan`, `SolidWorks`,
`FreeCAD`, `Rennlist`, `PFF`, `GrabCAD`, `Thingiverse` et `Printables`.

## Conclusion

Des propriétaires ont bien travaillé sur des fichiers 3D fonctionnels du 993.
Le corpus public porte surtout sur des petites pièces, accessoires, gabarits
d'atelier et maillages visuels. Aucun assemblage CAO paramétrique complet et
métrologique de la voiture n'a été trouvé.

Les deux pistes nouvelles les plus utiles au jumeau sont :

1. trois gabarits CAO de profondeur de pose du pare-brise, issus de gabarits
   physiques puis repris dans SolidWorks ;
2. un scan de Carrera complet annoncé à l'échelle réelle et à 2 mm de précision.

Le premier peut documenter une interface caisse-vitrage. Le second peut fournir
une enveloppe de carrosserie. Aucun ne doit être présenté comme géométrie
certifiée avant contrôle des fichiers, de l'échelle, de la variante et des
droits.

## Résultats classés

| Priorité | Élément | Format ou procédé annoncé | Preuve disponible | Limite actuelle |
|---|---|---|---|---|
| haute | gabarits de pose du pare-brise | SolidWorks puis 3 fichiers imprimables, haut/bas/côté | fil de conception, corrections d'échelle, lien Printables et retours d'usage | licence, fichiers maîtres, cotes et incertitude à vérifier |
| haute | scan complet d'une Carrera « barn find » | maillage de scan, 1,6 M triangles | taille réelle et précision 2 mm déclarées par le vendeur | payant, variante et rapport de calibration absents, redistribution interdite |
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

Les recherches sur PFF, les forums FreeCAD et Autodesk n'ont pas produit de
fichier CAO 993 partageable et mieux documenté. Les résultats GrabCAD trouvés
concernent surtout des carrosseries RWB, des miniatures ou des maillages de
rendu.

## Prochaine action de qualification

1. ouvrir les pages Printables et Thingiverse dans un navigateur ordinaire pour
   relever licence, auteur, formats et sommes de contrôle ;
2. demander aux auteurs des gabarits le fichier maître SolidWorks ou un STEP,
   les dimensions de référence et la variante de caisse testée ;
3. demander au vendeur du scan un extrait, le système de coordonnées, la méthode
   de mise à l'échelle et une carte d'erreur avant tout achat ;
4. n'importer dans le dépôt qu'un fichier dont la licence autorise réellement la
   redistribution ; sinon conserver URL, métadonnées et empreinte locale sans le
   maillage.
