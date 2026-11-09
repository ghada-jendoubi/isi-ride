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


@app.route("/mes-trajets")
@connexion_requise
def mes_trajets():
    """Liste des trajets publiés par l'étudiant connecté (BF5)."""
    db = get_db()
    trajets = db.execute(
        "SELECT * FROM trajets WHERE conducteur_id = ? ORDER BY date_heure DESC",
        (session["user_id"],),
    ).fetchall()
    db.close()
    maintenant = datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_template("mes_trajets.html", trajets=trajets, maintenant=maintenant)


@app.route("/annuler-trajet/<int:trajet_id>", methods=["POST"])
@connexion_requise
def annuler_trajet(trajet_id):
    """Annulation d'un trajet par son conducteur (BF9, RG6)."""
    maintenant = datetime.now().strftime("%Y-%m-%d %H:%M")
    db = get_db()
    # On ne peut annuler que ses propres trajets
    trajet = db.execute(
        "SELECT * FROM trajets WHERE id = ? AND conducteur_id = ?",
        (trajet_id, session["user_id"]),
    ).fetchone()

    if trajet is None:
        flash("Trajet introuvable.", "danger")
    elif trajet["statut"] == "annule":
        flash("Ce trajet est déjà annulé.", "info")
    elif trajet["date_heure"] <= maintenant:
        flash("Un trajet déjà passé ne peut plus être annulé.", "danger")
    else:
        db.execute("UPDATE trajets SET statut = 'annule' WHERE id = ?", (trajet_id,))
        # Les réservations en cours passent à « trajet annulé » (RG7)
        db.execute(
            """UPDATE reservations SET statut = 'trajet_annule'
               WHERE trajet_id = ? AND statut IN ('en_attente', 'acceptee')""",
            (trajet_id,),
        )
        db.commit()
        flash("Le trajet a été annulé.", "success")

    db.close()
    return redirect(url_for("mes_trajets"))


@app.route("/reserver/<int:trajet_id>", methods=["POST"])
@connexion_requise
def reserver(trajet_id):
    """Demande de réservation d'une place par un passager (BF14)."""
    maintenant = datetime.now().strftime("%Y-%m-%d %H:%M")
    db = get_db()
    trajet = db.execute("SELECT * FROM trajets WHERE id = ?", (trajet_id,)).fetchone()

    if trajet is None or trajet["statut"] != "actif" or trajet["date_heure"] <= maintenant:
        flash("Ce trajet n'est plus disponible.", "danger")
    elif trajet["conducteur_id"] == session["user_id"]:
        flash("Vous ne pouvez pas réserver une place sur votre propre trajet.", "danger")  # RG1
    elif trajet["places_restantes"] < 1:
        flash("Ce trajet est complet.", "danger")
    else:
        existe = db.execute(
            "SELECT id FROM reservations WHERE trajet_id = ? AND passager_id = ?",
            (trajet_id, session["user_id"]),
        ).fetchone()
        if existe:
            flash("Vous avez déjà envoyé une demande pour ce trajet.", "warning")  # RG2
        else:
            db.execute(
                "INSERT INTO reservations (trajet_id, passager_id) VALUES (?, ?)",
                (trajet_id, session["user_id"]),
            )
            db.commit()
            flash("Votre demande a été envoyée au conducteur.", "success")

    db.close()
    return redirect(url_for("mes_reservations"))


@app.route("/mes-reservations")
@connexion_requise
def mes_reservations():
    """Liste des demandes de l'étudiant avec leur statut (BF5, BF16)."""
    db = get_db()
    reservations = db.execute(
        """SELECT r.id, r.statut, t.date_heure, t.ville, t.sens, t.prix, t.point_rdv,
                  u.prenom, u.nom, u.email, u.telephone, a.note AS note
           FROM reservations r
           JOIN trajets t ON t.id = r.trajet_id
           JOIN utilisateurs u ON u.id = t.conducteur_id
           LEFT JOIN avis a ON a.reservation_id = r.id
           WHERE r.passager_id = ?
           ORDER BY t.date_heure DESC""",
        (session["user_id"],),
    ).fetchall()
    db.close()
    maintenant = datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_template("mes_reservations.html", reservations=reservations,
                           maintenant=maintenant)


