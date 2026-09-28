# Données publiques moteur M64/60 (993 Turbo) — relevé du 2026-09-27

Relevé external (agent de recherche, read-only) pour amorcer le squelette
paramétrique du programme `M64-WHOLE-ENGINE-TWIN-0001`. Chaque valeur porte un
niveau de preuve. **Rien ici n'est une mesure du projet** : aucune de ces
valeurs ne promeut une géométrie au-delà de `F1_envelope` sans métrologie.

Niveaux : `FACT_public` = publié par Porsche (brochure, manuel technique
usine) · `CROSSCHECKED` = deux sources secondaires indépendantes concordantes
· `SINGLE_SOURCE` = une seule source secondaire · `ASSUMPTION` = inférence
d'ingénierie.

## Valeurs établies

| Donnée | Valeur | Niveau | Source |
|---|---|---|---|
| Architecture | Flat-six, air/huile, biturbo parallèle (1 turbo/banc), dry sump | FACT_public | Brochure Porsche UK « 993 the Turbo » (1995) ; supplément OBD 1996 |
| Alésage × course | 100,0 × 76,4 mm | FACT_public | Brochure + Porsche 993 US Parts Guide |
| Cylindrée | 3 600 cm³ | FACT_public | Brochure |
| Taux de compression | 9,5:1 | FACT_public | Brochure 993 Turbo |
| Puissance / couple | 408 PS (300 kW) / 540 Nm | FACT_public | Brochure |
| Pression de suralimentation | 1,0 bar (350 kPa absolue) | FACT_public | Brochure 993 Turbo (notice : 0,8 bar effectif mesuré en service courant ; la brochure publie la pression de consigne max) |
| Masse à sec | 232 kg | FACT_public | Brochure 993 Turbo |
| Ordre d'allumage | 1-6-2-4-3-5 | FACT_public | Doc spec Carrera M64/23-24 (distributeur unique partagé) ; recoupé avec article 964 Turbo 3.6 |
| Jeu aux soupapes | Compensation hydraulique (poussoirs auto-réglables) — pas de spécification statique | FACT_public | Parts Guide + doc spec Carrera |
| Goujons de culasse | 12 × M8×22 par culasse | FACT_public | Parts Guide (pièces/quantités) |
| Joint tour de cylindre | 1 O-ring 102×2 par cylindre + 6 joints de culasse + 6 disques guide-air (quantités) | FACT_public | Parts Guide |
| Entraînement ventilateur | Courroie crantée/VP depuis vilebrequin, rapport ≈ 1:1,6 | FACT_public | Supplément OBD 1996 « Engine Specifications » |
| Débit d'air de refroidissement | 1 010 l/s à 6 100 tr/min | FACT_public | Supplément OBD 1996 |
| Débit d'air de refroidissement (seconde valeur, non corroborée) | 1 210 l/s à 5 750 tr/min | FACT_community | elferclassic.de (level C, declared) — rétrogradé en contre-vérification; la valeur primaire 1 010 l/s est level A (Supplément OBD 1996). NB: le manual 993 p.17 (OCR non relu) mentionne « 1010 l/sec at 6,000 rpm » — rpm à vérifier visuellement avant F2 |
| Capacité d'huile | 12 L filtre inclus | FACT_public | Brochure |

## Valeurs NON publiques (bloquent F2, voir contrats d'acquisition)

- Entraxe cylindres (pitch) et hauteur de vilebrequin→plan de joint : **non publiés** → M64-ACQ-0004.
- Nombre de pales du ventilateur et diamètres de poulies : **non publiés**
  - Voie logicielle : scan `Fan+Drive+0.21mm.obj` (sha256 6c0b12d4…, 1,26 M sommets; provenance à inscrire au registre) analysé dans `work/obj-intake-20260927/` — harmoniques angulaires 4–7 sur le slab inférieur, non concluantes ; étude lancée ce soir, interrompue par expiration du délai avant conclusion (consigner les hypothèses dans docs/research/m64-fan-drive-blade-count-2026-09-27.md avant de reprendre). Diamètres géométriques extraits : pignon à denture OD≈127,6 mm (hauteur 67,9 mm), poulie r_max≈127,8 mm.
  - Débits : valeur primaire **1 010 l/s à ≈6 100 tr/min** (level A, Supplément OBD 1996 ; écho manuel p.17 « 1010 l/sec at 6,000 rpm » OCR non relu, rpm à vérifier visuellement) ; 1 210 l/s @ 5 750 rétrogradé en contre-vérification (elferclassic, level C) — cf. tableau ci-dessus.
 → M64-ACQ-0005 (le débit total 1 010 l/s est publié, pas la géométrie de la roue).
- Désignation de banc (gauche/droite) et numéros de pièce des variantes : à confirmer sur plaque.
  - Note revue 2026-09-27 : la dérivation du motif de goujons depuis « 98,07/43,27 » est REJETÉE —
    ce sont des cotes de pignon d'arbre à cames (« Engine, Cylinder Head, Valve Drive », OCR non
    relu), pas le motif de vis. Acquis goujons : 12× M8×22 par culasse (level A). Motif, hauteur de
    culasse, épaisseur de joint = métrologie physique (ACQ-0001). Acquis via `catalog/sources/src-porsche-993-us-parts-guide-engine-cylinders.json` (level A ; « quantités et références, non une cotation
    géométrique » ; licence Porsche AG, référence interne, redistribution interdite) et `catalog/manual/993-workshop-manual-measurements.json` p.148
    (« 18 | Studs M8 x 22 2 », quantité + filetage seuls). Bonus ACQ-0004 : entraxes
    vilebrequin→paliers intermédiaires 133,57 et 78,77 ±0,25 mm (p.177, à relire visuellement).
