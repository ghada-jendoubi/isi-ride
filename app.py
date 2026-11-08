import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "isi-ride-cle-secrete-projet-l2-2026-x9k2m7q4"

# Domaine e-mail autorisé : étudiants de l'ISI
DOMAINE_ISI = "etudiant-isi.utm.tn"

# Liste prédéfinie des villes (RG12)
VILLES = [
    "Tunis", "Ariana", "Ben Arous", "La Manouba", "Nabeul", "Zaghouan",
    "Bizerte", "Béja", "Jendouba", "Le Kef", "Siliana", "Sousse",
    "Monastir", "Mahdia", "Sfax", "Kairouan", "Kasserine", "Sidi Bouzid",
    "Gabès", "Médenine", "Tataouine", "Gafsa", "Tozeur", "Kébili",
]


def get_db():
    """Ouvre la connexion à la base de données."""
    connexion = sqlite3.connect("database.db")
    connexion.row_factory = sqlite3.Row
    return connexion


@app.route("/")
def accueil():
    return render_template("accueil.html")


@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        prenom = request.form.get("prenom", "").strip()
        email = request.form.get("email", "").strip().lower()
        mot_de_passe = request.form.get("mot_de_passe", "")
        ville = request.form.get("ville", "")
        telephone = request.form.get("telephone", "").strip()

        # Vérifications (BF2, BNF2, BNF14)
        erreur = None
        if not nom or not prenom or not email or not mot_de_passe or not ville:
            erreur = "Tous les champs obligatoires doivent être remplis."
        elif not email.endswith("@" + DOMAINE_ISI):
            erreur = "Seules les adresses e-mail de l'ISI (@" + DOMAINE_ISI + ") sont acceptées."
        elif len(mot_de_passe) < 8:
            erreur = "Le mot de passe doit contenir au moins 8 caractères."
        elif ville not in VILLES:
            erreur = "Veuillez choisir une ville dans la liste."

        if erreur is None:
            connexion = get_db()
            existe = connexion.execute(
                "SELECT id FROM utilisateurs WHERE email = ?", (email,)
            ).fetchone()
            if existe:
                erreur = "Un compte existe déjà avec cette adresse e-mail."
            else:
                connexion.execute(
                    """INSERT INTO utilisateurs
                       (nom, prenom, email, mot_de_passe, ville, telephone)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (nom, prenom, email, generate_password_hash(mot_de_passe),
                     ville, telephone or None),
                )
                connexion.commit()
                connexion.close()
                flash("Compte créé avec succès. Vous pouvez vous connecter.", "success")
                return redirect(url_for("connexion"))
            connexion.close()

        flash(erreur, "danger")

    return render_template("inscription.html", villes=VILLES)


@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        mot_de_passe = request.form.get("mot_de_passe", "")

        db = get_db()
        utilisateur = db.execute(
            "SELECT * FROM utilisateurs WHERE email = ?", (email,)
        ).fetchone()
        db.close()

        if utilisateur is None or not check_password_hash(utilisateur["mot_de_passe"], mot_de_passe):
            flash("E-mail ou mot de passe incorrect.", "danger")
        elif utilisateur["bloque"] == 1:
            flash("Ce compte a été bloqué par l'administrateur.", "danger")  # BNF7
        else:
            session.clear()
            session["user_id"] = utilisateur["id"]
            session["prenom"] = utilisateur["prenom"]
            session["role"] = utilisateur["role"]
            flash("Bienvenue, " + utilisateur["prenom"] + " !", "success")
            return redirect(url_for("accueil"))

    return render_template("connexion.html")


@app.route("/deconnexion")
def deconnexion():
    session.clear()
    flash("Vous êtes déconnecté.", "info")
    return redirect(url_for("accueil"))


if __name__ == "__main__":
    app.run(debug=True)