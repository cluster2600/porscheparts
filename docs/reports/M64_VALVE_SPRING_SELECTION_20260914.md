# M64 4V — sélection de ressorts de soupape sur fiches fournisseurs

**Statut : criblage sur catalogues publics, pas qualification.** Rien n'a été commandé, aucun fournisseur contacté.
Les chiffres des ressorts sont recopiés des pages produit (accès 2026-09-14). Le reste suit le modèle V1
([M64_V1_VALVETRAIN_20260914.md](M64_V1_VALVETRAIN_20260914.md)) : came, masses, raideurs et jeux y sont **supposés**.

Données : [spring_candidates.json](../../twins/m64-cylinder-head/source/valvetrain/spring_candidates.json) ;
script : [spring_selection.py](../../twins/m64-cylinder-head/source/valvetrain/spring_selection.py) ;
résultats : [spring-selection-results.json](../../twins/m64-cylinder-head/evidence/valvetrain-v1/spring-selection-results.json) ;
tests : [test_m64_spring_selection.py](../../tests/test_m64_spring_selection.py) (11, unittest).

## Méthode

- Raideur k = (F_ouvert − F_siège) / levée, si les deux points sont publiés ; sinon la raideur publiée est utilisée.
  Chez Supertech, « Rate: X mm » se lit en lbf/mm : (204 − 76)/10 = 12,8 sur SPR-HM1007BE.
- Chaque ressort est monté à la hauteur de sa fiche. La hauteur du logement est un paramètre non sourcé.
- Levées 11,5 / 9,6 mm. Masse ressort 45 g et coupelle 13 g **supposées** : aucune n'est publiée.
- Critères : marge ≥ 1,25 à 8 000 tr/min ; réserve à spires jointives ≥ 1 mm à levée max ;
  décollement ou rebond 1-ddl ≤ 0,05 mm à 7 500 (jeu à chaud).
  Deux contrôles non bloquants : Ø ext ≤ 30 mm (logement **supposé**) et levée ≤ levée max publiée.
- **Contrainte : `not_computable` pour tous.** Aucun fournisseur ne publie le diamètre de fil.
  Aucune limite matériau n'est donc appliquée ni sourcée.

## Tableau (admission / échappement)

| # | Réf. | Type | Ø ext | H montée | Siège | Ouvert publié | k N/mm | Marge 8 000 | N à M = 1,25 | Décoll. 7 500 mm | Réserve spires mm (+20 % levée) | Levée max pub. | Prix | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | GSC Power-Division GSC5092 (991/992 GT3) | conique | n.p. | 40,0 | 113 lbf (503 N) | 265 lbf @ 13 mm | 52,0 | **1,36 / 1,56** | 8 350 | **0,042 / 0,035** | 4,3 / 6,2 (2,0) | 14,25 | 1 155 USD/24 | **passe** (Ø à confirmer) |
| 2 | PAC-1276X | beehive | 32,8 | 45,7 | 150 lbf | 420 lbf @ 16,8 | 71,6 | 1,84 / 2,10 | 9 710 | 0,014 / 0,009 | 7,0 / 8,9 | 16,5 | 305 USD/16 | Ø > 30, ressort drag trop haut |
| 3 | Ferrea S10122 (996 Turbo) | double | 28,0 | 33,5 | 98 lbf | 220 lbf @ 9 mm | 60,3 | 1,38 / 1,56 | 8 410 | 0,059 / 0,051 | 2,0 / 3,9 (−0,3) | **11,2 < 11,5** | 728 USD/24 | levée hors fiche, décoll. |
| 4 | Supertech SPR-H1021D (Honda K) | double | 30,0 | 40,4 | 95 lbf | 261 lbf @ 12 mm | 61,5 | 1,38 / 1,55 | 8 410 | 0,063 / 0,055 | 6,2 / 8,1 (3,9) | 15,3 | 606 USD/16 | décoll. marginal |
| 5 | Supertech SPR-TS1015 (2JZ) | double | 27,5 | 33,6 | 91 lbf | n.p. (raideur publiée) | 53,8 | 1,25 / 1,42 | 8 015 | 0,070 / 0,062 | 1,4 / 3,3 (−0,9) | 12,9 | 367 USD | limite |
| 6 | Supertech SPR-HM1007BE (S54) | beehive | 28,0 | 36,0 | 76 lbf | 204 lbf @ 10 mm | 56,9 | 1,21 / 1,34 | 7 860 | 0,102 / 0,088 | 1,7 / 3,6 | 14,0 | 1 060 USD/24 | échoue |
| 7 | Supertech SPR-2521/2 (S54) | double | 26,4 | 41,0 | 82 lbf | 186 lbf @ 10 mm | 46,3 | 1,10 / 1,25 | 7 510 | 0,088 / 0,078 | 5,0 / 6,9 | 14,5 | 944 USD/24 | échoue |
| 8 | Kelford KVS264 adm. (G16E) | beehive | n.p. | 35,0 | 100 lbf | 198 lbf @ 12 mm | 36,3 | 1,08 / 1,24 | 7 430 | 0,058 / 0,050 | 1,5 / 3,4 | n.p. | 504 GBP | échoue |
| 9 | Brian Crower BC1310 (2JZ) | double | 27,6 | 33,7 | 82 lbf | 180 lbf @ 10,2 mm | 42,9 | 1,06 / 1,20 | 7 360 | 0,120 / 0,078 | 3,6 / 5,5 | 11,94 | 18 USD/pc | échoue |

