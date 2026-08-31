# Scan local d'un moteur Porsche 917 avec cylindres

## Statut

- Niveau : `F0_reference`.
- Identification : suggérée par le nom du fichier, non vérifiée par une source.
- Licence et redistribution : inconnues ; publication du brut bloquée.
- Compatibilité 993 ou 935 : non démontrée.

Le fichier trouvé dans iCloud Drive représente visuellement un long carter de
moteur à plat avec deux rangées de six cylindres. Cela correspond à
l'architecture attendue d'un flat-12 et en fait une référence géométrique utile,
mais le nom du fichier ne constitue pas une preuve d'identification ou de cote.

## Empreinte et inspection

```text
SHA-256 428c4143d073f8330022f2fecbd1ac1ee7784d4f1565f1160020448dbdffa0ae
```

| Propriété | Résultat |
|---|---:|
| Taille | 107 128 223 octets |
| Sommets | 1 282 880 |
| Triangles | 2 465 879 |
| Composants topologiques | 3 |
| Enveloppe | 1002,175 × 768,275 × 739,765 unités OBJ |
| Arêtes ouvertes | 101 809 |
| Arêtes non-manifold | 0 |
| Faces de surface nulle | 2 |
| Étanche | non |

Les trois composants contiennent respectivement environ 2 320 604, 141 542 et
3 747 triangles. Le premier regroupe l'essentiel du carter et des cylindres ;
les deux autres devront être identifiés visuellement avant toute suppression.

## Apport possible au projet

Ce scan peut aider à développer et vérifier les méthodes génériques de :

- segmentation d'un grand ensemble moteur ;
- détection répétée des axes et entraxes de cylindres ;
- recalage de rangées de cylindres et plans de joint ;
- construction d'enveloppes de collision ;
- comparaison d'architectures de refroidissement par air.

Il ne doit pas servir directement à fabriquer une pièce de 993. Les interfaces,
matériaux et charges d'un moteur 917 diffèrent et aucune équivalence n'est
actuellement démontrée.

## Données à retrouver

1. URL ou vendeur d'origine ;
2. texte exact de la licence ;
3. définition du « 0.5 mm » dans le nom ;
4. variante du moteur 917 et configuration du scan ;
5. au moins une cote physique ou documentaire de contrôle.

La fiche structurée associée est
`catalog/sources/src-local-917-engine-case-cylinders-scan.json`.
