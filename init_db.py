import sqlite3
from werkzeug.security import generate_password_hash

connexion = sqlite3.connect("database.db")

with open("schema.sql", encoding="utf-8") as fichier:
    connexion.executescript(fichier.read())

admin_existe = connexion.execute(
    "SELECT id FROM utilisateurs WHERE role = 'admin'"
).fetchone()

if admin_existe is None:
    connexion.execute(
        """INSERT INTO utilisateurs
           (nom, prenom, email, mot_de_passe, ville, role)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("Admin", "ISI Ride", "admin@isi.local",
         generate_password_hash("admin12345"), "Tunis", "admin"),
    )
    print("Compte administrateur créé.")

connexion.commit()
connexion.close()
print("Base de données prête.")