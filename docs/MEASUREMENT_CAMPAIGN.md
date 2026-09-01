# Campagne de mesure — phase 2

## État

Les trois pilotes polymères sont préparés, mais aucune séance de mesure
physique n'est encore enregistrée dans `catalog/measurements/`. Le registre
contient maintenant une fiche séparée de spécifications documentaires du manuel
Porsche, qui ne remplace pas une campagne instrumentée. Le dépôt n'a pas accès à une
993, à une pièce déposée ni à un instrument : ce document est donc un dossier
de passation pour un contributeur extérieur. Il ne contient aucune cote
inventée.

## Ordre de travail

| Priorité | Pièce | Méthode minimale | Livrable attendu |
|---:|---|---|---|
| 1 | `993-INT-SWITCH-BLANK-0001` | Pied à coulisse et jauge de rayon | Sept dimensions D01–D07, trois répétitions, photo des repères, fiche JSON |
| 2 | `993-INT-SEAT-RAIL-COVER-0001` | Pied à coulisse, jauge de profondeur | Dimensions D01–D05 sur les deux côtés, contrôle de l'hypothèse de symétrie, fiche JSON |
| 3 | `993-INT-DOOR-PULL-0001` | Pied à coulisse et photogrammétrie à l'échelle | Cinq dimensions d'interface, photos avec barre d'échelle, manifeste et fiche JSON |

Les plans détaillés se trouvent dans le répertoire `parts/<part_id>/evidence/`.
La priorité 1 est le meilleur premier essai : la pièce est non critique et sa
géométrie maîtresse existe déjà dans
`parts/993-int-switch-blank-0001/source/switch_blank.py`.

## Pré-requis du contributeur

- Identifier la variante, le millésime et l'équipement du véhicule sans relever
  de numéro de châssis, de plaque ni de donnée personnelle.
- Photographier la pièce et son environnement avant la dépose, puis identifier
  les surfaces et axes avec les mêmes repères que dans la fiche de mesure.
- Déclarer le modèle, la résolution, l'interface et l'état d'étalonnage de
  chaque instrument.
- Utiliser au moins trois lectures par dimension critique. Une valeur saisie
  à la main reste `manual_entry`; elle ne doit jamais être présentée comme un
  flux instrumenté.
- Conserver les images brutes et les nuages de points hors du dépôt lorsqu'ils
  contiennent un identifiant de véhicule ou une donnée dont les droits ne sont
  pas établis. Ne déposer qu'une preuve autorisée et anonymisée.

## Procédure de séance

1. Copier `templates/measurement-record.json` vers
   `catalog/measurements/MEAS-<PART>-<DATE>.json` et renseigner le sujet avant
   toute lecture.
2. Contrôler le zéro et l'instrument sur une cale, une pige ou une référence
   connue; enregistrer le statut réel, pas un statut supposé.
3. Définir l'origine, les axes et les plans de référence. Les repères doivent
   rester identifiables sur les photos et dans la CAO.
4. Mesurer les interfaces avant les surfaces décoratives. Répéter chaque cote
   sans chercher à faire converger artificiellement les valeurs.
5. Photographier les fixations, jeux, surfaces d'appui et contradictions. Pour
   la poignée, placer une barre d'échelle certifiée dans chaque prise de vue.
6. Reporter les lectures brutes, calculer la valeur depuis leurs échantillons,
   puis consigner l'incertitude et sa base (`repeatability`, `instrument_resolution`
   ou `combined`).
7. Exécuter `make check`. Si une mesure ne passe pas le validateur, corriger la
   transcription ou la méthode; ne pas ajuster la valeur pour faire passer le
   contrôle.

## Porte de décision

Une fiche de pièce reste `concept` tant que la séance n'est pas complète et
revue. Le passage à `dimensionally_reviewed` demande les dimensions critiques,
les fichiers de preuve, la variante et une revue CAO. Le montage d'un prototype
est une étape séparée : il faudra alors consigner les jeux, les photos et les
écarts avant tout statut `prototype_fitted`.

Les trois pilotes sont des pièces d'habillage, mais la poignée reçoit des
efforts manuels répétés. Aucun matériau, réglage ou géométrie ne doit être
qualifié de sûr ou durable sur la seule base d'un bon ajustement statique.

## Brief CT optionnel

La CT n'est pas nécessaire pour le cache d'interrupteur. Elle peut être étudiée
pour la poignée si les interfaces cachées ne sont pas accessibles après dépose,
ou pour une pièce polymère présentant des canaux internes. Les fiches
`SRC-HACHTEL-BASIC-CT-SCAN`, `SRC-BMB-GERMANY-CT-RE` et
`SRC-VISION-METRIC-CT-DIGITIZATION` sont des pistes de prestation, pas des
mesures 993 existantes.

Toute demande doit exiger :

- variante et référence de pièce;
- volume couvert, résolution/voxel et incertitude annoncée;
- repères, échelle, orientation et traitement des surfaces cachées;
- volume brut ou format livré, segmentation, maillage et éventuel STEP;
- comparaison entre au moins trois dimensions d'interface et le relevé manuel;
- droits d'utilisation et de redistribution des fichiers livrés;
- interdiction de conclure à la précision d'une pièce de sécurité à partir du
  seul scan.

Une commande CT ou un achat de pièce nécessite une validation séparée du
mainteneur. Aucune dépense ni acquisition externe n'est présumée par ce dépôt.