@app.route("/annuler-reservation/<int:reservation_id>", methods=["POST"])
@connexion_requise
def annuler_reservation(reservation_id):
    """Annulation d'une demande ou d'une réservation par le passager (BF15)."""
    maintenant = datetime.now().strftime("%Y-%m-%d %H:%M")
    db = get_db()
    reservation = db.execute(
        """SELECT r.*, t.date_heure FROM reservations r
           JOIN trajets t ON t.id = r.trajet_id
           WHERE r.id = ? AND r.passager_id = ?""",
        (reservation_id, session["user_id"]),
    ).fetchone()

    if reservation is None:
        flash("Réservation introuvable.", "danger")
    elif reservation["statut"] not in ("en_attente", "acceptee"):
        flash("Cette réservation ne peut plus être annulée.", "danger")
    elif reservation["date_heure"] <= maintenant:
        flash("Le trajet a déjà eu lieu : annulation impossible.", "danger")  # RG6
    else:
        db.execute("UPDATE reservations SET statut = 'annulee' WHERE id = ?", (reservation_id,))
        # Si la réservation était acceptée, la place est libérée (BF15)
        if reservation["statut"] == "acceptee":
            db.execute(
                "UPDATE trajets SET places_restantes = places_restantes + 1 WHERE id = ?",
                (reservation["trajet_id"],),
            )
        db.commit()
        flash("Votre réservation a été annulée.", "success")

    db.close()
    return redirect(url_for("mes_reservations"))


@app.route("/demandes-recues")
@connexion_requise
def demandes_recues():
    """Demandes de réservation reçues sur les trajets du conducteur (BF7, BF11)."""
    db = get_db()
    demandes = db.execute(
        """SELECT r.id, r.statut, t.date_heure, t.ville, t.sens,
                  t.places_restantes, u.prenom, u.nom, u.email, u.telephone
           FROM reservations r
           JOIN trajets t ON t.id = r.trajet_id
           JOIN utilisateurs u ON u.id = r.passager_id
           WHERE t.conducteur_id = ?
           ORDER BY t.date_heure DESC, r.id DESC""",
        (session["user_id"],),
    ).fetchall()
    db.close()
    return render_template("demandes_recues.html", demandes=demandes)


@app.route("/accepter/<int:reservation_id>", methods=["POST"])
@connexion_requise
def accepter(reservation_id):
    """Acceptation d'une demande par le conducteur (BF8, RG4, RG5)."""
    maintenant = datetime.now().strftime("%Y-%m-%d %H:%M")
    db = get_db()
    # La réservation doit concerner un trajet appartenant au conducteur connecté
    reservation = db.execute(
        """SELECT r.id, r.statut, t.id AS trajet_id, t.statut AS statut_trajet,
                  t.date_heure, t.places_restantes
           FROM reservations r
           JOIN trajets t ON t.id = r.trajet_id
           WHERE r.id = ? AND t.conducteur_id = ?""",
        (reservation_id, session["user_id"]),
    ).fetchone()

    if reservation is None:
        flash("Demande introuvable.", "danger")
    elif reservation["statut"] != "en_attente":
        flash("Cette demande a déjà été traitée.", "warning")
    elif reservation["statut_trajet"] != "actif" or reservation["date_heure"] <= maintenant:
        flash("Ce trajet n'est plus disponible.", "danger")
    elif reservation["places_restantes"] < 1:
        flash("Il ne reste plus de place sur ce trajet.", "danger")  # RG5
    else:
        db.execute("UPDATE reservations SET statut = 'acceptee' WHERE id = ?", (reservation_id,))
        db.execute(
            "UPDATE trajets SET places_restantes = places_restantes - 1 WHERE id = ?",
            (reservation["trajet_id"],),
        )
        db.commit()
        flash("Demande acceptée. Les coordonnées du passager sont affichées.", "success")

    db.close()
    return redirect(url_for("demandes_recues"))


@app.route("/refuser/<int:reservation_id>", methods=["POST"])
@connexion_requise
def refuser(reservation_id):
    """Refus d'une demande par le conducteur (BF8)."""
    db = get_db()
    reservation = db.execute(
        """SELECT r.id, r.statut
           FROM reservations r
           JOIN trajets t ON t.id = r.trajet_id
           WHERE r.id = ? AND t.conducteur_id = ?""",
        (reservation_id, session["user_id"]),
    ).fetchone()

    if reservation is None:
        flash("Demande introuvable.", "danger")
    elif reservation["statut"] != "en_attente":
        flash("Cette demande a déjà été traitée.", "warning")
    else:
        db.execute("UPDATE reservations SET statut = 'refusee' WHERE id = ?", (reservation_id,))
        db.commit()
        flash("Demande refusée.", "info")

    db.close()
    return redirect(url_for("demandes_recues"))


