# F41 — qualification runtime Vast du digest C59

Le 3 septembre 2026, le superviseur F41 a exécuté le lot CAO borné sur une
instance Vast au Texas à partir du commit public
`045f41037f04b3dd69b72591d29713a17db8e1c3` et de l'image immuable :

`ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:c59c53b2611a1e3a9e9de5d2cedf8bfb0cd57e72582b2d6b29f6c8fc82bf7e6b`

Le bundle public de 40 368 octets, SHA-256
`2b2d7ace49c0915b5a56da001cf3fae8ca6b97d9bb9c30fd0bda19099c7b0db5`,
a été transféré puis exécuté sous le job `f41-c59-20260903t025511z`.
L'archive récupérée compte 772 358 octets et porte le SHA-256
`59ef86584e9dfb16481b76ce79bf5739b129ddf2d3a3869f700b2dd614bd86b5`.

## Résultat vérifié

- l'offre `49691948` a créé l'instance `49707819` ;
- le superviseur a terminé avec le code `0` ;
- 6 familles de graines de recherche F35 sur 138 familles planifiées ont été
  générées ; les 132 autres restent bloquées ;
- 6 STEP, 6 STL et 6 fichiers 3MF, soit 18 artefacts, ont passé le contrat
  d'intégrité et les contrôles de round-trip prévus ; aucun USD n'a été produit ;
- le journal source a été vérifié ;
- l'instance a été détruite avant la validation locale finale et son entrée
  `known_hosts` a été supprimée.

Cette preuve qualifie le digest C59 pour le transport et l'exécution de ce lot
CAO F41 précis. Elle ne transforme pas les graines F35 en géométrie moteur
mesurée, en définition de production ou en pièces libérées.

## Limites fermées

Les six familles restent des graines paramétriques de recherche. La sémantique
géométrique, les dimensions, interfaces, jeux, matériaux, charges, fatigue,
thermique, CFD, combustion, assemblage, USD/SimReady et PhysicsNeMo ne sont pas
validés. Il n'existe ici aucune corrélation physique ou banc, aucune preuve de
1 600 ch et aucune autorisation de fabriquer, d'imprimer du métal, de démarrer
le moteur ou de l'installer dans une 993.

Seuls ce résumé et `summary.json` sont publiés. L'archive CAO, les STEP, STL,
3MF, journaux runtime, inventaires Vast et secrets restent hors du dépôt.
