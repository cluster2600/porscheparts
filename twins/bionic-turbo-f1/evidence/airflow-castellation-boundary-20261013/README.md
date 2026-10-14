# Castellation régionale : raccord conservé, maillage rejeté

Le contrôle 091 conserve les 6 784 quadrilatères du raccord mais échoue à l'admission native. Aucun solveur d'écoulement n'a été lancé. Il s'agit du sous-domaine **fixe et synthétique** 086, sans rotor ni ports physiques ; aucune pièce du turbo n'est modifiée.

## Protocole et sources

La lecture de `refinementSurfaces.C` et `snappyRefineDriver.C`, leurs empreintes et le script reproductible ont été publiés dans les trois actifs préalables de la [release](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-castellation-boundary-2026-10-13) avant préparation. Le niveau est lu par région nommée, mais les étapes ultérieures ne constituent pas une protection générale du raccord. L'archive officielle v2406 reste inchangée.

Le plus petit raffinement isotrope non nul `(1 1)` est demandé uniquement sur `outer`, les autres régions restant à `(0 0)`. Ce contrôle exerce une nouvelle opération, sans balayage. Castellation seule, sans projection ni couches ; critères de qualité hérités, `nCellsBetweenLevels 3`, `minRefinementCells 0`, `writePrecision 16`. Les sorties de débogage conservent les étapes intermédiaires. Les répertoires numériques sont des étiquettes de maillage, **pas des temps d'écoulement**. Docker et les reçus sont inspectés ; entrées copiées avant chaque lancement, conteneurs conservés.

## 089 : cible fermée

La cible triangule exactement les 14 336 quadrilatères de frontière de 086 suivant `(v0,v1,v2)/(v0,v2,v3)` : 28 672 triangles, 14 336 sommets, quatre régions (rear/front : 768 triangles chacune ; join/outer : 13 568 chacune). Les coordonnées décodées, triangles orientés et arêtes appariées sont relus indépendamment. `surfaceCheck` confirme fermeture, une composante et une orientation cohérente ; code zéro, sans OOM, 2,372 s. Ce n'est pas une admission volumique.

Les quads gauchis et leur triangulation ne sont pas la même représentation. La borne symétrique de 5,259726 µm concerne exclusivement deux facettisations explicites : éventail à la moyenne des quatre sommets et triangulation sur la diagonale v0–v2. La convexité projetée et l'appariement barycentrique de leurs quatre triangles sont vérifiés. Ce n'est ni une distance mesurée ni une tolérance physique. Volume signé de la cible triangulée : 2,333381614256911e-6 m³ ; volume calculé depuis les polygones natifs : 2,333381635788163e-6 m³, différence −2,1531252e-14 m³. Le point intérieur est contrôlé par plans des faces et enroulement de la surface fermée.

## 090 : refus de syntaxe conservé

Il manque une accolade fermante dans `refinementSurfaces`. Le natif s'arrête avant raffinement : code 1, sans OOM, 0,422 s. Entrées, source et erreur sont conservées. 091 ajoute uniquement cette accolade dans les entrées `constant/system` ; les manifestes diffèrent naturellement par leur provenance. Aucun calcul 090 n'est rejoué.

## 091 : résultat refusé

Le lancement se termine avec code zéro sans OOM en 15,722 s, mais `checkMesh` refuse chacun des seize instantanés de maillage vérifiés. Le résultat final est dans `2.6e-06/polyMesh` ; `constant/polyMesh` reste le parent initial. Les étapes intermédiaires ne sont pas toutes identiques : certaines comportent 163 136 faces, contre 162 880 finales. Elles sont toutes conservées.

- 44 992 cellules, 76 049 points, 162 880 faces dont 137 648 internes ; une région fluide.
- 3 520 parents extérieurs donnent huit enfants chacun, soit 28 160 cellules de niveau 1 ; 16 832 parents restent au niveau 0. Aucun parent raffiné ne touche le raccord.
- Chaque cellule finale est rattachée indépendamment à son parent par ses sommets originaux et le centre partagé entre huit enfants. Toutes les chaînes d'arêtes s'annulent ; volumes positifs.
- Toutes les coordonnées originales décodées restent exactement présentes. Les 6 784 quads du raccord conservent leurs cycles orientés et coordonnées ; planéité maximale 1,06252e-17 m et normale géométrique de rotation 2,28795e-12 m/s. Le domaine est fixe : ce diagnostic n'applique pas une rotation et ne représente aucun débit d'air.
- Volume reconstruit 2,333381635788175e-6 m³, natif 2,333381635788208e-6 ; minimum cellulaire 3,6337154974e-12 m³. Planéité globale maximale 6,79194e-7 m.
- **6 700 cellules signalées concaves**, toutes au niveau grossier ; aucun de leurs parents ne touche le raccord. Ne pas confondre ce critère natif avec une preuve de concavité stricte ni en déduire une cause unique.
- **14 080 faces au-dessus de 70°**, maximum 81,887377°. Le journal snappy signale aussi 14 080 faces illégales au contrôle >65°. Ces diagnostics sont conservés séparément.
- Déterminant minimal 0,0062026257, supérieur au critère inchangé 0,001. Ce succès isolé ne compense pas les autres rejets.

Aucun repos, convergence linéaire, stabilité, débit ou puissance n'est qualifié. 084 reste interrompu au budget, sans champs finaux ; il n'est ni repris ni prolongé. Le traitement des parois physiques et la conservation des coquilles, jeux, connexions et couches restent ouverts.

Voir `validation.md`, `readback.json`, `target-readback.json` et `next-scope.md`. Les archives précédentes et tous les refus restent immuables.
