# Convergence20 et admission finie sous l'ancienne borne5δ

Cette version Python réutilise **sans recompilation ni modification** le
binaire exact de distanceV3. Elle sépare le budget de calcul du snap et le
critère géométrique mesuré.

```sh
python3 parts/993-eng-carrier-0001/source/native-cgal-distance-20261016-v4/setup.py \
  /chemin/neuf/distance-v4 --distance-runtime /chemin/distance-v3

python3 /chemin/snap/run.py ENTREE.npz /chemin/snap/jobs/essai20 \
  --grid-bits 51 --iterations 20 --max-drift-mm BORNE_ORIGINALE_5DELTA

python3 /chemin/neuf/distance-v4/run.py ENTREE.npz \
  /chemin/snap/jobs/essai20 /chemin/neuf/distance-v4/jobs/mesure20 \
  --frozen-limit-job /chemin/snap/jobs/essai5-original
```

Le reçu original doit porter exactement la même identité SHA256 d'entrée,
gs51, cinq itérations et la borne `5 × norm(pas) / 2`. Le nouveau snap doit
porter gs51, vingt itérations, les mêmes pas et une limite explicite
strictement égale à cette ancienne borne. Les reçus originaux sont copiés et
empreintés avant/après ; ils ne sont pas modifiés. Un mauvais SHA d'identité
est refusé, même si le cube du témoin a les mêmes coordonnées.

Le programme conserve sa borne cumulée de déplacement **20δ**. L'admission
sous **5δ** vérifie seulement l'**ensemble fini déclaré** de tous les sommets
et de tous les barycentres rationnels exacts, dans les deux directions, par
les mêmes distances Epeck et témoins de triangles queV3. Elle n'établit **pas
une borne continue globale de Hausdorff5δ**. Ces deux grandeurs et cette
portée sont distinctes dans le reçu ; augmenter le calcul n'élargit pas le
seuil mesuré.

Champs propres au schéma `fixed-finite-sample-drift-v4` :

- `convergence_iteration_budget`:20 ; `reference_iteration_budget`:5 ;
- `program_cumulative_rounding_budget_mm`:20δ ;
- `finite_sample_admission_limit_mm`:5δ ;
- `frozen_limit_audit_sha256`, `frozen_limit_native_sha256`,
  `frozen_limit_execution_receipt_sha256`.

Le retour natif vrai, les coordonnées IEEE exactes, les contacts globaux
Epeck, la topologie et la filiation restent exigés. Les anciennes versions
et leurs refus restent intacts. La version du lecteur de magasin doit
reconnaître explicitement ce nouveau schéma avant d'admettre une sortie.

Installation et deux témoins exécutés : cube20 sous sa borne originale5δ
admis avec distances0 ; même calcul avec reçu original d'un autre SHA
d'entrée refusé. Le binaire et les licences restent ceux deV3 : CGAL AABB
GPL-3.0-or-later ou commercial, noyau exact LGPL-3.0-or-later ou commercial.
Les limites restent deux CPU, 4 Gio, sans swap, 600 s et aucun réseau, avec
nettoyage du scope vérifié. Aucun booléen CSG n'est rejoué par ce réauditeur.
