import os
import json
import subprocess
import google.generativeai as genai
from dotenv import load_dotenv
import logging

# Configuration du logging pour un meilleur suivi
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- 1. CHARGEMENT DE LA CONFIGURATION ---


def load_config():
    """Charge la clé API depuis .env et la configuration utilisateur depuis config.json."""
    try:
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logging.error(
                "Clé API Gemini non trouvée. Assurez-vous qu'elle est définie dans le fichier .env"
            )
            return None, None

        with open("config.json", "r", encoding="utf-8") as f:
            user_config = json.load(f)

        return api_key, user_config
    except FileNotFoundError:
        logging.error("Le fichier 'config.json' est introuvable. Veuillez le créer.")
        return None, None
    except Exception as e:
        logging.error(f"Erreur lors du chargement de la configuration : {e}")
        return None, None


# --- 2. INTERACTION AVEC L'API GEMINI ---


def generate_letter_body(user_profile, job_ad_text):
    """Construit le prompt et interroge l'API Gemini pour générer le corps de la lettre."""

    # Construction d'un prompt détaillé pour guider le modèle
    prompt = f"""
    Tu es un expert en recrutement et un excellent rédacteur. Ta mission est de rédiger le corps d'une lettre de motivation percutante et personnalisée en français.

    **Voici les informations sur le candidat :**
    - Nom : {user_profile.get('nom_complet', 'N/A')}
    - Mon profil résumé : {user_profile.get('resume_personnel', 'N/A')}
    - Mes compétences clés : {', '.join(user_profile.get('competences_cles', []))}

    **Voici l'annonce pour laquelle le candidat postule :**
    ---
    {job_ad_text}
    ---

    **Instructions strictes :**
    - Adapte la lettre suivante à l'annonce fournie en mettant en avant les compétences et expériences du candidat qui correspondent le mieux aux exigences du poste  et au competance du candidat: Actuellement étudiant en deuxième année d'ingénieur à l'IMT Nord Europe (Anciennement 
Mines de Douai), spécialisé en conception mécanique, votre offre de stage en 
hydrodynamique navale a capté mon attention. Passionné par l'architecture navale et les défis 
hydrodynamiques, l'opportunité de rejoindre Naval Group est extrêmement motivante. 
Les missions que vous proposez, centrées sur l'amélioration des outils de calcul de tenue à la 
mer, correspondent à mon projet professionnel. L'idée de contribuer à l'optimisation des 
carènes et à la prédiction des performances de navires est une occasion unique de mettre en 
application mes connaissances théoriques. 
Ma formation en conception mécanique m'a permis de développer des compétences solides 
en simulation et en calcul par éléments finis, notamment avec des logiciels comme Abaqus. 
Mes connaissances en programmation, particulièrement en Python, alliées des bases en 
mécanique des fluides, me semblent être des atouts majeurs pour prendre en main vos outils, 
analyser des résultats et proposer des améliorations pertinentes. 
Mes expériences passées, y compris celle de moniteur de voile, m'ont appris à être rigoureux, 
organisé et à bien communiquer, des qualités essentielles pour travailler efficacement en 
équipe sur des projets d'envergure. 
Pratiquant les sports nautiques, je suis particulièrement sensible aux enjeux de la performance  
hydrodynamique. Je suis curieux, force de proposition et très motivé à l'idée de m'investir dans 

un projet qui aura une réelle valeur ajoutée pour votre équipe. 

    - Sois concis et va droit au but, en évitant les répétitions inutiles.
    - utilise des exemples concrets tirés du profil du candidat pour illustrer ses compétences et personnalise pour que l'entreprise voit que cette lettre lui est adresser specifiquement.
    - Utilise un langage professionnel simple sans etre pompeux.
    - Le ton doit être professionnel, sant tournure de phrase.
    -  **IMPORTANT** : Ne génère **UNIQUEMENT** que le corps de la lettre. N'inclus PAS "Cher Monsieur/Madame", l'objet, l'adresse, la date, ou la formule de politesse finale. Commence directement par le premier paragraphe.
    """

    try:
        logging.info("Envoi de la requête à l'API Gemini...")
        model = genai.GenerativeModel("gemini-2.5-pro")
        response = model.generate_content(prompt)
        logging.info("Réponse de l'API Gemini reçue.")
        return response.text
    except Exception as e:
        logging.error(f"Erreur lors de l'appel à l'API Gemini : {e}")
        return None


# --- 3. MANIPULATION DES FICHIERS ET COMPILATION LATEX ---


