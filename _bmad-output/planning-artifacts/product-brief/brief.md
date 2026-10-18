---
title: "Product Brief — Dual-Engine Autonomous VPS Agent Cluster"
status: "approved"
created: "2026-10-18"
updated: "2026-10-18"
author: "Mary (BMad Business Analyst)"
project: "Autonomus-Agentic-Income"
target_income: "10+ USD / day ($300+/month)"
---

# Product Brief — Dual-Engine Autonomous Income Cluster

## 1. Executive Summary & Serment d'Exécution
Ce document formalise la conception d'un cluster d'agents logiciels 100 % autonomes conçu pour opérer 24h/24 et 7j/7 sur un serveur privé virtuel (VPS) standard (Linux, 2-4 vCPU, 4-8 Go RAM), sans intervention humaine quotidienne, dans le but d'atteindre et dépasser un revenu passif net de **10 $ / jour** dès sa mise en service.

Le système adopte une architecture dite **Dual-Engine (Double Moteur)** :
1. **Moteur Récurrent (Engine A — B2B Data Utility & Micro-API) :** Sécurise le socle de revenu prévisible (zéro risque financier) en collectant, enrichissant et exposant des flux de données à haute valeur marchande via des endpoints d'API monétisés (RapidAPI, Whop, direct API keys).
2. **Moteur Vélocité (Engine B — Prediction Market Event Arbitrage) :** Capte des gains événementiels asymétriques en scannant les flux d'actualités certifiées et en exploitant la latence de réévaluation des marchés de prédiction (Polymarket / Kalshi) via des micro-ordres à faible risque.
3. **Le Superviseur Sentinelle (Core Engine — Autonomous Watchdog) :** Garantit la survie, la santé, le redémarrage automatique en conteneurs Docker et la reddition de comptes quotidienne sur Telegram.

---

## 2. Le Pourquoi & Les Principes Fondateurs

* **Principe d'indépendance humaine :** Le cluster doit s'auto-réparer, gérer ses limites de requêtes (rate-limits), renouveler ses caches et notifier son propriétaire uniquement via un rapport de synthèse financier quotidien ou une alerte critique.
* **Principe de frugalité ($0 operational LLM waste) :** 95 % du travail de filtrage et de transformation est déterministe (Python pur, regex, requêtes SQL locales). Les LLMs ne sont mobilisés que pour la validation sémantique ponctuelle sur des modèles gratuits ou quasi-gratuits (ex: Google Gemini Flash, Groq Llama-3.3-70B).
* **Principe de protection absolue du capital :** Le Moteur A ne nécessite aucun capital. Le Moteur B n'engage que des micro-allocations limitées (10 $ à 50 $ par arbitrage binaire vérifié avec double validation de source) sans jamais recourir à l'effet de levier.

---

## 3. Spécification des Deux Moteurs de Revenu

### Moteur A : B2B Digital Utility Micro-API (Cashflow prévisible)
* **Offre produit :** Fourniture d'une API spécialisée de surveillance d'asymétrie B2B :
  1. *Subventions & Appels d'offres publics qualifiés :* Extraction continue des avis de marchés et subventions européennes et françaises avec résumé sémantique du cahier des charges.
  2. *Tech-Stack & Surveillance RGPD :* API de détection de conformité technique et de trackers tiers pour agences web et consultants.
* **Modèle de monétisation :**
  - Listing sur RapidAPI / APILayer (Freemium : 50 requêtes gratuites/mois, puis tiers Pro à 19 $ - 49 $/mois).
  - 5 abonnements actifs à 29 $/mois = 145 $/mois (~5 $/jour net).

### Moteur B : Fast Event Arbitrage sur Polymarket (Revenus à vélocité)
* **Offre produit :** Surveillance en temps réel par polling websocket/RSS de flux d'actualités officielles (Reuters, Bloomberg, dépêches gouvernementales, cours officiels) croisée avec les contrats binaires actifs de Polymarket via l'API Polygon/CLOB.
* **Mécanique :** Lorsqu'un événement binaire est officiellement validé dans la presse mais que les parts de Polymarket s'échangent encore avec un spread (ex: part à 0.88 $ pour un rachat automatique garanti à 1.00 $ à la résolution), l'agent place un ordre d'achat immédiat.
* **Modèle de monétisation :** 2 à 3 micro-arbitrages réussis par semaine de 15 $ à 25 $ de profit net = ~5 $ à 10 $/jour en moyenne lissée.

---

## 4. Métriques de Succès (KPIs)
* **Milestone 1 :** Premier dollar encaissé ($1) dans les 14 jours suivant le déploiement sur VPS.
* **Milestone 2 :** 10 $ / jour de moyenne lissée sur 30 jours consécutifs ($300 / mois).
* **Uptime opérationnel :** > 99.8 % sur VPS sans redémarrage manuel.
* **Rapport Coût / CA :** Moins de 20 $/mois de frais de fonctionnement (VPS Hetzner inclus).
