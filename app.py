import sqlite3
from datetime import datetime
from functools import wraps
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


def connexion_requise(fonction):
    """Protège une page : il faut être connecté (BNF3)."""
    @wraps(fonction)
    def verifier(*args, **kwargs):
        if "user_id" not in session:
            flash("Veuillez vous connecter pour accéder à cette page.", "warning")
            return redirect(url_for("connexion"))
        return fonction(*args, **kwargs)
    return verifier


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


@app.route("/publier", methods=["GET", "POST"])
@connexion_requise
def publier():
    """Publication d'un trajet par un étudiant agissant comme conducteur (BF6)."""
    db = get_db()
    utilisateur = db.execute(
        "SELECT ville FROM utilisateurs WHERE id = ?", (session["user_id"],)
    ).fetchone()
    db.close()
    ville_defaut = utilisateur["ville"]  # RG9 : la ville du profil est pré-remplie

    if request.method == "POST":
        sens = request.form.get("sens", "")
        ville = request.form.get("ville", "")
        date_heure = request.form.get("date_heure", "")
        places = request.form.get("places", "")
        prix = request.form.get("prix", "")
        point_rdv = request.form.get("point_rdv", "").strip()

        # Conversion des valeurs saisies
        try:
            date_obj = datetime.strptime(date_heure, "%Y-%m-%dT%H:%M")
        except ValueError:
            date_obj = None
        try:
            places_int = int(places)
        except ValueError:
            places_int = 0
        try:
            prix_float = float(prix.replace(",", "."))
        except ValueError:
            prix_float = -1

        # Contrôles de saisie (BNF14, RG10)
        erreur = None
        if sens not in ("aller", "retour"):
            erreur = "Veuillez choisir le sens du trajet."
        elif ville not in VILLES:
            erreur = "Veuillez choisir une ville dans la liste."
        elif date_obj is None:
            erreur = "La date et l'heure sont invalides."
        elif date_obj <= datetime.now():
            erreur = "La date et l'heure doivent être dans le futur."
        elif places_int < 1 or places_int > 4:
            erreur = "Le nombre de places doit être compris entre 1 et 4."
        elif prix_float < 0:
            erreur = "Le prix doit être positif ou nul."

        if erreur is None:
            db = get_db()
            db.execute(
                """INSERT INTO trajets
                   (conducteur_id, sens, ville, date_heure, places_total,
                    places_restantes, prix, point_rdv)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (session["user_id"], sens, ville,
                 date_obj.strftime("%Y-%m-%d %H:%M"),
                 places_int, places_int, prix_float, point_rdv or None),
            )
            db.commit()
            db.close()
            flash("Votre trajet a été publié avec succès.", "success")
            return redirect(url_for("accueil"))

        flash(erreur, "danger")

    saisie = request.form if request.method == "POST" else {}
    return render_template("publier.html", villes=VILLES,
                           ville_defaut=ville_defaut, saisie=saisie)


@app.route("/rechercher")
def rechercher():
    """Recherche de trajets par ville, sens et date (BF12, BF13)."""
    ville = request.args.get("ville", "")
    sens = request.args.get("sens", "")
    date = request.args.get("date", "")
    trajets = None

    if ville and sens and date:
        maintenant = datetime.now().strftime("%Y-%m-%d %H:%M")
        db = get_db()
        trajets = db.execute(
            """SELECT t.*, u.prenom, u.nom,
                      (SELECT AVG(a.note)
                         FROM avis a
                         JOIN reservations r ON a.reservation_id = r.id
                         JOIN trajets t2 ON r.trajet_id = t2.id
                        WHERE t2.conducteur_id = u.id) AS note_moyenne
               FROM trajets t
               JOIN utilisateurs u ON u.id = t.conducteur_id
               WHERE t.statut = 'actif'
                 AND t.places_restantes > 0
                 AND u.bloque = 0
                 AND t.ville = ?
                 AND t.sens = ?
                 AND date(t.date_heure) = ?
                 AND t.date_heure > ?
               ORDER BY t.date_heure""",
            (ville, sens, date, maintenant),
        ).fetchall()
        db.close()

    return render_template("recherche.html", villes=VILLES, trajets=trajets,
                           ville=ville, sens=sens, date=date)


if __name__ == "__main__":
    app.run(debug=True)