def compile_latex_to_pdf(tex_filepath):
    """Compile un fichier .tex en .pdf et nettoie les fichiers temporaires."""
    directory = os.path.dirname(tex_filepath)
    filename = os.path.basename(tex_filepath)
    base_filename = os.path.splitext(filename)[0]

    # La commande pour compiler. L'option -interaction=nonstopmode évite que le script se bloque en cas d'erreur LaTeX.
    command = [
        "pdflatex",
        "-interaction=nonstopmode",
        f"-output-directory={directory}",
        tex_filepath,
    ]

    try:
        logging.info(f"Compilation de {filename} en PDF...")
        # On lance la compilation 2 fois pour s'assurer que les références sont correctes (table des matières, etc.)
        subprocess.run(command, check=True, capture_output=True, text=True)
        subprocess.run(
            command, check=True, capture_output=True, text=True
        )  # Seconde passe
        logging.info(f"PDF généré avec succès pour {base_filename}.pdf")

        # Nettoyage des fichiers auxiliaires
        for ext in [".aux", ".log", ".tex"]:
            aux_file = os.path.join(directory, f"{base_filename}{ext}")
            if os.path.exists(aux_file):
                os.remove(aux_file)
        logging.info("Fichiers temporaires nettoyés.")
        return True

    except FileNotFoundError:
        logging.error(
            "La commande 'pdflatex' est introuvable. Assurez-vous d'avoir une distribution LaTeX installée et dans votre PATH."
        )
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"Erreur lors de la compilation LaTeX pour {filename}.")
        logging.error("--- LOG LATEX ---")
        logging.error(e.stdout)
        logging.error(e.stderr)
        logging.error("--- FIN LOG ---")
        logging.error(f"Le fichier .log complet se trouve dans le dossier {directory}")
        return False


def create_cover_letter(user_config, job_ad_path, template_content):
    """Orchestre la création d'une lettre de motivation pour une annonce."""

    # Lecture de l'annonce
    with open(job_ad_path, "r", encoding="utf-8") as f:
        job_ad_text = f.read()

    # Génération du corps de la lettre via Gemini
    letter_body = generate_letter_body(user_config, job_ad_text)
    if not letter_body:
        return

    # Remplacement des placeholders dans le template
    final_tex_content = template_content
    for key, value in user_config.items():
        if isinstance(value, list):
            value = ", ".join(value)
        final_tex_content = final_tex_content.replace(f"%%{key.upper()}%%", str(value))

    final_tex_content = final_tex_content.replace("%%CORPS_LETTRE%%", letter_body)

    # Tentative simple d'extraire le nom du poste pour le titre
    # (Peut être amélioré avec une autre requête à Gemini si besoin)
    base_name = (
        os.path.splitext(os.path.basename(job_ad_path))[0]
        .replace("_", " ")
        .replace("annonce", "")
        .strip()
    )
    final_tex_content = final_tex_content.replace("%%POSTE_VISE%%", base_name.title())
    final_tex_content = final_tex_content.replace(
        "%%NOM_ENTREPRISE%%", "Nom de l'entreprise"
    )  # À adapter si l'info est dans l'annonce
    final_tex_content = final_tex_content.replace(
        "%%ADRESSE_ENTREPRISE%%", "Adresse de l'entreprise"
    )

    # Écriture et compilation du fichier LaTeX
    output_filename_base = f"lettre_motivation_{base_name.replace(' ', '_')}"
    tex_filepath = os.path.join("output", f"{output_filename_base}.tex")

    with open(tex_filepath, "w", encoding="utf-8") as f:
        f.write(final_tex_content)

    compile_latex_to_pdf(tex_filepath)


# --- 4. POINT D'ENTRÉE PRINCIPAL ---


def main():
    """Fonction principale qui exécute le script."""
    api_key, user_config = load_config()
    if not api_key or not user_config:
        return

    genai.configure(api_key=api_key)

    # Définition des chemins
    input_dir = "input"
    output_dir = "output"
    template_path = os.path.join("templates", "lettre_template.tex")

    # Vérification de l'existence des dossiers et du template
    if not os.path.isdir(input_dir):
        logging.error(f"Le dossier '{input_dir}' est introuvable.")
        return
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
        logging.info(f"Dossier '{output_dir}' créé.")
    if not os.path.exists(template_path):
        logging.error(f"Le template LaTeX '{template_path}' est introuvable.")
        return

    # Chargement du contenu du template une seule fois
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    # Traitement de chaque annonce dans le dossier input
    job_ads = [f for f in os.listdir(input_dir) if f.endswith(".txt")]
    if not job_ads:
        logging.warning(f"Aucun fichier .txt trouvé dans le dossier '{input_dir}'.")
        return

    for job_ad_filename in job_ads:
        logging.info(f"--- Début du traitement pour : {job_ad_filename} ---")
        job_ad_path = os.path.join(input_dir, job_ad_filename)
        create_cover_letter(user_config, job_ad_path, template_content)
        logging.info(f"--- Fin du traitement pour : {job_ad_filename} ---")


if __name__ == "__main__":
    main()
