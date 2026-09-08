# Domaine gaz du pilote d’admission à 6 mm

`build_gas_domain.py` assemble uniquement un **candidat de banc à froid** :
négatif d’admission natif 06, chambre à deux pans déjà construite, intérieurs
réels des sièges V2, soupapes d’admission levées de 6 mm, échappements fermés,
guides et récepteur de banc Ø100 × 100. Ces deux dimensions et l’équivalence
1 unité de scan = 1 mm restent des hypothèses explicites, pas des cotes M64
certifiées. Le récepteur n’est ni un piston ni une mesure de compression.

Les jeux tige-guide d’admission sont représentés sur leur longueur réelle du
module, de 20 à 55. Seules leurs deux faces annulaires supérieures peuvent
recevoir le rôle `fixture_stem_seals` : ce sont des joints de banc idéalisés
autorisés pour ce pilote, pas des joints mécaniques conçus ou qualifiés.
Les faces inférieures de ces annules sont des connexions internes, jamais des
parois ou des sorties artificielles.

## État constaté

Les passes séquentielles 02/03 et la soustraction simultanée 04 ont terminé
avec un rejet BRep, conservé dans leurs reçus privés. Le volume fusionné avant
soustraction est connexe et BRep-valide ; cela **n’autorise pas son maillage**
comme gaz puisqu’il contient encore les volumes des pièces mobiles et guides.
Le diagnostic séparé de 28 intersections constituant/siège, exécuté avant
toute fusion, retourne 0 solide et volume 0 pour chaque paire. Les très petits
solides d’intersection observés après fusion ne sont donc pas une preuve de
pénétration matérielle préalable. L’audit natif indépendant localise une
micro-coque partageant trois faces avec la coque principale, avec l’unique
défaut `InvalidImbricationOfShells`. Aucune coque n’a été supprimée à la main.

La passe 05 applique les **mêmes 12 outils** à chacun des constituants avant
fusion, selon `(union Ai) moins B = union(Ai moins B)`. Elle a réellement
terminé en 45,81 s avec un solide BRep-valide, également valide après relecture
native et STEP, sans changement de dimension ou de tolérance. Son volume de
995 964,587 unités³ comprend les conduits et le récepteur de banc : ce n’est
pas le volume de la chambre de combustion. Le reçu public est
[gas-domain-construction-20260908.json](../../evidence/gas-domain-construction-20260908.json).

L’alerte native `BOPAlgo_GeomAbs_C0`, également rencontrée sur le col local
de l’admission 2, a été localisée indépendamment sur l’arête B-spline 97,
entre les faces 36 (`walls_seat`) et 37 (`walls_port`). Ses trois nœuds internes
ont un saut de position numérique nul, mais de **vraies ruptures de tangente**
(environ 0,62°, 6,96° et 16,76°). Ce n’est ni une brèche ni simplement un angle
entre deux faces. La géométrie et les tolérances ne sont pas modifiées.

La revue indépendante autorise **une tentative diagnostique de maillage**
du BRep natif exact, à condition de conserver ces nœuds et de vérifier la
conformité de frontière, la topologie et la qualité des éléments obtenus.
`bop_no_faults` demeure **false** ; cette exception bornée n’est pas un
« BOP sans défaut », ni un maillage accepté, ni une autorisation de solveur.
Le STEP possède en plus 31 alertes `InvalidCurveOnSurface` : **STEP non qualifié
pour le maillage**, malgré sa validité BRep. L’empreinte du rapport indépendant
et les conditions exactes de cette tentative sont liées dans le reçu public.
La preuve indépendante détaillée et assainie est conservée dans
[native-gas-domain-independent-diagnostics-20260908.json](../../evidence/native-gas-domain-independent-diagnostics-20260908.json).

L’enrichissement de classement v2 conserve les empreintes de la géométrie et
les rapports d’origine. Les quatre faces planes recouvertes entièrement par
un vrai siège et l’outil négatif de chambre sont affectées à `walls_seat`,
avec les deux appariements et la règle de propriété enregistrés. Le négatif
constructeur ne constitue pas un second matériau. Les 88 faces sont ainsi
classifiées, sans face inconnue ou ambiguë, avec une entrée, une sortie et
deux joints annulaires de banc. Les contrôles BOP et col local non satisfaits
n’ont pas été changés par cette opération de classement.

Le contrôle de passage doit être **local à chaque siège** : un seul volume
valide, une section positive côté chambre et côté gorge, exclusion du tronc
commun et de l’autre siège. La simple connexité globale ne suffit pas.
Les frontières persistées sont ensuite appariées aux faces natives de leurs
sources, par type, support et recouvrement surfacique ; tout rôle absent ou
ambigu rejette le candidat. Un contrôle BOP est distinct d’un contrôle BRep.

Le maître de culasse n’est pas modifié par ce lot, les conduits ne sont pas
encore soustraits du corps et aucun calcul CFD, débit, Cd, essai thermique,
qualification moteur ou autorisation de fabrication n’est établi ici.
Les BRep/STEP, coordonnées et rapports détaillés restent privés ; seuls le
code, les tests et des agrégats avec empreintes sont publiables.

Tests sans noyau CAO :

```sh
python3 -m unittest discover -s tests -p test_m64_flowbench_gas_domain.py -v
```

L’option `--diagnose-pieces` réalise exclusivement les intersections
constituant/siège sans fusion et sans produire de domaine gaz. Un succès de
cette commande ne constitue pas un succès du constructeur complet.
