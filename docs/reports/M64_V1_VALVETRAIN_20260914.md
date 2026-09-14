# M64 V1 — distribution quatre soupapes : cinématique et dynamique simplifiée

**Statut : étude de sensibilité, pas qualification.** Aucune donnée de came M64,
aucune pesée, aucune corrélation banc. Chaque paramètre non sourcé est marqué
`assumed` avec justification dans
[valvetrain-v1-parameters.json](../../twins/m64-cylinder-head/evidence/valvetrain-v1/valvetrain-v1-parameters.json).
Les régimes ci-dessous sont les conséquences de ces hypothèses, pas des propriétés du M64.

Code : [valvetrain.py](../../twins/m64-cylinder-head/source/valvetrain/valvetrain.py),
[run_study.py](../../twins/m64-cylinder-head/source/valvetrain/run_study.py) ;
résultats et empreintes SHA-256 :
[valvetrain-v1-results.json](../../twins/m64-cylinder-head/evidence/valvetrain-v1/valvetrain-v1-results.json) ;
tests : [test_m64_valvetrain_v1.py](../../tests/test_m64_valvetrain_v1.py) (17, unittest).

## Hypothèses et provenance

| Donnée | Valeur adm. / éch. | Statut |
|---|---|---|
| Course | 76,4 mm | `sourced_reference` (P3) |
| Ø têtes | 40 / 33 mm | `sourced_reference` (Swindon S2, benchmark non retenu) |
| Levée max | 11,5 / 9,6 mm | `repository_design_candidate` (module V2) |
| Inclinaison axe soupape | 8° | `repository_design_candidate` |
| Bielle | 127 mm | `assumed` |
| Durée principale + 2 × rampe 40° | 240 / 236° vil. | `assumed` |
| Centres de levée | 105° ap. / 108° av. PMH croisement | `assumed` |
| Jeu froid ; Δ chaud | 0,10 ; −0,03 / 0,15 ; −0,05 mm | `assumed` |
| Masse équivalente (soupape + coupelle + commande + ressort/3) | 110 / 102 g | `assumed` |
| Ressort : fil 3,8, Ø moyen 22, 5 spires actives, L montée 40 mm, précharge 300 / 280 N | k = 38,8 N/mm (calculé) | `assumed` |
| Raideurs contact came / siège, amortissement ζ | 15 / 50 kN/mm, 0,05 | `assumed` |
| Jeu piston au PMH soupape fermée | 6,0 / 6,5 mm | `assumed` |
| Régime cible | 6 500 tr/min | `assumed` (scénario du dépôt) |

## Équations

- **Loi came** (angle vilebrequin φ, u = (φ − φc)/(Δ/2)) :
  C(φ) = h_r·R(φ) + A·(1 − u²)³(1 + c u²), c ∈ [0, 3) pour garder des flancs monotones.
  R est un créneau adouci par 10t³ − 15t⁴ + 6t⁵ sur chaque rampe. La loi est
  C² : accélération continue, jerk borné mais discontinu aux raccords.
  A = L_max + jeu_froid − h_r, donc la levée soupape à froid vaut exactement L_max.
- **Soupape** : x = max(C − jeu, 0) ; v = C′ω, a = C″ω², j = C‴ω³, avec ω en rad/s vilebrequin.
- **Ressort** : k = G d⁴ / (8 D³ n_a), longueur à spires jointives L_s = (n_a + 2) d.
  Contrainte de cisaillement τ = 8 F D K_w / (π d³) (facteur de Wahl), fréquence de surge f = ½ √(k / m_actif).
- **Marge** : M(N) = min sur a < 0 de (F₀ + k x) / (−m a). M ∝ 1/N², d'où
  N_décrochage = N_ref √(M_ref) et N_lim = N_ref √(M_ref / 1,25).
- **Piston–soupape** : jeu(φ) = d₀ + s(φ) − x(φ) cos α, avec la bielle-manivelle exacte
  s = r(1 − cos φ) + l − √(l² − r² sin² φ). Un avance/retard de came de ±10° est balayé.
- **1-ddl** : m ẍ = −k(x + x₀) − c ẋ + ⟨k_c(y − x) + c_c(ẏ − ẋ)⟩⁺ + ⟨k_s(−x) − c_s ẋ⟩⁺.
  Les deux contacts (came et siège) sont unilatéraux ; intégration RK4 à pas fixe
  (7 200 pas par cycle), troisième cycle retenu, jeu à chaud.

## Résultats (paramètres par défaut)

