---
title: "PRD — Apex Autonomous Quantitative Spot Grid Trading Agent"
status: "final"
created: "2026-10-18"
updated: "2026-10-18"
author: "John (BMad Product Manager)"
project: "Autonomus-Agentic-Income"
target_capital: "100 USD"
target_pnl: "10+ USD / day"
---

# Product Requirements Document (PRD) — Apex Trading Agent

## 1. Vision & Core Philosophy
Construire et déployer un agent quantitatif autonome capable de générer un revenu journalier passif récurrent dès 100 $ de capital, en éliminant les défauts mortels des bots traditionnels (liquidation, coupures réseau, état volatile en mémoire, absence de contrôle utilisateur à distance).

---

## 2. Exigences Fonctionnelles (FR)

### Ingestion Marché & Données Temps Réel
* **FR-1 : Connexion multi-échanges asynchrone.** Utiliser CCXT Async pour interroger les prix réels en direct (Ticker, Orderbook, OHLCV) toutes les 2 à 5 secondes avec gestion automatique du rate-limit.
* **FR-2 : Calcul dynamique des indicateurs de tendance.** Calculer en continu les moyennes mobiles exponentielles (EMA 50, EMA 200) et le RSI (14 périodes) sur les bougies 1m / 5m pour identifier le régime de marché (Range, Tendance Haussière, Tendance Baissière).

### Moteur de Grille Quantitatif (Strategy Core)
* **FR-3 : Génération de grille géométrique.** Calculer automatiquement les paliers de prix d'achat et de vente espacés d'un pourcentage fixe (ex: 1.0 % à 1.5 % de marge nette) autour du prix courant.
* **FR-4 : Filtre anti-couteau qui tombe (Trend Guard).** Si le RSI tombe sous 25 avec une cassure de l'EMA 200 (krach violent), l'agent suspend temporairement l'exécution de nouveaux ordres d'achat pour ne pas accumuler des jetons en chute libre.
* **FR-5 : Cycle complet Achat/Vente et Recyclage de Grille.** Dès qu'un ordre d'achat à un niveau est exécuté, l'agent place instantanément l'ordre de vente correspondant au niveau supérieur. Dès que la vente est touchée, le profit est consigné et l'ordre d'achat est replacé au niveau inférieur.

### Gestion du Risque & Sécurité du Capital
* **FR-6 : Spot Only (Zéro levier).** Strictement aucun trading sur marge ou produits dérivés futures. Le risque de liquidation est de 0.00 %.
* **FR-7 : Dimensionnement de position ($100 max).** Le capital total est fractionné en 8 à 10 tranches égales (ex: ~10 $ par niveau) pour ne jamais engager 100 % des fonds sur un seul niveau de prix.
* **FR-8 : Circuit Breaker de Stop-Loss d'Urgence.** Si le cours chute sous la limite inférieure absolue définie par l'utilisateur, l'agent suspend les opérations et alerte immédiatement sur Telegram.

### Persistance & Résilience aux Crashs
* **FR-9 : Base de données SQLite WAL.** Chaque ordre, niveau de prix, statut (open, filled, closed) et profit généré est écrit immédiatement en base SQLite avec `PRAGMA journal_mode=WAL;`.
* **FR-10 : Réconciliation automatique au démarrage.** Si le VPS est redémarré ou si le conteneur Docker est relancé, l'agent lit la base, restaure son inventaire et ses ordres en cours sans aucune intervention humaine.

### Interface & Terminal Télégramme Interactif
* **FR-11 : Notifications de trades en direct.** Chaque fois qu'une vente de grille est complétée, Telegram reçoit une alerte immédiate :  
  `💰 Profit Encaissé : +0.48 $ (1.2%) | Paire : SOL/USDT | Cumul du jour : +4.32 $`.
* **FR-12 : Commandes Telegram bidirectionnelles.** L'opérateur (Louay) peut envoyer des messages à son bot pour piloter le système :
  - `/status` : État des agents, prix actuel, grille active.
  - `/balance` : Solde disponible en USDT et en crypto.
  - `/profit` : P&L total du jour et cumul historique.
  - `/pause` : Met la grille en pause sans fermer les positions.
  - `/resume` : Relance les achats et ventes de grille.
* **FR-13 : Bilan journalier à 23h59 UTC.** Message de synthèse quotidien envoyé automatiquement sur Telegram avec le montant total net généré sur les dernières 24h.

---

## 3. Exigences Non-Fonctionnelles (NFR)
* **NFR-1 : Empreinte ressource ultra-faible.** CPU < 5 %, RAM < 150 Mo sur le VPS.
* **NFR-2 : Temps de réponse Telegram < 1 seconde.** Les commandes `/status` ou `/balance` doivent répondre quasi-instantanément.
* **NFR-3 : Tolérance aux coupures réseau.** En cas de timeout réseau, retry exponentiel (1s, 2s, 4s, 8s) sans jamais crasher le processus principal.
* **NFR-4 : Déploiement en 1 commande.** Démarrage immédiat via `docker compose up -d` avec persistance des données dans `./data`.
