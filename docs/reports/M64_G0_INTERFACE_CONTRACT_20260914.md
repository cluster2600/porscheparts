# M64 — G0, contrat d'interfaces critiques

14 septembre 2026. Portée : les huit `critical_interfaces` du
[contrat M64](../../twins/m64-cylinder-head/interface-contract.json), passé en
`schema_version` 2. Recherche limitée aux sources déjà présentes ou citées dans le
dépôt. Scan 935 privé, SSH et Vast indisponibles.

**Résultat : 0 interface trouvée, 5 partielles, 3 absentes. Aucune valeur
nominale ni tolérance n'est renseignée.** Les faits partiels sont enregistrés dans
`documented_partial_facts`, avec `promoted_to_nominal: false`.

## Extension du schéma et du validateur

Chaque interface porte maintenant `status` (`absent` / `partial` / `found`),
`source_locator`, `confidence` et `documented_partial_facts`. En schéma v2,
`validate_interface_contract.py` refuse :

- une valeur nominale ou une tolérance sans source enregistrée, localisateur et niveau de confiance ;
- `found` sans valeur nominale **et** tolérance ;
- `partial` sans fait documenté ;
- un fait partiel incomplet, à source non enregistrée ou promu en valeur nominale.

Deux sources ont été enregistrées : M1 (manuel 993 Carrera, registre local) et T1
(bulletin PCNA 9404). Les blocages de fabrication restent inchangés.

## Tableau par interface

Légende de confiance : *table* = table structurée issue du manuel, page non relue ;
*OCR* = occurrence OCR non relue ; *TSB* = bulletin relu visuellement le 7 septembre.

| Interface | Statut | Ce que disent les sources | Source et localisateur | Applicabilité |
|---|---|---|---|---|
| main_stud_axes | partiel | Goujons BM 8 × 20 / BM 8 × 50 ; serrage de culasse 20 Nm puis 90° | P1 p.58 pl. 103-00 rep. 5–6 ; M1 couples p.60 (*table*) | 964 M64.01/02/03 ; 993 Carrera. **Aucune coordonnée d'axe** |
| cylinder_register_diameter | absent | — L'alésage de 100 mm (P3) ne définit pas le registre ; la surface de 145 mm (T1) est une cote de réparation | — | — |
| cylinder_register_depth | absent | — | — | — |
| sealing_surface_definition | partiel | Joint acier 96410411520 placé dans la gorge du **cylindre** ; après réparation : Ø 145 mm, enlèvement de 0,10 ± 0,02 mm (0,20 mm au maximum), 32 µin | T1 p.1, 3 et 4 fig. 4 (*TSB*) | Réparation Carrera 2/4 1989–1991 uniquement ; ne constitue pas la définition de la portée neuve |
| cam_carrier_axes | partiel | Porte-arbres / culasse en M8, 23 Nm ; pignon d'arbre M12 × 1,5, 120 Nm | M1 couples p.60 (*table*) | 993 Carrera 2V ; **aucun axe de palier ni hauteur** |
| oil_feed_and_return_interfaces | absent | Seule piste : une bride vissée M24 × 1,5, côté **carter** et non culasse | — | — |
| intake_and_exhaust_flange_interfaces | partiel | Fixation échangeur / culasse à 28 Nm, filetage non indiqué | M1 couples p.61 (*table*) | 993 Carrera ; ni motif de fixation ni bride |
| seat_guide_and_spark_plug_interfaces | partiel | Bougie M14 × 1,25, 30 Nm ; cote « g » de guide 8,00–8,015 mm ; benchmark de soupapes 40 / 33 mm | M1 couples p.60 (*table*) ; M1 p.153 l.17 (*OCR*) ; S2 p.4 | 993 Carrera 2V ; kit Swindon 4V (tiers). Ni axes, ni inclinaisons, ni serrages |

Pistes non retenues : le [registre MAHLE](../../twins/m64-cylinder-head/valve-module-documentary-references-20260907.json)
(soupapes 2V Carrera et tables génériques de serrage des sièges) ne cote aucune
interface de culasse M64 Turbo. Les pages 152–157 du manuel restent non relues
(exemplaire introuvable, voir le [registre](M64_INTERFACE_SOURCE_REGISTER.md)).

## Mesures physiques à prendre sur une vraie culasse

Référentiel proposé : **A** = plan d'étanchéité culasse–cylindre (3 points de
palpage), **B** = axe du registre/centrage du cylindre considéré, **C** = axe du
goujon avant côté chaîne. Mesures sur MMT à 20 ± 1 °C, pièce stabilisée 4 h,
variante (numéro moteur, M64.50/60) et état (neuve/rectifiée) enregistrés,
3 répétitions. Les incertitudes visées (k = 2) sont des **objectifs de
métrologie** et non des tolérances de conception.

| Interface | Grandeurs | Instrument | Référence | Incertitude visée |
|---|---|---|---|---|
| main_stud_axes | Position XY de chaque trou de goujon, diamètre, perpendicularité à A, entraxes cylindre à cylindre | MMT palpeur ; tampons lisses | A, B, C | ±0,02 mm position ; ±0,01 mm Ø |
| cylinder_register_diameter | Ø du centrage (moyen, circularité, 4 hauteurs) | MMT, ou alésomètre à 3 touches étalonné | A, B | ±0,005 mm |
| cylinder_register_depth | Profondeur du centrage par rapport à A ; rayon ou chanfrein de fond | MMT ; comparateur sur marbre | A | ±0,01 mm |
| sealing_surface_definition | Ø intérieur/extérieur de portée, planéité, Ra/Rz, relief éventuel de gorge côté culasse ; gorge du cylindre en complément | MMT ; rugosimètre à palpeur (Lc 0,8 mm) ; règle et cales | A | Planéité ±0,005 mm ; Ra ±10 % ; Ø ±0,02 mm |
| cam_carrier_axes | Plan d'appui du porte-arbres (hauteur et parallélisme à A), trous M8 (position), axe de palier projeté par rapport à B | MMT ; montage de porte-arbres réel pour l'axe | A, B, C | ±0,02 mm hauteur ; ±0,02 mm axe |
| oil_feed_and_return_interfaces | Position, Ø et profondeur des passages d'alimentation et de retour ; joints | MMT ; jauges ; endoscope ; CT si accessible | A, C | ±0,05 mm position ; ±0,05 mm Ø |
| intake_and_exhaust_flange_interfaces | Plans de bride (orientation par rapport à A), motif des goujons, contour des conduits à la face | MMT ; pige de filetage ; scan structuré calé sur A/B/C pour le contour | A, B, C | ±0,03 mm plan et goujons ; ±0,1 mm contour |
| seat_guide_and_spark_plug_interfaces | Axes et inclinaisons des soupapes et de la bougie, Ø logement de siège et de guide (serrage), hauteur de siège, profondeur et portée de la bougie | MMT avec piges dans les guides ; alésomètre ; calibre M14 × 1,25 et jauge de profondeur | A, B | ±0,05° angle ; ±0,005 mm Ø logements ; ±0,02 mm hauteurs |

Chaque mesure devra entrer au registre avec instrument, étalonnage et
échantillons, conformément aux [portes qualité](../QUALITY_GATES.md). Une mesure
d'une culasse 2V de série renseigne une interface de montage, **pas** la
géométrie interne de la nouvelle culasse 4V.
