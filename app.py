from flask import Flask, render_template, request, redirect, url_for
from database import get_db, init_db
import os

app = Flask(__name__)

with app.app_context():
    if not os.path.exists("resto.db"):
        init_db()

VILLES_CAMEROUN = [
    "Yaoundé", "Douala", "Bafoussam", "Bamenda", "Garoua",
    "Maroua", "Ngaoundéré", "Bertoua", "Ebolowa", "Buéa"
]

@app.route("/")
def index():
    db = get_db()
    nb_restos = db.execute("SELECT COUNT(*) FROM restaurant").fetchone()[0]
    nb_menus = db.execute("SELECT COUNT(*) FROM menu").fetchone()[0]
    derniers = db.execute("""
        SELECT m.nom_plat, m.prix, r.nom as resto_nom, r.ville, m.date_ajout
        FROM menu m JOIN restaurant r ON m.restaurant_id = r.id
        ORDER BY m.date_ajout DESC LIMIT 5
    """).fetchall()
    db.close()
    return render_template("index.html", nb_restos=nb_restos, nb_menus=nb_menus, derniers=derniers)



@app.route("/ajouter", methods=["GET", "POST"])
def ajouter_menu():
    db = get_db()
    if request.method == "POST":
        nom_plat = request.form["nom_plat"]
        description = request.form.get("description", "")
        # ----------- MODIFIÉ ICI -----------
        try:
            prix = int(request.form["prix"])
        except ValueError:
            prix = 0
        if prix < 0:
            prix = 0  # ou redirection avec message d'erreur
        # ---------------------------------
        categorie = request.form.get("categorie", "")
        nom_resto = request.form["nom_resto"].strip()
        ville = request.form["ville"]

        resto = db.execute("SELECT id FROM restaurant WHERE nom = ? AND ville = ?", (nom_resto, ville)).fetchone()
        if not resto:
            db.execute("INSERT INTO restaurant (nom, ville) VALUES (?, ?)", (nom_resto, ville))
            db.commit()
            resto = db.execute("SELECT id FROM restaurant WHERE nom = ? AND ville = ?", (nom_resto, ville)).fetchone()
        restaurant_id = resto["id"]

        db.execute("""
            INSERT INTO menu (nom_plat, description, prix, categorie, restaurant_id)
            VALUES (?, ?, ?, ?, ?)
        """, (nom_plat, description, prix, categorie, restaurant_id))
        db.commit()
        db.close()
        return redirect(url_for("index"))

    restaurants = db.execute("SELECT DISTINCT nom, ville FROM restaurant ORDER BY nom").fetchall()
    db.close()
    return render_template("ajouter_menu.html", restaurants=restaurants, villes=VILLES_CAMEROUN)

@app.route("/dashboard")
def dashboard():
    db = get_db()
    prix_par_ville = db.execute("""
        SELECT r.ville, ROUND(AVG(m.prix), 2) as prix_moyen, COUNT(DISTINCT r.id) as nb_restos, COUNT(m.id) as nb_menus
        FROM restaurant r JOIN menu m ON r.id = m.restaurant_id
        GROUP BY r.ville
        ORDER BY prix_moyen ASC
    """).fetchall()

    restos_moins_chers = db.execute("""
        SELECT r.nom, r.ville, ROUND(AVG(m.prix), 2) as prix_moyen, COUNT(m.id) as nb_menus
        FROM restaurant r JOIN menu m ON r.id = m.restaurant_id
        GROUP BY r.id
        ORDER BY prix_moyen ASC
        LIMIT 10
    """).fetchall()

    plats_top = db.execute("""
        SELECT nom_plat, COUNT(*) as nb_occurrences, ROUND(AVG(prix), 2) as prix_moyen
        FROM menu
        GROUP BY nom_plat
        ORDER BY nb_occurrences DESC
        LIMIT 10
    """).fetchall()

    categories = db.execute("""
        SELECT categorie, COUNT(*) as nb
        FROM menu WHERE categorie != ''
        GROUP BY categorie
    """).fetchall()
    db.close()

    labels_villes = [v["ville"] for v in prix_par_ville]
    data_villes = [v["prix_moyen"] for v in prix_par_ville]

    labels_plats = [p["nom_plat"] for p in plats_top]
    data_plats = [p["nb_occurrences"] for p in plats_top]

    labels_cat = [c["categorie"] for c in categories]
    data_cat = [c["nb"] for c in categories]

    return render_template("dashboard.html",
                           prix_par_ville=prix_par_ville,
                           restos_moins_chers=restos_moins_chers,
                           plats_top=plats_top,
                           labels_villes=labels_villes,
                           data_villes=data_villes,
                           labels_plats=labels_plats,
                           data_plats=data_plats,
                           labels_cat=labels_cat,
                           data_cat=data_cat)
@app.route("/menus")
def liste_menus():
    db = get_db()
    menus = db.execute("""
        SELECT m.id, m.nom_plat, m.prix, m.categorie, m.date_ajout,
               r.nom as resto_nom, r.ville
        FROM menu m
        JOIN restaurant r ON m.restaurant_id = r.id
        ORDER BY m.date_ajout DESC
    """).fetchall()
    db.close()
    return render_template("menus.html", menus=menus)
@app.route('/supprimer/<int:menu_id>', methods=['POST'])
def supprimer_menu(menu_id):
    db = get_db()
    db.execute("DELETE FROM menu WHERE id = ?", (menu_id,))
    db.commit()
    db.close()
    return redirect(url_for('liste_menus'))   # Redirige vers /menus après suppression

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)