# Validation du dossier

Construction et lecture indépendante réussies sans assertion refusée : 12
manifestes ancrés à PR243, 284 entrées, six membres de l'archive officielle,
15 emplacements d'expressions et 153 reçus de boîtes. Il s'agit de contrôles
structurels/de provenance, pas de nouvelles preuves de maillage ou d'exécution.

Tests turbo : 108 réussis, un ignoré, 15.652 s.
`PATH=work/bionic-tools/bin:$PATH make check` : 3920 tests, 215.721 s,
172 ignorés, deux échecs flottants WE43/fan_stator et trois erreurs
rtree/networkx hors turbo. Les cinq labels sont identiques à PR243; le total
de tests a augmenté sur main entre les bases des deux phases. Code make 2,
code turbo 0. Les journaux et reçus sont conservés.

La première sélection de membre n'avait pas extrait le fichier applicatif
checkGeometry.C; sa lecture rg a signalé le fichier absent. L'accès au chemin
exact a ensuite réussi. Aucune assertion scientifique ou exécution native
n'est liée à cet incident, décrit dans source-access-attempts.json.

Aucun calcul de coordonnées, ratio ponctuel, ancien parcours, candidat,
dictionnaire, conteneur, solveur ou installation. Docker sans conteneur actif
au précontrôle. Aucun débit, puissance ou calibration validé.
