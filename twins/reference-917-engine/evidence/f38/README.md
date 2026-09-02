# Preuve numérique F38

`gas-path-network-f38-report.json` est la sortie canonique, déterministe et
hors réseau du réseau stationnaire F38. Le rapport lie sept parents par
SHA-256, publie les stations des deux variantes, relit les identités de masse
F33, calcule le devoir thermique prescrit de l'échangeur et ferme l'identité
d'arbre turbo. Il ne présente pas ces calculs comme validations indépendantes.
Les flottants calculés sont canonisés à 12 chiffres significatifs afin de
stabiliser la sortie entre versions Python supportées.

Le hash attendu du fichier est :

```text
f433c3a7e0dbfee9139bcd72b244dedfa28bf781101c0bd38ccb47bb9b565e10
```

La proximité du point turbo avec 1 600 hp mécaniques est une comparaison avec
le calcul 0D F33 non corrélé, pas une preuve de 1 600 PS/ch. La cible n'est pas
une entrée directe du solveur F38, mais son ascendance indirecte F34 et le seed
de dimensionnement inverse restent explicitement présents. Les maps turbo, la
dynamique 1D, le banc physique, le démarrage et la fabrication restent tous
bloqués.

Reproduction :

```bash
make 917-gas-path-network-f38
shasum -a 256 work/917-gas-path-network-f38/gas-path-network-f38-report.json
```
