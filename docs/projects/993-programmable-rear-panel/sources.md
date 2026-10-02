# Registre de sources

**Consultation : 27 septembre 2026, sauf S01 et S31–S34 relus le 28 septembre 2026.** Les pages fournisseur
attestent une offre publiée, pas un engagement, un stock ou une aptitude automobile.
Les documents sont liés, pas copiés dans le dépôt. Les hypothèses d'ingénierie et
les enveloppes financières de ce dossier sont nos propositions, non des données
extraites de ces sources.

| ID | Source primaire / lien | Élément étayé et limites |
|---|---|---|
| S01 | [Kingbright — LED basse consommation 0402](https://www.kingbrightusa.com/category.asp?catalog_name=LED&category_name=KCLow+Current-1.0X0.5MM+%280402%29&page=1) ; [fiche exacte APHHS1005LSECK/J3-PF](https://www.kingbrightusa.com/images/catalog/spec/aphhs1005lseck-j3-pf.pdf) | V.6A, 4 pages : composant rouge 1,0×0,5 mm, Vf typique 1,8 V / max 2,1 V à 2 mA et 25 °C, courant absolu max 30 mA sous conditions. Ne prouve pas le pas, une intensité derrière façade ni la tenue auto. La fiche APG1005 citée initialement était une autre référence, remplacée ici par la fiche exacte |
| S02 | [Waveshare — RGB-Matrix-P2.5-64x32](https://www.waveshare.com/rgb-matrix-p2.5-64x32.htm) | 64×32, pas 2,5 mm, HUB75, alimentation 5 V/2,5 A, puissance ≤12 W annoncée. Prix affichés 17,99–21,99 USD selon variante ; sélection/taxes/port à confirmer |
| S03 | [Waveshare — gamme P2/P2,5 64×64](https://www.waveshare.com/product/rgb-matrix-p2.5-64x64.htm) | Tableau de variantes incluant P2 64×64 ; pas une garantie de disponibilité ni de tenue extérieure |
| S04 | [Newhaven — NHD-1.5-128128G, fiche](https://newhavendisplay.com/content/specs/NHD-1.5-128128G.pdf) | Exemple OLED petit format 128×128 ; vie/température à considérer selon conditions spécifiées. Aucun OLED pleine largeur qualifié |
| S05 | [Formlabs — Clear Resin V5](https://formlabs.com/products/clear-resin/) ; [fiche matière](https://formlabs-media.formlabs.com/datasheets/2401900-TDS-ENUS-0.pdf) | Transparence et finition possibles, éclairage/prototypes ; pas de qualification extérieure automobile établie |
| S06 | [Stratasys — VeroClear](https://www.stratasys.com/en/materials/materials-catalog/polyjet-materials/veroclear/) | Photopolymère transparent rigide PolyJet ; comparer à thermoplastiques réels, ne pas les assimiler |
| S07 | [Protolabs — procédés Europe](https://www.protolabs.com/en-gb/services/3d-printing/) ; [matières plastiques](https://www.protolabs.com/services/3d-printing/plastic/) ; [finitions](https://www.protolabs.com/media/1021595/us_3dp_surface_finish_guide.pdf) | SLA transparente/WaterShed et PolyJet documentés ; grade disponible, usine et finition à confirmer pour le devis européen |
| S08 | [Texas Instruments — LM7480-Q1](https://www.ti.com/product/LM7480-Q1) ; [fiche](https://www.ti.com/lit/ds/symlink/lm7480-q1.pdf) | Contrôleur protection polarité/load dump, MOSFET externes ; ne valide pas un circuit complet |
| S09 | [Nordic — nRF52840, spécification](https://docs-be.nordicsemi.com/bundle/nRF52-Series-PS/raw/resource/enus/nRF52840_PS_v1.0.pdf) ; [chaîne de boot](https://nrfconnectdocs.nordicsemi.com/ncs/latest/nrf/app_dev/bootloaders_dfu/mcuboot_nsib/bootloader.html) | MCU BLE candidat et infrastructure boot/DFU ; module, SDK stable/version et mémoire à figer au portage |
| S10 | [Apple — Apple Media Service Reference](https://developer.apple.com/library/archive/documentation/CoreBluetooth/Reference/AppleMediaService_Reference/Introduction/Introduction.html) | Accessoire GATT client de métadonnées iOS par BLE ; document archivé, daté 2014, relu directement. Compatibilité actuelle à tester |
| S11 | [Android — MediaSessionManager](https://developer.android.com/reference/android/media/session/MediaSessionManager) | Accès sessions actives soumis à permission système ou listener de notifications autorisé ; pas un accès universel sans consentement |
| S12 | [Ab Concept — scan](https://abconcept.ch/prestation/scan-3d/) ; [localisation](https://abconcept.ch/contact/) | Scan de composants, STL, reconstruction ; La Chaux-de-Fonds. Page relue directement après échec ponctuel de l'outil web |
| S13 | [INCO 3D](https://www.inco3d.ch/) | Services scan/rétro-ingénierie/impression/thermoformage et localisation Pully ; transparence automobile et délais non prouvés |
| S14 | [gigAtec](https://gigatec.ch/) | Développement, industrialisation et production locale à Vallorbe annoncés ; origine entrants et expérience spécifique à qualifier |
| S15 | [Systronic-EMS](https://systronic-ems.com/) | Conception/assemblage et implantation en Suisse romande publiés ; site de commande à vérifier |
| S16 | [Eurocircuits — capacités PCBA](https://www.eurocircuits.com/services/pcb-assembly-capabilities/) ; [services/fabrication](https://www.eurocircuits.com/blog/eurocircuits-launch-5-working-day-pcb-assembly-prototype-service/) | Assemble ses PCB ; page capacités affiche 3/5/7/10 jours ouvrés sous conditions. Offre générale Allemagne/Hongrie. Délai total, stock, site et transport à confirmer ; ne pas assimiler assemblage à délai livré |
| S17 | [Bourquin — services](https://www.bourquinsa.ch/fr/que-faisons-nous/services/) ; [sites](https://www.bourquinsa.ch/ueberuns/standorte/) | Conception emballage et site Couvet ; attribution de fabrication, MOQ et tarifs projet inconnus |
| S18 | [DTC — examens de modifications](https://www.dtc-ag.ch/fr/prestations/securite-active/examens-de-modifications) | Offre d'examens CH/internationaux à Vauffelin ; périmètre mandat à convenir |
| S19 | [TÜV Rheinland — éclairage automobile](https://www.tuv.com/luxembourg/de/pr%C3%BCfung-lichttechnischer-einrichtungen.html) | Laboratoire Berlin et rapports d'essais pour réception de type ; habilitations publiées, contrat actuel à confirmer |
| S20 | [Porsche Classic — 993](https://www.porsche.com/australia/accessoriesandservice/classic/models/993/993/) | Description constructeur du bandeau et logo réfléchissant rouge ; ne donne pas l'inventaire homologué par référence |
| S21 | [Bergvill F/X — notice kit 993 distribuée par Design911](https://www.design911.co.uk/uploads/pdfs/bergvillfx/Rear_fog_light_conversion_kit_Porsche%20993.pdf) | Ensemble réflecteur/antibrouillard et fonction antibrouillard sur configurations concernées ; document fabricant d'accessoire, aucune approbation réglementaire de la conversion déduite |
| S22 | [Fedlex — OETV RS 741.41](https://www.fedlex.admin.ch/eli/cc/1995/4425_4425_4425/fr) | Portail officiel atteint mais texte consolidé non extrait (JavaScript) ; articles/version à confirmer avant avis formel |
| S23 | [OFROU — identification feux/catadioptres](https://www.astra.admin.ch/dam/astra/fr/dokumente/homologation_vonfahrzeugen/kennzeichnung_derlichterundrueckstrahlerece-eg.pdf.download.pdf/identification_desfeuxetdescatadioptresece-ce.pdf) ; [homologations](https://www.astra.admin.ch/fr/homologations) | Repérage des catégories et point d'entrée autorités, pas un accord pour cette pièce |
| S24 | [StVZO §49a](https://www.gesetze-im-internet.de/stvzo_2012/__49a.html) | Texte officiel relu : équipements lumineux autorisés, y compris affichage extérieur dynamique éclairé |
| S25 | [StVZO §19](https://www.gesetze-im-internet.de/stvzo_2012/__19.html) | Conséquences possibles de modifications sur Betriebserlaubnis ; examen juridique spécifique nécessaire |
| S26 | [EUR-Lex — RED 2014/53/UE](https://eur-lex.europa.eu/eli/dir/2014/53/oj/eng) | Texte officiel accessible ; normes harmonisées/version applicables au produit à sélectionner avec laboratoire |
| S27 | [OFCOM — conditions de mise sur le marché](https://www.bakom.admin.ch/fr/conditions-de-mise-sur-le-marche) | Évaluation, dossier, déclarations, informations et marquage radio ; page datée 16 janvier 2025 |
| S28 | [Bluetooth SIG — qualification](https://www.bluetooth.com/develop-with-bluetooth/qualify/) | Qualification avant vente/distribution ; frais et voie exacte non chiffrés ici |
| S29 | [IPI — critères produits industriels](https://www.ige.ch/en/protecting-your-ip/indications-of-source/indications-of-source-basics/criteria-for-determining-origin/industrial-products) | Seuil 60 %, activité essentielle et étape physique suisse, calculateur officiel |
| S30 | [IPI — FAQ Swissness](https://www.ige.ch/fr/droit-et-politique/evolutions-nationales/indications-de-provenance/indications-de-provenance-suisses/questions-frequentes-swissness) | Coûts inclus/exclus et exceptions ; page relue directement, emballage et SAV exclus notamment |

## Complément électronique — consultation du 28 septembre 2026

| ID | Source primaire / lien | Élément étayé et limites |
|---|---|---|
| S31 | [TI — TLC5947, fiche SBVS114B](https://www.ti.com/lit/ds/symlink/tlc5947.pdf) | Rev. B, broches DAP §5 ; VCC 3–5,5 V, courant recommandé 2–30 mA, seuils logiques §6.3 ; alimentation logique §6.6 ; courant idéal `41 × 1,20 / R` ; BLANK haut nécessaire au démarrage et registre initial indéfini §8.3 ; chaîne de 288 bits, poids fort en premier et latch §8.4. Protection thermique avec reprise automatique. Marges à faible courant non validées pour notre coupon |
| S32 | [TI — SN74LVC125A, fiche SCAS290T](https://www.ti.com/lit/ds/symlink/sn74lvc125a.pdf) | Rev. T : brochage PW 14, buffer 3 états, alimentation 1,65–3,6 V ; seuil haut 2 V dans la plage 2,7–3,6 V. Ne pas confondre avec une isolation ni autoriser le branchement à chaud sans étude des rails |
| S33 | [TI — SN74LVC1G04, fiche SCES214AF](https://www.ti.com/lit/ds/symlink/sn74lvc1g04.pdf) | Rev. AF : inverseur, brochage DBV 5, seuil haut 2 V à 3,3 V, protection Ioff ; ne remplace ni watchdog ni superviseur de tension |
| S34 | [Nordic — alimentation du nRF52840 DK](https://docs.nordicsemi.com/r/bundle/ug_nrf52840_dk/page/ug/dk/hw_power_supply.html) ; [sélection de source](https://docs.nordicsemi.com/r/bundle/ug_nrf52840_dk/page/ug/dk/power_source.html) ; [guide v1.4.1 §8.3](https://infocenter.nordicsemi.com/pdf/nRF52840_DK_User_Guide_v1.4.1.pdf) | Modes d'alimentation et régulateur 3 V en mode VDD ; n'autorise pas à tirer la puissance des LED depuis le DK. Révision de carte et GPIO à identifier avant câblage |

Les prix, stocks et délais de ces quatre composants n'ont pas été vérifiés.
Les fichiers fabricants sont uniquement liés ; aucun PDF propriétaire recopié.

## Références à faire confirmer, non présentées comme lues intégralement

- [UNECE — règlements 141–160](https://unece.org/transport/vehicle-regulations-wp29/standards/addenda-1958-agreement-regulations-141-160) : accès direct 403 lors de cette passe.
  Le périmètre R148/R150 et les autres règlements mentionnés sont une liste de
  questions au laboratoire ; séries/version et dispositions transitoires non vérifiées.
- [EUR-Lex — règlement délégué 2022/30](https://eur-lex.europa.eu/eli/reg_del/2022/30/oj/eng) : réponse directe sans texte exploitable dans cette passe. Vérifier texte consolidé,
  dates et champ cybersécurité avec organisme radio ; aucune exemption affirmée.
- Anibis 180 CHF et budgets historiques : **source = brief du porteur**, annonce,
  acquisition et devis d'origine non disponibles ; aucune URL inventée.

## Limites de collecte

Recherches ciblées FR/DE/EN et sites fabricants/autorités ; pas d'audit global,
contact fournisseur, inscription ni achat. L'outil de recherche web a ensuite
renvoyé une erreur d'authentification expirée (401). Les pages publiques nécessaires
ont été relues directement avec le client HTTP système, validation TLS maintenue ;
aucune restriction d'accès n'a été contournée. Un premier essai Python avait échoué
sur la chaîne de certificats locale. Les sources bloquées restent marquées comme
telles ; pas de boucle de recherche pour les forcer. Aucun texte normatif payant,
manuel propriétaire, scan ou photographie tiers n'est incorporé.
