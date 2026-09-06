# M64 — registre initial des interfaces et sources

État : recherche documentaire, 6 septembre 2026. Cible utilisateur : famille
M64 964/993, développement turbo quatre soupapes avec comparaison deux soupapes.
Ce registre ne fige ni une variante ni une compatibilité de montage.

## Résultat exploitable

Les catalogues Porsche officiels allemands sont accessibles : les anciennes URL
`D_964_KATALOG.pdf` / `D_993_KATALOG.pdf` ne doivent plus servir de point d'entrée.
Le catalogue courant fournit références, restrictions et quelques dimensions de
composants ; ce n'est pas un plan coté de culasse. Les sources trouvées permettent
de poursuivre sans inventer une grille de goujons ni demander immédiatement un
nouveau scan. Elles ne suffisent pas encore à contraindre tous les axes en CAO.

## Sources primaires vérifiées

| ID | Source et accès | Usage |
| --- | --- | --- |
| P0 | [Porsche Classic Originalteile Katalog, allemand](https://www.porsche.com/germany/accessoriesandservice/classic/originalpartscatalogue/) | Point d'entrée officiel, liens 964 et 993 ouverts |
| P1 | [PET 964, Kat. 013, édition 24.07.2017](https://files.porsche.com/f/332100/b26b3c7233/kat013-d-911-94-katalog.pdf) | 794 pages ; pages PDF 55–59, planches 102/103, examinées pour cylindre/culasse |
| P2 | [PET 993, Kat. 017](https://files.porsche.com/f/332100/db8e7dba1c/kat017-d-911-98-katalog.pdf) | 674 pages, accès initial confirmé ; extraction détaillée des interfaces à poursuivre, appels de lecture ultérieurs en erreur |
| P3 | [Porsche : White giants](https://newsroom.porsche.com/en/history/porsche-history-white-giants-991-turbo-964-turbo-3-6-993-turbo-s-13863.html) | Dimensions moteur des Turbo 3.6 et Turbo S, pas dessin d'interface |
| P4 | [Porsche : Die 911 Turbo Generationen](https://newsroom.porsche.com/de/pressemappen/50-Jahre-Porsche-Turbo-36122/Die-911-Turbo-Generationen.html) | Contexte officiel allemand des générations |
| S1 | [Swindon, produit M64 24 soupapes](https://swindonpowertrain.com/products/24-valve-porsche-911-m64-cylinder-head-kit/) | Compatibilité déclarée fabricant, pas validation de notre conception |
| S2 | [Swindon, fiche produit, 6 pages](https://swindonpowertrain.com/wp-content/uploads/2025/10/M64-24V-Cylinder-Head-Kit-Product-Sheet-0923.pdf) | Pages PDF 3–4 : composition et données techniques |

Les PDF restent chez leurs éditeurs ; aucun manuel ni illustration propriétaire
n'est ajouté au dépôt. Les numéros de page ci-dessous sont ceux du PDF, base 1.

## Données nominales réellement sourcées

| Donnée | Valeur publiée | Périmètre/source | Limite |
| --- | --- | --- | --- |
| Alésage × course | 100 × 76,4 mm | 964 Turbo 3.6 et 993 Turbo S, P3 | Ni diamètre du registre ni tolérance |
| Rapport volumétrique | 7,5:1 / 8,0:1 | Respectivement ces deux modèles, P3 | Références historiques, pas consignes de notre projet |
| Goujon, repère 5 | BM 8 × 20 ; 99906200602 | P1 p.58, 103-00 | Position/engagement non cotés |
| Goujon, repère 6 | BM 8 × 50 ; 99906204102 | P1 p.58 | Position/engagement non cotés |
| Goujon, repère 7 | BM 8 × 22 / BM 8 × 30 | M64.01/02/03 / M64.50 ; P1 p.58 | Différence de variante explicite |
| Goujon, repère 8 | BM 6 × 30 / BM 8 × 120 | M64.01/02/03 / M64.50 ; P1 p.58 | Ne pas fusionner ces nomenclatures |
| Cales de soupapes | 0,25 ; 0,5 ; 1,5 mm | P1 p.59 | Pas une hauteur montée de ressort |
| Soupapes Swindon admission/échappement | 40 / 33 mm | S2 p.4 | Benchmark 4V, non OEM |
| Levées maximales Swindon | 11,5 / 9,6 mm | S2 p.4 | Pas une loi de came complète |
| Durées à 1 mm | 255° / 245° | S2 p.4 | Calage des événements non défini ici |
| Plage d'alésage Swindon | 95–102,7 mm | S2 p.4 | Ne définit pas notre registre |
| Volume indiqué de culasse | 16,6 cm³ | S2 p.4 | Pas le volume mort assemblé piston compris |

## Différences à conserver

P1 distingue M64.01/02/03, M64.50 et M30.69. Il répertorie des écrous de culasse
distincts (96410438201 / 96410438220) et une évolution d'étanchéité dès 1991 avec
renvoi TI groupe 1, document 1570 (02/00). Référence d'étanchéité : 96410411520.
La TI doit être consultée avant de reconstruire la portée. Les éclatés ne sont
pas des dessins dimensionnels contractuels.

P3 distingue la 964 Turbo 3.3 (M30) de la Turbo 3.6 (M64). Notre référence commune
M64 n'inclut donc pas automatiquement toutes les 964 Turbo.

Swindon déclare réutiliser lubrification, cylindres, carters, entraînement par
chaînes/couvercles et échappement M64 (S1). S2 précise « standard 993 » dans le
paragraphe d'installation : cette nuance appelle une vérification 964/993, pas
une équivalence supposée. L'admission 997 GT3 et les bobines 718 sont des
compatibilités annoncées du kit, non de notre culasse. Le kit comprend aussi
porte-arbres, arbres, linguets/axes et retours d'huile : quatre soupapes ne sont
pas une simple modification des trous d'une culasse deux soupapes.

Les rapports nominaux 11,5–12:1 du kit sont associés aux pistons Swindon (S2).
Ils ne constituent pas une recommandation de compression turbo. Le régime
annoncé de 12 000 tr/min n'est pas notre régime validé.

## Interfaces encore non cotées dans ce registre

| Interface | Preuve encore nécessaire | Travail suivant autorisé |
| --- | --- | --- |
| Grille des goujons principaux, pions | Coordonnées, axes, tolérances, plans de référence | PET puis manuel/TI ou dessin fournisseur traçable |
| Registre et portée cylindre/culasse | Diamètres, profondeurs, gorge, planéité et état de surface par version | Lire TI 1570 et recouper références cylindre/joint |
| Distribution et porte-arbres | Axes/paliers, hauteur, entrée de chaîne, jeux, entraînement accessoires | Séparer 964 et 993 ; définir le nouvel ensemble 4V |
| Admission/échappement | Implantation, brides, passages, fixations et tolérances | Rapprocher PET, joints et dessins fournisseur |
| Lubrification | Positions et sections des alimentations/retours, joints et débit disponible | Ne pas dimensionner un refroidissement huile depuis une photo |
| Sièges/guides et bougie | Axes, serrages, longueurs, matériaux, jeux à chaud | Données fournisseur sélectionné et conception contrôlée |

Une référence commune de pièce ne prouve pas à elle seule l'identité de toutes
les interfaces. Aucune cote n'est mesurée sur une perspective photographique.
La dimension 90 mm de l'ancien modèle 917 n'est pas transférée au M64 ; passer
à 100 mm ne signifie pas mettre uniformément tout le scan à l'échelle.

## Prochaine étape bornée

Extraire la planche culasse du PET 993, comparer les nomenclatures aux planches
964 ci-dessus, puis obtenir les données de service relatives à la portée.
Publier ensuite un contrat machine-readable où chaque cote comporte variante,
source/page, nominal, tolérance et statut. Les inconnues restent nulles ; elles
ne deviennent ni valeurs par défaut de CAO ni paramètres de simulation validés.

## Recherche ciblée dans les données locales déjà présentes

Le registre `catalog/manual/993-workshop-manual-measurements.json` contient
2 496 enregistrements (111 données techniques, 195 couples et 2 190 occurrences).
La source `catalog/sources/src-porsche-workshop-manual-993.json` identifie un
manuel **993 Carrera**, sans volume Turbo ; les droits interdisent la
redistribution du manuel. Les faits et leurs localisateurs peuvent être suivis
sans recopier les pages.

| Piste retrouvée | Localisateur interne | Confiance et décision |
| --- | --- | --- |
| Goujon M8 × 22 | PDF 148, ligne 46 | OCR non revu ; pas d'implantation |
| Dimension « g » 8,00–8,015 mm | PDF 153, ligne 17 | Passage relatif aux guides ; feature/procédure à relire |
| Valeur guides 0,06–0,08 mm | PDF 153, ligne 56 | Ne pas la qualifier de jeu de marche ou de serrage sans contexte complet |
| Dimensions soupapes, notamment « b » 7,970 − 0,012 mm | PDF 155, ligne 22 | Colonnes Carrera/RS mélangées par OCR ; pas de promotion CAO |
| Dimension admission « A » 36,7 + 0,3 mm et 37,2 + 0,3 mm | PDF 157, ligne 35 | Affectation des variantes et définition de A non résolues |
| Culasse : 20 Nm puis 90° ; porte-arbres : M8, 23 Nm | Table structurée PDF 60 | Couples/procédure, pas entraxes ni effort de précharge directement calculable |

Les pages 152–157 figurent dans la liste globale `manually_checked_pages`, mais
les occurrences conservent individuellement `ocr_unreviewed`. Cette liste ne
suffit pas à réétiqueter chaque cote comme vérifiée. La cote OCR 0,80 mm p.152
ne doit notamment pas devenir un jeu nominal de guide sans lire la procédure
de contrôle d'usure.

`catalog/specifications/porschefanatics-993-technical-data.json` retrouve
l'alésage 100 et la course 76,4, mais avec unités OCR corrompues et statut
`ocr_transcription_unverified`. Ce sont des transcriptions apparentées au même
manuel, pas un contre-contrôle indépendant. P3 reste la source retenue pour
les valeurs historiques turbo. Le contrat contient maintenant ces pistes
locales en section séparée ; toutes les interfaces critiques demeurent nulles.
