# Essai numerique de resistance — plancher 964 en torsion

Chaine : gmsh 4.15.2 (maillage coque) -> CalculiX 2.21 (elements S3).
Acier E = 210 000 MPa, nu = 0,3. Unites mm, N, MPa.

Cas de charge : arriere encastre, couple de 1290 N.m applique en pointes de
longeron a l'avant (1000 N vers le haut a gauche, 1000 N vers le bas a droite,
bras de levier 1290 mm).

## Epaisseur de tole

Donnee apportee par le proprietaire du projet : **0,8 mm annonce par Porsche,
1,0 mm mesure**. Les deux valeurs sont conservees, non moyennees.

| epaisseur | rotation | raideur en torsion | vM max |
|---|---|---|---|
| 0,8 mm (annonce) | 0,5283 deg | **2442 N.m/deg** | 86,1 MPa |
| 1,0 mm (mesure)  | 0,4222 deg | **3055 N.m/deg** | 68,8 MPa |

Rapport de raideur 1,251 pour un rapport d'epaisseur 1,250. **La raideur suit
l'epaisseur lineairement, pas au cube.** La structure travaille en cisaillement
de membrane, comme un caisson ferme, et non en flexion de plaque. L'ecart entre
0,8 et 1,0 vaut donc 25 % de raideur et 25 % de contrainte : ce n'est pas un
detail de modelisation.

Les 0,2 mm d'ecart demandent une explication avant d'etre utilises. La caisse
964 est galvanisee a chaud ; zinc, appret, peinture et cire de corps creux
s'ajoutent a la tole. Une mesure au pied a coulisse sur panneau en place mesure
l'empilement, pas l'acier. **Pour le calcul, c'est l'epaisseur d'acier qui
porte**, donc 0,8 mm tant que la mesure n'est pas refaite sur tole decapee ou au
mesureur a ultrasons. Retenir 1,0 mm surestimerait la raideur de 25 %.

## Ou ca travaille

| zone | contrainte moyenne | p95 | max |
|---|---|---|---|
| longeron (caisson ferme) | 22,0 MPa | 50,5 | 66,8 |
| traverse | 21,6 MPa | 30,0 | 45,7 |
| plancher | 10,4 MPa | 24,1 | 31,9 |

**Le longeron porte la torsion.** Les 1 % de noeuds les plus charges sont a
100 % dans le longeron, et le restent apres exclusion de 300 mm en avant de
l'encastrement : le resultat n'est pas un artefact de condition aux limites.
Environ 22 % du pic brut l'etait toutefois — 86,1 MPa tombent a 66,8 MPa une
fois la zone d'encastrement ecartee. Le rapport longeron/plancher est de 2,12.

Ce resultat converge avec le manuel : la planche 50-013 designe le *inner side
member* comme panneau en acier haute resistance. Porsche a mis l'acier HS la ou
le calcul place le chemin d'effort.

## Ce que ces chiffres ne sont pas

**2442 N.m/deg n'est pas la raideur d'une 964.** Le modele ne contient ni
tablier, ni cloison arriere, ni tunnel central, ni passages de roue, ni pavillon,
ni pieds milieu, ni cadre de pare-brise, qui portent l'essentiel de la torsion
d'une caisse complete. Il ne contient que plancher, deux longerons et trois
traverses.

De plus la section de longeron 90 x 120 mm et la section de traverse 80 x 70 mm
restent `ASSUMED` : le volume V ne les publie pas. La position longitudinale des
traverses depend de la chaine de datums, elle-meme non calee (voir le README du
jumeau).

Sont robustes, parce qu'ils ne dependent pas de ces inconnues :
- la loi d'echelle lineaire en epaisseur, qui est un resultat de mecanique ;
- le fait que le longeron, et non le plancher, porte la torsion.

Ne sont pas robustes : toutes les valeurs absolues de raideur et de contrainte.

## Rejouer

    source ../source/env.sh
    pycad build_shell.py 0.8 1.0 && pycad run_fea.py 0.8 t08
    pycad build_shell.py 1.0 1.0 && pycad run_fea.py 1.0 t10

## Variante composite

`run_fea.py` accepte desormais deux arguments optionnels, `E` et `nu`, qui
valent par defaut ceux de l'acier : les appels a deux arguments ci-dessus sont
inchanges. `laminate.py` calcule les proprietes quasi-isotropes d'un stratifie
carbone, aramide ou hybride depuis les constantes de pli, et `composite_study.py`
rejoue l'essai de torsion a raideur egale pour chacun.

Resultat court : a iso-raideur, le carbone monolithique ne gagne que **18 %** de
masse surfacique et l'aramide en **perd 30 %**, parce que ce caisson travaille en
cisaillement de membrane et que le critere est `G/rho`, non `E/rho`. L'analyse
complete et ses reserves sont dans `docs/research/964-chassis-carbone-kevlar.md`.

    pycad build_shell.py 0.8 1.0 && pycad composite_study.py

## Architecture contre materiau

`build_body.py` etend le modele coque aux elements qui **ferment** le caisson —
tablier avant, cloison arriere, tunnel central — et `architecture_study.py`
rejoue l'essai sur trois architectures et deux materiaux a masse egale. Le cas
`f`, plancher seul, redonne le maillage et la valeur de `build_shell.py`.

A masse egale, fermer la caisse vaut **x 1,61** en raideur specifique, passer au
carbone **x 1,25**, et les deux se multiplient (1,98 mesure pour 2,01 attendu) :
les leviers sont separables et ne se substituent pas. Le tunnel central seul
apporte +72 %, plus que les deux cloisons. Sections et hauteurs de cloison sont
`ASSUMED` ; seuls les rapports sont exploitables.

    pycad architecture_study.py
