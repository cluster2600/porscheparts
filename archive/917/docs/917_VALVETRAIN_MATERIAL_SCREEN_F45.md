# Criblage distribution et matière F45 — culasse 917/30 turbo

## Résultat

F45 fournit un **pré-dimensionnement analytique**, reproductible et fermé par
défaut, de deux architectures de recherche : 2 soupapes et 4 soupapes par
cylindre. Il ne libère ni une culasse, ni une distribution, ni une impression.

La contrainte géométrique est absolue dans ce sous-lot :

- alésage strictement circulaire de 90 mm, issu de l'autorité F45 ;
- composants fonctionnels circulaires uniquement ;
- enveloppe extérieure `scan-contour` conservée ;
- aucune ovalisation, mise à l'échelle anisotrope, surface de corps ou ailette
  synthétique ;
- aucune cote d'interface Porsche inventée.

L'[image comparative](../twins/reference-917-engine/evidence/f45-valvetrain/valvetrain-material-screen-f45.png)
est donc volontairement une vue de paquetage en plan. Elle n'est pas un rendu
de culasse.

## Frontière de preuve

Les seules dimensions historiques directes de soupapes suivies dans le dépôt
proviennent de la fiche FIA du **Type 912 initial atmosphérique de 4 494,2 cm³** :
47,5/40,5 mm et levées 12,1/10,5 mm à l'admission/échappement. Elles ne sont
jamais relabellées « 917/30 exactes ». Elles servent de référence documentaire,
pas d'entrée géométrique transférée au candidat turbo F45.

Le kit Swindon 24 soupapes est un benchmark M64 pour alésages 95–102,7 mm. Ses
40/33 mm, levées 11,5/9,6 mm et 12 000 tr/min déclarés ne sont pas transférés à
l'alésage 90 mm.

Toutes les dimensions F45 ci-dessous sont des **hypothèses de recherche**. Les
angles d'axes, logements, interférences, jeux, portées, cotes de ressort et
interfaces de commande restent à mesurer ou à recevoir sur plans fournisseurs.

## Hypothèses de calcul

Le criblage commun utilise 9 000 tr/min, un événement symétrique de 300° vilebrequin,
un profil demi-cosinus, un rapport gorge/tête de 0,86 et un coefficient de débit
non corrélé de 0,72. Les différences de pression de 0,25 MPa à l'admission et
0,50 MPa à l'échappement sont des charges exploratoires, pas des traces cylindre.

Les équations sont enregistrées dans le JSON :

\[
A_{rideau}=n\pi d_vL,
\qquad
A_{gorge}=n\frac{\pi(0{,}86d_v)^2}{4}
\]

\[
t_e=\frac{\theta_e}{6N},
\qquad
v_{max}=\frac{\pi L}{t_e},
\qquad
a_{max}=\frac{2\pi^2L}{t_e^2}
\]

\[
k=\frac{Gd_f^4}{8D_m^3N_a},
\qquad
K_W=\frac{4C-1}{4C-4}+\frac{0{,}615}{C},
\qquad
\tau=K_W\frac{8FD_m}{\pi d_f^3}
\]

La fréquence d'événement quatre temps vaut 75 Hz à 9 000 tr/min. La fréquence
propre reportée est un modèle SDOF avec un tiers de la masse des ressorts. Elle
ne remplace ni une analyse multi-corps, ni une carte de surge, ni un spintron.
La limite de cisaillement de 1 000 MPa est uniquement un seuil de recherche,
pas un allowable fournisseur.

## Matrice 2V / 4V

| Paramètre | 2V F45 | 4V F45 |
|---|---:|---:|
| Admission | 1 × Ø42 × levée 11,5 mm | 2 × Ø31,5 × levée 10 mm |
| Échappement | 1 × Ø35 × levée 10 mm | 2 × Ø26 × levée 9 mm |
| Tiges | Ø7 mm | Ø7 mm |
| Aire admission effective écran | 737,8 mm² | 830,0 mm² |
| Aire échappement effective écran | 512,3 mm² | 565,5 mm² |
| Masse totale estimée des têtes+tiges | 81,8 g | 132,4 g |
| Bord minimum siège/alésage | 1,50 mm | 3,27 mm |
| Pont minimum siège/siège | 2,00 mm | 3,25 mm |
| Siège/bougie de paquetage | non défini | 3,16 mm |
| Écart minimum des enveloppes de ressort | 12,9 mm | 8,7 mm |

Le paquetage 4V augmente l'aire effective de criblage de 12,5 % à l'admission
et de 10,37 % à l'échappement, mais augmente de 61,95 % la masse totale estimée
des quatre soupapes. Cette comparaison n'est pas un résultat de banc de flux.
La bougie centrale Ø10 mm n'est qu'une enveloppe de paquetage, pas une interface
Porsche définie.

## Cinématique et ressorts

