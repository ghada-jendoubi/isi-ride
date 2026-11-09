import sqlite3
from datetime import datetime, timedelta

db = sqlite3.connect("database.db")

# Les deux premiers comptes étudiants : conducteur puis passager
comptes = db.execute(
    "SELECT id, email FROM utilisateurs WHERE role = 'etudiant' ORDER BY id LIMIT 2"
).fetchall()

if len(comptes) < 2:
    print("Il faut deux comptes étudiants pour ce test.")
else:
    conducteur, passager = comptes
    hier = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")

    curseur = db.execute(
        """INSERT INTO trajets
           (conducteur_id, sens, ville, date_heure, places_total, places_restantes, prix, point_rdv)
           VALUES (?, 'aller', 'Tunis', ?, 3, 2, 4.0, 'Trajet de test')""",
        (conducteur[0], hier),
    )
    db.execute(
        "INSERT INTO reservations (trajet_id, passager_id, statut) VALUES (?, ?, 'acceptee')",
        (curseur.lastrowid, passager[0]),
    )
    db.commit()
    print("Trajet de test créé.")
    print("Conducteur :", conducteur[1])
    print("Passager   :", passager[1])

db.close()