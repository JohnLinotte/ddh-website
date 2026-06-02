# BUILD-REPORT — Département des Harnais

Vérification d'intégration sous `/home/John/Work/ddh-website` (hors `.git`).
Portée : les pages du site listées ci-dessous. Ce rapport est un méta-artefact
(comme `DESIGN-SYSTEM.md`, hors site) et n'entre pas dans le périmètre scanné
pour le token éditeur tiers (cf. check 5).

Aucune valeur de design n'a été modifiée. Aucune page n'a été redessinée.
Aucune correction de contenu appliquée (voir « Corrections » plus bas).

## Pages

| # | Page (chemin) | nav `.on` | lang=fr | title sans token tiers | lie `/assets/ddh.css` | cartel verbatim | footer verbatim |
|---|---|---|---|---|---|---|---|
| 1 | `index.html` | Index | oui | oui | oui (1) | identique | identique |
| 2 | `records/index.html` | Records | oui | oui | oui (1) | identique | identique |
| 3 | `records/2026-05-24/index.html` | Records | oui | oui | oui (1) | identique | identique |
| 4 | `atelier/index.html` | L'Atelier | oui | oui | oui (1) | identique | identique |
| 5 | `atelier/t0/index.html` | L'Atelier | oui | oui | oui (1) | identique | identique |
| 6 | `cabinet/index.html` | Le Cabinet | oui | oui | oui (1) | identique* | identique* |

\* Le contenu du cartel et du footer de `cabinet/index.html` est **byte-identique**
aux 5 autres pages (vérifié par md5 après normalisation de l'indentation de tête).
Seule différence : tout le corps de `<div class="page">` y est indenté d'un niveau
de plus (6 espaces au lieu de 4). C'est cosmétique, pas une altération de contenu —
non corrigé (voir « Corrections »).

## Checks demandés

| # | Check | Résultat | Preuve |
|---|---|---|---|
| 1 | Bloc cartel (`<h1 class="cartel-name"> … Harnais`) identique partout (hors nav `.on`) | **PASS** | md5 du bloc cartel complet, indentation de tête normalisée, identique sur les 6 pages (`ed325d41…`). Le `<h1 class="cartel-name">` est mot-pour-mot identique : `Département` / `des` / `Harnais`, mêmes `<span>`. |
| 2 | Footer identique partout, placeholders `{{ADRESSE}}/{{BCE}}/{{TVA}}` intacts | **PASS** | md5 du bloc footer, indentation normalisée, identique sur les 6 pages (`1bdad384…`). Les 3 placeholders présents et intacts sur chaque page. Glyphes vérifiés : `—` U+2014, `·` U+00B7, `©` U+00A9, `&deg;`, `&nbsp;`. |
| 3 | Toutes les pages lient `/assets/ddh.css` | **PASS** | Exactement 1 `<link rel="stylesheet" href="/assets/ddh.css">` par page (6/6). |
| 4 | Liens nav + internes : cible existante (root-relatif depuis la racine du site) | **PASS pour la nav** ; 4 cibles internes manquantes (forward-refs) | Voir « Liens cassés ». Les 4 liens de nav (`/`, `/records/`, `/atelier/`, `/cabinet/`) résolvent tous vers un `index.html` existant. |
| 5 | ZÉRO token éditeur tiers (le nom de la stack) dans `**` hors `.git` | **PASS** | `grep -rniI` insensible à la casse sur l'arbre hors `.git` : 0 occurrence (exit 1). |
| 6 | Aucun token chaud (cream/beige/sepia/#F4F1E8/oklch chaud) survivant, surtout Records | **PASS** | Voir « Palette ». Aucun mot chaud (la seule occurrence de « sepia » est une **négation** dans un commentaire de `ddh.css` : « JAMAIS sepia »). Aucun hex chaud. Palette entièrement froide (teintes bleu 252–255 + vert froid 128–135 en oklch). Records n'a aucun `<style>` de page → hérite 100 % de `ddh.css`. |
| 7 | HTML grossièrement valide (balises fermées, lang=fr, title sans token tiers) | **PASS** | `<html>/<head>/<body>/<footer>` équilibrés 1:1 sur les 6 pages. `lang="fr"` partout. Aucun title ne contient le token tiers. |

## Palette (preuve du check 6)

Tokens couleur de `assets/ddh.css` (`:root`), tous **froids** :

- `--stone-50/100/200/300` (fond, filets) : `oklch(… 252–255)` → teinte **bleu** ~255, chroma 0.004–0.007 (gris neutre froid).
- `--ink / --ink-soft / --ink-faint` (texte) : `oklch(… 252–255)` → teinte **bleu** ~252–255 (encre gris froid).
- `--moss / --moss-deep / --moss-bright / --moss-pale` (accent) : `oklch(… 128–135)` → teinte **vert froid** 128–135 (la bande chaude serait ~20–110 ; aucun token n'y tombe).

Aucun hex dans `ddh.css` (palette = oklch + `var()` + `color-mix(in oklab, …)`).
`in oklab` dans les `color-mix` est l'espace d'interpolation, **pas** une couleur.
Les `color-mix(in oklab, var(--moss) …)` de la page `index.html` (filigrane froid +
filets du triptyque) sont tous bâtis sur `--moss` (vert froid) — aucune chaleur.

## Liens cassés restants (check 4)

Quatre cibles internes root-relatives n'existent pas encore sur le disque. Toutes sont
des **renvois en avant cohérents** (artefacts/pages à publier), pas des fautes de frappe
vers un fichier presque-existant. Conformément à la consigne (« NE redesigne RIEN » +
« Liste les liens cassés »), elles sont **listées, pas supprimées** — retirer le lien
légal du footer casserait la propriété « footer verbatim » (checks 1/2) ; vider 2 des 3
cartes de l'index Records serait un redesign.

| Lien (cible) | Présent dans | Nature |
|---|---|---|
| `/mentions-legales` | les 6 footers (`index`, `records/index`, `records/2026-05-24`, `atelier/index`, `atelier/t0`, `cabinet/index`) | Page légale non encore créée. Doit rester (intégrité du footer verbatim). |
| `/records/2026-05-23/` | `records/index.html:82` (carte d'index) | Carnet à publier (seul `2026-05-24` existe). |
| `/records/2026-05-22/` | `records/index.html:94` (carte d'index) | Carnet à publier. |
| `/records/2026-05-24/trace.zip` | `records/2026-05-24/index.html:127` | Trace de fabrication (.zip) à joindre. |
| `/atelier/t0/etalon` | `atelier/t0/index.html:159` | « zip étalon » de l'essai T0, à publier. |

Note : `/records/feed.xml` est présent et résout (`records/feed.xml` existe). Les liens
externes `https://…` (sources arXiv, Anthropic, OpenAI, Stratechery, etc.) sont hors
périmètre du check « le fichier cible existe-t-il » (cibles distantes, non vérifiées ici).

## Corrections appliquées

**Aucune.** Tous les checks de contenu passent en l'état. Le seul écart observé —
l'indentation plus profonde du corps de `cabinet/index.html` — est purement cosmétique
(le contenu cartel + footer y est byte-identique aux autres pages, prouvé par md5).
Le reflow de ce corps serait une édition multi-lignes à risque d'erreur réel, sans
gain sur aucun check, et ne touche aucune valeur de design : **laissé tel quel**.
