# Porsche 917 — F43, contrat G3–G5 comparable 2V/4V

## Verdict

Le contrat comparable est défini et l'audit des preuves existantes est
exécuté. **Aucun nouveau calcul long n'a été lancé**, car les domaines fluides
2V/4V étanches et comparables n'existent pas dans le dépôt. Lancer OpenFOAM ou
un solveur moteur sur la géométrie actuelle produirait un résultat non
comparable.

Le plan comprend 18 cas G3–G5 : trois domaines, deux architectures et trois
maillages. Tous utilisent une seule définition des conditions turbo F33. Ces
conditions sont des hypothèses clean-sheet 2026 non corrélées; elles ne sont
ni des données historiques 1973, ni un point moteur validé.

Le rapport déterministe est
[`evidence/f43-g3-g5-comparable/audit-report.json`](../twins/reference-917-engine/evidence/f43-g3-g5-comparable/audit-report.json).
Toutes les autorisations fabrication, impression métal et démarrage restent
fermées.

## Architecture d'essai

```text
                       BC turbo F33 unique, non validée
                                   |
                 +-----------------+-----------------+
                 |                 |                 |
       G3 conduits fixes   G4 cycle mobile    G5 refroidissement air
       OpenFOAM 3D         XiFluid/OpenFOAM    OpenFOAM air/CHT futur
            versus              versus                versus
       modèle 1D orifice   Cantera angle-vilebrequin  corrélation + conduction
                 |                 |                 |
          2V et 4V x coarse / medium / fine
                 |
       bilans masse + énergie + convergence + écart interméthodes
```

Les tailles métriques de cellules restent nulles. L'échelle, les domaines et
les surfaces fonctionnelles ne sont pas suffisamment qualifiés pour choisir
une taille en millimètres sans l'inventer.

Les seuils numériques du protocole sont :

- résidu massique relatif maximal : 0,5 %;
- résidu énergétique relatif maximal : 5 %;
- variation medium→fine de la métrique primaire : 5 %;
- écart relatif entre méthodes indépendantes : 20 %.

Un succès sur ces seuils ne constituerait pas une validation physique.

## Audit des calculs déjà présents

### G3 — OpenFOAM 2V/4V

F33 contient bien six exécutions OpenFOAM : 2V et 4V, chacune sur 3 456,
11 664 et 27 648 cellules. Les retours solveur sont nuls. Les débits du maillage
fin sont 0,113341 kg/s en 2V et 0,136519 kg/s en 4V, soit un écart historique
de 20,45 %.

Cette comparaison n'est pas recevable pour F43 : les domaines sont des conduits
rectangulaires équivalents, non les conduits et soupapes complets; les lignes
ne contiennent ni bilan entrée/sortie de masse, ni flux d'énergie total; aucune
seconde méthode indépendante n'est présente. Les variations medium→fine sont
7,53 % et 7,77 %, supérieures à la règle F43 de 5 %.

### G4 — Cantera et ICEEngineFoam

Cantera F33 a réellement exécuté un équilibre UV à quatre états et ferme
l'identité algébrique de masse du cas turbo. Il n'a exécuté ni intégration en
angle vilebrequin, ni variante 2V/4V, ni convergence cyclique.

Le seul calcul moteur maillé est le tutoriel OpenFOAM 13
`XiFluid/engine2Valve2D` à deux soupapes. Il vérifie le chemin logiciel et un
changement de topologie, mais n'utilise aucune géométrie Porsche 917. Le
binaire nommé `iceEngineFoam` n'est pas présent, le cas 4V n'a pas été exécuté
et Cantera n'est pas couplé au cas.

### G5 — refroidissement air

F34 a exécuté un RANS OpenFOAM externe 4V avec bilan énergétique relatif de
1,025 %, Δp de 1 859 Pa et h effectif de 120,38 W/m²K. Son contrôle de maillage
strict échoue et il n'existe pas de cas 2V associé.

F36 ne ferme ni l'accord deux maillages RANS ni le bilan global. F42 obtient un
accord de h entre son proxy de canal et la corrélation, mais échoue sur la
pression, n'accepte pas le cas OpenFOAM F41 exact et ne réalise pas une CHT de
culasse complète. Ces preuves sont donc conservées comme audits 4V, pas comme
comparaison 2V/4V.

