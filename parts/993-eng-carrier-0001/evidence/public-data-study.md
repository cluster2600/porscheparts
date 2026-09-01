# Étude sur données publiques — 993-ENG-CARRIER-0001

Contexte : ni la pièce ni les instruments de mesure ne sont disponibles. Tout
doit venir de sources publiques.

## Ce que cette contrainte plafonne

`docs/QUALITY_GATES.md` demande des mesures critiques et une revue CAO pour
atteindre `dimensionally_reviewed`, et un montage prouvé pour
`prototype_fitted`. Aucune source publique ne fournit ni l'un ni l'autre.

**La fiche ne peut donc pas dépasser `concept`.** Ce n'est pas une lourdeur
administrative : sans les entraxes de fixation réels, une pièce fabriquée ne
se monterait pas, et sans section réelle, aucun calcul ne représente la pièce.

Pour une pièce présumée critique, la conséquence est nette : ce document est une
**étude d'orientation**, pas un dossier de fabrication.

## Le relevé PET a tranché l'identité de la pièce

Source : `SRC-PORSCHEFANATICS-OEM`, transcription tracée du catalogue PET
993 révision KAT 17, illustration 109-00 page 115.

| Référence | Berceau | Véhicules | Position PET |
|---|---|---|---|
| 993 115 021 **53** | **Turbo** | 993 Turbo 1995-1998 | groupe « Engine suspension Turbo », pos. 17 |
| 993 115 021 90 | standard | Carrera, C4, S, 4S — hors Turbo et RS | groupe « Engine suspension », pos. 1 |
| 993 115 021 41 | RS | 993 RS | groupe « Engine suspension », pos. 1 |

Trois conséquences directes :

1. **La pièce demandée est le berceau Turbo**, et cette destination est établie
   par le groupe du catalogue, pas déduite d'une compatibilité de revendeur.
   La fiche a été corrigée en conséquence : elle ne mentionne plus le -90 comme
   s'il s'agissait de la même pièce.
2. Les trois berceaux sont des références distinctes. Rien ne permet aujourd'hui
   de dire en quoi ils diffèrent : aucune cote n'existe dans un catalogue.
3. **Le berceau tubulaire du marché spécialisé est explicitement non Turbo.**
   Le berceau Turbo n'a donc aucune alternative de rechange connue — ce qui, pour
   la phase 1, en fait un cas documenté de pièce difficile à obtenir.

Matière, masse et prix restent inconnus **y compris dans le relevé PET** : le
catalogue ne les publie pas. Ce n'est pas une lacune du relevé, c'est la nature
d'un catalogue de pièces.

## Recherche dans les forums — ce qui a survécu à la vérification

Les résumés de moteur de recherche annonçaient du solide : construction soudée,
corrosion et fissuration en extrémité de berceau, dépose possible sans sortir le
moteur, kits de renfort à souder, obligation de renforcer le berceau avec des
supports rigides.

**Aucune de ces affirmations n'a survécu à l'ouverture des pages.** Les trois
pages accessibles citées à l'appui — deux fils 911uk et un fil du club GB — ne
mentionnent pas le berceau moteur. Les fils Rennlist qui le mentionnent
refusent l'accès automatisé (HTTP 403).

C'est exactement le piège que décrit `docs/SOURCE_POLICY.md` : deux sources qui
se recopient ne font pas deux confirmations.

**Second passage, hors Rennlist.** En cherchant sur les forums germanophones et
britanniques plutôt que sur celui qui bloque, deux pages se sont ouvertes et ont
confirmé une partie de ces affirmations — sur le **964**, pas sur le 993 :

- `SRC-PCGB-CRACKED-ENGINE-MOUNT-BRACKET` : la pièce fissure, se répare par
  soudure, et le renfort rapporté est courant. Un contributeur signale l'effet
  secondaire : *« the welding of the strengthening gusset caused it to warp. So
  back to the shop and 5 mins under a press sorted it. »* Photographie jointe.
