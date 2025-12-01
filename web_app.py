import os
from datetime import datetime

import google.generativeai as genai
from flask import Flask, render_template, request, send_from_directory, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.utils import secure_filename

from main import load_config, create_cover_letter
import gmail_utils
import json
import plotly
import plotly.graph_objs as go
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import csv
import io
from flask import Response, flash



BASE_DIR = os.path.abspath(os.path.dirname(__file__))
os.chdir(BASE_DIR)

INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
TEMPLATE_FILES = [
    "lettre_template.tex",
    "lettre_template_elegant.tex",
    "lettre_template_moderne.tex",
    "lettre_template_minimaliste.tex",
]


def ensure_directories():
    """S'assure que les dossiers nécessaires existent."""
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_templates():
    """Charge tous les templates LaTeX disponibles en mémoire."""
    templates_dict = {}
    for template_file in TEMPLATE_FILES:
        template_path = os.path.join(TEMPLATES_DIR, template_file)
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                templates_dict[template_file] = f.read()
        else:
            # On ne log pas ici pour éviter la verbosité au démarrage, la CLI le fera déjà
            continue

    if not templates_dict:
        raise RuntimeError("Aucun template LaTeX n'a été trouvé dans le dossier templates/.")
    if "lettre_template.tex" not in templates_dict:
        raise RuntimeError("Le template par défaut 'lettre_template.tex' est requis.")

    return templates_dict


API_KEY, USER_CONFIG = load_config()
if not API_KEY or not USER_CONFIG:
    raise RuntimeError("Impossible de charger la configuration ou la clé API.")

genai.configure(api_key=API_KEY)

ensure_directories()
TEMPLATES_DICT = load_templates()

app = Flask(__name__, template_folder="web_templates", static_folder="web_static")
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///candidatures.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Candidature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entreprise = db.Column(db.String(100), nullable=False)
    poste = db.Column(db.String(100), nullable=False)
    statut = db.Column(db.String(50), default='En préparation') # En préparation, Envoyée, Entretien, Refus, Offre
    date_creation = db.Column(db.DateTime, default=datetime.now)
    date_maj = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    fichier_pdf = db.Column(db.String(200)) # Chemin relatif du PDF
    url_offer = db.Column(db.String(500), nullable=True) # Lien de l'offre
    notes = db.Column(db.Text, nullable=True) # Pour tes remarques perso


def render_home(
    status=None,
    message=None,
    pdf_filename=None,
    match_info=None,
    job_info=None,
    form_data=None,
):
    """Centralise le rendu de la page d'accueil."""
    return render_template(
        "index.html",
        status=status,
        message=message,
        pdf_filename=pdf_filename,
        match_info=match_info or {},
        job_info=job_info or {},
        form_data=form_data or {"job_text": "", "custom_prompt": ""},
    )


@app.route("/", methods=["GET"])
def index():
    """Affiche le formulaire principal."""
    return render_home()


