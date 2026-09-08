# Source de rapport — cotes allemandes et préparation TÜV

Ce fichier conserve les constats de recherche avant synthèse. Les pages ont été
consultées le 2 septembre 2026. Les textes et médias tiers ne sont pas copiés.

## Question de décision

Quelles cotes allemandes publiques peuvent alimenter la monocoque carbone 964/993,
et quelles données restent obligatoires avant une discussion crédible avec un
expert de réception individuelle ?

## Sources primaires retenues

| Source | Fait retenu | Limite |
|---|---|---|
| [Porsche Finder DE, 964 Carrera 2 Coupé](https://finder.porsche.com/de/de-DE/details/porsche-911-carrera-2-coupe-gebraucht-W39O34) | 4 250 × 1 652 × 1 310 mm ; empattement 2 272 ; voies 1 374/1 374 ; masses 1 350/1 425/1 690 kg | annonce dynamique, aucune cote de caisse XYZ |
| [Porsche Finder DE, 993 Carrera Cabriolet II](https://finder.porsche.com/de/de-DE/details/porsche-911-carrera-cabriolet-gebraucht-Z5OOK2) | 4 245 × 1 735 × 1 300 mm ; empattement 2 272 ; voies 1 405/1 444 ; masses 1 370/1 445/1 710 kg | annonce dynamique, Cabriolet, aucune cote de caisse XYZ |
| [Porsche Newsroom DE, 993 Turbo S](https://newsroom.porsche.com/de/historie/porsche-historie-weisse-riesen-991-turbo-964-turbo-3-6-993-turbo-s-13822.html) | 4 245 × 1 795 × 1 285 mm ; empattement 2 272 ; masse 1 575 kg | aucune voie, tolérance ou interface |
| [Porsche Newsroom DE, trente ans du 993](https://newsroom.porsche.com/de/pressemappen/60-Jahre-Porsche-911/30-Jahre-911-Carrera-der-Generation-993-%E2%80%93-Der-letzte-seiner-Art.html) | la carrosserie Turbo est plus large de 60 mm ; différences de variantes décrites | pas un plan de construction |
| [Tkaczyk, Richtsatz Porsche](https://richtsatz-mieten.de/richtsaetze/porsche/) | Celette 564.330, 964 avec supplément 993 | aucun plan ni résultat numérique public |
| [TÜV SÜD, FAQ tuning](https://www.tuvsud.com/de-de/branchen/mobilitaet-und-automotive/tuning-eintragungen-und-aenderungsabnahmen/tuning-faq) | modification non couverte : nouvelle autorisation 19(2)/21 | FAQ générale, décision au cas par cas |
| [StVZO, paragraphe 21](https://www.gesetze-im-internet.de/stvzo_2012/__21.html) | rapport d'expert, description technique et protocoles d'essais nécessaires | ne prescrit pas publiquement un essai unique de monocoque 964/993 carbone |
| [TÜV SÜD, méthodes virtuelles](https://www.tuvsud.com/de-de/branchen/mobilitaet-und-automotive/automotive/pruefloesungen-und-compliance-services/virtuelle-testmethoden) | simulations structurelles et crash ; corrélation physique et essais matériau | aucune validation du modèle actuel |
| [TÜV SÜD, Datenblattservice](https://www.tuvsud.com/de-de/branchen/mobilitaet-und-automotive/oldtimer/oldtimer-datenblattservice) | données liées au numéro de châssis ; 159 € pour un VP jusqu'à 2000 | service d'immatriculation, points de marbre non annoncés |

## Sources écartées comme cotes de conception

- Les schémas de forums ou pièces jointes Rennlist/PFF sans provenance complète,
  sans définition du point mesuré et sans tolérance.
- Les vues indexées par les moteurs de recherche lorsque le PDF d'origine est
  inaccessible ou sous droits non clarifiés.
- Les maillages de visualisation, scans commerciaux sans rapport de métrologie
  et descriptions de vendeurs de restomods.
- Les dimensions globales de produits, qui ne décrivent ni l'interface ni le
  chemin de charge.

## Matrice preuve-lacune

| Domaine | Valeur numérique publique | Suffisant pour CAO F2 | Action de fermeture |
|---|---|---|---|
| enveloppes Carrera étroites 964/993 | oui | non | confirmer chaque variante donneuse et recouper les véhicules réels |
| enveloppe Turbo large | partielle | non | obtenir voies, garde au sol et configuration exacte |
| points de caisse inférieurs | non | non | manuel Porsche V + Celette 564.330 + CMM |
| ancrages de suspension/direction | non | non | CMM et gabarits des sous-châssis |
| groupe motopropulseur | non | non | CMM, plans d'appui et enveloppes dynamiques |
| sièges et ceintures | non | non | mesure, exigences de charge et essais convenus avec l'expert |
| baies et ouvrants | non | non | scan surfacique, gabarits vitrages et contrôle des jeux |
| chemins de charge de choc | non | non | modèle F3, essais matière, sous-ensembles puis caisse |
| classification réglementaire | au cas par cas | non | Vorbesprechung écrite avec expert et autorité |

## Conclusion de recherche

Les sites allemands permettent de verrouiller l'ordre de grandeur et la famille
de carrosserie, mais pas de reconstruire légalement et sûrement une coque
autoporteuse. Le prochain euro utile n'est pas une location GPU : c'est la
pré-consultation réglementaire, le gel d'une variante donneuse, puis un relevé
Celette/CMM traçable. Une simulation haute fidélité lancée avant ces trois étapes
produirait un résultat précis sur une géométrie non démontrée.
