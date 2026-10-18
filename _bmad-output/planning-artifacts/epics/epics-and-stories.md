---
title: "Epics and User Stories — Apex Quantitative Trading Agent"
status: "approved"
created: "2026-10-18"
updated: "2026-10-18"
author: "Scrum Lead (BMad Method)"
project: "Autonomus-Agentic-Income"
---

# Epics and User Stories — Apex Quantitative Trading Agent

## Epic 1 : Quantitative Core, Config & SQLite WAL Persistence
Fournir la fondation de stockage et de réconciliation d'état en cas de redémarrage.

### Story 1.1 : SQLite WAL Database & State Reconciliation
* **Critères d'Acceptation :**
  - Tables `grid_orders`, `completed_trades`, `daily_pnl`, `bot_state`.
  - Mode `PRAGMA journal_mode=WAL;` activé.
  - Fonction de réconciliation au boot pour restaurer les ordres ouverts et l'inventaire.

### Story 1.2 : Configuration Module
* **Critères d'Acceptation :**
  - Chargement de `SYMBOL` (défaut: `SOL/USDT`), `TOTAL_CAPITAL_USD` (100.0), `GRID_LEVELS` (10), `GRID_STEP_PERCENT` (1.2%), `TRADING_MODE` (`paper` ou `live`).

---

## Epic 2 : Spot Grid Trading Engine, Trend Guard & Execution Router
L'intelligence quantitative qui extrait les micro-profits du marché 24/7.

### Story 2.1 : Market Feeder & Trend Guard
* **Critères d'Acceptation :**
  - Récupération asynchrone du ticker et des bougies via CCXT.
  - Calcul des indicateurs EMA 50, EMA 200 et RSI 14.
  - Blocage des ordres d'achat en cas de signal de panique/krach.

### Story 2.2 : Spot Grid Generator & Order Recycling
* **Critères d'Acceptation :**
  - Calcul des paliers géométriques autour du prix actuel.
  - Placement des ordres d'achat et de vente associés.
  - Dès qu'un ordre d'achat est rempli, création automatique de l'ordre de vente au niveau supérieur avec marge garantie.

### Story 2.3 : Hybrid Execution Router (Paper vs Live)
* **Critères d'Acceptation :**
  - En mode `paper` : simulation réaliste des fills selon le carnet d'ordres live.
  - En mode `live` : envoi des ordres réels via l'exchange CCXT configuré.

---

## Epic 3 : Telegram Command Terminal & Instant Trade Alerts
Permettre à Louay de suivre ses gains et de piloter son agent depuis son smartphone sans toucher à un terminal SSH.

### Story 3.1 : Instant Profit Alerts
* **Critères d'Acceptation :**
  - Notification Telegram instantanée dès qu'une vente de grille est complétée avec le gain net en dollars et le pourcentage.

### Story 3.2 : Interactive Commands Listener
* **Critères d'Acceptation :**
  - Écoute en arrière-plan des messages Telegram venant de `TELEGRAM_CHAT_ID`.
  - Réponses immédiates aux commandes `/status`, `/balance`, `/profit`, `/pause`, `/resume`, `/help`.

### Story 3.3 : Daily Midnight P&L Ledger Report
* **Critères d'Acceptation :**
  - Bilan comptable automatique envoyé à 23h59 UTC avec les gains nets générés au cours des 24 dernières heures.

---

## Epic 4 : Validation, Tests & Déploiement VPS
Validation complète et mise en production immédiate sur le VPS.

### Story 4.1 : Test Suite Complète
* **Critères d'Acceptation :**
  - 100 % des tests unitaires passants via `pytest`.

### Story 4.2 : Packaging Dockerfile, Compose & Déploiement Live sur VPS
* **Critères d'Acceptation :**
  - Conteneur Docker opérationnel, démarré sur le VPS `84.247.129.48` avec la commande `docker compose up -d`.
