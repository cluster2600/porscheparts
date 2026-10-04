# Chaîne logicielle : capacités et preuves

[Accueil du dépôt](../../README.md) · [Études et résultats](ENGINEERING.md) ·
[Dossier fabricant BLT, en anglais](MANUFACTURING_REVIEW.md)

État du 4 octobre 2026. La chaîne numérique exécutée ne constitue pas une chaîne
de fabrication physiquement qualifiée. « Disponible », « exécuté » et « vérifié »
sont distingués ci-dessous. Les versions/runtime proviennent des reçus de cette
étude ; aucun nouvel outil n'a été installé pour cet audit. Les résultats des
culasses et du support titane ne sont pas réutilisés comme preuves de ce rotor.

| Étape et runtime | Entrée → sortie réellement exécutée | Preuve et état | Limites / prochaine vérification |
| --- | --- | --- | --- |
| CAO : build123d 0.13 / OCP 8, Kali2 natif amd64 | Paramètres originaux R0/V2/V5 → BRep, STEP et tessellation ; rendus de la même géométrie | [Reçus géométriques](results/geometry/) : BRep valides, volume positif, rotor connecté, relecture STEP vérifiée | Échelle, identité 935/993, interfaces et tolérances non mesurées ; définir la pièce fonctionnelle indépendamment |
| Maillage : Gmsh 4.15.2, Kali2 natif | STEP rotor → C3D10 structural ou tétraèdres fluide | [Rapports FEM](results/mechanics/) : Jacobien Gauss4 positif, volume comparé au CAD, permutation C3D10 vérifiée ; [CFD](results/cfd/) : géométrie conservée | Pas de preuve métrologique ; couches de paroi absentes ; convergence locale des contraintes non établie |
| QA CFD : OpenFOAM Foundation 13, image existante figée | `volume.msh` → `polyMesh`, contrôles standard et `-allGeometry -allTopology` | Gates indépendants, échecs historiques conservés, R0 et V2 admis après raffinement sans abaisser les seuils | Gate de maillage indispensable mais insuffisant pour valider le modèle de turbulence ou le régime physique |
| Écoulement : même OpenFOAM 13, Kali2 Docker borné | Domaine admis, conditions/protocole figés → U/p/k/omega/nut/phi, débit et couple | Grille commune R0/V2 à 600 itérations ; R0 raffiné admis à 600, V2 raffiné à 600/750 échoue sur la pression seule ; sensibilité numérique appariée à relaxation 0,15 : R0/750 admis, V2/900 échoue encore sur la pression seule. Critères résidus, masse, stabilité et complétude des champs vérifiés ; puissance recoupée par couple × Ω | Écoulement isolé à pression totale d'entrée 0 / pression statique de sortie 0, 6000 tr/min ; convection premier ordre, MRF stationnaire ; bilan énergétique simplifié non fermé et sensibilité compressible requise |
| Rotation/modal : CalculiX 2.23, Kali2 natif | C3D10 + aluminium élastique supposé + alésage fixé → U/S et 12 fréquences | Douze jobs R0/V5/V2, deux tailles de maillage ; [comparaison](results/mechanics/three-variant-comparison.json) et vrais [champs R0](results/mechanics/R0-fields.png) | Modes R0/V5 sans précontrainte, gyroscopie, roulements/contact ; contraintes aux pieds de pale sensibles au maillage ; aucun régime sûr/fatigue qualifié |
| Screening LPBF : NumPy et script original, Kali2/Mac CPU | Vrai STL R0 → encombrements, surplombs, sections de couches et proxy de supports | [Rapport](results/lpbf/lpbf-screen.json), contrôle de volume par intégration des sections | Screening géométrique à 50 µm et enveloppe hypothétique ; ne simule ni supports physiques, ni chemin laser, ni chaleur |
| Retrait/débridage : CalculiX 2.23 natif, scripts originaux adaptés | Même CAD/maillage R0/V5, champ de contraction déclaré, attaches idéales → deux états U/S, retrait et libération | Benchmark analytique natif et cas comparatifs sous hypothèses ; contrôles zéro/amplitude/orientation/supports/maillage | Élasticité générique, amplitude non mesurée, aucune activation de couche, carte plastique/thermique ou calibration machine ; les pics d'attaches ponctuelles ne sont pas des contraintes de fabrication admissibles |
| Simulation process LPBF qualifiée | Recette, trajectoires, matériau T/plasticité, supports/plateau et calibration → distorsion/défauts qualifiés | **Non démontrée sur R0/V5** ; la présence d'un outil dans un ancien inventaire n'établit pas son exécution/validation sur ce cas | Obtenir les données atelier et choisir la méthode adaptée ; calibrer et valider sur un build indépendant |
| Post-traitements | Build réel + gamme thermique/coupe/usinage → état final et relevés avant/après | **Aucun traitement réel ni simulation thermique qualifiée R0/V5 exécuté** | BLT est cible de revue ; séquence et HIP éventuel à justifier, four/gamme/matière à approuver |
| CT / métrologie / NDT | Spécimen réel et dessin d'inspection → mesures, défauts et décision d'acceptation | **Aucun specimen/rapport d'inspection disponible** ; audit du scan privé et QA CAD exécutés, sans substituer une inspection industrielle | Demander résolution/détectabilité/volume couvert du CT, plan de mesure et critères de défauts/tolérances approuvés |
| OpenUSD 25.11, bibliothèque déjà disponible sur Mac | Tessellation analytique et métadonnées → assets/scène USD, parsing/composition/topologie/unités/matériaux | [Assets](omniverse/), 24 validateurs génériques sans finding ; mètres par unité et axes vérifiés | Ressource `shaderDefs.usda` absente : contrôle Sdr du shader non validé ; asset visuel et preuves liées, pas solveur physique |
| NVIDIA Omniverse / SimReady / RTX | Profil NVIDIA, runtime compatible et données corrélées → jumeau validé | **Pas de validation NVIDIA e2e ou rendu RTX exécuté pour cette mission** ; aucun GPU NVIDIA disponible sur les ressources autorisées | Runtime/profil et corrélation physique restent à établir ; OpenUSD générique seul ne démontre pas SimReady ou un jumeau validé |
| QA logiciel du dépôt : GitHub Actions | Commit exact → `make check` | PR129 fusionnée, main `8283155cb2b1275b0bf3e22d4d7459d4ac76b059`, [CI post-merge verte](https://github.com/cluster2600/porscheparts/actions/runs/37208996692) | Contrôles locaux historiques incompatibles conservés dans [rapport runtime](results/runtime/repository-checks.json) ; ces compléments exigent leur CI au commit exact ; physique distincte de CI |

Image OpenFOAM utilisée :
`ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f`.
Les jobs Kali2 de cette mission restent séquentiels, au plus quatre CPU et
six GiB ; les délais sont figés par job et les services tiers sont préservés.
La mémoire mesurée du client Docker ne représente pas le pic de mémoire du
conteneur : le plafond explicite du conteneur est la limite pertinente.

Le [dossier fabricant](MANUFACTURING_REVIEW.md) identifie les décisions atelier et
les essais physiques nécessaires. Aucune validation de fabrication, certification
matériau, qualification en service ou libération du catalogue n'est déclarée.
