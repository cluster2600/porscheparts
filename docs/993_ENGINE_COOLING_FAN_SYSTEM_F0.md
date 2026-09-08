# Sous-ensemble carter–turbine de refroidissement 993 F0

## Résultat

Le carter fixe `993-ENG-FAN-HOUSING-ALSI10MG-F0-0001` et la turbine tournante
`993-ENG-COOLING-IMPELLER-ALSI10MG-F0-0001` ont été réunis dans le premier
jumeau de sous-ensemble moteur 993. Le verdict est un **échec d'intégration
utile** : les deux concepts F0 ne peuvent pas fonctionner ensemble dans leur
état actuel.

| Contrôle | Résultat | Verdict |
|---|---:|---|
| Gorge synthétique du carter | 252 mm | hypothèse F0 |
| Diamètre synthétique de turbine | 280 mm | hypothèse F0 |
| Jeu radial froid | **−14 mm** | échec |
| Jeu radial libre à chaud | **−14,03822 mm** | échec |
| Gorge requise pour 2 mm de jeu radial | 284 mm | déficit de 32 mm |
| Intersection BRep exacte | **40 388,378651 mm³**, 2 solides | collision |
| Cibles de débit séparées | 1,25 contre 1,01 m³/s | incohérentes |
| Fréquences de passage supposées | 1 100 contre 2 000 Hz | incohérentes |

Le test BRep emploie les deux STEP relus par OpenCascade, alignés sur une
hypothèse explicite : axes coaxiaux et même plan avant `Z=0`. Il complète le
calcul analytique de jeu, mais ne transforme pas cet alignement synthétique en
position Porsche mesurée.

Le registre du jumeau est
[`catalog/twins/twin-993-engine-cooling-fan-system-f0.json`](../catalog/twins/twin-993-engine-cooling-fan-system-f0.json).
Le calcul reproductible est dans
[`evaluate_integration.py`](../twins/993-engine-cooling-fan-system-f0/source/evaluate_integration.py)
et sa preuve dans
[`integration-screen.json`](../twins/993-engine-cooling-fan-system-f0/evidence/integration-screen.json).

## Passage OpenUSD

Le préflight natif a correctement bloqué le Mac ARM : le Python actif ne
contenait ni le wheel `usd-convert-cad`, ni OpenUSD, ni Asset Validator, et
`usd-exchange 2.3.0` n'offre pas de wheel macOS ARM. Le même préflight a ensuite
réussi dans l'image Linux AMD64 immuable :

`ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:79e76882a8f493012eb4cc9ab061bce0ca2d075cd505d6e33a5200e7e1e9b126`

Cette exécution est restée CPU, sans GPU, sans réseau pendant les conversions et
avec `property_assignment_intent=skip`. Elle a utilisé le convertisseur officiel
`usd-convert-cad 0.2.0`, puis le validateur minimal du workflow NVIDIA :

- carter : 1 maillage, `300 × 300 × 170 mm`, validation minimale réussie ;
- turbine : 1 maillage, `280 × 280 × 30 mm`, validation minimale réussie ;
- assemblage : 2 références, 2 maillages, `Z-up`, `metersPerUnit=0,001`,
  validation minimale réussie ;
- aucun rigid body, collider ou joint n'a été ajouté.

Les USD sont des dérivés rejouables et restent hors Git. Leurs SHA-256, tailles,
métadonnées et verdicts assainis sont publiés dans
[`simready-conversion-summary.json`](../twins/993-engine-cooling-fan-system-f0/evidence/simready-conversion-summary.json).
Le script de composition est
[`build_usd_assembly.py`](../twins/993-engine-cooling-fan-system-f0/source/build_usd_assembly.py).

## Frontière de validité

« Validation USD minimale réussie » signifie seulement que les fichiers
s'ouvrent, ont un `defaultPrim`, des unités, un axe et une composition résolue.
Cela ne prouve ni la géométrie Porsche, ni le jeu réel, ni le refroidissement,
ni la survitesse, ni la fatigue, ni le confinement. Ce sous-ensemble n'est pas
SimReady, n'a reçu aucune propriété Physics, n'a exécuté aucun modèle
PhysicsNeMo et n'autorise ni fabrication, ni rotation, ni démarrage moteur.

Le prochain passage ne doit pas corriger silencieusement les valeurs F0 pour
faire disparaître la collision. Il faut d'abord acquérir le diamètre de gorge,
le diamètre de turbine, la position axiale, le faux-rond, le montage
axe–roulements–alternateur–poulie et le jeu froid réel. Ces mesures permettront
un jumeau `F2_interface`; une carte ventilateur et une courbe réseau mesurées
seront ensuite nécessaires avant CFD/CHT ou PhysicsNeMo.
