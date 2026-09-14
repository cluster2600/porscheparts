# Soupape d'admission 993 creuse — concept Ti64 LPBF F0

FVD publie pour la référence `99310540902` une tête de `49 mm`, une queue de
`8 mm`, une masse de `120 g` et un encombrement commercial de
`50 × 110 × 50 mm`. La fiche ne fournit ni longueur fonctionnelle, ni profil,
ni siège, ni gorge, ni matière, ni tolérance. PorscheFanatics identifie des
soupapes titane dans le kit Swindon quatre soupapes, sans établir la nuance ou
la compatibilité avec la culasse M64 deux soupapes.

Le F0 utilise donc seulement les diamètres publiés. Sa longueur de `109 mm`, sa
tête plate de `3 mm`, son raccord conique, sa cavité, son alésage axial de
`5 mm` et ses quatre nervures de `1,2 mm` sont des hypothèses indépendantes.

## Pourquoi étudier l'additif

L'intérêt LPBF n'est pas de reproduire une soupape pleine, mieux obtenue par
forge et usinage. Il est de fabriquer dans un seul corps une tête et une queue
creuses, avec des nervures internes distribuées selon les charges. L'alésage
reste ouvert à la pointe pour tenter le dépoudrage ; sa fermeture, son contrôle
et sa rétention ne sont pas définis. La comparaison obligatoire reste :

1. soupape titane pleine forgée et usinée ;
2. soupape creuse conventionnelle ou soudée par friction ;
3. corps creux Ti-6Al-4V LPBF avec fermeture qualifiée.

## Géométrie obtenue

Le STEP relu contient un solide BREP valide de `49 × 49 × 109 mm`. Son volume
est `12 545,86 mm³` et sa masse théorique `55,45 g` à `4,42 g/cm³`. Une forme
pleine partageant exactement le même extérieur synthétique pèserait `72,38 g` :
le creux enlève `23,38 %`. La différence de `64,55 g` face aux `120 g` publiés
n'est pas un gain OEM, car la fiche commerciale et le F0 ne définissent pas la
même géométrie.

## Criblages mathématiques

Le cas de régression prend `6 720 tr/min`, `12 mm` de levée sur `240°`
vilebrequin, un ressort de `520 N + 40 N/mm`, `0,20 MPa` de différentiel,
`+400 K` et `100 h`. Une loi harmonique simple donne une durée d'événement de
`5,95 ms`, une vitesse maximale de `6,33 m/s` et une accélération de
`6 685 m/s²`. Avec la masse CAO, l'inertie vaut `371 N` et l'effort axial de
criblage, ressort et pression inclus, `1,75 kN`.

La section annulaire de queue donne `57,1 MPa` en traction/compression nominale
et Euler `20,5 kN`. La plaque circulaire idéalisée de tête donne `6,23 MPa` et
`0,0037 mm`. Ces marges ambiantes ne couvrent ni le siège, ni le guide, ni les
clavettes, ni l'impact, ni les défauts LPBF.

Le premier mode de poutre encastrée vaut seulement `190,8 Hz`, soit `3,41` fois
la fréquence d'événement de `56 Hz` : ce résultat impose une analyse modale du
système complet et ne constitue pas une séparation fréquentielle acceptable.
Sur `100 h`, le décompte atteint `20,16 millions` d'événements sans prédire de
durée de vie.

La dilatation libre vaut `0,392 mm`. La borne totalement contrainte vaut
`396 MPa`, tandis que la conduction axiale 1D n'est que `1,37 W` avec les
propriétés de comparaison Ti64. Il faut donc mesurer les températures et
résoudre les contacts thermiques siège-guide avant toute conclusion.

## Reproduction logicielle

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-intake-valve-ti64-hollow-f0-0001/source/intake_valve.py \
  --out parts/993-eng-intake-valve-ti64-hollow-f0-0001/derived/intake_valve_ti64_hollow_f0.step \
  --report parts/993-eng-intake-valve-ti64-hollow-f0-0001/evidence/engineering-screen.json
```

## Gates suivants

1. Mesurer une soupape déposée, son siège, guide, clavettes, coupelle, ressort,
   came, basculeur et jeux piston-soupape.
2. Instrumenter loi de levée, pression, température, impact, flottement,
   rebond, lubrification et cycle de service.
3. Reconstruire les interfaces avec tolérances, état de surface, revêtements,
   duretés, surépaisseurs et fermeture réelle.
4. Résoudre multibody puis FEA contact/modal/thermique/HCF-LCF avec convergence,
   défauts et propriétés Ti64 orientées à chaud.
5. Qualifier orientation, supports, dépoudrage, traitement, HIP, usinage,
   couche alpha, CT, propreté, fermeture et équilibrage.
6. Tester à chaud la soupape grandeur réelle, puis une culasse entraînée et un
   moteur au banc sous revue professionnelle.

PhysicsNeMo attend des séries corrélées multibody-thermique-structure avec
train, holdout et hors-distribution. SimReady attend l'assemblage mesuré. Ce
STEP F0 n'est autorisé ni pour fabrication, ni pour montage, ni pour moteur.
