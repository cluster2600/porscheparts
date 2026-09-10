# Sourcing LPBF en Chine — première passe

Objet : trouver qui peut réellement imprimer
[`993-INT-SWITCH-TRIM-RING-F1-0001`](993_SWITCH_TRIM_RING_F1.md) en AlSi10Mg, et
répondre aux sept portes fermées de l'étape 04. Ce document ne recommande aucun
prestataire. Il enregistre ce que chacun **publie**, ce qu'il ne publie pas, et
les contradictions à lever avant de payer quoi que ce soit.

Toutes les affirmations ci-dessous sont adossées à une fiche de source dans
`catalog/sources/`. Une page commerciale est une source de niveau B : le
fournisseur parle de lui-même, et rien n'est vérifié.

## Le tri qui compte : atelier de service ou vendeur de machines

La recherche remonte deux familles qu'il ne faut pas confondre.

**Constructeurs et poudriers** — BLT (Xi'an Bright Laser Technologies), Farsoon,
Eplus3D, HBD. Ils vendent des machines et de la poudre. BLT et Farsoon équipent
les ateliers, Falcontech exploite une usine de machines Farsoon. Ils publient des
cartes matière utiles en comparaison, mais ne sont pas les interlocuteurs d'une
pièce unique de 6 g.

**Ateliers de service à devis en ligne** — Unionfab, JLC3DP, et les nombreux
intermédiaires du même modèle. C'est là que se traite une pièce unitaire.

## Candidats retenus et écartés

| prestataire | AlSi10Mg | statut | raison |
|---|---|---|---|
| Unionfab | oui | **candidat n°1** | seul du lot à publier parc machine, tolérances, paroi minimale, délai et certifications |
| JLC3DP | **non** | écarté pour cette pièce | catalogue métal limité à TC4, 316L et BJ-316L |
| Eplus3D | oui (poudre) | non applicable | constructeur de machines, pas atelier de service identifié |
| BLT, Farsoon, Falcontech | oui | non sollicités | échelle industrielle, sans intérêt pour une pièce unitaire |

### Unionfab — ce qui est publié

Parc de plus de cent machines BLT, Farsoon, EOS et UnionTech, systèmes SLM à
quatre et six lasers. Volume jusqu'à 800 × 800 × 700 mm. Paroi minimale
**0,5 mm**. Tolérance ±0,2 mm sous 100 mm. Délai SLM **5 à 7 jours ouvrés**.
**Aucun minimum de commande**. ISO 9001, ISO 14001, ISO 13485 et IATF 16949.
Usinage CNC, polissage, traitement thermique et anodisation en post-traitement.
Contrôle par MMT et scanner 3D.

Sur sa fiche AlSi10Mg : Rp0,2 180 MPa, Rm 300 MPa, A ≥ 8 %, 2,67 g/cm³,
Brinell 120, Ra 12 à 25 µm, minimum de commande 1 pièce.

### Trois contradictions à porter au devis

**1. L'épaisseur de couche, encore.** L'étape 04 avait déjà trouvé que le
criblage tranchait à 50 µm une route publiée à 30 µm. Unionfab en ajoute deux :
sa page de service annonce **0,035 mm**, et sa propre fiche AlSi10Mg annonce
**0,15 mm**. Cette dernière n'est pas une épaisseur LPBF plausible pour cet
alliage. Trois valeurs sur le même sujet, dont deux chez le même fournisseur :
la première question du devis est donc « à quelle épaisseur, sur quelle
machine ».

**2. La carte matière change avec le prestataire.** Rp0,2 180 MPa chez Unionfab
contre 233 MPa vertical sur les coupons EOS de la carte du dépôt, Rm 300 contre
461 MPa minimal. Ce n'est pas une erreur de l'un ou de l'autre : ce sont deux
routes différentes. C'est exactement ce que la porte 04 affirme, et la carte
procédé du dépôt devra être remplacée par celle du prestataire retenu, pas
complétée par elle.

**3. La paroi.** Unionfab annonce 0,5 mm de paroi minimale, JLC3DP recommande
1,5 mm pour le SLM. La bague a un premier centile d'épaisseur locale à
**0,833 mm**, et **11,45 %** de ses points de criblage sous 1,5 mm. Elle passe
la règle du premier, pas la recommandation du second. La question au fournisseur
est donc de savoir si sa paroi minimale est une limite de procédé ou une limite
de garantie dimensionnelle.

### Ce qu'aucun ne publie

Aucun des quatre ne publie de spécification de traitement thermique, de
tomographie, de contenu de certificat matière, de traçabilité du lot de poudre
ni de surépaisseur d'usinage. Ce sont cinq des sept portes fermées de l'étape
04 : la recherche documentaire ne les ouvrira pas, seul un échange contractuel
le fera.

## Prochain pas concret

Envoyer le dossier
[`supplier-rfq.md`](../../twins/993-switch-trim-ring-alsi10mg-f1/evidence/route-f1/993-int-switch-trim-ring-f1-0001-supplier-rfq.md)
et le STEP à Unionfab, en ajoutant les trois contradictions ci-dessus comme
questions. Le devis attendu porte sur **une** pièce ; son intérêt n'est pas la
bague, c'est de savoir ce qu'un prestataire chinois accepte de mettre par écrit
quand on le lui demande. C'est cette réponse qui décidera si la même chaîne peut
porter des pièces plus sérieuses.

Rappel de cadre : la pièce est classée `non_critical`, aucune porte de
fabrication n'est ouverte, et rien de ce qui sortirait de ce devis ne doit être
monté sur un véhicule avant mesure d'un exemplaire d'origine et du logement.

## Sources

- `SRC-UNIONFAB-METAL-3D-PRINTING-SERVICE`
- `SRC-UNIONFAB-ALSI10MG-SLM-MATERIAL`
- `SRC-JLC3DP-SLM-METAL-SERVICE`
- `SRC-EPLUS3D-ALSI10MG-MATERIAL`