| Architecture/famille | `vmax` (m/s) | `amax` (m/s²) | inertie (N) | charge gaz (N) | ressort ouvert (N) | marge charge | Wahl max (MPa) | marge bind pire cas (mm) | `fn/75 Hz` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2V admission | 6,503 | 7 355 | 512,2 | 346,4 | 1 466,1 | 1,708 | 992,3 | 2,52 | 2,034 |
| 2V échappement | 5,655 | 6 396 | 563,7 | 481,1 | 1 327,0 | 1,270 | 898,2 | 4,02 | 1,870 |
| 4V admission | 5,655 | 6 396 | 319,4 | 194,8 | 857,6 | 1,668 | 902,7 | 4,70 | 1,974 |
| 4V échappement | 5,089 | 5 756 | 381,5 | 265,5 | 797,9 | 1,233 | 839,8 | 5,70 | 1,775 |

Les deux ressorts concentriques CrSi de chaque architecture passent seulement
les écrans statiques hypothétiques de charge, Wahl et coil-bind. Le faible
rapport modal, surtout à l'échappement 4V, interdit toute conclusion dynamique.
Le JSON conserve donc `dynamic_screen_pass=false` et
`analytical_screen_pass=false` pour chaque famille.

Les soupapes et ressorts ne sont **pas imprimés** :

- admission : candidat Ti-6Al-4V acheté, forgé ou corroyé ;
- échappement : candidat INCONEL 751 acheté, sur barre ou forgé ;
- Nimonic : non noté, faute de source fabricant officielle suivie dans ce lot ;
- ressorts : CrSi ultra-propre acheté, revenu à l'huile, nitruré/grenaillé à
  confirmer avec le fournisseur ;
- sièges/guides : inserts achetés et usinés de finition. Les cotes de serrage,
  portées, jeux à chaud et alésages sont volontairement `null`.

## Criblage du corps LPBF

| Candidat | Données chaudes officielles suivies | Conductivité suivie | Décision F45 |
|---|---|---|---|
| Aheadd HT1, traitement #1 | Rp0,2 425/238/188 MPa à 25/200/250 °C | absente | non sélectionné |
| Aheadd HT1, traitement #2 | Rp0,2 285/270/216 MPa à 25/200/250 °C | absente | non sélectionné |
| A20X/A205 LPBF T7 | Rp0,2 445/311/215 MPa à 20/200/250 °C | absente | non sélectionné |
| EOS AlF357 T6-like | Rp0,2 265 MPa à 20 °C | 150 W/mK à l'ambiante | non sélectionné |
| EOS AlSi10Mg T6 | Rp0,2 245 MPa à 20 °C | 155–165 W/mK selon orientation | non sélectionné |

La demande « Aheadd HT2 » est normalisée : la fiche Constellium décrit le
**traitement #2 du même Aheadd HT1**, pas un alliage Aheadd HT2 distinct.
A20X publie un point de traction à 250 °C mais circonscrit son emploi annoncé à
190 °C ; le point à 250 °C ne constitue donc pas une autorisation de service.

Aucun candidat ne dispose ici d'une carte complète, propre à la route
machine/poudre/orientation/traitement : `k(T)`, `E(T)`, dilatation, plasticité,
LCF/HCF/TMF, fluage/relaxation, sensibilité aux défauts et répétabilité du build.
La sélection matériau reste donc `null`. Des coupons à chaud représentatifs
de la machine et du traitement final sont obligatoires.

## Livrables et reproduction

- [rapport JSON](../twins/reference-917-engine/valvetrain-material-screen-f45.json) ;
- [générateur déterministe](../twins/reference-917-engine/source/build_valvetrain_material_screen_f45.py) ;
- [tests](../tests/test_917_valvetrain_material_screen_f45.py) ;
- [image comparative](../twins/reference-917-engine/evidence/f45-valvetrain/valvetrain-material-screen-f45.png).

```bash
make 917-valvetrain-material-f45
make 917-valvetrain-material-f45-check
```

Le contrôle échoue si le JSON suivi n'est plus identique au calcul. Tous les
gates de libération restent à `false`, notamment interfaces 917, loi de came,
plans fournisseurs, press-fits à chaud, carte matière complète, spintron,
fatigue thermomécanique, impression métal et démarrage moteur.

## Sources officielles

- [FIA, fiche d'homologation nº 250](https://historicdb.fia.com/sites/default/files/car_attachment/1601078401/homologation_form_number_250_group_4.pdf), valeurs Type 912 initial uniquement ;
- [Constellium, Aheadd HT1](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/aheadd_ht1_fact_sheet_230620.ccac52e244fb.pdf) ;
- [ECKART, A20X/A205 LPBF](https://www.eckart.net/en/download/document/view/id/519) ;
- [EOS, AlF357](https://www.eos.info/metal-solutions/data-sheets/all-processes-and-materials?id=eos-aluminium-alf357) ;
- [EOS, AlSi10Mg](https://www.eos.info/metal-solutions/metal-materials/data-sheets/mds-eos-aluminium-alsi10mg) ;
- [TIMET, Ti-6Al-4V](https://www.timet.com/documents/datasheets/alpha-and-beta-alloys/timetal-6-4.pdf) ;
- [Special Metals, INCONEL alloy 751](https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-751.pdf) ;
- [MAHLE, catalogue technique de distribution](https://www.mahle-aftermarket.com/media/homepage/facelift/media-center/product-catalogs/mahle_valve_train_components_catalog_2025_screen_v002.pdf) ;
- [Swindon Powertrain, kit 24 soupapes M64](https://swindonpowertrain.com/products/24-valve-porsche-911-m64-cylinder-head-kit/).
