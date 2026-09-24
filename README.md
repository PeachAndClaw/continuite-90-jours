# Peach & Claw — Carte de continuité 90 jours

Page commerciale dédiée au test payant de la Carte de continuité 90 jours : un diagnostic borné pour consultants indépendants et petites agences B2B, livré sous 72 heures pour 250 € HT.

## Principe de validation

- aucun développement SaaS avant deux commandes payées ;
- aucune connexion bancaire ni collecte de secrets ;
- devis et paiement à la commande avant démarrage ;
- le spécimen public est fictif et explicitement présenté comme tel ;
- une demande de suivi récurrent doit venir des acheteurs avant toute hypothèse d’abonnement.

## Développement local

```bash
python3 -m http.server 4173
```

Puis ouvrir <http://127.0.0.1:4173>.

## Vérification

La surface publique comprend :

- métadonnées SEO, canonical, Open Graph et carte X/Twitter ;
- données structurées Schema.org (`Organization`, `WebSite`, `WebPage`, `Service`, `Offer`, `FAQPage`) ;
- `robots.txt`, `sitemap.xml` et `llms.txt` ;
- page de transparence, polices auto-hébergées, aucun traceur ni formulaire ;
- tests navigateur bureau/mobile et contrôle des liens, actifs, débordements, métadonnées et garde-fous commerciaux.

```bash
.venv/bin/python tests/smoke.py
```

Le rapport d’audit daté est conservé dans [`AUDIT-2026-09-24.md`](AUDIT-2026-09-24.md).

## Publication

La branche `main` est publiée sur GitHub Pages par le workflow officiel `pages.yml`.

© Peach & Claw. Tous droits réservés.