@app.route("/generate", methods=["POST"])
def generate():
    """Traite le formulaire, lance la génération et renvoie le résultat."""
    job_file = request.files.get("job_file")
    job_text = request.form.get("job_text", "").strip()
    custom_prompt = request.form.get("custom_prompt", "").strip()

    form_defaults = {
        "job_text": job_text,
        "custom_prompt": custom_prompt,
    }

    announcement_content = None

    if job_file and job_file.filename:
        raw_bytes = job_file.read()
        if not raw_bytes:
            return render_home(
                status="error",
                message="Le fichier fourni est vide.",
                form_data=form_defaults,
            )
        try:
            announcement_content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return render_home(
                status="error",
                message="Impossible de lire le fichier en UTF-8. Merci de fournir un fichier texte.",
                form_data=form_defaults,
            )
    elif job_text:
        announcement_content = job_text
    else:
        return render_home(
            status="error",
            message="Veuillez fournir un fichier .txt ou coller le texte de l'annonce.",
            form_data=form_defaults,
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_name = secure_filename(job_file.filename) if job_file and job_file.filename else "texte"
    input_filename = f"web_annonce_{timestamp}_{original_name or 'annonce'}.txt"
    input_path = os.path.join(INPUT_DIR, input_filename)

    with open(input_path, "w", encoding="utf-8") as f:
        f.write(announcement_content)

    custom_prompt_value = custom_prompt if custom_prompt else None

    try:
        result = create_cover_letter(
            USER_CONFIG,
            input_path,
            TEMPLATES_DICT,
            custom_instructions=custom_prompt_value,
        )
    except Exception as exc:
        return render_home(
            status="error",
            message=f"Erreur lors de la génération : {exc}",
            form_data=form_defaults,
        )

    if result and result.get("success") and result.get("pdf_path"):
        pdf_filename = os.path.basename(result["pdf_path"])

        # Sauvegarde en base de données
        nouvelle_candidature = Candidature(
            entreprise=result['job_info'].get('entreprise', 'Inconnue'),
            poste=result['job_info'].get('poste', 'Stage'),
            fichier_pdf=pdf_filename,
            statut="En préparation"
        )
        db.session.add(nouvelle_candidature)
        db.session.commit()

        return render_home(
            status="success",
            message="Lettre générée avec succès.",
            pdf_filename=pdf_filename,
            match_info=result.get("match_info"),
            job_info=result.get("job_info"),
            form_data={"job_text": "", "custom_prompt": custom_prompt},
        )

    return render_home(
        status="error",
        message="La génération a échoué. Consultez les logs pour plus de détails.",
        match_info=result.get("match_info") if result else None,
        job_info=result.get("job_info") if result else None,
        form_data=form_defaults,
    )


@app.route("/download/<path:filename>", methods=["GET"])
def download(filename):
    """Permet de télécharger un PDF généré."""
    safe_name = os.path.basename(filename)
    file_path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(file_path):
        return render_home(
            status="error",
            message="Le fichier demandé est introuvable.",
        ), 404

    return send_from_directory(OUTPUT_DIR, safe_name, as_attachment=True)


@app.route("/dashboard")
def dashboard():
    # Récupère tout, trié par date décroissante
    candidatures = Candidature.query.order_by(Candidature.date_creation.desc()).all()
    return render_template("dashboard.html", candidatures=candidatures)


@app.route("/update_status/<int:id>", methods=["POST"])
def update_status(id):
    candidature = Candidature.query.get_or_404(id)
    candidature.statut = request.form.get("statut")
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route("/delete/<int:id>")
def delete_candidature(id):
    candidature = Candidature.query.get_or_404(id)
    db.session.delete(candidature)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route("/api/update_status/<int:id>", methods=["POST"])
def api_update_status(id):
    """API pour mettre à jour le statut via Drag & Drop (JSON)."""
    candidature = Candidature.query.get_or_404(id)
    data = request.get_json()
    new_status = data.get("statut")
    
    if new_status:
        candidature.statut = new_status
        db.session.commit()
        return {"success": True, "message": f"Statut mis à jour : {new_status}"}, 200
    return {"success": False, "message": "Statut manquant"}, 400


def generate_email_content(candidature, user_config):
    """Génère le corps du mail d'accompagnement via Gemini."""
    
    prompt = f"""
    Tu es un expert en communication professionnelle. Rédige un email d'accompagnement pour une candidature.
    
    **Contexte :**
    - Candidat : {user_config.get('nom_complet', 'Le candidat')}
    - Entreprise : {candidature.entreprise}
    - Poste : {candidature.poste}
    - Pièces jointes incluses : CV et Lettre de motivation
    - Mentionnes le fait que le candidat soit en école d'ingénieur a IMT Nord Europe (anciennement Mines de Douai)
    
    **Consignes :**
    - Le mail doit être simple, court, poli et professionnel,il doit mentionner le poste et "candidature spontanée" si c'est une candidature spontanée.
    - Il doit inviter le recruteur à consulter les pièces jointes.
    - Ton : Cordial et direct.
    - Pas d'objet (il sera ajouté séparément).
    - Signature : "Cordialement," suivi du nom du candidat.
    
    Génère UNIQUEMENT le corps du mail.
    """
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Madame, Monsieur,\n\nJe vous adresse ma candidature spontanée pour un stage au sein de {candidature.entreprise}.\nVous trouverez ci-joint mon CV et ma Lettre de motivation, détaillant mon profil et mon intérêt.\n\nJe me tiens à votre disposition pour tout échange.\n\nCordialement,\n{user_config.get('nom_complet', '')}"


@app.route("/create_draft/<int:id>", methods=["POST"])
def create_draft_route(id):
    candidature = Candidature.query.get_or_404(id)
    email_destinataire = request.form.get("email_destinataire")
    cv_file = request.files.get("cv_file")
    
    if not email_destinataire:
        return render_home(status="error", message="L'adresse email du destinataire est requise.")

    # Sauvegarde temporaire du CV si fourni
    cv_path = None
    if cv_file and cv_file.filename:
        cv_filename = secure_filename(f"cv_{id}_{cv_file.filename}")
        cv_path = os.path.join(INPUT_DIR, cv_filename)
        cv_file.save(cv_path)
    
    # Récupération du chemin de la lettre de motivation
    lm_path = None
    if candidature.fichier_pdf:
        lm_path = os.path.join(OUTPUT_DIR, candidature.fichier_pdf)
    
    # Liste des pièces jointes
    attachments = []
    if lm_path and os.path.exists(lm_path):
        attachments.append(lm_path)
    if cv_path and os.path.exists(cv_path):
        attachments.append(cv_path)
        
    # Génération du corps du mail
    email_body = generate_email_content(candidature, USER_CONFIG)
    subject = f"Candidature - {candidature.poste} - {USER_CONFIG.get('nom_complet', '')}"
    
    # Création du brouillon
    result = gmail_utils.create_draft(email_destinataire, subject, email_body, attachments)
    
    # Nettoyage du CV temporaire
    if cv_path and os.path.exists(cv_path):
        os.remove(cv_path)
        
    if result.get("success"):
        return redirect(url_for('dashboard')) # On pourrait ajouter un flash message ici si on utilisait flash
    else:
        return render_home(status="error", message=f"Erreur lors de la création du brouillon : {result.get('error')}")


@app.route("/add_manual", methods=["POST"])
def add_manual():
    """Ajoute manuellement une candidature."""
    entreprise = request.form.get("entreprise")
    poste = request.form.get("poste")
    date_str = request.form.get("date")
    url_offer = request.form.get("url_offer")
    notes = request.form.get("notes")
    pdf_file = request.files.get("pdf_file")

    if not entreprise or not poste:
        # Idéalement, utiliser flash messages ici
        return redirect(url_for('dashboard'))

    try:
        date_creation = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.now()
    except ValueError:
        date_creation = datetime.now()

    pdf_filename = None
    if pdf_file and pdf_file.filename:
        # On sauvegarde dans OUTPUT_DIR pour être cohérent avec les autres
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = secure_filename(pdf_file.filename)
        pdf_filename = f"manual_{timestamp}_{safe_name}"
        pdf_file.save(os.path.join(OUTPUT_DIR, pdf_filename))

    new_candidature = Candidature(
        entreprise=entreprise,
        poste=poste,
        statut="Envoyée", # Statut par défaut demandé
        date_creation=date_creation,
        url_offer=url_offer,
        notes=notes,
        fichier_pdf=pdf_filename
    )
    db.session.add(new_candidature)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route("/export_db")
def export_db():
    """Exporte la base de données en CSV."""
    candidatures = Candidature.query.all()
    
    # Création d'un buffer en mémoire
    output = io.StringIO()
    # Ajout du BOM pour qu'Excel reconnaisse l'UTF-8 automatiquement
    output.write('\ufeff')
    writer = csv.writer(output)
    
    # En-têtes
    headers = ["id", "entreprise", "poste", "statut", "date_creation", "url_offer", "notes"]
    writer.writerow(headers)
    
    # Données
    for c in candidatures:
        writer.writerow([
            c.id,
            c.entreprise,
            c.poste,
            c.statut,
            c.date_creation.strftime('%Y-%m-%d %H:%M:%S') if c.date_creation else "",
            c.url_offer,
            c.notes
        ])
        
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=candidatures.csv"}
    )


