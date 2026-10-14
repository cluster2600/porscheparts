# Planéité à centre natif et gardes mathématiques

Ce contrôle traite les expressions mathématiques de planéité OpenFOAM v2406
sur les 153 boîtes conservées, u=q_m source. Il utilise le **centre natif de
face**, le seuil source 0.8 et le terme additif ROOTVSMALL. Aucun aplanissement,
ratio ponctuel, subdivision ou nouveau candidat. Ce n'est pas une admission
native ou un résultat CFD.

## Domaine et contrôles

L'enveloppe fermée est inchangée :
`[18685771944522017155/18446744073709551616,
9345323731508729405/9223372036854775808]`.
Les deux boîtes aux déterminants indécis restent présentes. Treize manifestes
parents et leurs 309 entrées sont ancrés au commit PR244
`cbf1a91cf4d53872ad2b067b0dc1fe5fe95e7f2b`.

Les 18 560 faces uniques comprennent 5 376 triangles (branche native de
planéité initialisée à 1) et 13 184 quads. Les quads gardent leurs coordonnées
et leur gauchissement. L'éventail pour la somme des normes est construit autour
de C_f natif PR236, et non autour de la moyenne arithmétique de preuve PR241.

Le parcours prescrit couvre d'abord l'enveloppe : 15 232 faces passent et
3 328 restent indécises. Leurs **509 184 contrôles locaux** sur les 153 boîtes
passent tous. Ainsi chaque boîte est couverte pour ce seul critère, sans
nouvelle exclusion. Les 3 328 indécisions sur l'enveloppe restent enregistrées.
Toutes les 527 744 lignes de bornes sont conservées dans
`flatness-bounds.jsonl.gz`, distribué dans l'archive.

Les gardes de centre de face et la condition d'entrée dans la branche de
planéité sont vérifiées quantitativement pour les quads aux domaines utilisés.
Pour chaque cellule, m>0 et E>=ROOTVSMALL sont vérifiés avec les seules faces
internes, avant division par m. Le triple volume hérité PR241 est comparé à
VSMALL avant /3. Les **6 144 gardes de déterminant et 6 144 gardes de volume**
sont inactives pour les expressions mathématiques sur l'enveloppe. Aucun ancien
polynôme de volume ou déterminant n'est rejoué; les deux indécisions de
PR238 ne sont pas levées par ces gardes.

## Reconstruction et relecture

`check_flatness.py` utilise les moments centrés PR236 et le noyau 160 bits
épinglé. `verify_flatness.py` reconstruit séparément les faces avec les six
gabarits hex réduits, contrôle les cycles opposés, puis utilise les moments
indépendants PR236 et la représentation dyadic192 PR238 déjà démontrée.
Il n'importe pas le nouveau premier évaluateur. Chaque borne reconstruite
doit être incluse dans sa borne primaire et chaque signe positif confirmé.
Neuf références analytiques sont vérifiées par chaque programme avant ses
applications : triangle, carré et quad gauchi symétrique à trois échelles.

`read_summary.py` relit l'ordre couvert et les comptes par boîte, puis extrait
les minima des bornes positives. C'est une lecture structurelle; la deuxième
reconstruction géométrique est celle de `verify_flatness.py`. Les reçus,
sources et journaux distinguent ces fonctions.

## Portée native et obligations restantes

Les constantes sont les rationnels des littéraux double sous l'hypothèse
WM_DP : ROOTVSMALL=1e-150, VSMALL=1e-300 et seuil 0.8, avec leurs valeurs
binary64 exactes dans les reçus. Le terme additif est conservé dans les
opérations d'intervalles même lorsqu'il est plus petit que leur quantum.
Ce n'est pas une borne des erreurs flottantes d'une exécution OpenFOAM, ni
une inspection de son futur binaire ou de la conversion writePrecision 16.

L'orthogonalité native possède son propre terme additif encore à traiter.
Décomposition checkFaceTets, poids, rapports, skewness, contacts internes de
dimension inférieure et bilan flottant restent distincts. Le dossier PR244
reste le registre des obligations : cette phase ne transforme pas les
113 boîtes aux prédicats nécessaires passants en solutions admises.

Les trois intervalles synthétiques ne qualifient pas les surfaces physiques,
les faces gauchies 086/091, la couronne entière, les couches ou le repos.
Le cas 084 reste incomplet et ne sera pas relancé. Aucun débit, puissance ou
calibration validé.

## Résultat de la lecture indépendante

La reconstruction est terminée sans assertion refusée : les **527 744
encadrements de faces et 2 100 224 bornes individuelles** sont tous relus,
avec inclusion des bornes indépendantes et confirmation des signes positifs.
Les 6 144 cellules sont contrôlées pour les deux gardes. La plus petite borne
de planéité utilisée dans la couverture positive est environ
**0.8545777791134115**, et non une planéité évaluée à un ratio choisi.
Les minima E et 3V sur l'enveloppe sont environ 1.1921329184726966e-7 m² et
5.746512310449939e-12 m³, très supérieurs aux constantes de branche, pour les
expressions mathématiques étudiées. Voir validation.md pour les tests et limites.
