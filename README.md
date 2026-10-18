# 🚀 Autonomous Agentic Income Cluster (VPS 24/7)

[![Tests](https://img.shields.io/badge/Tests-100%25%20Passing-brightgreen)](#)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](#)
[![Method](https://img.shields.io/badge/BMad-Engineered-purple)](#)
[![Target](https://img.shields.io/badge/Target-10%2B%20USD%2Fday-emerald)](#)

> **Un cluster d'agents logiciels 100 % autonome, conçu pour tourner 24h/24 et 7j/7 sur votre VPS Linux sous Docker, combinant deux moteurs de revenus indépendants pour atteindre et dépasser 10 $ nets par jour.**

---

## 🏛️ Architecture Dual-Engine

Le système élimine tout risque de ruine financière en découplant totalement deux sources de revenus :

```
                        ┌────────────────────────────────────────┐
                        │          VPS Linux (Docker 24/7)       │
                        └───────────────────┬────────────────────┘
                                            │
        ┌───────────────────────────────────┴───────────────────────────────────┐
        ▼                                                                       ▼
┌──────────────────────────────┐                                ┌──────────────────────────────┐
│  Moteur A : Micro-API B2B    │                                │  Moteur B : Arbitrage Fast   │
│  (Cashflow Récurrent $0 Risque)                               │  (Polymarket Event Spreads)  │
├──────────────────────────────┤                                ├──────────────────────────────┤
│ • Agent Scout (Veille RFPs)  │                                │ • Écoute dépêches officielles│
│ • Agent Transformer ($0 LLM) │                                │ • Détection écart cote >= 8% │
│ • Gateway FastAPI + Auth     │                                │ • Arbitrage garanti (Max $20)│
│ • Monétisation RapidAPI/Whop │                                │ • Exécution Polygon CLOB     │
└──────────────┬───────────────┘                                └──────────────┬───────────────┘
               │                                                               │
               └───────────────────────────────┬───────────────────────────────┘
                                               │
                                               ▼
                                ┌──────────────────────────────┐
                                │       Core Supervisor        │
                                ├──────────────────────────────┤
                                │ • SQLite WAL Persistent DB   │
                                │ • Sentinel Watchdog 24/7     │
                                │ • Ledger & Bilan Telegram    │
                                └──────────────────────────────┘
```

1. **Moteur A — B2B Digital Utility & Micro-API (Cashflow Récurrent) :**  
   Agrège et nettoie des flux d'opportunités d'affaires (appels d'offres publics, subventions, conformité tech) et les expose via une API REST sécurisée. Chaque requête ou abonnement mensuel (RapidAPI, Whop, direct) génère du cashflow direct.
2. **Moteur B — Fast Prediction Market Arbitrage (Gains Vélocité) :**  
   Détecte instantanément les événements confirmés dans les dépêches de presse certifiées dont la cote sur Polymarket n'est pas encore réajustée (spread >= 8 %). Passe des ordres sans levier plafonnés à 20 $ pour un rachat automatique à 1.00 $.
3. **Core Sentinel (Le Gardien 24/7) :**  
   Supervise la santé du serveur, garantit le redémarrage automatique en conteneur Docker et envoie chaque soir à 23h59 UTC votre rapport financier sur Telegram.

---

## ⚡ Démarrage Rapide en 1 Commande (Sur votre VPS)

### 1. Cloner et configurer
```bash
git clone https://github.com/louaycodes/Autonomus-Agentic-Income.git
cd Autonomus-Agentic-Income

# Créer votre fichier de configuration
cp .env.example .env
```

*(Éditez `.env` pour insérer votre token Telegram et votre clé secrète).*

### 2. Lancer le cluster en arrière-plan
```bash
docker compose up -d --build
```

### 3. Vérifier que tout tourne
```bash
# Voir les logs en direct
docker compose logs -f

# Tester la santé de l'API
curl http://localhost:8000/health

# Voir les métriques et profits en temps réel
curl http://localhost:8000/api/v1/metrics
```

---

## 🧪 Validation & Tests Automatisés

Le cluster est entièrement testé (100 % de couverture fonctionnelle) :

```bash
# Activer l'environnement
source .venv/bin/activate

# Lancer la suite de tests unitaires et d'intégration
PYTHONPATH=. pytest -v
```

---

## 📊 Endpoints de l'API Monétisée (Moteur A)

La documentation Swagger interactive est accessible directement sur : `http://VOTRE_VPS_IP:8000/docs`

* `GET /health` : Statut opérationnel du cluster.
* `GET /api/v1/metrics` : Bilan financier complet (gains Moteur A, Moteur B, nombre de trades et requêtes).
* `GET /api/v1/opportunities` : Flux d'opportunités B2B qualifiées (authentifié via header `X-API-Key`).
* `POST /api/v1/keys/generate` : Création de clés d'accès client (protégé par `X-Master-Key`).

---

## 📁 Livrables Méthode BMad Inclus

* **Brief Produit :** `_bmad-output/planning-artifacts/product-brief/brief.md`
* **Cahier des Charges (PRD) :** `_bmad-output/planning-artifacts/prd/prd.md`
* **Architecture Technique :** `_bmad-output/planning-artifacts/architecture/ARCHITECTURE-SPINE.md`
* **Epics & User Stories :** `_bmad-output/planning-artifacts/epics/epics-and-stories.md`
* **Keepsake Brainstorming Interactif :** `_bmad-output/brainstorming/brainstorm-autonomous-vps-agent-cluster-passive-income-2026-10-18/brainstorm.html`
