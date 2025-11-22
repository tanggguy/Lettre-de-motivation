import os
import json
import subprocess
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from dotenv import load_dotenv
import logging
from datetime import datetime

# Configuration du logging pour un meilleur suivi
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- 1. CHARGEMENT DE LA CONFIGURATION ---


def load_config():
    """Charge la cle API depuis .env et la configuration utilisateur depuis config.json."""
    try:
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logging.error(
                "Cle API Gemini non trouvee. Assurez-vous qu'elle est definie dans le fichier .env"
            )
            return None, None

        with open("config.json", "r", encoding="utf-8") as f:
            user_config = json.load(f)

        return api_key, user_config
    except FileNotFoundError:
        logging.error("Le fichier 'config.json' est introuvable. Veuillez le creer.")
        return None, None
    except Exception as e:
        logging.error(f"Erreur lors du chargement de la configuration : {e}")
        return None, None


# --- 2. INTERACTION AVEC L'API GEMINI ---


def extract_job_info(job_ad_text):
    """Extrait automatiquement les informations cles de l'annonce avec Gemini."""

    prompt = f"""
    Tu es un expert en analyse d'annonces d'emploi. Analyse cette annonce et extrais les informations suivantes au format JSON strict.
    
    **Annonce :**
    ---
    {job_ad_text}
    ---
    
    **Instructions :**
    Retourne UNIQUEMENT un objet JSON valide avec cette structure exacte (sans markdown, sans commentaires) :
    {{
        "entreprise": "nom de l'entreprise",
        "poste": "titre exact du poste sans "H/F et resume si trop long, 6 mot max; le mot 'stage' doit etre inclus si c'est un stage"",
        "type_contrat": "CDI/CDD/Stage/Alternance/etc",
        "duree": "duree si applicable (ex: 6 mois) sinon null",
        "localisation": "ville et/ou region",
        "date_debut": "date de debut souhaitee si mentionnee, sinon null",
        "competences_requises": ["competence1", "competence2", "competence3"],
        "outils_technologies": ["outil1", "outil2"],
        "niveau_etudes": "niveau requis (ex: Bac+5, Ingenieur)",
        "langues": {{"francais": "niveau", "anglais": "niveau"}},
        "salaire": "si mentionne, sinon null",
        "avantages": ["avantage1", "avantage2"],
        "missions_principales": ["mission1", "mission2", "mission3"],
        "secteur": "secteur d'activite de l'entreprise",
        "valeurs_entreprise": ["valeur1", "valeur2"],
        "ton_annonce": "formel/moderne/startup/etc"
    }}
    
    Si une information n'est pas disponible, utilise null ou une liste vide selon le type.
    """

    try:
        logging.info(" Extraction des informations de l'annonce...")
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)

        # Nettoyer la reponse pour extraire uniquement le JSON
        text = response.text.strip()
        if hasattr(response, "candidates"):
            for candidate in response.candidates:
                print(f"Finish reason: {candidate.finish_reason}")
                print(f"Safety ratings: {candidate.safety_ratings}")

        # Enlever les balises markdown si presentes
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        job_info = json.loads(text)

        logging.info(f" Informations extraites :")
        logging.info(f"   - Entreprise : {job_info.get('entreprise', 'N/A')}")
        logging.info(f"   - Poste : {job_info.get('poste', 'N/A')}")
        logging.info(f"   - Type : {job_info.get('type_contrat', 'N/A')}")
        logging.info(f"   - Localisation : {job_info.get('localisation', 'N/A')}")
        logging.info(
            f"   - Competences requises : {', '.join(job_info.get('competences_requises', [])[:3])}..."
        )

        return job_info

    except json.JSONDecodeError as e:
        logging.error(f" Erreur de parsing JSON : {e}")
        logging.error(f"Reponse brute : {response.text[:500]}")
        return None
    except Exception as e:
        logging.error(f" Erreur lors de l'extraction : {e}")
        return None


def calculate_match_score(user_profile, job_info):
    """Calcule un score de compatibilite entre le profil et l'annonce."""
    if not job_info:
        return None

    score = 0
    details = []

    user_skills = set([s.lower() for s in user_profile.get("competences_cles", [])])
    required_skills = set([s.lower() for s in job_info.get("competences_requises", [])])
    required_tools = set([s.lower() for s in job_info.get("outils_technologies", [])])

    # Matching des competences
    matching_skills = user_skills.intersection(required_skills)
    matching_tools = user_skills.intersection(required_tools)

    if matching_skills:
        score += len(matching_skills) * 20
        details.append(
            f" {len(matching_skills)} competences correspondent : {', '.join(matching_skills)}"
        )

    if matching_tools:
        score += len(matching_tools) * 15
        details.append(f" {len(matching_tools)} outils  : {', '.join(matching_tools)}")

    # Bonus si toutes les competences requises sont couvertes
    if required_skills and required_skills.issubset(user_skills):
        score += 20
        details.append(" Toutes les competences requises sont maÃ®trisees !")

    score = min(score, 100)  # Plafonner Ã  100

    return {
        "score": score,
        "details": details,
        "matching_skills": list(matching_skills),
        "matching_tools": list(matching_tools),
        "missing_skills": list(required_skills - user_skills),
    }


