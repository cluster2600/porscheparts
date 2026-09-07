# Bague de commutateur 993 — jumeau F1

Cette bague aluminium non critique est le premier pilote métallique du flux
993. La fiche commerciale fournit quatre cotes : Ø extérieur 30,5 mm,
profondeur 10,5 mm, Ø intérieur avant 23 mm et arrière 28 mm. Le maître
`build123d` reconstruit un anneau à alésage conique et confronte son volume OCCT
au volume analytique d'un cylindre moins un tronc de cône.

Le résultat est volontairement au niveau **F1 / concept**. Le cône intérieur est
une interprétation, pas une mesure. Les tolérances, rayons, ouverture du tableau
de bord, état de surface et nuance d'aluminium restent inconnus. Le STEP ne doit
donc pas être envoyé en fabrication ni monté sur un véhicule.

## Calculs exécutés

- paroi radiale avant : `(30,5 - 23) / 2` ;
- paroi radiale arrière : `(30,5 - 28) / 2` ;
- volume : cylindre extérieur moins tronc de cône intérieur ;
- masse indicative : volume multiplié par 2,67 g/cm³, densité de criblage
  AlSi10Mg explicitement non attribuée à la pièce d'origine ;
- croissance thermique et pression de serrage laissées bloquées jusqu'à la
  mesure de l'ouverture OEM et à la sélection d'une carte matière qualifiée.

La géométrie est imprimable en LPBF en première lecture, mais sa forme
axisymétrique rend le tournage CNC probablement plus rationnel. Le pilote sert à
valider la chaîne numérique ; le choix industriel reste ouvert.

## Reproduction

```sh
python3 parts/993-int-switch-trim-ring-f1-0001/source/switch_trim_ring.py \
  --report parts/993-int-switch-trim-ring-f1-0001/evidence/geometry-screen.json
```

L'export STEP exige l'image CAO verrouillée du dépôt. PhysicsNeMo et un GPU Vast
ne sont pas requis ici : il n'existe ni champ complexe ni données d'entraînement
justifiant un surrogate. Les formules déterministes et OCCT sont l'autorité de
ce premier contrôle.
