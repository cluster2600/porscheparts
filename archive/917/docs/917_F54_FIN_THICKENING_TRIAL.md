# F54 — essai contrôlé d'épaississement des ailettes

## Modification effectivement construite

Le générateur `thicken_scan_fins_f54.py` reprend les 41 contours privés
scan-dérivés utilisés pour la reconstruction F43. Il modifie uniquement les
hauteurs de 14 paires `fin_lower` / `fin_upper` : espacement nominal de
1,5 à 2,0 unité du scan, symétriquement autour de chaque plan médian.
Les coordonnées latérales de tous les contours restent identiques, ainsi
que les contours d'extrémité. Aucun ovale, ellipse ou volume global de
substitution n'est introduit. Les profils sources ne sont pas écrasés.

Les espaces entre les ailettes diminuent : l'effet sur le débit d'air et
le refroidissement doit être recalculé avant de retenir ce candidat.
L'échelle absolue demeure non certifiée ; ces espacements ne constituent
pas des cotes physiques certifiées.

## Preuves disponibles

- Source profils : `99ffbcfda94082838b5ee00fcd105d1879b14f1d2eee58dd63a4825e51b43bdf`.
- STEP épaissi : `ed8a211c99506406478a5acb2397924d6d925790794ef506a857379b597079e5`.
- Audit OCCT : BRepCheck valide, zéro résultat BOP avec les modes
  intersections, petites arêtes, reconstruction de faces, continuité et
  courbes sur surfaces ; un solide, une coque, 5 122 faces, aucune arête
  libre, dégénérée ou non-manifold.
- Maillage de surface : 175 266 triangles, étanche.
- Sur 2 000 sondes, 212 valeurs sous le seuil par sphère inscrite et 41
  par rayon normal. Le critère d'épaisseur reste non satisfait.
- Trois tests unitaires passent : conservation des contours et de l'entrée,
  rejet des espacements non finis/réducteurs ou provoquant un chevauchement,
  rejet des paires incomplètes ou de l'espacement source inattendu.

Un témoin inchangé est reconstruit avec le même générateur, les mêmes
contours et les mêmes paramètres de maillage (1–4 unités du scan,
60 points de courbure). Son STEP porte le hash
`e92caeb9e61f8fd254997224c0c6f65512d5ce55e7a543bcf59c8deb80f72968`.
Les distributions de sondes seront comparées entre ces deux enveloppes,
sans les confondre avec les culasses percées 2V et 4V.

Le témoin retourne 199 sondes faibles par sphère inscrite et 35 par rayon
normal, contre 212 et 41 pour le candidat épaissi. Les positions des sondes
dépendent des triangulations et des aires : cette comparaison n'est pas une
mesure point à point ni une preuve statistique de dégradation. Elle ne
démontre toutefois aucun gain sur le critère demandé. **Le candidat à 2,0
n'est pas retenu comme correction des épaisseurs** et reste une expérience
privée. Les maîtres F53 ne sont pas remplacés.

## Limites et suite

Ce candidat est une **enveloppe d'essai**, pas la culasse assemblée : les
conduits, sièges et galeries internes ne sont pas encore réintégrés dans
cette variante. Il ne remplace pas les maîtres 2V/4V F53 corrigés.
Le passage nominal à 2,0 ne garantit pas les épaisseurs locales aux
transitions. Il faut attribuer les sondes persistantes aux surfaces CAO,
retoucher les zones concernées, puis recontrôler les deux variantes
complètes et le refroidissement. Aucune fabrication n'est autorisée.

Les STEP, STL, profils et cartes de sondes restent dans le stockage privé.