def generate_letter_body(
    user_profile, job_ad_text, job_info=None, custom_instructions=None
):
    """Construit le prompt et interroge l'API Gemini pour générer le corps de la lettre."""

    # Enrichir le prompt avec les informations extraites
    context_info = ""
    if job_info:
        context_info = f"""
    **Informations extraites de l'annonce :**
    - Entreprise : {job_info.get('entreprise', 'N/A')}
    - Poste : {job_info.get('poste', 'N/A')}
    - Type de contrat : {job_info.get('type_contrat', 'N/A')}
    - Localisation : {job_info.get('localisation', 'N/A')}
    - Secteur : {job_info.get('secteur', 'N/A')}
    - Missions principales : {', '.join(job_info.get('missions_principales', [])[:5])}
    - Compétences clés recherchées : {', '.join(job_info.get('competences_requises', [])[:5])}
    - Outils/Technologies : {', '.join(job_info.get('outils_technologies', []))}
    - Valeurs de l'entreprise : {', '.join(job_info.get('valeurs_entreprise', []))}
    - Ton de l'annonce : {job_info.get('ton_annonce', 'professionnel')}
    """

    instructions_block = ""
    if custom_instructions:
        instructions_block = f"""
    **Instructions supplémentaires à respecter absolument :**
    {custom_instructions}
    """

    # Construction d'un prompt détaillé pour guider le modèle
    prompt = f"""
    Tu es un expert en recrutement et un excellent rédacteur. Ta mission est de rédiger le corps d'une lettre de motivation percutante et personnalisée en français.

    **Voici les informations sur le candidat :**
    - Nom : {user_profile.get('nom_complet', 'N/A')}
    - Mon profil résumé : {user_profile.get('resume_personnel', 'N/A')}
    - Mes compétences clés : {', '.join(user_profile.get('competences_cles', []))}

    {context_info}
    {instructions_block}

    **Voici l'annonce complète pour contexte :**
    ---
    {job_ad_text}
    ---

    CONSIGNES STRICTES :

FORMAT :
- Génère UNIQUEMENT le corps de la lettre (3 paragraphes maximum)
- N'inclus PAS : formule d'appel, objet, adresse, date, formule de politesse finale
- Commence directement par le premier paragraphe
- Maximum 2500 caractères espaces compris

STRUCTURE OBLIGATOIRE :

① - ACCROCHE (3-4 lignes)
Indique la formation actuelle et précise (anciennement Mines de Douai) à la première mention d'IMT Nord Europe, explique pourquoi cette entreprise/ce poste précisément en citant des éléments concrets de l'annonce. Fais le lien avec une expérience pertinente du candidat si pertinent.

② - COMPÉTENCES TECHNIQUES (5-6 lignes)
Mets en avant les compétences techniques clés si pertinents (CAO, simulations, programmation), les expériences professionnelles pertinentes, et les projets académiques en lien direct avec les missions décrites dans l'annonce. Sois précis et factuel.

③ - APPORT MUTUEL (4-5 lignes)
Explique ce que le candidat apporte concrètement à l'entreprise et ce qu'il souhaite développer pendant ce stage. Termine par une phrase d'ouverture vers un entretien sans formule de politesse.

TON, À RESPECTER ABSOLUMENT :
- Courant, simple et direct
- Évite le jargon pompeux et les formules convenues ("je me permets de", "vivement intéressé par", "immédiatement retenu mon attention", "opportunité unique", "défi technique","je souhaite mettre ma rigueur technique au service d'un enjeu stratégique", "complexes problématiques","correspondent précisément", etc.)
- Privilégie les verbes d'action, phrases courtes (maximum 2 lignes par phrase) et les faits concrets : "correspond à", "m'intéresse", "je peux apporter"
- Naturel et authentique
- Utilise la forme active : "Je peux apporter" plutôt que "Je souhaite apporter"


RÈGLES IMPORTANTES :
- Personnalise systématiquement en citant des éléments précis de l'annonce
- Ne répète pas le CV, apporte de la valeur ajoutée
- Montre une réelle connaissance de l'entreprise et du secteur
- Sois concis : chaque mot doit compter
- Pour citer le nom du poste, utilise le mot stage si c'est un stage
Génère maintenant la lettre de motivation.
"""
    try:
        logging.info("Génération du corps de la lettre...")
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            generation_config={
                "temperature": 0.6,
                "top_p": 0.9,
                "top_k": 64,
            },
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            },
        )
        response = model.generate_content(prompt)
        if hasattr(response, "candidates"):
            for candidate in response.candidates:
                print(f"Finish reason: {candidate.finish_reason}")
                print(f"Safety ratings: {candidate.safety_ratings}")

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

    # La commande pour compiler. L'option -interaction=nonstopmode evite que le script se bloque en cas d'erreur LaTeX.
    command = [
        "pdflatex",
        "-interaction=nonstopmode",
        f"-output-directory={directory}",
        tex_filepath,
    ]

    try:
        logging.info(f" Compilation de {filename} en PDF...")
        # On lance la compilation 2 fois pour s'assurer que les references sont correctes (table des matiÃ¨res, etc.)
        subprocess.run(command, check=True, capture_output=True, text=True)
        subprocess.run(
            command, check=True, capture_output=True, text=True
        )  # Seconde passe
        logging.info(f" PDF  avec succes : {base_filename}.pdf")

        # Nettoyage des fichiers auxiliaires
        for ext in [".aux", ".log", ".tex"]:
            aux_file = os.path.join(directory, f"{base_filename}{ext}")
            if os.path.exists(aux_file):
                os.remove(aux_file)
        logging.info(" Fichiers temporaires nettoyes.")
        return True

    except FileNotFoundError:
        logging.error(
            " La commande 'pdflatex' est introuvable. Assurez-vous d'avoir une distribution LaTeX installee et dans votre PATH."
        )
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f" Erreur lors de la compilation LaTeX pour {filename}.")
        logging.error("--- LOG LATEX ---")
        logging.error(e.stdout)
        logging.error(e.stderr)
        logging.error("--- FIN LOG ---")
        logging.error(f"Le fichier .log complet se trouve dans le dossier {directory}")
        return False


