# Appel à mesures — 993-ENG-CARRIER-0001

Demande à publier sur les forums. Le principe : demander **peu**, nommer
précisément, et rendre les résultats.

Ne pas demander « des mesures ». Demander trois cotes et une photo. Une demande
courte reçoit des réponses ; une liste de neuf cotes n'en reçoit aucune.

## Version anglaise — Rennlist, Pelican Parts, 911uk, PCGB

> **Three measurements wanted: 993 Turbo engine carrier (993 115 021 53)**
>
> I am documenting the 993 Turbo engine carrier for an open, non-commercial
> reverse-engineering project. The catalogue puts this reference in the Turbo
> engine suspension group, and unlike the non-Turbo carrier it has no aftermarket
> alternative that I can find.
>
> I do not have the part and I am not asking anyone to take a car apart. If you
> have a carrier off the car — on the bench, on a shelf, or at a breaker — three
> numbers would help enormously:
>
> 1. centre-to-centre distance between the two body mounting holes, left to right
> 2. diameter of those mounting holes
> 3. material thickness at a mounting point
>
> A photograph with a ruler or caliper lying in shot is just as valuable, and
> tells me things the numbers do not.
>
> Please say which car it came from and what you measured with — a caliper and a
> tape measure are not the same evidence, and I would rather record that honestly
> than pretend to a precision I do not have.
>
> Everything gathered goes back to this thread, and into a public repository with
> the source credited. Nothing is sold. Safety note: this is a structural part
> carrying the engine, so nothing here is a repair instruction, and no printed
> copy of it will ever carry a load.

## Version allemande — PFF, Carpassion, Elfertreff

> **Drei Maße gesucht: Motorträger 993 Turbo (993 115 021 53)**
>
> Ich dokumentiere den Motorträger des 993 Turbo für ein offenes, nicht
> kommerzielles Projekt. Der Teilekatalog führt diese Nummer in der Gruppe
> Motoraufhängung Turbo, und anders als beim Nicht-Turbo-Träger finde ich dafür
> keinen Ersatz im Zubehörmarkt.
>
> Ich habe das Teil nicht und bitte niemanden, ein Auto zu zerlegen. Falls jemand
> einen ausgebauten Träger hat — auf der Werkbank, im Regal oder beim Verwerter —
> würden drei Zahlen sehr helfen:
>
> 1. Mittenabstand der beiden karosserieseitigen Befestigungsbohrungen, links
>    nach rechts
> 2. Durchmesser dieser Bohrungen
> 3. Materialstärke an einer Befestigungsstelle
>
> Ein Foto mit Lineal oder Messschieber im Bild ist genauso wertvoll.
>
> Bitte dazuschreiben, aus welchem Fahrzeug das Teil stammt und womit gemessen
> wurde. Messschieber und Zollstock sind nicht dieselbe Grundlage, und ich
> möchte das lieber ehrlich festhalten als eine Genauigkeit vortäuschen.
>
> Alle Ergebnisse kommen in diesen Thread zurück und in ein öffentliches
> Repository, mit Nennung der Quelle. Es wird nichts verkauft. Sicherheitshinweis:
> Es handelt sich um ein tragendes Bauteil; nichts davon ist eine
> Reparaturanleitung, und ein gedrucktes Abbild wird niemals belastet.

## Où publier

| Forum | Langue | Pourquoi |
|---|---|---|
| Rennlist, sous-forums 993 Turbo et 993 | EN | Le plus grand vivier ; des fils sur cette pièce existent déjà |
| Pelican Parts, Porsche 964/993 Technical | EN | Public bricoleur, pièces sur l'établi |
| 911uk.com | EN | Vérifié actif et accessible |
| Porsche Club GB | EN | Vérifié accessible |
| PFF.de, Carpassion, Elfertreff | DE | Là où les 993 se restaurent |
| Carpokes | EN | Petit forum, mais dédié impression 3D et CAO Porsche |

Cibles hors forum, souvent plus efficaces : les casses spécialisées, qui ont la
pièce en rayon, et Rennline, qui commercialise un renfort de berceau 993 et un
berceau tubulaire non Turbo — donc a déjà mesuré la pièce d'origine.

## Traitement des réponses

Une réponse n'est pas une mesure tant qu'elle n'est pas enregistrée :

```bash
python3 scripts/capture_caliper.py \
    --record catalog/measurements/meas-993-eng-carrier-0001.json \
    --dimension D01 --description "Entraxe des fixations caisse" \
    --values <valeurs communiquees>
```

L'instrument déclaré et son incertitude comptent autant que la valeur. Deux
contributeurs qui donnent le même chiffre sans dire comment ils l'ont obtenu ne
font pas deux confirmations.