| Indicateur | Admission | Échappement |
|---|---|---|
| Accél. max + / − à 6 500 | 7 840 / −4 500 m/s² | 6 780 / −3 900 m/s² |
| Effort d'inertie max à 6 500 | 865 N | 694 N |
| Marge ressort à 6 500 | **1,40** | **1,53** |
| Décrochage quasi statique (M = 1) | **≈ 7 680 tr/min** | ≈ 8 030 tr/min |
| Limite à M = 1,25 | ≈ 6 870 tr/min | ≈ 7 190 tr/min |
| 1-ddl : micro-décollement > 0,05 mm | dès 6 250 | dès 6 250 |
| 1-ddl : affolement franc > 0,5 mm | 8 000 | 8 250 |
| Réserve à spires jointives | 1,9 mm (OK ≥ 1,0) | 3,8 mm |
| τ à levée max | **962 MPa** (élevé) | 842 MPa |
| Surge ressort | 562 Hz | 562 Hz |
| Vitesse d'appui sur rampe, froid / chaud | 0,51 / 0,45 m/s | 0,55 / 0,51 m/s |
| Jeu piston min (balayage ±10°, froid/chaud) | 4,3 mm (avance +10°) | 5,6 mm (retard −10°) |

L'avance de came réduit le jeu piston à l'admission et le retard le réduit à
l'échappement. Aucune interférence n'apparaît avec d₀ supposé ; ce résultat
dépend entièrement de ce d₀ non conçu.

**Sensibilité du décrochage quasi statique (±20 %, admission) :**

- durée principale : −20 % / +10 % ;
- diamètre du fil : −16 % / +8 %, mais le fil +20 % met les spires jointives en défaut ;
- masse soupape : +6 % / −5 % ;
- précharge : −4,5 % / +4,3 % ;
- levée : +6 % / −4 %, et la levée +20 % met les spires jointives en défaut ;
- masse de commande : ±2 % ;
- coefficient c : ≤ 2 %.

Le modèle 1-ddl montre un micro-décollement près de 6 250 tr/min, avant le
décrochage quasi statique. Il vient de la vibration du contact came excitée par
le jerk. Son amplitude dépend des raideurs et de l'amortissement supposés.

## Ce qui reste non établi

- Profil de came, levée, calage, jeu et type de commande (hydraulique ou mécanique) réels du M64 4V.
- Masses pesées, raideur et courbe du ressort, ressort double, frottement guide/joint.
- Raideurs de la chaîne cinématique, flexion d'arbre et de culbuteur, dynamique hydraulique.
- Géométrie réelle du piston, des encoches et de la chambre. Le jeu est ramené à un seul point axial.
- Dilatations à chaud calculées. Le Δ de jeu est seulement un paramètre.
- Surge du ressort modélisé comme un continuum. Seule sa fréquence est donnée ;
  la dynamique n'est pas couplée au train.
- Corrélation banc : aucune. Rien ici ne vaut sélection ni autorisation de fabrication.

## Contre-calculs en test

- Dérivées analytiques recoupées par intégration trapèze.
- Continuité C² et flancs monotones.
- Raideur et longueur jointive recalculées à la main.
- Marge en 1/N² et décrochage retrouvé par bissection.
- Bielle-manivelle aux limites (PMH, PMB, développement en r/l).
- Jeu piston calculé à la main en un point.
- Cas limite harmonique et conservation de l'énergie du RK4.
- Suivi de la cinématique à bas régime, décollement d'un ressort faible.
- Contrôle de provenance et vérification des empreintes.

## G0 — manuel d'atelier 993, groupe 15 (ajout du 2026-09-14)

Registre : [993-workshop-manual-group15-cylinder-head.json](../../catalog/manual/993-workshop-manual-group15-cylinder-head.json),
chaque valeur relue sur l'image de la page (`page_checked`). **Applicabilité : 993 Carrera
2 soupapes ; références d'origine, pas des cotes du 4 soupapes visé.**

| Donnée | Valeur | Page PDF |
|---|---|---|
| Calage à 1 mm de levée, jeu nul | AO 1° av. PMH, AF 60° ap. PMB, EO 45° av. PMB, EF 6° ap. PMH | 16 |
| Tableau 15 05 M64/05/06 (imprimé) | 1° / 240° / 225° / **2°** — conflit EF 6° contre 2° non résolu | 175 |
| Jeu | hydraulique ; course poussoir 0,2–1,85 (adm) / 0,6–2,25 mm (éch) | 16, 151 |
| Soupapes adm / éch | Ø 49 ±0,1 / 42,5 ±0,1 ; tige 7,970 −0,012 (éch conique 7,950→7,970) ; L 110,1 / 109 ; 45° | 155 |
| Guides | alésage 8,00–8,015 ; serrage 0,06–0,08 ; Ø ext. 13,060 (alésage culasse 13,000–13,018) ; dépassement 16,5 −0,3 ; basculement max 0,80 | 152–154 |
| Ressorts | doubles ; longueur montée A 36,7 +0,3 / 35,7 +0,3 (RS : 37,2 / 35,8) | 148, 157 |
| Culasse | écrous 20 Nm + 90° ±2° ; goujons M8×22 dépassement 23 −0,5 | 148, 150 |

Absents du manuel : angle/largeur des sièges, longueur libre et efforts ressorts, levée
max, jeux d'arbre à cames, planéité/rectification, centrage cylindre, toute donnée M64/60.
Le jeu `stock_993_manual_parameters()` remplace seulement centres de levée (119,5° / 610,5°)
et jeu (0, hydraulique) ; les défauts restent inchangés. Il n'est pas utilisé par `run_study.py`.
