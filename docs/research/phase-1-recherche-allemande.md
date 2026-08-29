# Phase 1 — Recherche allemande, lot 1

Date d’accès : 29 août 2026.

## Périmètre

Cette première vague vise les sources techniques officielles du marché allemand
et les géométries publiques attribuées à la Porsche 993. Les requêtes ont été
formulées en allemand, notamment :

- `Porsche 993 Ersatzteilkatalog technische Dokumentation`
- `Porsche 993 3D Scan CAD Modell STL Lizenz`
- `Porsche 993 Karosserie Punktwolke CAD`
- `Porsche 993 Maße Toleranzen Reparaturleitfaden`
- `Porsche 993 3D Druck Ersatzteile`

Les fichiers tiers n’ont pas été téléchargés dans le dépôt. Une licence déclarée
par un index secondaire reste à confirmer sur la publication originale.

## Résultats directs

1. Le [PET officiel 993](../../catalog/sources/src-porsche-pet-993.json) est un
   PDF de 674 pages couvrant Carrera, Carrera S, Carrera 4/4S, Carrera RS,
   Cabriolet, Targa et Turbo. Il fournit références, variantes et éclatés, mais
   aucune géométrie cotée de fabrication.
2. Le [catalogue allemand de littérature](../../catalog/sources/src-porsche-literature-catalogue-de.json)
   confirme les références des guides de réparation et OBD-II allemands pour
   Carrera et Turbo. Il ne contient pas les guides eux-mêmes.
3. La [boutique de littérature technique](../../catalog/sources/src-porsche-technical-literature-de.json)
   propose notamment des ouvrages de types, dimensions et tolérances. Les
   publications sous droits ou payantes restent hors du dépôt.
4. Le [Parts Finder allemand](../../catalog/sources/src-porsche-classic-partsfinder-de.json)
   sert à dater prix et disponibilité. Une absence de résultat ne prouve pas
   qu’une pièce est abandonnée.
5. Neuf assets 993 communautaires ont été retrouvés avec auteur, licence
   déclarée, nombre de fichiers et dimensions déclarées. Aucun n’a encore une
   vérification dimensionnelle indépendante.

La recherche n’a pas trouvé de scan complet de 993, librement redistribuable et
accompagné d’une précision métrologique démontrée. Les modèles commerciaux de
carrosserie trouvés sont principalement des maillages de visualisation ; ils ne
remplacent pas une mesure de pièce.

## Vague ciblée : marbre et manuel d’atelier

Une seconde vague a repris les requêtes `frame data`, `body dimensions`,
`Celette`, `Group 5`, `Running Gear`, `KATALOG_993` et leurs équivalents
allemands `Karosseriemaße`, `Richtbankdaten`, `Richtsatz` et
`Reparaturleitfaden`.

- Le volume V du [manuel d’atelier officiel](../../catalog/sources/src-porsche-workshop-manual-993.json)
  contient les dimensions de construction, les dimensions de réparation de
  caisse et les dimensions du plancher. Le volume IV couvre le train roulant.
- Les copies intégrales repérées sur Cannell, PDFCoffee, Scribd et par échanges
  privés de forums n’ont pas de droit de diffusion démontré. Elles ne sont ni
  téléchargées ni référencées comme sources exploitables.
- Un [jeu de marbre Celette MZx 964/993](../../catalog/sources/src-celette-mzx-964-993-jigs.json)
  est confirmé par le fabricant. Il est destiné au maintien et à la mesure,
  sans opération de tirage, mais sa fiche publique ne révèle aucune coordonnée.
- [Car-O-Data](../../catalog/sources/src-car-o-liner-car-o-data.json) contient des
  fiches professionnelles de mesure supérieure et inférieure de caisse. La
  présence d’une fiche 993 n’est pas confirmée publiquement.
- La requête `site:porsche.com "KATALOG_993" filetype:pdf` n’a pas retrouvé un
  meilleur PET que le Kat 017 officiel déjà enregistré.

Conclusion : le chemin le plus crédible vers la géométrie de caisse est le
volume V officiel ou l’accès encadré à une base de marbre professionnelle. Une
copie PDF trouvée par Google n’est pas, à elle seule, une source légalement
réutilisable.

## Matrice des vingt candidats

`D` signifie ici référence communautaire ou visuelle sans précision démontrée.
`PET` signifie que seule l’identité de la pièce est confirmée : la géométrie doit
être mesurée ou reconstruite légalement.

