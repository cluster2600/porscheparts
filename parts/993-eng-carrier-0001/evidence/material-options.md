# Choix matière pour une pièce usinée — 993-ENG-CARRIER-0001

Question posée : quelle matière pour que ce soit **plus solide**, et peut-être
**plus léger** ?

Les valeurs ci-dessous sont des ordres de grandeur de manuel. Une nuance retenue
devra être confirmée sur certificat matière du fournisseur, comme l'exige
`SAFETY.md`.

## Le point de départ, contre-intuitif

| Matière | E (GPa) | ρ (g/cm³) | Rm (MPa) | Raideur relative | Masse relative |
|---|---:|---:|---:|---:|---:|
| Acier au carbone, S355 | 210 | 7,85 | 500 | 1,00 | 1,00 |
| 42CrMo4 trempé revenu | 210 | 7,85 | 1000 | 1,00 | 1,00 |
| 17-4PH H1025 | 197 | 7,80 | 1070 | 0,94 | 0,99 |
| Aluminium 7075-T6 | 71 | 2,80 | 570 | 0,34 | 0,36 |
| Ti-6Al-4V | 114 | 4,43 | 950 | 0,54 | 0,56 |

**Tous les aciers ont le même module.** Passer d'un acier ordinaire à un acier à
haute résistance ne change **rien** à la raideur, donc rien à la flèche ni à
l'alignement du groupe motopropulseur. Si le symptôme est un moteur qui penche,
la nuance n'y peut rien : c'est la section qui décide.

## « Plus solide » ne veut pas dire « nuance plus résistante »

La pièce ne casse pas en traction, elle **fissure**. C'est de la fatigue, et la
fatigue à l'amorçage se joue sur quatre leviers, dans cet ordre :

1. **La géométrie.** Rayons de raccordement généreux, suppression des changements
   de section brutaux, perçages éloignés des zones tendues. C'est le levier
   dominant, et il est gratuit.
2. **L'état de surface.** Une surface usinée fine vaut mieux qu'une surface brute.
3. **Les contraintes résiduelles.** Le grenaillage de précontrainte met la peau en
   compression et retarde l'amorçage. Peu coûteux, très efficace.
4. **La nuance**, en dernier — et avec une réserve : plus un acier est résistant,
   **plus il est sensible aux entailles**. Une nuance à 1000 MPa mal raccordée
   peut tenir moins longtemps qu'un acier ordinaire bien dessiné.

À cela s'ajoute une règle propre à ce dossier : **ne pas souder**. La famille
fissure, et le témoignage recueilli montre qu'un gousset soudé voile la pièce.
Une pièce usinée monobloc évite ce défaut par construction.

## Nuances défendables

| Nuance | Pourquoi | Réserve |
|---|---|---|
| **42CrMo4 / AISI 4140, trempé revenu** | Le choix classique d'une pièce structurale usinée : bon compromis ténacité, endurance et usinabilité, matière peu chère | Ne résiste pas à la corrosion, protection obligatoire dans un environnement dont la corrosion est documentée |
| **17-4PH, état H1025 ou H1075** | Résistance comparable **et** inoxydable : supprime le besoin de revêtement, donc un mode de dégradation en moins | Plus cher, plus délicat à usiner ; état de revenu à choisir, H900 est trop fragile pour de la fatigue |
| Acier ordinaire S355 | Le moins cher | Aucun gain, à ne retenir que si le calcul montre que la pièce est surdimensionnée |

Entre les deux premiers, le choix se fait sur la corrosion. Le dossier a établi
que l'environnement est corrosif : cela penche vers le **17-4PH**, sous réserve
du coût.

## Et « plus léger » ?

Deux voies, et une seule est raisonnable.

**Par substitution de matière : non.**

- L'**aluminium 7075-T6** est trois fois moins raide. À géométrie identique, la
  pièce fléchirait trois fois plus. Et l'aluminium n'a **pas de limite
  d'endurance** : sous chargement cyclique, la ruine finit toujours par arriver,
  ce qui est le contraire de ce qu'on veut sur une pièce qui fissure déjà.
  S'ajoute un couple galvanique avec une caisse acier. **Écarté.**
- Le **titane** a déjà été traité : environ 0,45 kg de gain, soit 0,03 % de la
  masse du véhicule, contre une revue complète. **Non justifié.**

**Par la forme : oui, et c'est la seule voie.**

La pièce d'origine porte déjà deux trous d'allègement : le constructeur a fait ce
travail. Aller plus loin suppose de savoir où la matière ne travaille pas, donc
d'avoir les cas de charge et la géométrie réelle. Sans eux, alléger revient à
retirer de la matière au hasard sur une pièce qui casse déjà.

## Ce que je recommanderais, en l'état

Une pièce **usinée dans la masse en 42CrMo4 trempé revenu**, ou en **17-4PH** si
le budget accepte l'inoxydable, à **géométrie d'origine**, avec rayons soignés,
surface fine dans les zones tendues et grenaillage de précontrainte.

Objectif : **égaler la pièce d'origine et durer plus longtemps**, pas gagner du
poids. Sur une pièce présumée critique qui fissure en service, la durabilité est
le seul gain qui se défende — et il reste conditionné à une revue d'ingénierie.

Rien de tout cela ne peut être arrêté avant d'avoir les cotes et les cas de
charge. C'est un cadre de décision, pas une décision.
