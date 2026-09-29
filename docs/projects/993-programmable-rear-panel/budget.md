# Budget modifiable — CHF

Date : 27 septembre 2026. **Aucun devis fournisseur reçu ou prix de revient
vérifié.** [budget.csv](budget.csv) contient trois séries distinctes : historique,
ventilation hypothétique de cet historique, scénario cible et dépenses ponctuelles.
[Le calculateur](software/cost_model.py) les affiche séparément, sans les cumuler
comme des dépenses indépendantes. Montants hors TVA récupérable ; droits de douane,
taxes non récupérables, change et Incoterm seront renseignés avec les devis.

## Base conservée et ce qu'elle signifie

| Base fournie par le porteur | CHF | Statut |
|---|---:|---|
| Prototype | 685–1 450 | Estimation historique non contractuelle ; périmètre non détaillé |
| Série 100 | 223–420 / unité | Même statut ; ne prouve ni Swissness ni homologation |
| Série 1 000 | 138–271 / unité | Même statut ; économies d'échelle à démontrer |
| Cible fabrication | environ 250 / unité | Objectif ; pas prix de vente |

Les lignes `unit_100` et `unit_1000` sont une **répartition de travail** qui somme
exactement aux fourchettes historiques, et non une nouvelle validation de celles-ci.
Elles rendent visibles les postes à faire chiffrer ; chaque poste doit être remplacé
par une offre datée précisant quantité, site, finition, contrôle et transport.
L'historique prototype ne finance pas implicitement tout le développement logiciel,
les essais ou l'homologation.

## Scénario cible : plafond de négociation, pas promesse

`candidate_250` = optique 50 + PCBA afficheur 60 + commande/protection 28 + joints/
visserie 15 + assemblage 30 + contrôle 12 + rebuts/retouche 10 + emballage 10 +
transport 10 + garantie 25 = **250 CHF**. Le coût avant emballage, transport et
provision garantie est 205 CHF. Cette définition élargie évite d'oublier le coût
livré et le SAV ; convenir du périmètre exact des « 250 CHF fabrication ».

- Assemblage : 0,5 h × 60 CHF/h = 30 ; le temps du porteur n'est pas gratuit.
  À 1 h, ce scénario passe à 280 CHF. La CAO reste entièrement à sa charge,
  valorisée séparément dans les dépenses ponctuelles.
- Rebuts : provision 10 CHF par unité bonne, à remplacer par le rendement réel.
  Pour 195 CHF engagés avant rebut, rendement 95 % : supplément 195/0,95−195 ≈
  10,26 CHF ; à 90 % : 21,67 CHF. Ne pas ajouter simultanément ces suppléments
  et une provision couvrant déjà les mêmes pertes.
- Garantie : provision 25 CHF, non prédiction de taux de panne ; recalculer
  fréquence × coût SAV (pièce, main-d'œuvre, retours, expédition).

**Compromis chiffrés, hypothétiques :** le plafond afficheur est 250−190=60 CHF.
Une offre à 95 CHF au lieu de 60 donnerait 285 CHF ; ajouter 5 CHF de puissance
fait 290 CHF. À 140 CHF d'afficheur et +15 CHF de puissance : 345 CHF. Le RGB ne
sera retenu à 250 CHF que si devis et gains sur d'autres postes comblent 40–95 CHF
sans supprimer protections, contrôles ou rémunération. Ce sont des sensibilités,
pas des prix RGB constatés.

Le passage de 4 à 2,5 mm multiplie les pixels par 2,56 à surface constante ; de
4 à 1 mm par 16. Le coût complet n'évolue pas linéairement avec ce nombre : PCB,
placement, drivers, rendement et alimentation comptent. **On ne peut pas démontrer
aujourd'hui l'incompatibilité d'une résolution non définie avec 250 CHF.** Demander
un prix PCBA par panneau utile à trois pas, jamais extrapoler des dizaines de
milliers de LED achetées au détail. Réduire surface active, pas, nombre de couleurs
ou cadence constitue les leviers ; comparer l'effet sur lisibilité au coupon.

Le prix public observé du module Waveshare [S02] est une plage **17,99–21,99 USD**
selon sélection sur la page (variante exacte, taxes, port et change non engagés).
C'est seulement un repère d'achat coupon, pas une BOM de série en CHF.

## Dépenses ponctuelles et financement

Les lignes `nre` sont des **enveloppes de planification proposées**, pas l'historique
ni des devis : scan, ingénierie, logiciels, temps CAO, gabarits, emballage, essais
et homologation. Le poste `approval` est une provision, sans garantie que la voie
routière soit possible ni que le montant maximal suffise. Les frais Bluetooth SIG
et éventuels organismes sont à confirmer dans ce poste, pas supposés nuls.

Outillage injection pleine largeur, reprise après échec, licence tierce et campagne
commerciale ne sont pas chiffrés : devis nécessaires. Le total NRE est donc partiel : **21 230–64 980 CHF** avec les hypothèses actuelles,
dont temps interne valorisé ; ce montant ne remplace pas les 685–1 450 CHF
historiques du seul prototype. Amortissement illustratif : 212,30–649,80 CHF
à 100 unités, ou 21,23–64,98 CHF à 1 000 unités, en sus du coût unitaire.
La pièce à 180 CHF et les coupons sont inclus comme hypothèses de lancement ;
le prototype historique reste affiché séparément. Avant engagement, rapprocher
les scopes des devis pour ne pas compter deux fois coupons/cartes/prestations.

Amortissement commercial = NRE réel / nombre d'unités vendables raisonnablement
prévu, ajouté au coût unitaire. Le script montre les effets à 100 et 1 000 pièces.
Cela ne transforme pas une dépense ponctuelle en coût récurrent de fabrication,
et ne constitue pas le calcul d'origine : ce dernier a ses propres règles.

## Swissness : registre distinct

[swissness.csv](swissness.csv) reprend **le même** scénario à 250 CHF en séparant
contenu importé et valeur ajoutée suisse. Exemples non prouvés : facture d'un EMS
suisse de 60 CHF = 45 d'entrants étrangers + 15 de transformation suisse, pas
60 suisses. Les coûts inconnus restent au dénominateur et hors numérateur, à titre
conservateur ; cette convention ne remplace pas la méthode réglementaire.

Sans R&D : 115 / 205 = **56,10 %**, donc objectif de 60 % non atteint dans cet
exemple. Pour illustration seulement, 20 700 CHF de R&D admissible réalisée
entièrement en Suisse, alloués à 1 000 unités, donneraient (115+20,7)/(205+20,7)
= **60,12 %** ; à 2 000 unités, seulement **58,21 %**. Le résultat est sensible à
l'assiette et à l'amortissement. Aucune dépense R&D n'est réputée effectivement
suisse ni admissible sans preuve. Ne pas choisir un volume artificiellement faible
pour atteindre le seuil ; valider l'allocation avec l'IPI/conseil compétent.

Le calculateur accepte `--rd-ch`, `--rd-foreign`, `--units` et marque le résultat
**ILLUSTRATIVE_ONLY** tant que les preuves manquent. Même un résultat ≥60 % ne
valide pas l'activité conférant les caractéristiques essentielles et l'étape
physique requises en Suisse. Voir [compliance.md](compliance.md).
