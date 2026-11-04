---
title: 'Tableau de bord Web Mobile Réel en Dinars Tunisiens (DT)'
type: 'feature'
created: '2026-11-05'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Louay a besoin d'une interface web mobile-responsive claire, ultra-simple et intuitive pour suivre l'activité du bot de trading APEX en temps réel, sans aucun jargon financier et exclusivement libellée en Dinars Tunisiens (DT / TND) avec interdiction absolue de tout symbole dollar ($).

**Approach:** Créer un micro-service dashboard FastAPI léger et ultra-réactif qui lit en lecture seule la base `trading.db` en temps réel, servant une interface web moderne (Tailwind CSS + Chart.js via CDN) adaptée aux smartphones, affichant les KPIs vulgarisés (Capital en DT, Gains du jour en DT, Total des bénéfices en DT, Nombre d'opérations réussies, statut du bot en direct, graphiques simples d'évolution et répartition), et le déployer sur le VPS avec un accès public direct sur le port 8085.

</frozen-after-approval>

## Implementation Notes

- Backend : Micro-service Python FastAPI (`src/dashboard/app.py`), lecture `trading.db` avec conversion systématique DT (taux fixe 3.10 DT/USD ou configurable via env `DT_RATE`).
- Frontend : Single Page Application élégante, moderne, mode sombre soigné avec contrastes lisibles, responsive mobile (cartes tactiles, grands chiffres, badges verts de gain, graphiques Chart.js simples sans surcharge visuelle).
- ZÉRO DOLLAR : Règle absolue dans tout le code HTML/JS/CSS/API — uniquement la devise "DT".
- Conteneurisation : `Dockerfile.dashboard` léger et ajout du service `dashboard` dans `docker-compose.yml` (port 8085:8085).
- Déploiement : Synchronisation git, build et lancement sur le VPS avec URL publique `http://84.247.129.48:8085/`.

## Review Triage Log

- `total_trades` aggregation in SQL: `patch` (verdict: medium, remplacé `COUNT(*)` par `COUNT(*)` sur `completed_trades`).
- CORS wildcard with credentials: `patch` (verdict: medium, défini `allow_credentials=False`).
- Unscoped Binance ticker query: `patch` (verdict: medium, filtrage par paramètre `symbols` ciblé).
- Read-only volume mount on SQLite WAL: `patch` (verdict: high, volume standard monté dans docker-compose pour éviter tout conflit SQLite WAL).
- Compose service coordination: `patch` (verdict: medium, ajout de `depends_on: [trading-agent]`).
- Container CMD and non-root security: `patch` (verdict: medium, ajout utilisateur non-root `clusteruser` et `HEALTHCHECK`).
- Client polling stacking: `patch` (verdict: medium, remplacé `setInterval` par `setTimeout` récursif chaîné).
- Float formatting and badge styling: `patch` (verdict: low, arrondi `toFixed(2)` sur le ROI et correction de la classe CSS).
- Chart current day omission: `patch` (verdict: medium, inclusion garantie de la date du jour avec le gain actuel).
- Test mock isolation: `patch` (verdict: medium, isolation complète sans requêtes externes et tests des cas nominaux et d'erreur).


