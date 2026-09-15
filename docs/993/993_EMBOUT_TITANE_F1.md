# Embout d'échappement titane — première pièce titane du dépôt

Sélectionnée par [décision 0007](../decisions/0007-premier-titane-embout-echappement.md).

## La sélection, pas le choix

La grille de [`TITANIUM.md`](../TITANIUM.md) et les trois familles où l'additif
gagne ont été appliquées aux **32 fiches** du catalogue par
`scripts/screen_titanium_candidates.py`. Cinq pièces seulement ressortent
éligibles ; vingt-sept tombent sur la classe de sécurité, l'absence de famille
additive, la température, le besoin de conduire la chaleur ou l'obligation de
garder une raideur acier.

Le criblage est **fail-closed** : ajouter une fiche au catalogue sans la juger
le fait échouer. Un test le vérifie.

Le collecteur d'échappement obtient le meilleur score du lot, **+7**, et se fait
écarter à 900 °C : c'est un cas nickel. L'embout suit à +6 et gagne parce que
tout converge — consolidation du conduit, de la coque et des huit nervures en un
seul corps, cavité annulaire qu'aucun usinage ne produit, petite série, rupture
bénigne, et une seule interface à mesurer.

## Ce que la géométrie donne

Étape 02 **`passed`** : maillage étanche, monocomposant, 13 820 triangles, lié au
STEP par SHA-256.

Étape 03 `completed_screening`, orientation `roll_y_25`, **4 936 couches
réellement tranchées à 30 µm** :

| grandeur | valeur |
|---|---|
| hauteur de construction | 148,1 mm |
| nouveaux îlots | 2 |
| couches à aire non soutenue | 1 044 |
| aire non soutenue maximale | 0,603 mm² |
| enveloppe conservative de supports | 7,24 cm³ |
| épaisseur locale, premier centile | 0,600 mm |
| épaisseur locale minimale | 0,460 mm |
| volume de poudre piégé au voxel de 1 mm | aucun détecté |

La paroi minimale de 0,460 mm passe le minimum procédé EOS de 0,3 à 0,4 mm, mais
sans confort. Et **le dépoudrage n'est pas démontré** : un canal annulaire de
2,7 mm sur 120 mm de long ne se juge pas à un criblage voxel de 1 mm. Endoscopie
ou tomographie exigées.

## Les deux alliages, et le chiffre qui les sépare

| | Ti-6Al-4V | Ti-6242 |
|---|---|---|
| masse de criblage | **212,3 g** — contre 406,4 g en IN625, soit **−47,7 %** | 217,6 g |
| plafond de fluage | 400 °C | 550 °C |
| marge à 427 °C | **−27 °C** | +123 °C |
| épaisseur de couche publiée | 30 µm | aucune |
| paroi minimale publiée | 0,3 à 0,4 mm | aucune |
| traitement thermique publié | 800 °C 2 h argon | aucun |
| atelier de service | **partout** | **nulle part** |
| portes fermées, étape 04 | 6 | 10 |

Les deux routes s'excluent proprement. Le Ti-6Al-4V est disponible, documenté,
et bloqué par **un seul chiffre**. Le Ti-6242 règle ce chiffre et perd tout le
reste : première mise en œuvre LPBF publiée en 2020, c'est un sujet de recherche.

## Ce qu'il faut aller chercher

Les 427 °C viennent d'un cas synthétique du criblage F0 — gaz à 850 K, moteur
3,8 L à 6 500 tr/min, deux sorties — **jamais mesuré sur un véhicule**. Un
embout réel, en aval du silencieux, peut fonctionner cent degrés plus bas.

Un thermomètre infrarouge sur la sortie après roulage tranche la question. À
350 °C ou moins, le Ti-6Al-4V passe et la pièce se commande chez n'importe quel
atelier titane. À 427 °C confirmés, le titane sort du jeu à coût raisonnable et
la réponse redevient l'IN625, deux fois plus lourd mais achetable.

Aucun calcul de ce dépôt ne remplacera cette mesure.

## Reproduction

```bash
make titanium-screen        # criblage des 32 fiches
make tip-routes             # les deux cartes de route, étape 04
make titanium-screen-check tip-routes-check
python3 -m unittest tests.test_993_exhaust_tip_titanium_f1
```

La géométrie et le criblage LPBF demandent l'image verrouillée du dépôt :

```bash
docker run --rm -v "$PWD":/w -w /w ghcr.io/cluster2600/3dprinting993-mesh-cfd \
  python3 parts/993-exh-oval-tip-in625-f0-0001/source/oval_exhaust_tip.py \
  --material ti64 \
  --out parts/993-exh-oval-tip-ti-f1-0001/derived/oval_exhaust_tip_ti_f1.step \
  --surface parts/993-exh-oval-tip-ti-f1-0001/derived/oval_exhaust_tip_ti_f1.stl \
  --report parts/993-exh-oval-tip-ti-f1-0001/evidence/engineering-screen-ti64.json
```

Le maître est partagé avec la variante IN625 : **une seule géométrie, plusieurs
métaux**. C'est `--material` qui change la carte, pas le dessin.
