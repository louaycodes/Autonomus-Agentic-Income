---
title: "PRD — Dual-Engine Autonomous Income Cluster"
status: "final"
created: "2026-10-18"
updated: "2026-10-18"
author: "John (BMad Product Manager)"
project: "Autonomus-Agentic-Income"
target_kpi: "10+ USD / day ($300+/month) on 24/7 VPS"
---

# Product Requirements Document (PRD) — Dual-Engine Autonomous Income Cluster

## 1. Vision & Core Value Proposition
Offrir un cluster logiciel robuste, hautement résilient, tournant 24h/24 et 7j/7 sous conteneurs Docker sur un VPS Linux, qui combine deux sources de revenus complémentaires et décorrelées pour générer au minimum **10 $ nets par jour** sans intervention humaine continue.

---

## 2. Personas & User Journey

### Persona : Louay (Propriétaire & Opérateur Stratégique)
* **Objectif :** Déployer le cluster une fois via `docker-compose up -d`, définir ses clés de configuration, et recevoir chaque soir un récapitulatif financier et opérationnel sur Telegram.
* **Tolérance au risque financier :** Nulle sur le capital principal. Les gains doivent être sécurisés et le système ne doit jamais s'exposer à des pertes illimitées.
* **User Journey Opérateur :**
  1. **Jour 0 (Déploiement) :** Louay clone le dépôt sur son VPS, configure `.env` (clés API gratuites, bot token Telegram, wallet Polygon sécurisé avec micro-fond) et lance `docker-compose up -d`.
  2. **Jour 1 à 14 (Bootstrapping & 1er Dollar) :**
     - Moteur A s'enregistre sur les annuaires d'APIs et sert ses premières requêtes d'enrichissement B2B.
     - Moteur B détecte sa première asymétrie événementielle sur Polymarket et exécute un arbitrage validé.
  3. **Régime de croisière (24/7) :** Notification journalière à 23h59 UTC sur Telegram résumant : Requêtes API servies, Arbitrages exécutés, Profit net du jour (USD), Santé système.

---

## 3. Exigences Fonctionnelles (Functional Requirements)

### Moteur A : B2B Digital Utility Micro-API (Cashflow Récurrent)
* **FR-1 : Ingestion asynchrone continue.** Le module *Scout* doit interroger périodiquement (toutes les heures ou selon flux) les flux publics d'appels d'offres (BOAMP, TED Europe) et les registres de conformité tech sans déclencher de blocage IP.
* **FR-2 : Normalisation et déduplication déterministe.** Le module *Transformer* doit nettoyer, extraire les métadonnées clés (budget, date limite, mots-clés techniques, entité émettrice) et persister les entités en base locale SQLite/Postgres. Coût LLM : 0 $.
* **FR-3 : Passerelle API & Gestion des Accès.** Le module *Gateway* (FastAPI) doit exposer des endpoints REST paginés, sécurisés par `X-API-Key`, avec limitation de débit (rate limiting) par palier d'abonnement.
* **FR-4 : Intégration Monétisation.** Le Gateway doit valider les quotas via intégration directe compatible RapidAPI / Whop / Stripe webhooks.

### Moteur B : Fast Prediction Market Event Arbitrage (Gains Vélocité)
* **FR-5 : Écoute en temps réel des dépêches d'actualités certifiées.** L'agent doit monitorer les flux d'agences reconnues (Reuters, AP, dépêches d'instituts de statistiques officielles) via RSS et webhooks.
* **FR-6 : Matching sémantique avec les marchés ouverts Polymarket.** Comparer en moins de 2 secondes les conditions de résolution des contrats Polymarket actifs avec les dépêches confirmées.
* **FR-7 : Règle de sécurité Anti-Hallucination & Anti-Perte.** Aucun ordre n'est exécuté sans :
  1. Une certitude de correspondance > 98 % validée par double filtre déterministe et LLM.
  2. Un écart de cote supérieur à 8 % (ex: probabilité implicite marché <= 0.90 alors que l'événement est officialisé).
  3. Une allocation maximale par trade plafonnée (ex: 20 $ max).
* **FR-8 : Exécution d'ordre non-custodial via API Polymarket CLOB.** Signature et envoi de l'ordre d'achat via la clé privée Polygon configurée dans le coffre d'environnement sécurisé.

### Superviseur Sentinelle (Core Engine)
* **FR-9 : Auto-Restart & Gestion des Pannes.** Si un sous-processus plante, le conteneur Docker redémarre avec un backoff exponentiel.
* **FR-10 : Sentinel Watchdog.** Vérification de santé (healthcheck) toutes les 60 secondes. Vérification de l'espace disque, mémoire et connectivité réseau.
* **FR-11 : Reporting Telegram Automatisé.** Notification instantanée en cas d'erreur bloquante (ex: solde insuffisant, clé API invalide) et notification récapitulative quotidienne des gains à 23h59.
* **FR-12 : Mode Simulation / Dry-Run.** Capacité de démarrer le système avec `SIMULATION_MODE=true` pour valider l'intégralité des flux et des profits théoriques sans engager de fonds réels.

---

## 4. Exigences Non-Fonctionnelles (Non-Functional Requirements)

* **NFR-1 : Empreinte ressource ultra-légère.** Consommation totale de RAM du cluster < 1.5 Go, CPU < 15 % en moyenne sur un VPS standard.
* **NFR-2 : Tolérance aux pannes réseau.** Retry automatique avec jitter sur toutes les requêtes externes (APIs, nœuds RPC).
* **NFR-3 : Sécurité des clés secrètes.** Aucune clé privée ou secrète stockée en dur dans le code. Utilisation exclusive de variables d'environnement (`.env`) isolées du code source.
* **NFR-4 : Zéro coût d'infrastructure supplémentaire.** Fonctionne intégralement sur un seul VPS Linux avec Docker et Docker Compose.
* **NFR-5 : Traçabilité & Auditabilité.** Chaque décision d'arbitrage et chaque transaction API est journalisée avec timestamp, source, hash et delta financier.
* **NFR-6 : Latence de détection.** Détection et validation d'arbitrage événementiel en moins de 3 secondes après publication de la dépêche.
