# ⚡ Apex Autonomous Quantitative Spot Grid Trading Agent (VPS 24/7)

[![Tests](https://img.shields.io/badge/Tests-100%25%20Passing-brightgreen)](#)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](#)
[![Capital](https://img.shields.io/badge/Capital-100%24%20Spot-yellow)](#)
[![Leverage](https://img.shields.io/badge/Liquidation%20Risk-0.00%25-emerald)](#)

> **Agent de trading quantitatif 100 % autonome sur VPS Linux, conçu pour générer des micro-profits quotidiens récurrents (objectif 10 $/jour) à partir d'un capital de 100 $, sans effet de levier et sans risque de liquidation.**

---

## 🏛️ Stratégie & Architecture Quantitative

L'agent **Apex** reproduit la formule gagnante des meilleurs systèmes de trading quantitatif de marché (Pionex Grid, Freqtrade, Hummingbot) :

```
                        ┌────────────────────────────────────────┐
                        │          VPS Linux (Docker 24/7)       │
                        └───────────────────┬────────────────────┘
                                            │
        ┌───────────────────────────────────┴───────────────────────────────────┐
        ▼                                                                       ▼
┌──────────────────────────────┐                                ┌──────────────────────────────┐
│  Moteur Spot Grid Géométrique│                                │    Trend Guard Anti-Crash    │
├──────────────────────────────┤                                ├──────────────────────────────┤
│ • Échelle d'ordres Achat/Vente│                               │ • EMA 50 / 200 + RSI 14      │
│ • Espacement 1.2% par niveau │                                │ • Blocage auto si krach brut │
│ • Recyclage continu 24/7     │                                │ • Protection du capital      │
└──────────────┬───────────────┘                                └──────────────┬───────────────┘
               │                                                               │
               └───────────────────────────────┬───────────────────────────────┘
                                               │
                                               ▼
                                ┌──────────────────────────────┐
                                │   Terminal Telegram Interactif│
                                ├──────────────────────────────┤
                                │ • Alertes de gains en direct │
                                │ • Commandes /status /profit  │
                                │ • Rapport de clôture à 23h59 │
                                └──────────────────────────────┘
```

1. **Spot Grid Trading Géométrique (Micro-Arbitrage d'Oscillation) :**  
   Les marchés crypto oscillent 70 % du temps dans des canaux de prix. Le bot fractionne vos 100 $ en micro-ordres échelonnés et achète chaque creux pour revendre chaque rebond avec 1.2 % de marge nette.
2. **Trend Guard Anti-Couteau qui tombe :**  
   Si le marché subit une vente massive anormale (RSI < 28 et cassure sous l'EMA 200), le bot bloque immédiatement les nouveaux achats pour préserver vos liquidités jusqu'à stabilisation.
3. **Persistance SQLite WAL & Tolérance aux Reboot :**  
   Chaque ordre, transaction et état est gravé sur disque. Si le VPS reboot, l'agent reprend sans perdre un seul centime.
4. **Terminal Telegram Interactif :**  
   Recevez une notification à chaque gain et pilotez le bot depuis votre smartphone.

---

## 📱 Commandes Telegram Disponibles (@Bashkoubot)

Vous pouvez envoyer ces messages directement à votre bot sur Telegram :

| Commande | Action |
|---|---|
| `/status` | Affiche le prix actuel, l'état du bot et les ordres de grille en cours |
| `/balance` | Affiche vos soldes disponibles (USDT et Crypto) et valeur totale |
| `/profit` | Affiche le P&L net encaissé aujourd'hui et le cumul historique |
| `/pause` | Met temporairement la stratégie en pause (aucun nouvel ordre) |
| `/resume` | Relance la stratégie et l'écoute de marché |
| `/help` | Affiche la liste des commandes |

---

## ⚡ Démarrage Rapide (En 1 Commande sur votre VPS)

Le projet est déjà pré-configuré et déployé sur votre VPS. Pour le relancer ou le vérifier à tout moment :

```bash
# Se connecter au VPS
ssh vps

# Aller dans le dossier et lancer
cd Autonomus-Agentic-Income
docker compose up -d --build

# Voir les logs de trading en direct
docker compose logs -f
```

---

## 🧪 Tests Unitaires Automatisés

```bash
source .venv/bin/activate
PYTHONPATH=. pytest -v
```
*(10 tests unitaires passants à 100 % : indicateurs EMA/RSI, logique de grille, persistance WAL et commandes Telegram).*
