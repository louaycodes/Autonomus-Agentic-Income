---
title: "Epics and User Stories — Dual-Engine Autonomous Income Cluster"
status: "approved"
created: "2026-10-18"
updated: "2026-10-18"
author: "Scrum Lead (BMad Method)"
project: "Autonomus-Agentic-Income"
---

# Epics and User Stories — Dual-Engine Autonomous Income Cluster

## Epic 1 : Core Supervisor, Persistent Storage & Financial Ledger
Fournir le socle de survie et de reddition de comptes du cluster sur VPS Linux.

### Story 1.1 : SQLite WAL & Financial Ledger Engine
* **En tant que :** Système autonome,
* **Je veux :** Une couche de données persistante SQLite configurée en mode WAL avec gestion des transactions atomiques et traçabilité financière,
* **Afin de :** Consigner chaque requête API servie, chaque arbitrage simulé/réel et calculer les profits nets sans concurrence de verrouillage.
* **Critères d'Acceptation :**
  - [x] Initialisation automatique des tables : `api_keys`, `api_requests`, `arbitrage_events`, `daily_ledger`.
  - [x] Activation de `PRAGMA journal_mode=WAL;` et `PRAGMA busy_timeout=5000;`.
  - [x] Méthode pour enregistrer les revenus journaliers et générer le bilan net.

### Story 1.2 : Sentinel Supervisor & Telegram Alerting
* **En tant que :** Propriétaire (Louay),
* **Je veux :** Un module de supervision 24/7 qui teste la santé des agents et m'envoie chaque soir un récapitulatif sur Telegram (ou alerte immédiate en cas d'erreur bloquante),
* **Afin de :** Suivre mes revenus et savoir que le système tourne sans devoir me connecter au terminal SSH du VPS.
* **Critères d'Acceptation :**
  - [x] Boucle de contrôle de santé périodique (RAM, disque, connectivité).
  - [x] Formatage du rapport quotidien : Requêtes servies, Gains Moteur A, Gains Moteur B, Profit total USD, Uptime.
  - [x] Mode fallback silencieux / log local si Telegram n'est pas configuré.

---

## Epic 2 : Engine A — B2B Data Utility & Monétisation Micro-API
Mettre en place le moteur de cashflow récurrent sans risque financier.

### Story 2.1 : Scout & Transformer — Ingestion de Données d'Opportunités B2B
* **En tant que :** Développeur / Client B2B,
* **Je veux :** Un pipeline qui extrait et normalise des opportunités d'affaires (appels d'offres publics, subventions, listings tech qualifiés),
* **Afin d' :** Obtenir des données fraîches et enrichies prêtes à l'emploi.
* **Critères d'Acceptation :**
  - [x] Collecteur asynchrone pour sources publiques ouvertes (BOAMP, TED, registres ouverts).
  - [x] Nettoyeur déterministe en Python pur ($0 de coût API LLM).
  - [x] Stockage dédupliqué en base SQLite avec horodatage et index de recherche.

### Story 2.2 : Gateway REST FastAPI Monétisée (Compatible RapidAPI / Whop)
* **En tant que :** Client consommateur d'API,
* **Je veux :** Interroger des endpoints `/api/v1/opportunities` et `/api/v1/market-signals` protégés par clé d'API,
* **Afin de :** Payer pour consommer de la donnée stratégique.
* **Critères d'Acceptation :**
  - [x] FastAPI avec support des headers `X-API-Key` et `X-RapidAPI-Proxy-Secret`.
  - [x] Rate limiting intégré par clé (ex: 10 req/min sur tier gratuit, illimité sur tier pro).
  - [x] Documentation OpenAPI (/docs) auto-générée avec exemples réels.

---

## Epic 3 : Engine B — Polymarket Fast Event Arbitrage (Vélocité)
Capter des profits asymétriques sur les marchés de prédiction lors de confirmations d'actualités.

### Story 3.1 : Real-Time News Monitor & Matcher Polymarket
* **En tant que :** Moteur d'arbitrage,
* **Je veux :** Surveiller les flux d'actualités officielles en temps réel et les croiser avec le carnet d'ordres Polymarket,
* **Afin d' :** Identifier les retards de cotation sur des événements résolus.
* **Critères d'Acceptation :**
  - [x] Écoute des flux RSS/Websocket de dépêches d'actualités.
  - [x] Comparaison sémantique et calcul de l'écart (spread >= 8 %).
  - [x] Respect de la limite de risque (max 20 $ par ordre).

### Story 3.2 : Dual Execution Engine (Simulation & Live Polygon)
* **En tant que :** Opérateur,
* **Je veux :** Que le moteur d'arbitrage fonctionne en mode simulation sécurisée (`SIMULATION_MODE=true`) avant tout passage en live,
* **Afin de :** Valider les gains virtuels et la précision des signaux sans engager de capital réel prématurément.
* **Critères d'Acceptation :**
  - [x] Simulation de carnet d'ordres avec calcul de slippage théorique et gaz.
  - [x] Module de signature Web3 pour transition transparente vers le live.

---

## Epic 4 : Validation, Tests & Déploiement VPS Docker
Assembler le code de production, les tests unitaires et le package de déploiement en 1 commande.

### Story 4.1 : Suite de Tests Unitaires & Intégration
* **Critères d'Acceptation :**
  - [x] Couverture des flux SQLite WAL, du Gateway FastAPI, du Matcher d'arbitrage et du Watchdog.
  - [x] 100 % de tests passants via `pytest`.

### Story 4.2 : Dockerfile, Docker Compose & Guide de Déploiement VPS
* **Critères d'Acceptation :**
  - [x] Dockerfile multi-stage allégé en Alpine/Debian-slim (< 200 Mo).
  - [x] docker-compose.yml avec redémarrage automatique `always`, volume persistant et isolation réseau.
  - [x] Fichier `.env.example` prêt à l'emploi.
