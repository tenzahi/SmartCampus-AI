# SmartCampus AI

Plateforme agentique d'orientation universitaire pour l'IIT et l'ISB.
Un chatbot accompagne les futurs étudiants : orientation, préinscription, QCM et suivi jusqu'à l'inscription.

## Technologies

- **Frontend** : Next.js
- **Backend** : FastAPI (Python)
- **Base de données** : PostgreSQL (avec pgvector)
- **Conteneurs** : Docker et Docker Compose

## Prérequis

Installer ces deux outils :

- [Git](https://git-scm.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (lancé avant de commencer)

## Installation

```bash
git clone https://github.com/tenzahi/SmartCampus-AI.git
cd SmartCampus-AI
git checkout feature/task-7-backend-init
```

Créer le fichier de configuration :

```bash
# Windows (PowerShell)
copy .env.example .env

# Mac / Linux
cp .env.example .env
```

Démarrer le projet :

```bash
docker compose up --build
```

> La première fois, le démarrage peut prendre quelques minutes.

## Adresses du projet

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| Documentation de l'API | http://localhost:8000/docs |
| Test de la base de données | http://localhost:8000/health/db |
| Liste des formations (démo) | http://localhost:8000/programmes |

## Vérifier que tout fonctionne

1. Ouvrir http://localhost:8000/health/db : le résultat doit être `{"database":"ok"}`.
2. Ouvrir http://localhost:8000/programmes : 4 formations de démonstration doivent s'afficher.
3. Ouvrir http://localhost:3000 : le frontend doit s'afficher.

## Commandes utiles

```bash
docker compose up -d              # démarrer en arrière-plan
docker compose logs -f backend    # voir les logs du backend
docker compose down               # arrêter le projet
docker compose down -v            # arrêter et réinitialiser la base de données
```

## Structure du projet

```
SmartCampus-AI/
├── backend/          API FastAPI
│   └── app/
│       ├── api/routes/   routes de l'API
│       ├── core/         configuration, base de données, erreurs
│       ├── schemas/      modèles de données
│       └── services/     logique métier
├── frontend/         application Next.js
├── db/init.sql       création des tables et données de démonstration
├── docker-compose.yml
└── .env.example      modèle du fichier de configuration
```

## Problèmes fréquents

- **Docker ne démarre pas** : vérifier que Docker Desktop est lancé.
- **Port déjà utilisé** : fermer le programme qui occupe le port 3000, 8000 ou 5432.
- **Base de données vide ou ancienne** : exécuter `docker compose down -v`, puis `docker compose up --build`.
- **Erreur sur les variables POSTGRES** : vérifier que le fichier `.env` existe à la racine du projet.

## Équipe

Projet IA générative 2026-2027, IIT, Groupe 5.