| # | Candidat | Origine | Preuve actuelle | Lacune avant CAO ou prototype | Priorité |
|---:|---|---|---|---|---|
| 1 | Languette de couvercle de filtre à pollen | [Asset](../../catalog/sources/src-renn3d-pollen-filter-cover-tabs.json) | 4 STL, photos, CC-BY déclarée, niveau D | Licence exacte, mesure et montage 993 | Haute |
| 2 | Languette de cache d’interrupteurs de console | [Asset](../../catalog/sources/src-renn3d-console-switch-tab-repair.json) | 1 STL, photo, CC-BY déclarée, niveau D | Licence exacte et montage 993 | Haute |
| 3 | Porte-gobelets de console | [Asset](../../catalog/sources/src-renn3d-center-console-cup-holder.json) | 1 STL, photo montée, domaine public déclaré, niveau D | Confirmer droits, variante et interférences | Haute |
| 4 | Support de téléphone sur compteur 82 mm | [Asset](../../catalog/sources/src-renn3d-gauge-ring-phone-mount.json) | 1 STL, CC-BY déclarée, niveau D | Risque de marque sur cerclage et stabilité | Moyenne |
| 5 | Cadres d’adaptation haut-parleur 4x6 | [Asset](../../catalog/sources/src-renn3d-hifi-speaker-adapter-frames.json) | 2 STL, domaine public déclaré, niveau D | Échelle publiée manifestement incohérente | Bloquée |
| 6 | Barre de grille arrière custom | [Asset](../../catalog/sources/src-renn3d-custom-split-grille-bar.json) | 3 STL, CC-BY-NC-SA déclarée, niveau D | Non OEM, non commercial, montage à confirmer | Basse |
| 7 | Outil de pose du joint spi arrière | [Asset](../../catalog/sources/src-renn3d-rear-main-seal-tool.json) | 4 STL, CC-BY-SA déclarée, niveau D | Cotes fonctionnelles et procédure atelier | Moyenne |
| 8 | Bouton de déverrouillage de dossier de siège | [Asset](../../catalog/sources/src-renn3d-seat-back-release-button.json) | 1 STL, références OEM déclarées, niveau D | Revue sécurité siège et compatibilité | Bloquée |
| 9 | Support de purge d’embrayage déportée | [Asset](../../catalog/sources/src-renn3d-remote-clutch-bleeder-bracket.json) | 2 STL, CC-BY-NC déclarée, niveau D | Proximité système d’embrayage, revue sécurité | Bloquée |
| 10 | Cache de capteur intérieur, `993 659 147 00` | PET, planche 813-40 | Référence officielle, 1996 et après | Original mesurable, clips et matière | Haute |
| 11 | Bouton HVAC, `993 659 146 00` | PET, planche 813-40 | Référence officielle | Original mesurable, indexation et matière | Haute |
| 12 | Bouton HVAC, `993 659 145 00` | PET, planche 813-40 | Référence officielle | Original mesurable, indexation et matière | Haute |
| 13 | Bouton HVAC, `944 653 205 00` | PET, planche 813-40 | Référence officielle, quantité 2 | Compatibilité partagée et original mesurable | Haute |
| 14 | Bouton d’éclairage, `993 613 055 00` | PET, planche 903-06 | Référence officielle | Interface avec commande, symbole séparé | Haute |
| 15 | Cabochon d’éclairage, `993 613 250 00` | PET, planche 903-06 | Référence officielle | Géométrie, pictogramme et tenue thermique | Moyenne |
| 16 | Cabochon dégivrage, `993 613 253 00` | PET, planche 903-06 | Référence officielle | Géométrie, pictogramme et translucide | Moyenne |
| 17 | Cabochon antibrouillard avant, `993 613 251 00` | PET, planche 903-06 | Référence officielle | Géométrie, pictogramme et translucide | Moyenne |
| 18 | Cabochon antibrouillard arrière, `993 613 252 00` | PET, planche 903-06 | Référence officielle | Géométrie, pictogramme et translucide | Moyenne |
| 19 | Cache de colonne, `993 552 277 00` | PET, planche 903-10 | Référence officielle | Variante, fixations et jeu avec commandes | Moyenne |
| 20 | Grille de haut-parleur M490, `993 555 777 00` | PET, planche 911-05 | Référence officielle, quantité 2 | Original, acoustique, texture et montage | Moyenne |

## Écarts et décisions

| Question | État | Décision de projet |
|---|---|---|
| Scan complet 993 ouvert et métrologique | Non trouvé | Ne pas construire le jumeau à partir d’un maillage artistique |
| Licence exacte des assets communautaires | Souvent déclarée par un index secondaire | Vérifier la page originale avant tout import |
| Dimensions des candidats PET | Absentes des éclatés | Mesurer un original ou son environnement |
| Disponibilité commerciale actuelle | Non auditée pièce par pièce | Utiliser le Parts Finder avec date et conserver `inconnu` sinon |
| Première pièce titane | Hors de cette vague | Attendre besoins mécaniques, charges et bénéfice matière démontré |

## Prochaine porte

Pour les trois candidats de priorité haute issus d’assets, la prochaine action
est de vérifier la publication originale, puis de créer une fiche pièce seulement
après obtention d’un exemplaire ou de mesures reproductibles. Pour les candidats
PET, il faut photographier et mesurer la pièce ou son logement avec le modèle de
mesure du dépôt.
