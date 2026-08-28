# Phase 1 — Inventaire des sources

Ce document suit l’avancement de la Phase 1. Il n’héberge aucun contenu protégé :
il enregistre où une information se trouve, comment elle a été consultée et ce
que son statut juridique autorise.

## Lot 1 — Catalogues officiels, manuels légalement accessibles et mesures

Consulté le 28 août 2026. Chaque URL a été ouverte avant d’être inscrite ; les
échecs d’accès sont conservés au même titre que les succès.

### Catalogues et documents officiels

| Fiche | Contenu | Accès | Réutilisation | Preuve |
|---|---|---|---|---|
| `SRC-PORSCHE-PET-993` | Catalogue Pièces d’Origine Porsche Classic | disponible | interdite | A |
| `SRC-PORSCHE-NEWSROOM-993` | Dossier historique et gamme | disponible | interdite | A |
| `SRC-PORSCHE-NEWSROOM-993-30Y` | Dossier de presse « 30 ans du 993 » | disponible | interdite | A |
| `SRC-PORSCHE-SHOP-TECHLIT` | Littérature technique officielle à l’achat | disponible, catalogue vide | interdite | non noté |
| `SRC-PORSCHE-CLASSICSHOP-USA` | Ancienne boutique Classic (manuels 993) | hors service (DNS) | interdite | non noté |

### Manuels et données techniques accessibles

| Fiche | Contenu | Accès | Réutilisation | Preuve |
|---|---|---|---|---|
| `SRC-9XXTEILE-PET-DIAGRAMS` | Vues éclatées et numéros de pièces | libre | interdite | C |
| `SRC-PCA-993-ALIGNMENT` | Réglages de trains d’origine | libre | interdite | C |
| `SRC-WIKIPEDIA-993` | Encombrement véhicule et variantes | libre | attribution requise | D |
| `SRC-STUTTCARS-993-PARTS` | Diagrammes PET annoncés | payant | inconnue | non noté |
| `SRC-STUTTCARS-993-TORQUE` | Couples de serrage moteur | payant | inconnue | non noté |

### Mesures et données dimensionnelles

| Fiche | Contenu | Accès | Réutilisation | Preuve |
|---|---|---|---|---|
| `SRC-CARGEOMETRY-993-BODY` | Points de mesure caisse et soubassement | achat (20 USD) | interdite | B |
| `SRC-WHEEL-SIZE-993` | Jantes, déports, entraxe | libre | inconnue | C |
| `SRC-CARFOLIO-993` | Masses et cotes par variante | libre | interdite | D |
| `SRC-RENNLIST-993-FORUMS` | Mesures d’atelier communautaires | bloqué aux robots | inconnue | C |
| `SRC-PELICANPARTS-964-993-FORUM` | Mesures d’atelier communautaires | bloqué aux robots | inconnue | C |

## Sources écartées

Écartées sans être inscrites au registre. Le motif est conservé pour éviter de
les réexaminer.

| Source | Motif |
|---|---|
| Scribd, SlideShare, eManualOnline, eManuals, workshopcarmanuals | Rediffusion du manuel d’atelier Porsche sans droit démontrable |
| Pièces jointes de forum contenant des planches cotées d’usine | Même document protégé, republié par un tiers |
| Agrégateurs de PDF sans éditeur identifiable | Provenance invérifiable |

Une source écartée peut rester utile comme indice de l’existence d’un document.
Elle ne devient jamais une référence du catalogue.

## Constats du lot 1

- Aucun plan coté d’usine n’est légalement accessible librement. Les vues
  éclatées renseignent l’assemblage et la nomenclature, pas la géométrie.
- La donnée dimensionnelle exploitable viendra de la mesure directe, complétée
  par un référentiel de caisse acheté (`SRC-CARGEOMETRY-993-BODY`).
- Les numéros de pièces sont accessibles gratuitement, mais leur rediffusion ne
  l’est pas : ils servent d’identifiant de travail, pas de contenu publié.
- Deux forums majeurs refusent l’accès automatisé ; leur consultation reste
  manuelle et chaque valeur reprise doit être remesurée.
- Le corpus communautaire recopie fréquemment la même origine non citée ; la
  règle « deux copies ne font pas deux confirmations » s’applique directement.

## Reste à faire en Phase 1

- [ ] Modèles 3D sous licence vérifiable
- [ ] Classement par variante, année et disponibilité
- [x] Pièces manquantes ou difficiles à obtenir — premier cas documenté par une
      source : le berceau moteur Turbo `993 115 021 53` n'a aucune alternative de
      rechange, le berceau tubulaire du marché spécialisé étant explicitement non
      Turbo. Les trois candidats polymères de la phase 2 restent, eux, choisis sur
      critères d'ingénierie et non sur une rareté documentée.
- [ ] Évaluation croisée provenance, licence, précision, réutilisation

État : vingt candidats documentés, le seuil de sortie de phase est atteint en
nombre. Deux des derniers ajouts (`SRC-TEILE-COM-993-ENGINE-CARRIER`,
`SRC-RENNLINE-TUBULAR-ENGINE-CARRIER`) refusent l'accès automatisé : ils comptent
comme candidats recensés, pas comme sources exploitées.
