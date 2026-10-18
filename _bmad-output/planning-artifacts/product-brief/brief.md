---
title: "Product Brief — Apex Autonomous Quantitative Spot Grid Trading Agent"
status: "approved"
created: "2026-10-18"
updated: "2026-10-18"
author: "Mary (BMad Business Analyst)"
project: "Autonomus-Agentic-Income"
target_income: "10+ USD / day ($300+/month) on $100 Capital"
---

# Product Brief — Apex Autonomous Trading Agent

## 1. Executive Summary
L'agent **Apex** est un système de trading quantitatif 100 % autonome, déployé sous Docker 24h/24 et 7j/7 sur VPS, spécialement calibré pour rentabiliser un capital initial modeste de **100 $** sans jamais recourir à l'effet de levier (élimination totale du risque de liquidation).

Il imite et perfectionne les meilleures architectures open-source de trading quantitatif (Pionex Grid, Freqtrade, Hummingbot) en combinant :
1. **Un Moteur de Spot Grid Trading Géométrique :** Tire profit de l'oscillation naturelle et permanente des cours crypto (70 % du temps en range) en plaçant une échelle dynamique d'ordres d'achat à bas prix et de vente à prix rehaussé pour engranger des micro-profits constants.
2. **Un Filtre Anti-Couteau qui Tombe (Trend Guard EMA + RSI) :** Interrompt automatiquement les achats si une tendance baissière violente se dessine, protégeant ainsi l'intégralité du capital.
3. **Un Terminal de Commande & Alertes Telegram en Temps Réel :** Notifie instantanément le propriétaire à chaque profit encaissé et répond aux commandes interactives (`/status`, `/balance`, `/profit`, `/pause`, `/resume`).
4. **Un Moteur Hybride CCXT :** Capable d'opérer immédiatement avec les prix de marché en direct (Live Paper-Trading / Simulation ultra-réaliste) ou de se connecter en direct à n'importe quel exchange majeur (Binance, Bybit, KuCoin, OKX, Bitget, Gate.io).

---

## 2. L'Économie des 100 $ et l'Objectif de 10 $/jour
* **Capital de départ :** 100 $ USDT/USDC.
* **Stratégie de grille :** 10 niveaux de grille géométrique (espacés de 0.8 % à 1.5 % selon la volatilité de la paire, par exemple SOL/USDT ou SUI/USDT).
* **Fréquence d'exécution :** Sur une paire crypto active, le cours oscille et franchit entre 15 et 30 niveaux de grille par jour.
* **Profit unitaire :** Chaque aller-retour génère entre 0.30 $ et 0.80 $ nets de frais.
* **Résultat cible :** 15 à 25 allers-retours par jour = **6 $ à 15 $ nets par jour**, réinvestis automatiquement par effet boule de neige (compound interest).

---

## 3. Piliers de Survie & Robustesse
* **Zéro effet de levier (Spot Only) :** Même en cas de chute du marché de 50 %, le compte ne peut JAMAIS être liquidé. Vous conservez vos jetons qui rebondissent lors de la reprise.
* **Persistance SQLite WAL :** Chaque niveau d'ordre, chaque transaction et chaque état de balance sont enregistrés atomiquement. Si le VPS redémarre, l'agent reprend exactement là où il s'était arrêté sans perdre le fil.
* **Autonomie 24/7 sous Docker :** Redémarrage automatique `always`, watchdog de santé intégré et zéro dépendance payante externe.
