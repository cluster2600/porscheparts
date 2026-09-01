# 0003 — Pas de moisson automatisée chez les revendeurs

Date : 28 août 2026

## Contexte

Le jumeau numérique se remplit référence par référence, et une seule source
publiait une masse par pièce tout en répondant aux requêtes automatisées : le
catalogue de Rose Passion, structuré par illustrations PET comme le squelette
d'assemblage. Un outil de récupération ciblée a donc été étudié.

## Ce que la vérification a établi

`https://www.rosepassion.com/robots.txt`, relevé le 28 août 2026, s'ouvre sur
ces quatre lignes :

```
User-agent: ClaudeBot
Disallow: /
User-agent: Claude-Web
Disallow: /
```

Le site ferme l'intégralité de ses pages à ces agents, en les nommant en
premier. Aucune directive `Crawl-delay` n'existe : il n'y a pas de fréquence
tolérée, la réponse à « à quel rythme » est « pas du tout ».

Les conditions de vente sont, elles, interdites à **tous** les robots. Elles
n'ont donc pas été lues, et la question de la réutilisation des données produit
reste **sans réponse** — pas répondue favorablement.

## Décision

**Aucun outil de ce dépôt n'interrogera automatiquement ce catalogue.** Le
script étudié a été écrit puis supprimé sans être versé.

Le contournement évident est nommé ici pour être exclu : envoyer un
`User-Agent` maison ferait correspondre le client au groupe permissif `*`, où
les fiches produit sont autorisées. C'est précisément ce que l'implémentation
avait fait, et c'est du contournement — se renommer pour passer un refus qui
vous nomme n'est pas obtenir une permission.

## Ce qui reste ouvert

- **Une lecture humaine dans un navigateur.** `robots.txt` régit les robots, pas
  une personne. La réutilisation des données reste soumise aux conditions, qui
  restent à lire.
- **Une autorisation écrite du vendeur**, ou un extrait de données fourni par
  lui, qui règlerait aussi la question de la réutilisation.

## Correction associée

La fiche `SRC-ROSEPASSION-993-PARTS` et `catalog/reference/README.md`
affirmaient que ce revendeur « répond à la récupération automatisée ». C'était
une confusion entre « le serveur renvoie une page » et « l'exploitant autorise
l'accès automatisé ». Les deux textes sont corrigés.