## DOE F43 — refroidissement air LPBF

Le DOE reste séparé du couple conceptuel F33 : son baseline est le master 4V
F41 scan-verrouillé, stocké hors Git. Sept géométries et trois maillages sont
prévus, soit 21 cas :

1. peau fidèle au scan, sans modification;
2. canaux d'air traversants en goutte autoportante;
3. canaux traversants en losange autoportant;
4. épaisseur et pas d'ailettes variables;
5. pin-fins ouverts autour du siège échappement et du pont de bougie;
6. lattice ouvert, visible en CT et dépoudrable;
7. nervures de conduction vers les zones dont le fort débit aura été mesuré.

Les métriques obligatoires sont les températures maximales siège/pont/bougie,
Δp, débit par zone, uniformité, masse, contrainte thermique, angle minimal,
volume de supports, chemins de dépoudrage et dimension visible en CT.

La comparaison à enveloppe externe quasi identique utilisera une distance
normale enregistrée vers F41, hors datums d'usinage. Sa tolérance reste nulle :
ni l'échelle absolue ni les interfaces ne permettent de fixer une valeur.

Sont interdits : chemise liquide, cavité fermée, piège à poudre aveugle,
microcanal sans probabilité de détection CT et dépoudrage démontrés, support
interne non extractible. Chaque canal doit être ouvert et contrôlable depuis
deux extrémités ou disposer d'une preuve équivalente de nettoyage.

## Circuit d'huile secondaire

L'air forcé reste le refroidissement principal. Le circuit secondaire prévu
est : alimentation carter sec sous pression → galerie de distribution →
guides/paliers et jets calibrés vers échappement, ressorts et porte-arbres →
retours gravitaires ouverts → aspiration scavenge → réservoir et refroidisseur
d'huile externes.

Les passages imprimés doivent être traversants ou ouverts, rinçables, visibles
en CT et accessibles à l'usinage ou à des bouchons qualifiés. Ils ne forment
jamais une chemise liquide autour de la chambre.

Le DOE huile doit couvrir froid/chaud avec viscosité mesurée, pression
d'alimentation et régime, débit par jet, température de paroi et marge de
cokéfaction, aération, temps de drainback et marge de scavenge sous inclinaison
et accélération. Toutes les propriétés, pressions, diamètres, coordonnées de
jets, limites de cokéfaction et conditions d'accélération restent `null`.

L'écran F37 ne les verrouille pas : Hagen–Poiseuille et Darcy–Weisbach avec
`f=64/Re` sont la même relation en régime laminaire. Il ne simule ni jets, ni
aération, ni retours gravitaires.

## Exécution et fixture

Pour vérifier l'audit suivi :

```sh
python3 twins/reference-917-engine/source/audit_g3_g5_comparable_execution_f43.py \
  --check twins/reference-917-engine/evidence/f43-g3-g5-comparable/audit-report.json
make 917-f43-g3-g5-comparable-check
```

La fixture `tests/fixtures/917-g3-g5-synthetic-case-results.json` contient des
valeurs artificielles, étiquetées comme telles. Elle exerce uniquement les
formules de bilan, convergence et écart interméthodes. Ses résultats sont
explicitement exclus des métriques d'ingénierie et ne peuvent ouvrir aucune
porte.

## Gaps bloquants

- artefacts STEP/STL fonctionnels F33 non publiés et domaines fluides absents;
- enveloppe et interfaces communes 2V/4V non vérifiées;
- aucune version 2V scan-fidèle du master F41;
- lois de came, jeux, calibration combustion et BC turbo non corrélées;
- aucun Cantera angle-vilebrequin comparable au solveur mobile;
- aucune paire refroidissement air 2V/4V, aucune CHT complète;
- dimensions LPBF, contrôle CT/dépoudrage et écart externe non qualifiés;
- carte matériau chaude 260–350 °C absente;
- huile : propriétés, carte pression, coefficients de jets, cokéfaction,
  aération, drainback et scavenge non mesurés.

Ces manques sont détaillés par identifiants `GAP-*` dans le rapport JSON.
