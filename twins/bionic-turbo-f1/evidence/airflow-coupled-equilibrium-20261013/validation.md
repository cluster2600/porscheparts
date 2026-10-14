# Validation et refus de qualification

Le précontrôle natif du maillage passe. Le calcul est arrêté par le timeout
inchangé, code 124 sans OOM ; aucune fin native normale. Le lecteur vérifie
les empreintes de tous les payloads et toutes les copies d’entrées initiales,
les minima/maxima finis et synchrones, puis l’absence de champs finaux. Un
second lecteur vérifie les 111 pas complets et le pas 112 interrompu avec deux
résolutions pression écrites. Aucun calcul natif n’est rejoué.

Le comparateur retrouve l’identité de toutes les entrées hors polyMesh et des
critères avec 076 ; commande, CPU, mémoire et timeout sont inchangés.
La géométrie est exactement celle de 083, sans extrapoler son admission au repos.

- Tests turbo : 109 exécutés en 18,220 s, 108 réussis et un ignoré.
- `PATH=work/bionic-tools/bin:$PATH make check` : 3 896 tests en 287,040 s,
  172 ignorés, mêmes deux échecs flottants WE43/fan_stator et trois erreurs
  rtree/networkx hors turbo ; le contrôle global local n’est pas vert.
- Scripts : analyse AST ; rapports : lecture JSON ; lecteurs exécutés sur les
  payloads natifs définitifs, assertions réussies.

Les seuils sont respectés sur l’historique écrit jusqu’à 11,1 µs. Le repos sur
20 µs est NON QUALIFIÉ, faute de fin et de champs finaux. Le dépassement de
budget n’est pas présenté comme une preuve d’instabilité physique. Aucun
résultat de débit ou de puissance n’est autorisé par cette phase.