@app.route("/import_db", methods=["POST"])
def import_db():
    """Importe un fichier CSV pour mettre à jour la base de données."""
    if 'file' not in request.files:
        return redirect(url_for('dashboard'))
        
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('dashboard'))

    if file:
        stream = None
        # Tentative avec UTF-8 (standard)
        try:
            stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
        except UnicodeDecodeError:
            # Si échec, tentative avec cp1252 (Excel Windows par défaut)
            file.stream.seek(0)
            try:
                stream = io.StringIO(file.stream.read().decode("cp1252"), newline=None)
            except UnicodeDecodeError:
                 # Dernier recours : latin-1
                file.stream.seek(0)
                stream = io.StringIO(file.stream.read().decode("latin-1"), newline=None)

        if stream:
            try:
                csv_input = csv.reader(stream)
                
                headers = next(csv_input) # Skip headers
                # Vérification basique des headers si besoin, mais on va supposer que l'utilisateur utilise le format d'export
                
                updated_count = 0
                
                for row in csv_input:
                    # On s'attend à : id, entreprise, poste, statut, date_creation, url_offer, notes
                    if len(row) < 7:
                        continue
                        
                    c_id = row[0].strip()
                    
                    if not c_id:
                        # Création d'une nouvelle candidature
                        try:
                            date_creation = datetime.strptime(row[4], '%Y-%m-%d %H:%M:%S') if row[4] else datetime.now()
                        except ValueError:
                            date_creation = datetime.now()

                        new_candidature = Candidature(
                            entreprise=row[1],
                            poste=row[2],
                            statut=row[3],
                            date_creation=date_creation,
                            url_offer=row[5],
                            notes=row[6]
                        )
                        db.session.add(new_candidature)
                        updated_count += 1
                    else:
                        # Mise à jour existante
                        candidature = Candidature.query.get(c_id)
                        
                        if candidature:
                            candidature.entreprise = row[1]
                            candidature.poste = row[2]
                            candidature.statut = row[3]
                            # On ne touche pas à date_creation pour une mise à jour sauf si besoin
                            candidature.url_offer = row[5]
                            candidature.notes = row[6]
                            updated_count += 1
                
                db.session.commit()
            
            except Exception as e:
                print(f"Erreur lors de l'import : {e}")
            
    return redirect(url_for('dashboard'))


