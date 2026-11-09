import os
import sys
import sqlite3
from datetime import datetime, timedelta

import pytest
from werkzeug.security import generate_password_hash

# Permet d'importer app.py depuis le dossier tests
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from app import app, DOMAINE_ISI

EMAIL_CONDUCTEUR = "conducteur@" + DOMAINE_ISI
EMAIL_PASSAGER = "passager@" + DOMAINE_ISI


# ---------------------------------------------------------------
# Outils communs aux tests
# ---------------------------------------------------------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    """Crée un client de test avec une base de données temporaire vide."""
    monkeypatch.chdir(tmp_path)
    connexion = sqlite3.connect("database.db")
    with open(os.path.join(RACINE, "schema.sql"), encoding="utf-8") as fichier:
        connexion.executescript(fichier.read())
    connexion.close()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def texte(reponse):
    """Retourne le contenu de la page sous forme de texte."""
    return reponse.get_data(as_text=True)


def lire(requete, params=()):
    """Lit des données dans la base de test."""
    c = sqlite3.connect("database.db")
    resultat = c.execute(requete, params).fetchall()
    c.close()
    return resultat


def inscrire(client, email, mot_de_passe="motdepasse1", ville="Tunis"):
    return client.post("/inscription", data={
        "nom": "Test", "prenom": "Etu", "email": email,
        "mot_de_passe": mot_de_passe, "ville": ville, "telephone": "",
    }, follow_redirects=True)


def connecter(client, email, mot_de_passe="motdepasse1"):
    return client.post("/connexion", data={
        "email": email, "mot_de_passe": mot_de_passe,
    }, follow_redirects=True)


def date_future(jours=3):
    return (datetime.now() + timedelta(days=jours)).strftime("%Y-%m-%dT%H:%M")


def publier_trajet(client, places="3", prix="5", date_heure=None):
    return client.post("/publier", data={
        "sens": "aller", "ville": "Tunis",
        "date_heure": date_heure or date_future(),
        "places": places, "prix": prix, "point_rdv": "Entree ISI",
    }, follow_redirects=True)


def scenario_reservation(client):
    """Le conducteur publie un trajet, puis un passager envoie une demande."""
    inscrire(client, EMAIL_CONDUCTEUR)
    connecter(client, EMAIL_CONDUCTEUR)
    publier_trajet(client)
    passager = app.test_client()
    inscrire(passager, EMAIL_PASSAGER)
    connecter(passager, EMAIL_PASSAGER)
    reponse = passager.post("/reserver/1", follow_redirects=True)
    return passager, reponse


# ---------------------------------------------------------------
# Inscription et connexion (BF1, BF2, BF3, BNF1, BNF2)
# ---------------------------------------------------------------

def test_inscription_valide(client):
    reponse = inscrire(client, EMAIL_CONDUCTEUR)
    assert "Compte créé avec succès" in texte(reponse)


def test_mot_de_passe_est_hache(client):
    inscrire(client, EMAIL_CONDUCTEUR, mot_de_passe="motdepasse1")
    stocke = lire("SELECT mot_de_passe FROM utilisateurs WHERE email = ?",
                  (EMAIL_CONDUCTEUR,))[0][0]
    assert stocke != "motdepasse1"
    assert len(stocke) > 20


def test_inscription_domaine_refuse(client):
    reponse = inscrire(client, "test@gmail.com")
    assert "Seules les adresses e-mail" in texte(reponse)
    assert lire("SELECT id FROM utilisateurs") == []


def test_inscription_mot_de_passe_trop_court(client):
    reponse = inscrire(client, EMAIL_CONDUCTEUR, mot_de_passe="abc")
    assert "au moins 8 caractères" in texte(reponse)


def test_inscription_email_deja_utilise(client):
    inscrire(client, EMAIL_CONDUCTEUR)
    reponse = inscrire(client, EMAIL_CONDUCTEUR)
    assert "existe déjà" in texte(reponse)


def test_connexion_valide(client):
    inscrire(client, EMAIL_CONDUCTEUR)
    reponse = connecter(client, EMAIL_CONDUCTEUR)
    assert "Bienvenue, Etu" in texte(reponse)


def test_connexion_mauvais_mot_de_passe(client):
    inscrire(client, EMAIL_CONDUCTEUR)
    reponse = connecter(client, EMAIL_CONDUCTEUR, mot_de_passe="mauvais-mot-de-passe")
    assert "incorrect" in texte(reponse)


def test_injection_sql_refusee(client):
    """Sécurité (BNF4) : une injection SQL ne doit pas permettre de se connecter."""
    inscrire(client, EMAIL_CONDUCTEUR)
    reponse = client.post("/connexion", data={
        "email": "' OR '1'='1", "mot_de_passe": "' OR '1'='1",
    }, follow_redirects=True)
    assert "incorrect" in texte(reponse)
    assert "Bienvenue" not in texte(reponse)


def test_page_protegee_sans_connexion(client):
    """Sécurité (BNF3) : publier un trajet exige d'être connecté."""
    reponse = client.get("/publier", follow_redirects=True)
    assert "Veuillez vous connecter" in texte(reponse)


# ---------------------------------------------------------------
# Publication et recherche de trajets (BF6, BF12, BF13, RG10)
# ---------------------------------------------------------------

def test_publier_trajet_valide(client):
    inscrire(client, EMAIL_CONDUCTEUR)
    connecter(client, EMAIL_CONDUCTEUR)
    reponse = publier_trajet(client)
    assert "publié avec succès" in texte(reponse)
    assert len(lire("SELECT id FROM trajets")) == 1


