import os
from datetime import datetime

import google.generativeai as genai
from flask import Flask, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from main import load_config, create_cover_letter


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


if __name__ == "__main__":
    app.run(debug=True)
