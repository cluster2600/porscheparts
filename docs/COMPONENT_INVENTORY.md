# Inventaire des composants physiques du jumeau

## Règle d'admission

Un composant entre dans `catalog/components/` seulement si les quatre éléments
suivants sont sourcés : taille, masse, matière et application au 993. Une source
doit aussi identifier la pièce sans ambiguïté.

La géométrie est classée séparément :

- `interface_proxy` : seuls les paramètres nominaux connus sont représentés ;
- `envelope` : l'encombrement extérieur est documenté ;
- `detailed_solid` : la forme est assez complète pour des contrôles locaux ;
- `scan` : géométrie acquise, avec échelle et précision déclarées.

Un composant complet peut rejoindre un assemblage `logical` même si ses
transformations 3D sont inconnues. Il ne peut participer à un contrôle spatial
que si ses interfaces et leur précision sont connues.

## Premier lot admis

| Composant | Taille | Masse | Matière | Géométrie | Assemblage |
|---|---|---:|---|---|---|
| `COMP-FUCHS-37024.013` | 7J x 17 ET55, 5x130, alésage 71,58 mm | 7,50 kg | aluminium forgé | proxy d'interface | essieu avant, quantité 2 |
| `COMP-FUCHS-37026.013` | 9J x 17 ET55, 5x130, alésage 71,5 mm | 7,95 kg | aluminium forgé | proxy d'interface | essieu arrière, quantité 2 |
| `COMP-FUCHS-37027.011` | 8J x 18 ET52, 5x130, alésage 71,5 mm | 8,20 kg | aluminium forgé | proxy d'interface | essieu avant, quantité 2 |
| `COMP-FUCHS-37028.011` | 10J x 18 ET65, 5x130, alésage 71,5 mm | 8,80 kg | aluminium forgé | proxy d'interface | essieu arrière, quantité 2 |

Source primaire : documentation publique du fabricant Otto Fuchs. Il s'agit de
roues compatibles, pas de fichiers CAO Porsche ni d'une affirmation qu'elles
étaient montées d'origine sur toutes les variantes.

Assemblages admis : jeu 17 pouces de 30,90 kg et jeu 18 pouces Carrera de
34,00 kg. Les montages Turbo avec entretoises restent séparés et incomplets.

Les Michelin Pilot Sport PS2 N3 17 pouces sont des candidats bien identifiés par
Porsche et Michelin. Ils ne sont pas encore admis : les masses disponibles
proviennent de vendeurs et varient, et la construction matière exacte de ces
références n'est pas fournie dans les documents fabricant retenus.

Le premier lot freinage est également qualifié mais non admis. Brembo et ATE
recoupent les dimensions des disques avant Carrera ; ATE donne les références
Porsche associées et Brembo documente aussi le disque arrière. Aucun des
documents constructeur retenus ne publie toutefois la masse nette unitaire ni
une nuance matière complète. Les
détails et la porte de sortie sont consignés dans
[la recherche germanophone sur le freinage](research/phase-2-freinage-allemand.md).

## File d'acquisition

Les prochains lots sont recherchés par sous-ensemble : roues et pneumatiques,
freinage, roulements et joints standardisés, transmission, moteur, carrosserie,
habitacle. Une fiche incomplète reste dans le registre de sources ou dans une
issue de recherche ; elle ne reçoit pas de faux poids ou matériau par défaut.