def test_publier_date_passee_refusee(client):
    inscrire(client, EMAIL_CONDUCTEUR)
    connecter(client, EMAIL_CONDUCTEUR)
    hier = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    reponse = publier_trajet(client, date_heure=hier)
    assert "dans le futur" in texte(reponse)
    assert lire("SELECT id FROM trajets") == []


def test_publier_cinq_places_refuse(client):
    inscrire(client, EMAIL_CONDUCTEUR)
    connecter(client, EMAIL_CONDUCTEUR)
    reponse = publier_trajet(client, places="5")
    assert "compris entre 1 et 4" in texte(reponse)


def test_publier_prix_negatif_refuse(client):
    inscrire(client, EMAIL_CONDUCTEUR)
    connecter(client, EMAIL_CONDUCTEUR)
    reponse = publier_trajet(client, prix="-3")
    assert "positif ou nul" in texte(reponse)


def test_recherche_trouve_le_trajet(client):
    inscrire(client, EMAIL_CONDUCTEUR)
    connecter(client, EMAIL_CONDUCTEUR)
    publier_trajet(client)
    jour = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    reponse = client.get("/rechercher?ville=Tunis&sens=aller&date=" + jour)
    assert "Entree ISI" in texte(reponse)


# ---------------------------------------------------------------
# Réservations (BF14, BF15, BF8, RG1, RG2, RG4, BNF6)
# ---------------------------------------------------------------

def test_reserver_propre_trajet_refuse(client):
    inscrire(client, EMAIL_CONDUCTEUR)
    connecter(client, EMAIL_CONDUCTEUR)
    publier_trajet(client)
    reponse = client.post("/reserver/1", follow_redirects=True)
    assert "votre propre trajet" in texte(reponse)


def test_demande_puis_double_demande(client):
    passager, reponse = scenario_reservation(client)
    assert "demande a été envoyée" in texte(reponse)
    reponse = passager.post("/reserver/1", follow_redirects=True)
    assert "déjà envoyé" in texte(reponse)


def test_acceptation_diminue_les_places_et_annulation_les_libere(client):
    passager, _ = scenario_reservation(client)
    # Une demande en attente ne retire pas de place
    assert lire("SELECT places_restantes FROM trajets WHERE id = 1")[0][0] == 3
    reponse = client.post("/accepter/1", follow_redirects=True)
    assert "Demande acceptée" in texte(reponse)
    assert lire("SELECT places_restantes FROM trajets WHERE id = 1")[0][0] == 2
    passager.post("/annuler-reservation/1", follow_redirects=True)
    assert lire("SELECT places_restantes FROM trajets WHERE id = 1")[0][0] == 3


def test_contact_visible_seulement_apres_acceptation(client):
    passager, _ = scenario_reservation(client)
    avant = texte(passager.get("/mes-reservations"))
    assert EMAIL_CONDUCTEUR not in avant
    client.post("/accepter/1")
    apres = texte(passager.get("/mes-reservations"))
    assert EMAIL_CONDUCTEUR in apres


def test_annulation_trajet_met_a_jour_les_reservations(client):
    passager, _ = scenario_reservation(client)
    client.post("/annuler-trajet/1", follow_redirects=True)
    statut = lire("SELECT statut FROM reservations WHERE id = 1")[0][0]
    assert statut == "trajet_annule"


# ---------------------------------------------------------------
# Avis (BF10, RG8)
# ---------------------------------------------------------------

def test_note_apres_le_trajet_une_seule_fois(client):
    passager, _ = scenario_reservation(client)
    client.post("/accepter/1")
    # On recule la date du trajet dans le passé
    hier = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    c = sqlite3.connect("database.db")
    c.execute("UPDATE trajets SET date_heure = ? WHERE id = 1", (hier,))
    c.commit()
    c.close()
    reponse = passager.post("/noter/1", data={"note": "5"}, follow_redirects=True)
    assert "Merci" in texte(reponse)
    reponse = passager.post("/noter/1", data={"note": "4"}, follow_redirects=True)
    assert "déjà noté" in texte(reponse)
    assert lire("SELECT note FROM avis")[0][0] == 5


# ---------------------------------------------------------------
# Administration (BF18, BF20, BNF3, BNF7)
# ---------------------------------------------------------------

def test_admin_interdit_a_un_etudiant(client):
    inscrire(client, EMAIL_CONDUCTEUR)
    connecter(client, EMAIL_CONDUCTEUR)
    reponse = client.get("/admin", follow_redirects=True)
    assert "Accès réservé" in texte(reponse)


def test_blocage_d_un_compte(client):
    inscrire(client, EMAIL_CONDUCTEUR)
    identifiant = lire("SELECT id FROM utilisateurs WHERE email = ?",
                       (EMAIL_CONDUCTEUR,))[0][0]
    # Création d'un compte administrateur dans la base de test
    c = sqlite3.connect("database.db")
    c.execute(
        """INSERT INTO utilisateurs (nom, prenom, email, mot_de_passe, ville, role)
           VALUES ('Admin', 'Test', 'admin@isi.local', ?, 'Tunis', 'admin')""",
        (generate_password_hash("admin12345"),),
    )
    c.commit()
    c.close()
    admin = app.test_client()
    connecter(admin, "admin@isi.local", "admin12345")
    admin.post("/admin/bloquer/" + str(identifiant), follow_redirects=True)
    reponse = connecter(client, EMAIL_CONDUCTEUR)
    assert "Ce compte a été bloqué" in texte(reponse)