-- Exécuté automatiquement au premier démarrage de PostgreSQL.
-- Données de démonstration FICTIVES : à remplacer par les vraies informations IIT / ISB.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS programmes (
    id             SERIAL PRIMARY KEY,
    etablissement  VARCHAR(10)  NOT NULL,      -- 'IIT' ou 'ISB'
    nom            VARCHAR(150) NOT NULL,
    niveau         VARCHAR(50)  NOT NULL,      -- Licence, Prépa, Ingénierie...
    description    TEXT
);

CREATE TABLE IF NOT EXISTS candidats (
    id               SERIAL PRIMARY KEY,
    nom              VARCHAR(100) NOT NULL,
    email            VARCHAR(150) UNIQUE NOT NULL,
    langue_preferee  VARCHAR(20)  DEFAULT 'fr',   -- fr, tunisien, arabizi
    programme_id     INT REFERENCES programmes(id),
    created_at       TIMESTAMP DEFAULT NOW()
);

INSERT INTO programmes (etablissement, nom, niveau, description) VALUES
 ('IIT', 'Licence Informatique (démo)',        'Licence',    'Exemple de licence en informatique.'),
 ('IIT', 'Cycle préparatoire intégré (démo)',  'Prépa',      'Exemple de cycle préparatoire.'),
 ('IIT', 'Cycle ingénieur (démo)',             'Ingénierie', 'Exemple de cycle ingénieur.'),
 ('ISB', 'Formation ISB (démo)',               'Licence',    'Exemple de formation ISB.');

INSERT INTO candidats (nom, email, langue_preferee, programme_id) VALUES
 ('Candidat Test 1', 'test1@example.com', 'tunisien', 2),
 ('Candidat Test 2', 'test2@example.com', 'fr',       1);