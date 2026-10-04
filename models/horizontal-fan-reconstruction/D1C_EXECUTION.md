# D1C : essai terminé, admission numérique limitée

Une seule branche de 60 itérations a été autorisée après libération des
réservations Kali2. Elle reprend le même état V2/900 et les mêmes 80 fichiers
de partition MPI que le témoin D1 conservé. Le seul changement numérique est
`SIMPLE.consistent no` → `yes`. Aucun maillage, condition physique, schéma,
relaxation, tolérance ou critère d'admission n'est changé.

[Résultat et fenêtres natives](results/cfd/D1C-bounded-result.json) ·
[Résumé original à 960](results/cfd/D1C-960-flow-summary.json) ·
[Champs comparés et reflux](results/cfd/D1C-matched960-field-differences.json) ·
[Bilan des ports](results/cfd/D1C-960-energy-and-port-analysis.json) ·
[Conservation](results/runtime/D1C-native-archive-verification.json).

## Mesures et critères identiques

Les itérations 901–960 sont toutes terminées, sans queue partielle. Chaque
table native contient **61 mesures, état 900 compris**, soit 60 nouvelles.
Les trois fenêtres prospectives 901–920 / 921–940 / 941–960 disposent de vingt
échantillons consécutifs ; la dernière est la fenêtre d'admission. Les cinq
champs finaux U/p/k/omega/nut contiennent chacun 453 496 cellules finies.

| Mesure sur 941–960 | Témoin D1 consistent no | D1C consistent yes |
| --- | ---: | ---: |
| Résidu initial p maximal | 1,386159985×10⁻⁴ | 7,622277815×10⁻⁵ |
| Débit de sortie moyen, m³/s | 1,15229935155 | 1,152299802885 |
| Puissance moyenne, W | 2429,758222624 | 2429,768471103 |
| CV débit | 2,77178×10⁻⁷ | 3,30038×10⁻⁷ |
| CV couple | 3,04282×10⁻⁵ | 2,59172×10⁻⁵ |
| Déséquilibre maximal des ports | 1,44516×10⁻⁵ | 1,43770×10⁻⁵ |

La baisse du maximum initial p est **45,0116 %**. Le candidat passe tous les
critères originaux : p ≤10⁻⁴, U ≤10⁻⁵, k/ω ≤10⁻⁴, déséquilibre ≤0,5 %, CV
débit ≤1 %, CV couple ≤2 %, direction et champs complets finis. Il satisfait
la règle prospective « baisse p ≥30 % et tous les gates » : ce résultat étaye
une **sensibilité numérique au couplage**, sans identifier une cause physique.
Le témoin D1 reste non admis sur p. Les mesures R0 manquantes ne sont pas
restaurées et aucune paire historique fine n'est rétroactivement admise.

Le débit moyen change de +0,00003917 % et la puissance de +0,00042179 %.
Ces différences ne prouvent aucun gain de refroidissement ou de rendement.
Les itérations stationnaires ne représentent ni temps physique, ni fréquence
de rotor, ni réalisations statistiques indépendantes.

![Résidus natifs D1C et témoin, fenêtre finale fixée avant calcul](results/cfd/D1C-residuals.png)

## Reflux et champs locaux : limites explicites

À 960, le reflux brut reste **0,123990213 m³/s**, soit **10,76024 %** du débit
net. Il concerne les mêmes 1 572 faces sur 4 542 et **35,15382 %** de la surface
de sortie, pratiquement comme le témoin. L'amélioration du résidu n'a pas
résolu l'influence possible de cette sortie proche, ni fourni une résistance
de moteur mesurée.

La comparaison des champs à 960 donne une différence p RMS pondérée par
volume de 0,544038 Pa, mais un maximum local de **317,669 Pa** ; ΔU RMS est
0,0624630 m/s. La stabilité des débits/couples intégrés ne garantit donc pas
l'insensibilité des champs locaux. Ces différences ne sont ni des résidus
algébriques cellulaires ni une incertitude expérimentale. L'indépendance de
maillage, les couches de paroi, les interfaces et conditions installées
restent non qualifiées.

Le Mach absolu maximal reste 0,3766 sous les hypothèses de screening :
une sensibilité compressible demeure requise. La pression totale de sortie
pondérée par flux est 1569,57 Pa. Le ratio énergie des ports / puissance
0,7444 n'est pas un rendement qualifié. Le couple de pression est retrouvé
avec une erreur relative de 4,68×10⁻¹² et la vitesse de paroi Ω×r à
7,05×10⁻⁹ m/s ; ces identités vérifient la lecture des sorties, pas leur
validation physique.

## Budget et clôture

Préflight actuel : Kali2 amd64, 12 CPU logiques, mémoire disponible
11 353 784 320 octets, aucun conteneur d'écoulement actif. Les limites réelles
sont 4 CPU, cpuset 0/2/4/5, RAM et mémoire+swap 5 GiB, réseau absent, UID/GID
1000, capabilities supprimées et sources/baseline/capsule en lecture seule.
Les services préexistants restent identiques.

Solveur 117,18 s, reconstruction 4,97 s, audit natif 2,63 s ; préparation,
archivage et vérification compris, **128,169 s au total**, sous le plafond
global 300 s. Le conteneur propre est libéré à **18:25:36 UTC le 4 octobre
2026**. Aucune seconde branche, phase additionnelle, relance ou prolongation.

L'archive privée des champs finaux, journaux, systèmes et reçus contient
25 membres vérifiés, 47 464 242 octets, SHA-256
`916c4b4e2a23c22e112763f58a9592896ee28e8f7e05ae8cb608e73c776fbfad`.
Les trois tables natives sont conservées et rapatriées séparément : leurs
empreintes correspondent au résumé natif original inclus dans l'archive.
Le transfert et chaque membre sont vérifiés. Scan, champs complets et tables
restent privés ; les rapports publiés sont assainis.

Les [configurations utilisées](parameters/D1C-executed-configurations/) et
le [manifeste de capsule](parameters/D1C-executed-capsule-manifest.json) sont
conservés. Les indicateurs `not_launched` des protocoles figés décrivent leur
préparation avant lancement ; ils ne remplacent pas le reçu d'exécution.
Le [protocole prospectif](parameters/D1-coupling-proposed-protocol.json) reste
préservé sans réécriture après connaissance du résultat.

Reproduction du paquet et analyses depuis les entrées natives privées :

~~~sh
python source/prepare_d1c_capsule.py . work/D1C-capsule
python source/analyze_d1c_result.py PRIVATE_D1C_INPUTS . work/D1C-result.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python source/compare_d1c_native_fields.py PRIVATE_D1_CONTROL_FIELDS PRIVATE_D1C_INPUTS work/D1C-field-differences.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python source/analyze_flow_balance.py PRIVATE_D1C_CASE work/D1C-port-analysis.json --time 960
python source/verify_study.py
~~~

Ces commandes ne lancent aucun solveur. Une reproduction du calcul via
`launch_d1c.py` exige une nouvelle fenêtre coordonnée et les sources privées
900/partition ; elle n'est pas lancée automatiquement.