- Profil de came : non public → M64-ACQ-0002.
  - Partiellement couvert 2026-09-27 (lane valvetrain; SINGLE_SOURCE miroir d'atelier non relu; pages citées `ocr_unreviewed` sauf pp. 152–157 checkées; Valve Drive = chapitre 15) : p.153 alésage de presse du guide g = 8.00–8.015 mm avec **jeu guide/tige 0.06–0.08 mm** (tige 8 mm ⇒ alésage 7.92–7.94 mm implicite); p.151 dimensionnement des pieces de rattrapage (levée ≥ 0.2 mm admission, valeur outil 0.6 mm échappement; Taille 1 −0.5 mm / Taille 2 −1.0 mm; comparateur 1.85/2.25 mm); p.152 contrôle de rétention tête/siège à 10 mm (fragment « inlet 0.80 / exhaust 0.80 » vraisemblablement un code d'alésage, non un jeu); p.155 siège/stack 49+0.1 / 42.5+0.1 / 51… tronqué. Profil complet (cercle de base, flancs, durées, ressorts) : inconnu → ACQ-0002 reste ouvert.
  - Partiellement couvert 2026-09-27 (lane valvetrain, à vérifier contre manuel autorisé) : distribution M64 Turbo à 1 mm de levée, 0 jeu : admission 12° ADPM / admission ferme 63° APPM ; échappement ouvre 56° APPM / ferme 5° ADPM ; recouvrement au PMH 1,01 ± 0,04 mm (réf. 0,1 mm) ; pignons d'arbre à cames 993 105 247 51 (G) / 993 105 246 51 (D). Source : miroir atelier (workshop-manuals.com), SINGLE_SOURCE non relu — non réconcilié avec le manuel local p.175 (OCR). Profil complet (cercle de base, flancs, durées, centroïdes) et ressorts (raideur, longueur libre, hauteur montée, efforts) : toujours inconnus → ACQ-0002 reste ouvert.

- Carte compresseur K16 : non publique → M64-ACQ-0003.

## Sources consultées (identifiants à enregistrer dans catalog/sources/)

1. Brochure Porsche UK « 993 the Turbo », 1995, archive statique anstack (GitHub) — fiche technique.
2. 993 Technical Specification Booklet (usine) — données Carrera/Carrera 4.
3. Porsche 993 US Parts Guide (porscheknowledge.com) — lignes de partage, visserie, poussoirs, entraînement par courroie, turbine de ventilation.
4. Supplément OBD 1996 « Engine Specifications » (993 Carrera M64/23-24) — architecture commune M64 : allumage, rapport ventilateur, débit, distribution hydraulique, carter sec.

## Règle appliquée

Aucune valeur SINGLE_SOURCE ou ASSUMPTION ne migre dans le code de géométrie
sans promotion préalable (ADR-0004, charte projet).

---

## Exécution du scaffold PicoGK (2026-09-27, soir)

- Build vérifié dans le conteneur `m64-engineering-worker` (image
  `m64-engineering-worker:latest`) : SDK .NET 8.0.131, PicoGK 2.3.0 compilé
  depuis `/opt/PicoGK` (cible retendue en `net8.0`, le paquet NuGet officiel
  exige `net9.0`).
- Le runtime natif `picogk.so` est exposé sous le nom attendu par le binding
  (`picogk.26.2.so`) et la visionneuse tourne sous `xvfb-run` (pas d'écran).
- Sorties exportées et copiées dans le dépôt :
  `twins/m64-engine-system/picogk/out/m64-engine-layout.stl` (326 296
  triangles, voxel 5 mm) et `m64-layout.log`. Le `.vdb` reste dans le worker
  (`/build/picogk/out`).
- La géométrie reste au statut `F1_envelope` : poutres et sphères englobantes,
  les valeurs ASSUMPTION du fichier `M64EngineLayout.cs` ne deviennent
  exploitables qu'après promotion via les contrats `M64-ACQ-*`.

## Additif K16 (lane de recherche K16, 2026-09-27 soir)

Rapport final de la lane K16 (read-only, dépôt vérifié non modifié par la lane) :

- Identité recoupée : gauche = BorgWarner/KKK **5316-988-6736** (Porsche 993 123 013 51→52),
  droit = **5316-988-6735** (993 123 014 51→52), désignation **K16-2467GGA/8.88** des deux côtés
  (CROSSCHECKED : pages TurboMaster 6735/6736 consultées en direct, catalogue BorgWarner, cross-ref design911).
- Roues (SINGLE_SOURCE Invasion Auto) : turbine ⌀induit 54,96 / ⌀exduct 48,97 mm, 12 pales ;
  compresseur ⌀induit 40,6 / ⌀exduct 60,5 mm, 6+6. A/R turbine **8,0 cm²** (CROSSCHECKED deux
  catalogues vendeurs). Angles de volute α 307,5° / β 70°. Wastegate 5825-110-4006, ressort
  0,50 bar / lève 4,20 mm (SINGLE_SOURCE). Carter palier gauche 5316-151-0008 ≠ droit 5316-151-0002.
- Pression de suralimentation : 0,8 bar effectif retenu (brochure chriffrée dans Christophorus /
  catalogues) ; la notice « 1,0 bar » du relevé initial est une pression de consigne max, la
  lecture 350 kPa absolue est conservée mais à re-vérifier sur la brochure papier.
- **Carte compresseur toujours absente du domaine public** → M64-ACQ-0003 reste bloquant ;
  rendement, jeux internes, vitesse rotor maxi, journal/biels non publiés.
- Fiches sources créées : `SRC-TURBOMASTER-993-K16-6736-LEFT-UNIT`,
  `SRC-INVASIONAUTOPRODUCTS-993-K16-INTERNAL-DATA` (validateur sources OK, 358 enregistrements).