n.p. = non publié. Les URL figurent dans le JSON.

Écartés faute de fiche chiffrée accessible : Ferrea KT4034 (page 403), Kelford KVS02-BT (sans effort ouvert),
PAC-1204X/1205X (403), Kibblewhite 911/964 2V, Cat Cams, Schrick, Del West, Manley, Swindon, Protomotive.
Aucun kit Porsche 964/993 2V ne publie de fiche chiffrée. Le jeu d'origine 105 901 51, conçu pour des
poussoirs hydrauliques en 2V, n'est pas un candidat 4V.

## Recommandation

**Principale : GSC Power-Division GSC5092.** C'est le ressort conique du 991/992 GT3 : même famille flat-six
4V haute vitesse, régime annoncé 11 000 tr/min, coupelle titane et siège fournis. C'est le seul candidat
qui passe les trois critères durs, aux deux côtés : marge 1,36 à 8 000, décollement 0,042 mm à 7 500,
réserve à spires jointives 4,3 mm (2,0 mm même avec +20 % de levée), levée max publiée 14,25 mm.
Réserve : le Ø extérieur n'est pas publié.

**Alternative : Supertech SPR-H1021D** (ressort double Honda K, coupelle Ti Gr5). Marge 1,38 et grande réserve
à spires jointives (6,2 mm). Ø ext 30,0 mm publié, donc tout juste au Ø maxi supposé. Décollement 0,063 mm
à 7 500 : juste au-dessus du seuil, un écart qui est dans le bruit des raideurs supposées du modèle 1-ddl.

Le Ferrea S10122 (996 Turbo) a de bons efforts, mais sa fiche plafonne la levée à 11,2 mm, sous les 11,5 mm visés.

## Reste à confirmer

1. **Logement réel** : Ø lamage, hauteur montée, entraxe entre les deux ressorts d'un même côté. Rien de cela
   n'est conçu ; la vérification du Ø à 30 mm est une hypothèse.
2. **Masses** : ressort et coupelle titane non publiés ; 45 g + 13 g sont supposés. Il faut les pesées.
3. **Demande de fiche aux fournisseurs** (non envoyée) : Ø ext GSC5092, diamètre de fil, longueur libre,
   matériau et limite de fatigue. Sans elles, pas de contrainte ; sans elles, pas de fréquence de surge.
4. **Mesure au banc de ressort** : courbe effort-longueur, hauteur jointive réelle et dispersion sur le lot.
   Le Ferrea montre déjà un écart de 11 % entre sa raideur publiée et celle tirée de ses deux points.
5. Profil de came, raideurs de la chaîne et amortissement réels. Les régimes ci-dessus en dépendent directement.
