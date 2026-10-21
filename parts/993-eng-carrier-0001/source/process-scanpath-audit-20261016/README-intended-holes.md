# Normalisation des trous couverts par la construction intentionnelle

`exact_intended_holes.normalize_holes(result, primitives, allowed)` renvoie un
candidat et un reçu. Il conserve les coordonnées de l'extérieur et des trous
retenus ; il ne crée aucun sommet et n'appelle aucun overlay polygonal.

Un trou convexe peut être retiré seulement si deux preuves passent : son
ensemble entier appartient au domaine permis, et chaque cellule de sa partition
rationnelle appartient à au moins une primitive de l'union intentionnelle.
La partition utilise toutes les droites des frontières des primitives ; ses
aires sont conservées exactement. L'appartenance est constante à l'intérieur
de chaque cellule. L'union finie des primitives étant fermée, elle contient
également toutes les frontières des cellules couvertes.

Les trous non convexes, partiellement couverts, réellement absents des
primitives ou hors du domaine permis restent inchangés. Aucune taille minimale
ni tolérance d'aire n'intervient. Les empreintes des primitives doivent être
liées à celles du domaine et des balayages réels par le constructeur.

Le reçu `status=completed` décrit cette opération locale, sans admettre le
support. Après normalisation, les preuves `D ⊆ candidat ⊆ allowed` restent
obligatoires, puis viennent triangulation, remappage, contacts, connexité et
audit complet des trajectoires réellement exposées.

Le [témoin skin576](intended-hole-evidence/skin576-assessment.json) conserve
le refus du résultat IEEE initial malgré une différence GEOS vide. Ses quatre
trous triangulaires sont chacun couverts entièrement par `D ∪ balayages` et
`allowed`. Leur retrait certifié passe les deux inclusions, avec tous les
sommets de l'extérieur inchangés. Ce témoin reste une construction planaire
locale ; aucun support complet n'a été régénéré par ce contrôle.

```sh
work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -B -m unittest tests.test_carrier_exact_intended_holes -v
```

Neuf tests ciblés vérifient les refus, la couverture collective par plusieurs
primitives, l'absence de nouveaux sommets et la reproduction des reçus réels.