def save_job_metadata(job_info, match_info, output_path):
    """Sauvegarde  de l'annonce et du matching."""
    if not job_info:
        return

    metadata = {
        "job_info": job_info,
        "match_score": match_info,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    metadata_path = output_path.replace(".pdf", "_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    logging.info(f"  sauvegardees : {os.path.basename(metadata_path)}")


def select_template_by_tone(job_info):
    """
    Selectionne automatiquement le meilleur template selon le ton de l'annonce
    et le secteur de l'entreprise.
    """
    if not job_info:
        return "lettre_template.tex"  # Template par defaut

    ton = job_info.get("ton_annonce", "").lower()
    secteur = job_info.get("secteur", "").lower()
    entreprise = job_info.get("entreprise", "").lower()

    # RÃ¨gles de selection
    # Version 2 (Moderne) pour startups, tech, innovation
    if any(
        keyword in ton for keyword in ["startup", "moderne", "innovant", "dynamique"]
    ):
        return "lettre_template_moderne.tex"

    if any(
        keyword in secteur for keyword in ["tech", "digital", "innovation", "software"]
    ):
        return "lettre_template_moderne.tex"

    # Version 3 (Minimaliste) pour conseil, finance, luxe
    if any(keyword in secteur for keyword in ["conseil", "finance", "audit", "banque"]):
        return "lettre_template_moderne.tex"

    if any(keyword in ton for keyword in ["formel", "sobre", "classique", "premium"]):
        return "lettre_template_moderne.tex"

    # Version 1 (Ã‰legante) pour industrie, grandes entreprises (defaut)
    return "lettre_template_moderne.tex"


def create_cover_letter(
    user_config, job_ad_path, templates_dict, custom_instructions=None
):
    """Orchestre la création d'une lettre de motivation pour une annonce."""

    with open(job_ad_path, "r", encoding="utf-8") as f:
        job_ad_text = f.read()

    job_info = extract_job_info(job_ad_text)
    template_name = select_template_by_tone(job_info)
    template_content = templates_dict.get(
        template_name, templates_dict["lettre_template.tex"]
    )

    logging.info(f"Template sélectionné : {template_name}")

    match_info = None
    if job_info:
        match_info = calculate_match_score(user_config, job_info)
        if match_info:
            logging.info(f"Score de compatibilité : {match_info['score']}/100")
            for detail in match_info["details"]:
                logging.info(f"   {detail}")
            if match_info["missing_skills"]:
                logging.warning(
                    "Compétences manquantes : "
                    + ", ".join(match_info["missing_skills"])
                )

    result = {
        "success": False,
        "pdf_path": None,
        "tex_path": None,
        "job_info": job_info,
        "match_info": match_info,
    }

    letter_body = generate_letter_body(
        user_config,
        job_ad_text,
        job_info,
        custom_instructions=custom_instructions,
    )
    if not letter_body:
        return result

    final_tex_content = template_content
    for key, value in user_config.items():
        if isinstance(value, list):
            value = ", ".join(value)
        final_tex_content = final_tex_content.replace(f"%%{key.upper()}%%", str(value))

    final_tex_content = final_tex_content.replace("%%CORPS_LETTRE%%", letter_body)

    if job_info:
        poste = job_info.get("poste", "Candidature")
        entreprise = job_info.get("entreprise", "Nom de l'entreprise")
        final_tex_content = final_tex_content.replace("%%POSTE_VISE%%", poste)
        final_tex_content = final_tex_content.replace("%%NOM_ENTREPRISE%%", entreprise)

        poste_clean = (
            poste.replace("-", "")
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
        )
        entreprise_clean = entreprise.replace(" ", "_")
        output_filename_base = f"lettre_motivation_{entreprise_clean}_{poste_clean}"
    else:
        base_name = (
            os.path.splitext(os.path.basename(job_ad_path))[0]
            .replace("_", " ")
            .replace("annonce", "")
            .strip()
        )
        final_tex_content = final_tex_content.replace(
            "%%POSTE_VISE%%", base_name.title()
        )
        final_tex_content = final_tex_content.replace(
            "%%NOM_ENTREPRISE%%", "Nom de l'entreprise"
        )
        output_filename_base = f"lettre_motivation_{base_name.replace(' ', '_')}"

    final_tex_content = final_tex_content.replace(
        "%%ADRESSE_ENTREPRISE%%", "Adresse de l'entreprise"
    )

    tex_filepath = os.path.join("output", f"{output_filename_base}.tex")
    pdf_filepath = os.path.join("output", f"{output_filename_base}.pdf")

    with open(tex_filepath, "w", encoding="utf-8") as f:
        f.write(final_tex_content)

    success = compile_latex_to_pdf(tex_filepath)
    json_export = user_config.get("json_export", False)
    if success and job_info and json_export:
        save_job_metadata(job_info, match_info, pdf_filepath)

    result.update(
        {
            "success": bool(success),
            "pdf_path": pdf_filepath if success else None,
            "tex_path": tex_filepath,
            "job_info": job_info,
            "match_info": match_info,
        }
    )

    return result


# --- 4. POINT D'ENTRÃ‰E PRINCIPAL ---


def main():
    """Fonction principale qui exécute le script."""
    api_key, user_config = load_config()
    if not api_key or not user_config:
        return

    genai.configure(api_key=api_key)

    input_dir = "input"
    output_dir = "output"
    templates_dir = "templates"

    if not os.path.isdir(input_dir):
        logging.error(f"Le dossier '{input_dir}' est introuvable.")
        return
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
        logging.info(f"Dossier '{output_dir}' créé.")

    templates_dict = {}
    template_files = [
        "lettre_template.tex",
        "lettre_template_elegant.tex",
        "lettre_template_moderne.tex",
        "lettre_template_minimaliste.tex",
    ]

    for template_file in template_files:
        template_path = os.path.join(templates_dir, template_file)
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                templates_dict[template_file] = f.read()
            logging.info(f"Template chargé : {template_file}")
        else:
            logging.warning(f"Template non trouvé : {template_file}")

    if not templates_dict:
        logging.error("Aucun template disponible !")
        return

    job_ads = [f for f in os.listdir(input_dir) if f.endswith(".txt")]
    if not job_ads:
        logging.warning(f"Aucun fichier .txt trouvé dans le dossier '{input_dir}'.")
        return

    logging.info(f"\n{'='*60}")
    logging.info(f"Génération de {len(job_ads)} lettre(s) de motivation")
    logging.info(f"{'='*60}\n")

    for i, job_ad_filename in enumerate(job_ads, 1):
        logging.info(f"\n{'-'*60}")
        logging.info(f"[{i}/{len(job_ads)}] Traitement : {job_ad_filename}")
        logging.info(f"{'-'*60}")
        job_ad_path = os.path.join(input_dir, job_ad_filename)
        result = create_cover_letter(
            user_config,
            job_ad_path,
            templates_dict,
            custom_instructions=None,
        )
        if result and result.get("success") and result.get("pdf_path"):
            logging.info(f"Lettre générée : {result['pdf_path']}")
        else:
            logging.warning("Échec de génération pour cette annonce.")
        logging.info(f"{'-'*60}\n")

    logging.info(f"\n{'='*60}")
    logging.info(f"Génération terminée ! Consultez le dossier '{output_dir}'")
    logging.info(f"{'='*60}\n")


if __name__ == "__main__":
    main()