- `SRC-PFF-RENNLINE-MOTORTRAEGER` : berceau — appelé *Schwert* — fissuré,
  *« das Schwert angebrochen ist »*, moteur *« schief hängt »*, deux
  photographies. Une révision usine *« leicht verstärkt »* vers 1991 est évoquée,
  sans référence à l'appui. Le renfort du marché est cité autour de 614 €, ce qui
  pousse plusieurs contributeurs à souder eux-mêmes.

Ce que cela établit : **un mode de défaillance de famille**, la fissuration, et
une pratique de réparation par soudure dont l'effet secondaire est le voilage.

Ce que cela n'établit pas : la construction, la matière et le comportement de la
référence Turbo `993 115 021 53`, qui est une pièce distincte. Et une pièce qui
se voile au soudage d'un simple gousset dit quelque chose de sa raideur : c'est
une information de conception, pas une anecdote.

Ce qui est vérifié, en revanche, par lecture directe
(`SRC-911UK-993-RUST-LOCATIONS`) : la corrosion du 993 touche notamment les
**longerons arrière** et les **supports arrière de groupe motopropulseur**.
L'environnement du berceau est corrosif, ce qui pèse sur le choix matière et sur
l'isolation galvanique si le titane était retenu.

## Recherche en allemand — ce qu'elle a changé

Recherche menée le 28 août 2026 sur `Motorträger`, forums germanophones,
revendeurs allemands et brevets. Résultat : **aucune donnée nouvelle sur la
pièce**.

- La boutique Porsche Classic allemande apparaît dans les résultats, mais son
  hôte ne résout toujours pas (échec DNS confirmé une seconde fois).
- Les manuels gratuits d'Autodoc pour le 993 couvrent l'huile moteur et les
  balais d'essuie-glace, rien de structural.
- Les forums allemands (Carpassion, PFF, Elfertreff) traitent de la dépose
  moteur, mais l'accès automatisé est limité (HTTP 429) ; une seule remarque
  utile ressort des extraits, sur des goujons très massifs et souvent corrodés.
