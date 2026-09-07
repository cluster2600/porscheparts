# Module quatre soupapes : références de portées et d'ajustements

## Apport concret

Le [catalogue fabricant MAHLE, Valve Train Components 2025, v002](https://www.mahle-aftermarket.com/media/homepage/facelift/media-center/product-catalogs/mahle_valve_train_components_catalog_2025_screen_v002.pdf)
donne deux références réelles pour **M64.01–03 Carrera / Carrera 4, deux
soupapes par cylindre**, PDF p.825 / page imprimée 823, ligne 14 :

| Référence | Fonction | Tête / tige / longueur, mm | Angle de portée |
| --- | --- | --- | --- |
| 503 VE 32000 000 | Admission | 48,98 / 8,95 / 110,1 | 45° |
| 503 VA 32001 000 | Échappement | 42,5 / 8,95 / 106,4 | 45° |

Les colonnes et dessins d'en-tête ont été contrôlés visuellement selon le
skill PDF. **45° désigne la portée de soupape, pas l'inclinaison de son axe.**
Cette ligne n'est ni Turbo ni quatre soupapes. Les valeurs de catalogue ne
comprennent pas de tolérances de fabrication.

Le même document distingue deux ajustements :

| Interface | Plage de référence fabricant | Localisateur |
| --- | --- | --- |
| Tige-guide, tige 6–7 mm | Admission 10–40 µm ; échappement 25–55 µm | PDF p.27 / imprimée 25 |
| Tige-guide, tige 8–9 mm | Admission 20–50 µm ; échappement 35–65 µm | Même tableau |
| Insert de siège OD 30–40 mm dans culasse aluminium | Serrage 0,050–0,090 mm | PDF p.30 / imprimée 28 |
| Insert de siège OD 40–50 mm dans culasse aluminium | Serrage 0,060–0,100 mm | Même tableau |

La table tige-guide ne précise littéralement ni « radial/diamétral » ni une
température de mesure. Celle des sièges ne tranche pas l'affectation d'une
valeur exactement à la frontière de deux plages. **Pas de transposition
automatique en diamètres CAO, ni en ajustements qualifiés LPBF/turbo.**

## Conséquence pour la reconstruction

On peut maintenant construire un module mécanique avec **deux surfaces
coniques en regard**, une bande de contact explicite, un guide coaxial et des
jeux distincts. Retenir 45° pour son premier candidat reste un **choix de
conception documenté** ; cela ne rend pas la conversion conforme à une
définition Porsche quatre soupapes inexistante dans cette source.

Restent à choisir et dimensionner : tête/tige des quatre soupapes, largeur et
position de portée, angles de raccord, gorge, marge de soupape, inclinaison et
implantation des axes, longueur engagée des guides et leur serrage. Les jeux
chauds, les sièges dans l'alliage imprimé, les ressorts et les dégagements de
distribution doivent ensuite être calculés avec les matériaux et charges
retenus. Les références 2V ci-dessus ne sont pas des achats sélectionnés pour
la conversion.

Le manuel 993 Carrera déjà référencé dans le projet demeure inaccessible aux
chemins connus : ses valeurs OCR 152–157 n'ont pas été réinterprétées. Ce
complément remplace cette impasse par des références fabricant accessibles,
sans modifier le contrat d'interfaces.

## Traçabilité et vérification

Le lien a été suivi depuis la [page officielle des catalogues MAHLE](https://www.mahle-aftermarket.com/eu/en/media-center/product-catalogs/).
Le fichier privé téléchargé contient 1 161 pages et 15 373 822 octets ; SHA-256
`d9be89be7a5bb369f7bcf7d20477661f4e93355fc24c362734403c91b346e2c9`.
L'ancien lien `mahle_valves_catalog_2025_screen.pdf` renvoie 404 ; c'est le
fichier `mahle_valve_train_components_catalog_2025_screen_v002.pdf` qui a été
relu. Les métadonnées de ce PDF portent le 27 janvier 2026 ; le copyright
imprimé reste 2025. Pages PDF 27, 29, 30 et 825 contrôlées visuellement.

Les [faits structurés](../twins/m64-cylinder-head/valve-module-documentary-references-20260907.json)
conservent variantes, localisateurs et limites. Aucun PDF ni aucune figure
fabricant n'est ajouté au dépôt. **Aucune autorisation de fabrication.**
