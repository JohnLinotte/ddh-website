# Département des Harnais — site statique

Atelier d'auteur de John Linotte : harness d'agents IA, agentivité, deterministic-first. Bruxelles, mmxxvi.

**En ligne** : https://harnais.be

## Ce que contient ce dépôt

- `index.html`, `carnet/`, `essais/`, `a-propos/`, `colophon/`, `vie-privee/`, `404.html` — les pages publiées.
- `_scripts/build_feeds.py` — le pipeline de génération des métadonnées, en Python stdlib pur (aucun framework) : `sitemap.xml`, flux RSS + JSON Feed (Carnet et Essais), JSON-LD schema.org, `llms.txt` + `llms-full.txt`, balises canonical.
- `_templates/` — partials Pinegrow (nav, footer, page).
- `robots.txt` — Content-Signal `search=yes, ai-input=yes, ai-train=no` + Allow explicite des answer engines (ClaudeBot, GPTBot, PerplexityBot, Google-Extended, Applebot-Extended…).

## Méthode — deterministic-first

Le pipeline SEO/GEO est entièrement déterministe, en Python stdlib. Le LLM n'intervient jamais dans la production des métadonnées. On relance `_scripts/build_feeds.py` après chaque publication.

## Licence

- **Code** (`_scripts/build_feeds.py`, `_templates/`) : MIT — voir `LICENSE`.
- **Contenu éditorial** (billets du Carnet, essais, pages) : Creative Commons BY 4.0 — https://creativecommons.org/licenses/by/4.0/

Mentionner l'auteur (John Linotte) et l'URL source.

## Auteur

John Linotte — https://harnais.be — contact@harnais.be