- Les spécialistes allemands publient des masses pour d'autres pièces allégées
  (supports de pare-chocs aluminium, gain annoncé d'environ 3,5 kg), mais aucun
  berceau moteur allégé avec masse annoncée.
- Aucun brevet Porsche pertinent trouvé sur le berceau d'un 911 à moteur arrière.

La conclusion tient en une phrase : **la géométrie de cette pièce n'existe dans
aucune source publique, dans aucune langue testée.**

## Ce que les données publiques ont réellement donné

| Donnée | Valeur | Source | Niveau |
|---|---|---|---|
| Groupe et fonction | Motorträger, groupe 109-00 | teile.com (titre indexé, page 403) | C |
| Références voisines | 993 115 021 53 et -90 | résultats de recherche revendeurs | C |
| Couple moteur | 330 Nm à 5 000 tr/min (Carrera MY94-95) | `SRC-ELFERSPOT-993-PORTRAIT`, page lue | C |
| Masses à vide | 1 370 kg Carrera, 1 500 kg Turbo, 1 295 kg GT2 | idem | C |
| Précédent marché | berceau tubulaire de remplacement 964/993 | Rennline (page 403) | D |

## Ce qu'elles n'ont pas donné

- Entraxes et diamètres des fixations, côté caisse et côté supports moteur.
- Sections, épaisseurs, mode d'obtention, matière d'origine.
- Dégagements disponibles dans la baie moteur.
- **Masse du moteur seul.** Un chiffre de 232 kg (atmosphérique) et 268 kg
  (turbo) circule, mais il vient d'un résumé de fil de forum que je n'ai pas pu
  ouvrir. Il n'est donc pas retenu comme entrée.

Sans masse supportée vérifiée, le premier chiffre du premier cas de charge
manque déjà.

## Ce que le calcul peut trancher sans la pièce

La question « le titane a-t-il un sens ici ? » ne dépend pas de la géométrie
exacte. Elle dépend des matériaux. `source/material_tradeoff.py` la traite sur
un profil creux générique de 600 mm, en flexion, et recoupe l'analytique par un
calcul CalculiX.

| Comparaison | Résultat |
|---|---|
| Géométrie identique | Ti-6Al-4V 44 % plus léger, mais **1,84 fois plus souple** |
| Raideur identique | section à agrandir de 17 %, et **23 % plus léger** malgré cela |
| Masse identique | titane 1,70 fois plus raide |

Indice matériau en flexion à section libre, `E^0.5 / ρ` : acier 58,4 — Ti-6Al-4V
76,2, soit **+31 % en faveur du titane**.

Recoupement EF contre théorie des poutres : +2,3 % (acier), +2,2 % (titane).
L'écart est du bon signe et du bon ordre — cisaillement et effet d'encastrement
assouplissent le modèle volumique.

### Ce que la fiche produit du vendeur a établi

Quatre photographies et une fiche technique changent trois choses.

**La pièce est monobloc.** Une lame incurvée à section variable, percée de deux
grands trous d'allègement et de plusieurs trous de fixation, terminée à chaque
extrémité par un bossage cylindrique, avec une finition dorée évoquant une
zingaison passivée jaune. Rien n'indique une construction soudée.

Cela ne contredit pas les forums, cela les explique : les renforts soudés dont
ils parlent sont des **goussets rapportés sur une pièce monobloc**. Souder sur
une pièce forgée et traitée, c'est exactement ce qui la voile.

**La matière est presque certainement de l'acier.** Recoupement de densité, à
1,96 kg pour 600 mm de long :

| Matière | Volume | Section moyenne équivalente |
|---|---:|---|
| Acier | 250 cm³ | 416 mm², soit ~10 mm sur 40 mm de haut |
| Aluminium | 726 cm³ | 1210 mm², soit ~30 mm sur 40 mm de haut |
| Ti-6Al-4V | 442 cm³ | 737 mm², soit ~18 mm sur 40 mm de haut |

La lame visible sur les photographies est élancée. L'hypothèse aluminium
demanderait une pièce trois fois plus épaisse : elle est écartée.

**Le prix était faux d'un ordre de grandeur.** Le berceau Turbo neuf est affiché
à **1 788 USD** hors port, disponibilité « available soon ». Le chiffre de 225 à
270 € rapporté plus tôt par un résumé de recherche ne tenait pas.

Et l'encombrement de 600 × 50 × 50 mm concorde avec les proportions visibles :
il décrit vraisemblablement la pièce arrondie au centimètre, pas un colis.

### Conclusion technique, révisée par la masse annoncée

Le raisonnement matériau reste valable : le titane est défendable sur une pièce
en flexion **si la section peut grossir de 17 %**.

Mais une masse annoncée de 1,96 kg change la réponse. Le gain à raideur égale
serait d'environ **0,45 kg**, soit **0,03 % de la masse du véhicule**.

C'est le prix total du concours. Pour l'empocher il faudrait redessiner les
sections, établir des cas de charge complets, passer une revue d'ingénierie
formelle, qualifier un procédé LPBF, contrôler la pièce, et maîtriser grippage
et couple galvanique dans un environnement dont la corrosion est documentée.

**Sur ces chiffres, le titane n'est pas justifié sur cette pièce**, et
`docs/TITANIUM.md` le disait déjà dans sa liste « quand il ne l'est pas ».

Le défaut constaté sur la famille n'est d'ailleurs pas la masse : c'est la
**fissuration**. La pièce utile n'est donc pas une pièce plus légère, c'est une
pièce plus endurante. C'est exactement ce que le marché traite déjà, par un
renfort vendu autour de 614 € et par de la soudure d'atelier.

### Ce que le prix change, en revanche

À 1 788 USD la pièce neuve, sans alternative de rechange connue, sur une
référence donnée « available soon » donc pas en stock, l'argument de reproduction
cesse d'être la masse et devient **la disponibilité et le coût**.

C'est un motif légitime, et c'est même le cœur du projet. Il ne déplace en rien
la barre de sécurité : la pièce reste présumée critique, donc revue d'ingénierie
formelle, cas de charge, contrôle. Mais reproduire une lame en acier à géométrie
équivalente est un problème d'ingénierie ordinaire, là où gagner 450 g en titane
n'en valait pas la peine.

Le procédé plausible n'est d'ailleurs plus la fabrication additive : une lame
monobloc en acier relève de l'usinage dans la masse, du forgeage ou de la
découpe-pliage, selon ce que la géométrie réelle révélera.

Cette conclusion tient sur des chiffres communiqués sans source, et tombe si la
masse réelle est différente. Elle est de toute façon plus solide que le silence :
elle dit ce qu'il faudrait mesurer pour la renverser.

## Chemins réellement ouverts, sans pièce ni outillage

1. **Le relevé de géométrie de caisse à 20 USD** (`SRC-CARGEOMETRY-993-BODY`) —
   à considérer avec prudence après lecture de ses conditions le 28 août 2026 :

   - contenu annoncé : montants, ouvertures de portes et vitrages, soubassement,
     cotes diagonales, capot — orienté réparation collision. **Les points
     d'ancrage du groupe motopropulseur n'y sont pas annoncés.**
   - service fourni « AS IS », sans garantie d'exactitude ni d'exhaustivité, avec
     une clause excluant explicitement toute réclamation si une réparation
     fondée sur ces données tourne mal ;
   - aucune concession de droit de rediffusion : donnée de référence uniquement,
     qui reste hors du dépôt ;
   - origine des données non nommée ;
   - la commande demande nom, courriel, téléphone et **numéro de châssis**.

   Conséquence : écrire au vendeur avant d'acheter, pour demander si la feuille
   993 couvre les ancrages arrière du groupe motopropulseur. Vingt dollars ne
   sont pas une somme, mais acheter sans cette réponse, c'est payer pour un
   repère de caisse dont on ignore s'il répond à la question posée.
2. **La documentation d'atelier officielle**, par deux voies légales :

   - **PCSS / TSI** (`SRC-PORSCHE-PCSS-TSI`), portail Porsche d'information de
     réparation ouvert aux ateliers indépendants au titre des règlements RMI,
     avec abonnement payant à la durée. Voie la plus courte si la couverture
     s'étend au 993 — à vérifier, le portail ne répond qu'en JavaScript.
   - **Manuel d'atelier WKD 483 121** (`SRC-PORSCHE-WORKSHOP-MANUAL-993`), huit
     volumes, vendu neuf et d'occasion.

   Attente à corriger tout de suite : un manuel d'atelier donne des couples de
   serrage, des procédures et un ordre de dépose. **Il ne contient pas de plan
   coté de pièce.** Il ne fournira donc pas la géométrie du berceau. Il apporte
   en revanche la précontrainte de boulonnerie, qui manque au cas de charge.

   Les copies PDF circulant sur Scribd, SlideShare et les revendeurs de manuels
   restent écartées : aucun droit de rediffusion démontrable.
3. **Demander des mesures à la communauté**, avec le plan de mesure de cette
   pièce et `scripts/capture_caliper.py` : une personne possédant la pièce peut
   produire une fiche de mesure exploitable. La traçabilité de l'instrument est
   alors ce qui sépare une contribution utilisable d'un chiffre de forum.
4. **Poursuivre l'étude matériau** sans la pièce : elle est déjà concluante sur
   le principe et ne demande aucune acquisition.

## Ce qui reste interdit

- Déduire des cotes d'une photographie de vente sans échelle.
- Fabriquer une pièce sur une géométrie estimée.
- Faire porter le moteur par un tirage polymère.
- Publier quoi que ce soit comme pièce libérée sans revue d'ingénierie formelle.
