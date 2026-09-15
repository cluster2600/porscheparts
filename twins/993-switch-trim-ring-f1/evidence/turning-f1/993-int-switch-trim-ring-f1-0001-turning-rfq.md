# Demande de devis, tournage — 993-INT-SWITCH-TRIM-RING-F1-0001

**Bague aluminium de finition de commutateur, reconstruction F1**

Demande de devis et de faisabilite, pas un ordre de fabrication. La piece
est classee `non_critical`. Le fournisseur est invite a contredire
ce qui suit, en particulier le choix de nuance.

## 1. Ce qui est fourni

| fichier | role | SHA-256 |
|---|---|---|
| `switch_trim_ring_f1.step` | maitre STEP | `3b59150dc69d962d9ea5606fd23d3afc552c953c919150c307904b351bba00df` |

Le STEP est le maitre. **Il porte des arêtes vives et aucune tolerance** :
les deux points sont ouverts ci-dessous et font partie de la question posee.

## 2. Route demandee

| poste | valeur |
|---|---|
| procede | CNC turning from bar |
| nuance | **EN AW-6063 T6** |
| designations | EN AW-6063 (AlMg0,7Si), UNS A96063, EN 755-2 for extruded bar |
| barre | Ø32 mm |
| diametre exterieur | 30.5 mm |
| profondeur | 10.5 mm |
| paroi la plus mince | 1.25 mm |
| finition | tournage de finition puis anodisation brillante |
| anodisation | anodisation sulfurique decorative, incolore, epaisseur a convenir |

**Pourquoi le 6063 et pas le 6061.** La piece est visible et ne porte rien :
le critere qui gouverne est l'aspect. Le 6063 est la nuance de reference de
l'anodisation brillante. Nous savons que c'est le moins agreable des deux a
tourner :

- Le 6063 est tendre et collant : copeaux longs et filants qui chargent l'outil.
- Outil carbure non revetu, arete vive et polie, grande vitesse de coupe, avance continue sans temps mort.
- Ce n'est pas une difficulte de procede mais une contrainte de parametres, a transmettre au tourneur.

Si votre atelier juge le 6063 deraisonnable pour cette piece, dites-le et
chiffrez le 6061 T6 en regard, en indiquant ce que l'aspect y perd.

## 3. Questions ouvertes

- **thin_wall_workholding_reviewed** — La paroi la plus mince vaut 1.25 mm, soit 4.1 % du diametre exterieur. Un serrage en mors durs sur cette bague peut l'ovaliser, et la tronconnage final la liberer deformee. Mors doux, bague de serrage ou reprise sur mandrin expansible sont a arbitrer par le tourneur.
- **edge_break_specified** — Le maitre parametrique a des arêtes vives. Une bague decorative se juge d'abord sur son arête avant, et une arête vive s'anodise mal et coupe au montage. Chanfrein ou rayon avant, arriere et d'alesage restent a decider puis a porter au modele.
- **fit_dimension_toleranced** — Le diametre exterieur de 30.5 mm est la cote qui decide du maintien dans le tableau de bord, et il n'a aucune tolerance. Il vient d'une page de vente d'une bague adaptable, pas d'une mesure du logement. Sans ouverture mesuree, aucune tolerance ne peut etre prescrite honnetement.
- **anodising_growth_subtracted_from_fit** — Une couche de 5 a 15 um croit pour moitie vers l'exterieur, soit environ 0.005 a 0.015 mm sur le diametre. C'est du meme ordre que le jeu recherche : la correction ne peut etre appliquee qu'une fois la porte precedente ouverte.
- **material_certificate_contracted** — Ni nuance certifiee, ni etat metallurgique verifie ne sont engages avec un tourneur.

## 4. La cote d'ajustement, et ce que nous proposons

L'ouverture du tableau de bord n'est pas mesuree, et le diametre exterieur est repris d'une page de vente.

Sur une piece tournee, la deuxieme et la troisieme coutent une fraction de la premiere. Commander trois bagues nues, non anodisees, a trois diametres exterieurs echelonnes, essayer, puis n'anodiser que la bonne — en retranchant alors la croissance de couche.

Diametres demandes : **30.40 mm**, **30.50 mm**, **30.60 mm**, trois pieces nues, non anodisees.

_Mesurer le logement reste preferable et reste a faire. La serie de trois est ce qui permet d'avancer sans metrologie du vehicule, pas ce qui la remplace._

## 5. Livrables attendus avec le devis

- prix des trois bagues nues, puis prix de l'anodisation d'une seule ;
- prix de la meme piece en 6061 T6, pour comparaison ;
- chanfreins ou rayons d'arête que vous recommandez, et pourquoi ;
- tolerance que votre tour tient reellement sur le diametre exterieur ;
- epaisseur d'anodisation obtenue et sa dispersion ;
- certificat matiere de la barre ;
- delai.

## 6. Reserve

Les cotes proviennent d'une fiche commerciale d'une bague adaptable, pas
d'un plan d'origine ni d'une mesure. Aucune piece issue de ce devis ne doit
etre consideree comme conforme a l'origine.
