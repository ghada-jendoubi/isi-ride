# ISI Ride

Plateforme web de covoiturage réservée aux étudiants de l'ISI (Institut Supérieur d'Informatique, Université Tunis El Manar).

Projet réalisé dans le cadre de la matière « Outils de Travail Collaboratif » (L2-CS, AU 2026/2027), enseignante : Dr. Zakia ZOUAGHIA.

## Fonctionnalités

- Inscription limitée aux adresses e-mail de l'ISI (`@etudiant-isi.utm.tn`)
- Publication de trajets (aller vers l'ISI ou retour), de 1 à 4 places
- Recherche par ville, sens et date, avec la note moyenne du conducteur
- Demandes de réservation, acceptation ou refus par le conducteur, annulation
- Affichage du numéro de téléphone des deux étudiants après acceptation uniquement
- Note de 1 à 5 étoiles attribuée au conducteur après le trajet
- Espace d'administration : blocage de comptes, suppression de trajets

## Technologies

Python, Flask, SQLite, Jinja2, Bootstrap 5, Git et GitHub.

## Installation en local

```
git clone https://github.com/ghada-jendoubi/isi-ride.git
cd isi-ride
python -m pip install -r requirements.txt
python init_db.py
python app.py
```

Le site est alors accessible sur http://127.0.0.1:5000.

`init_db.py` crée la base de données et un compte administrateur de développement. Son mot de passe doit être changé avant toute mise en ligne.

## Tests

```
python -m pip install pytest
python -m pytest tests -v
```

Les tests automatiques utilisent une base de données temporaire, jamais la vraie.

## Limites connues

- Le domaine de l'e-mail est vérifié, mais pas l'adresse elle-même (pas de lien de confirmation).
- Le formulaire d'inscription se vide après une erreur de saisie.

## Perspectives

- Confirmation de l'e-mail par lien
- Lieu de départ précis obligatoire et filtre par quartier
- Notifications automatiques