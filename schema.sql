CREATE TABLE IF NOT EXISTS utilisateurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    mot_de_passe TEXT NOT NULL,
    ville TEXT NOT NULL,
    telephone TEXT,
    role TEXT NOT NULL DEFAULT 'etudiant' CHECK (role IN ('etudiant', 'admin')),
    bloque INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trajets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conducteur_id INTEGER NOT NULL,
    sens TEXT NOT NULL CHECK (sens IN ('aller', 'retour')),
    ville TEXT NOT NULL,
    date_heure TEXT NOT NULL,
    places_total INTEGER NOT NULL CHECK (places_total BETWEEN 1 AND 4),
    places_restantes INTEGER NOT NULL CHECK (places_restantes >= 0),
    prix REAL NOT NULL CHECK (prix >= 0),
    point_rdv TEXT,
    statut TEXT NOT NULL DEFAULT 'actif' CHECK (statut IN ('actif', 'annule')),
    FOREIGN KEY (conducteur_id) REFERENCES utilisateurs(id)
);

CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trajet_id INTEGER NOT NULL,
    passager_id INTEGER NOT NULL,
    statut TEXT NOT NULL DEFAULT 'en_attente'
        CHECK (statut IN ('en_attente', 'acceptee', 'refusee', 'annulee', 'trajet_annule')),
    date_demande TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trajet_id) REFERENCES trajets(id),
    FOREIGN KEY (passager_id) REFERENCES utilisateurs(id),
    UNIQUE (trajet_id, passager_id)
);

CREATE TABLE IF NOT EXISTS avis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER NOT NULL UNIQUE,
    note INTEGER NOT NULL CHECK (note BETWEEN 1 AND 5),
    date_avis TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reservation_id) REFERENCES reservations(id)
);