@app.route("/noter/<int:reservation_id>", methods=["POST"])
@connexion_requise
def noter(reservation_id):
    """Note de 1 à 5 donnée par le passager au conducteur après le trajet (BF10, RG8)."""
    maintenant = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        note = int(request.form.get("note", ""))
    except ValueError:
        note = 0

    db = get_db()
    reservation = db.execute(
        """SELECT r.id, r.statut, t.date_heure
           FROM reservations r
           JOIN trajets t ON t.id = r.trajet_id
           WHERE r.id = ? AND r.passager_id = ?""",
        (reservation_id, session["user_id"]),
    ).fetchone()
    deja_note = db.execute(
        "SELECT id FROM avis WHERE reservation_id = ?", (reservation_id,)
    ).fetchone()

    if reservation is None:
        flash("Réservation introuvable.", "danger")
    elif reservation["statut"] != "acceptee":
        flash("Vous ne pouvez noter que les trajets dont la réservation a été acceptée.", "danger")
    elif reservation["date_heure"] > maintenant:
        flash("Vous pourrez noter ce conducteur après le trajet.", "warning")
    elif deja_note:
        flash("Vous avez déjà noté ce trajet.", "warning")
    elif note < 1 or note > 5:
        flash("La note doit être comprise entre 1 et 5.", "danger")
    else:
        db.execute(
            "INSERT INTO avis (reservation_id, note) VALUES (?, ?)",
            (reservation_id, note),
        )
        db.commit()
        flash("Merci, votre note a été enregistrée.", "success")

    db.close()
    return redirect(url_for("mes_reservations"))

def admin_requis(fonction):
    """Réserve une page à l'administrateur (BF18)."""
    @wraps(fonction)
    def verifier(*args, **kwargs):
        if "user_id" not in session:
            flash("Veuillez vous connecter pour accéder à cette page.", "warning")
            return redirect(url_for("connexion"))
        if session.get("role") != "admin":
            flash("Accès réservé à l'administrateur.", "danger")
            return redirect(url_for("accueil"))
        return fonction(*args, **kwargs)
    return verifier


@app.route("/admin")
@admin_requis
def admin():
    """Tableau de bord : liste des utilisateurs et des trajets (BF18, BF19)."""
    db = get_db()
    utilisateurs = db.execute(
        "SELECT id, nom, prenom, email, ville, role, bloque FROM utilisateurs ORDER BY id"
    ).fetchall()
    trajets = db.execute(
        """SELECT t.id, t.date_heure, t.ville, t.sens, t.places_restantes, t.places_total,
                  t.prix, t.statut, u.prenom, u.nom
           FROM trajets t
           JOIN utilisateurs u ON u.id = t.conducteur_id
           ORDER BY t.date_heure DESC"""
    ).fetchall()
    db.close()
    return render_template("admin.html", utilisateurs=utilisateurs, trajets=trajets)


@app.route("/admin/bloquer/<int:utilisateur_id>", methods=["POST"])
@admin_requis
def admin_bloquer(utilisateur_id):
    """Blocage ou déblocage d'un compte étudiant (BF20)."""
    db = get_db()
    utilisateur = db.execute(
        "SELECT id, role, bloque FROM utilisateurs WHERE id = ?", (utilisateur_id,)
    ).fetchone()

    if utilisateur is None:
        flash("Utilisateur introuvable.", "danger")
    elif utilisateur["role"] == "admin":
        flash("Le compte administrateur ne peut pas être bloqué.", "danger")
    elif utilisateur["bloque"] == 0:
        db.execute("UPDATE utilisateurs SET bloque = 1 WHERE id = ?", (utilisateur_id,))
        db.commit()
        flash("Le compte a été bloqué.", "success")
    else:
        db.execute("UPDATE utilisateurs SET bloque = 0 WHERE id = ?", (utilisateur_id,))
        db.commit()
        flash("Le compte a été débloqué.", "success")

    db.close()
    return redirect(url_for("admin"))


@app.route("/admin/supprimer-trajet/<int:trajet_id>", methods=["POST"])
@admin_requis
def admin_supprimer_trajet(trajet_id):
    """Suppression définitive d'un trajet par l'administrateur (BF21)."""
    db = get_db()
    trajet = db.execute("SELECT id FROM trajets WHERE id = ?", (trajet_id,)).fetchone()

    if trajet is None:
        flash("Trajet introuvable.", "danger")
    else:
        # On supprime d'abord les avis, puis les réservations, puis le trajet
        db.execute(
            """DELETE FROM avis WHERE reservation_id IN
               (SELECT id FROM reservations WHERE trajet_id = ?)""",
            (trajet_id,),
        )
        db.execute("DELETE FROM reservations WHERE trajet_id = ?", (trajet_id,))
        db.execute("DELETE FROM trajets WHERE id = ?", (trajet_id,))
        db.commit()
        flash("Le trajet a été supprimé définitivement.", "success")

    db.close()
    return redirect(url_for("admin"))
if __name__ == "__main__":
    app.run(debug=True)