@app.route("/analytics")
def analytics():
    # 1. KPIs
    total_candidatures = Candidature.query.count()
    candidatures_en_cours = Candidature.query.filter(Candidature.statut.in_(['Envoyée', 'Entretien'])).count()
    entretiens_decroches = Candidature.query.filter_by(statut='Entretien').count()
    offres_decroches = Candidature.query.filter_by(statut='Offre').count()
    
    # Taux de conversion (Envoyée -> Entretien)
    # On considère comme "Envoyées" tout ce qui n'est pas "En préparation"
    candidatures_envoyees_total = Candidature.query.filter(Candidature.statut != 'En préparation').count()
    conversion_rate = 0
    if candidatures_envoyees_total > 0:
        conversion_rate = round(((entretiens_decroches + offres_decroches )/ candidatures_envoyees_total) * 100, 1)

    # 2. Graphique : Candidatures par jour (Bar Chart)
    # On récupère les dates de création
    candidatures = Candidature.query.order_by(Candidature.date_creation).all()
    dates = [c.date_creation.strftime('%Y-%m-%d') for c in candidatures]
    
    # Compte par jour
    from collections import Counter
    date_counts = Counter(dates)
    sorted_dates = sorted(date_counts.keys())
    counts = [date_counts[d] for d in sorted_dates]

    fig_daily = go.Figure(data=[
        go.Bar(x=sorted_dates, y=counts, name='Candidatures', marker_color='#2563eb')
    ])
    fig_daily.update_layout(
        title='Candidatures par Jour',
        xaxis_title='Date',
        yaxis_title='Nombre',
        template='plotly_white',
        margin=dict(l=20, r=20, t=40, b=20),
        height=300
    )
    graph_daily_json = json.dumps(fig_daily, cls=plotly.utils.PlotlyJSONEncoder)

    # 3. Graphique : Cumulatif (Line Chart)
    cumulative_counts = []
    running_total = 0
    for count in counts:
        running_total += count
        cumulative_counts.append(running_total)

    fig_cumulative = go.Figure(data=[
        go.Scatter(x=sorted_dates, y=cumulative_counts, mode='lines+markers', name='Cumul', line=dict(color='#059669', width=3))
    ])
    fig_cumulative.update_layout(
        title='Progression Cumulée',
        xaxis_title='Date',
        yaxis_title='Total Candidatures',
        template='plotly_white',
        margin=dict(l=20, r=20, t=40, b=20),
        height=300
    )
    graph_cumulative_json = json.dumps(fig_cumulative, cls=plotly.utils.PlotlyJSONEncoder)

    # 4. Entonnoir de Conversion (Funnel Chart)
    # Logique : Envoyée -> Entretien -> Offre
    # Envoyée = Tout sauf "En préparation"
    # Entretien = Entretien + Offre
    # Offre = Offre
    count_envoyees = candidatures_envoyees_total
    count_entretiens = entretiens_decroches + offres_decroches
    count_offres = offres_decroches

    fig_funnel = go.Figure(go.Funnel(
        y=["Candidatures Envoyées", "Entretiens", "Offres"],
        x=[count_envoyees, count_entretiens, count_offres],
        textinfo="value+percent initial",
        marker={"color": ["#2563eb", "#f59e0b", "#10b981"]}
    ))
    fig_funnel.update_layout(
        title='Entonnoir de Conversion',
        template='plotly_white',
        margin=dict(l=20, r=20, t=40, b=20),
        height=300
    )
    graph_funnel_json = json.dumps(fig_funnel, cls=plotly.utils.PlotlyJSONEncoder)

    # 5. Heatmap d'Activité (Par jour de la semaine)
    # On veut savoir quel jour de la semaine on postule le plus
    days_order = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    day_counts = {day: 0 for day in days_order}
    
    # Mapping weekday int (0=Monday) to name
    weekday_map = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}
    
    for c in candidatures:
        day_name = weekday_map[c.date_creation.weekday()]
        day_counts[day_name] += 1
        
    fig_heatmap = go.Figure(data=[
        go.Bar(x=days_order, y=[day_counts[d] for d in days_order], marker_color='#8b5cf6')
    ])
    fig_heatmap.update_layout(
        title='Activité par Jour de la Semaine',
        xaxis_title='Jour',
        yaxis_title='Candidatures',
        template='plotly_white',
        margin=dict(l=20, r=20, t=40, b=20),
        height=300
    )
    graph_heatmap_json = json.dumps(fig_heatmap, cls=plotly.utils.PlotlyJSONEncoder)

    # 6. Nuage de Mots (Bubble Chart)
    # Extraction des mots clés des postes
    import re
    from collections import Counter
    
    all_text = " ".join([c.poste for c in candidatures]).lower()
    # Nettoyage basique
    words = re.findall(r'\w+', all_text)
    stopwords = {'de', 'et', 'le', 'la', 'les', 'un', 'une', 'pour', 'en', 'à', 'au', 'du', 'des', 'stage', 'alternance', 'cdi', 'cdd'} 
    # On garde 'stage'/'alternance' ou pas ? L'utilisateur a dit "Basé sur les titres", souvent "Stage Data Scientist". 
    # Si on enlève 'stage', on voit mieux la techno. Gardons 'stage' dans stopwords pour voir les métiers.
    
    filtered_words = [w for w in words if w not in stopwords and len(w) > 2]
    word_counts = Counter(filtered_words)
    
    # Top 20 mots
    common_words = word_counts.most_common(20)
    
    if common_words:
        words_list, counts_list = zip(*common_words)
        # Bubble chart "hack" : scatter plot avec positions random ou spiral
        # Pour faire simple et joli : on utilise juste la taille des bulles sur un axe X catégoriel ou random
        # Mieux : Packed Bubble Chart est complexe sans librairie dédiée.
        # Alternative simple : Bar chart horizontal trié ou Treemap
        # L'utilisateur a validé "Bubble Chart". On va faire un Scatter simple avec des coordonnées pseudo-aléatoires pour disperser.
        import random
        
        # On essaie de disperser un peu pour pas que tout se chevauche
        x_vals = [random.uniform(0, 10) for _ in range(len(words_list))]
        y_vals = [random.uniform(0, 10) for _ in range(len(words_list))]
        sizes = [c * 15 for c in counts_list] # Scale factor
        colors = [f'hsl({random.randint(0, 360)}, 70%, 50%)' for _ in range(len(words_list))]
        
        fig_wordcloud = go.Figure(data=[go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers+text',
            text=words_list,
            textposition="top center",
            marker=dict(
                size=sizes,
                color=colors,
                opacity=0.6
            )
        )])
        fig_wordcloud.update_layout(
            title='Mots-clés des Postes',
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            template='plotly_white',
            margin=dict(l=20, r=20, t=40, b=20),
            height=300
        )
    else:
        fig_wordcloud = go.Figure()
        fig_wordcloud.update_layout(title="Pas assez de données pour le nuage de mots")

    graph_wordcloud_json = json.dumps(fig_wordcloud, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template(
        "analytics.html",
        total_candidatures=total_candidatures,
        candidatures_en_cours=candidatures_en_cours,
        conversion_rate=conversion_rate,
        graph_daily_json=graph_daily_json,
        graph_cumulative_json=graph_cumulative_json,
        graph_funnel_json=graph_funnel_json,
        graph_heatmap_json=graph_heatmap_json,
        graph_wordcloud_json=graph_wordcloud_json
    )



if __name__ == "__main__":
    with app.app_context():
        # Migration simple : vérifie si la colonne url_offer existe
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('candidature')]
        if 'url_offer' not in columns:
            print("Migration : Ajout de la colonne url_offer...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE candidature ADD COLUMN url_offer VARCHAR(500)"))
                conn.commit()
        
        db.create_all()
    app.run(debug=True)
