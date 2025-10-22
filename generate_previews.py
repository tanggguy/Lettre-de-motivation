import os
import subprocess
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def compile_latex_to_pdf(tex_filepath):
    """Compile un fichier .tex en .pdf et nettoie les fichiers temporaires."""
    directory = os.path.dirname(tex_filepath)
    filename = os.path.basename(tex_filepath)
    base_filename = os.path.splitext(filename)[0]

    command = [
        "pdflatex",
        "-interaction=nonstopmode",
        f"-output-directory={directory}",
        tex_filepath,
    ]

    try:
        logging.info(f"📄 Compilation de {filename} en PDF...")
        subprocess.run(command, check=True, capture_output=True, text=True)
        subprocess.run(command, check=True, capture_output=True, text=True)
        logging.info(f"✅ PDF généré avec succès : {base_filename}.pdf")

        # Nettoyage des fichiers auxiliaires
        for ext in [".aux", ".log", ".tex"]:
            aux_file = os.path.join(directory, f"{base_filename}{ext}")
            if os.path.exists(aux_file):
                os.remove(aux_file)
        logging.info("🧹 Fichiers temporaires nettoyés.")
        return True

    except FileNotFoundError:
        logging.error(
            "❌ La commande 'pdflatex' est introuvable. Assurez-vous d'avoir une distribution LaTeX installée."
        )
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Erreur lors de la compilation LaTeX pour {filename}.")
        logging.error("--- LOG LATEX ---")
        logging.error(e.stdout)
        logging.error(e.stderr)
        logging.error("--- FIN LOG ---")
        return False


def generate_preview_pdf(template_path, output_dir="output"):
    """
    Génère un PDF de prévisualisation d'un template avec des variables vides.

    Args:
        template_path: Chemin vers le fichier template .tex
        output_dir: Dossier de sortie pour les PDF
    """
    # Créer le dossier de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)

    # Lire le contenu du template
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    # Dictionnaire des variables à remplacer
    variables = {
        "NOM_COMPLET": "Tanguy SAILLY",
        "ADRESSE": "Adresse complète",
        "CODE_POSTAL": "Code postal Ville",
        "EMAIL": "email@example.com",
        "TELEPHONE": "06 XX XX XX XX",
        "POSTE_VISE": "Intitulé du poste",
        "NOM_ENTREPRISE": "Nom de l'entreprise",
        "ADRESSE_ENTREPRISE": "Adresse de l'entreprise",
        "CORPS_LETTRE": """ Les missions que vous décrivffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff fffffffffffffff fffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff vffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff ffffffffffffffffffffffffff fjhdgzdfgzdfSfdscaszx ffffffffffez, centrées sur la conception et le développement de solutions d’ingé nierie mécanique, la réalisation de calculs et d’analyses de conception, ainsi que la participation au développement de simulateurs et d’applications 3D, sont en parfaite adéquation avec mon projet professionnel. L’opportunité de contribuer à des projets exigeant une qualité d’exécution sans faille, de l’innovation et une approche pragmatique, valeurs que SOGECLAIR met en avant, me motive particulièrement. Ma formation m’a permis d’acquérir de solides compétences en ingénierie mécanique et design, notamment en modélisation 3D, simulation et calcul technique. Je maîtrise des logiciels comme SolidWorks, Catia et Abaqus pour la modélisation de pièces et assemblages, la mise en plan, la simulation et le calcul par éléments finis avec RDM7. Mes solides connaissances des matériaux et des procédés de fabrication constituent également un atout. Par ailleurs, mon expérience d’automaticien stagiaire chez Groupe API, où j’ai œuvré à l’optimisation informatique et au développement de logiques de contrôle (Grafcet), combinée à mes compétences en Python et Java, démontre ma capacité à appréhender des environnements techniques complexes et à participer à des développements fonctionnels, essentiels dans le domaine du Digital Engineering. Je suis également doté des qualités transversales essentielles à la réussite des projets d’envergure. Mon stage d’automaticien m’a appris l’analyse fonctionnelle, l’autonomie et la force de proposi tion, tandis que mes étés comme moniteur de voile au Centre nautique d’Erquy ont renforcé mon esprit d’équipe, ma rigueur et mes aptitudes à la communication et à l’organisation, des atouts pour la gestion de projet technique. Curieux et engagé, je suis convaincu de pouvoir m’intégrer rapidement à vos équipes et d’apporter une contribution significative aux projets innovants de SOGECLAIR, notamment dans la recherche de solutions durables. Je suis particulièrement enthousiasmé à l’idée de mettre mes compétences au service de SOGE CLAIR et de contribuer à votre engagement pour l’excellence et la satisfaction client. Ce stage représenterait pour moi une occasion unique de m’investir dans un environnement stimulant et d’évoluer au sein d’une entreprise reconnue pour son expertise. Je serais ravi de vous exposer plus en détail ma motivation et mes aptitudes lors d’un entretien""",
    }

    # Remplacer les variables dans le template
    filled_content = template_content
    for key, value in variables.items():
        filled_content = filled_content.replace(f"%%{key}%%", value)

    # Nom du fichier de sortie
    template_name = Path(template_path).stem
    preview_name = f"{template_name}_preview"
    tex_output_path = os.path.join(output_dir, f"{preview_name}.tex")

    # Écrire le fichier .tex avec les variables remplies
    with open(tex_output_path, "w", encoding="utf-8") as f:
        f.write(filled_content)

    logging.info(f"📝 Fichier .tex créé : {tex_output_path}")

    # Compiler en PDF
    success = compile_latex_to_pdf(tex_output_path)

    if success:
        pdf_path = os.path.join(output_dir, f"{preview_name}.pdf")
        logging.info(f"✅ Prévisualisation générée : {pdf_path}")
    else:
        logging.error(f"❌ Échec de la génération du PDF pour {template_name}")


def generate_all_previews():
    """Génère des PDF de prévisualisation pour tous les templates."""
    templates_dir = "templates"
    output_dir = "output"

    # Liste des templates
    template_files = [
        "lettre_template.tex",
        "lettre_template_elegant.tex",
        "lettre_template_moderne.tex",
        "lettre_template_minimaliste.tex",
    ]

    logging.info(f"\n{'='*60}")
    logging.info(f"🚀 Génération des prévisualisations de templates")
    logging.info(f"{'='*60}\n")

    for template_file in template_files:
        template_path = os.path.join(templates_dir, template_file)

        if os.path.exists(template_path):
            logging.info(f"\n{'─'*60}")
            logging.info(f"📋 Traitement : {template_file}")
            logging.info(f"{'─'*60}")
            generate_preview_pdf(template_path, output_dir)
            logging.info(f"{'─'*60}\n")
        else:
            logging.warning(f"⚠️  Template non trouvé : {template_path}")

    logging.info(f"\n{'='*60}")
    logging.info(f"✅ Génération terminée ! Consultez le dossier '{output_dir}'")
    logging.info(f"{'='*60}\n")


if __name__ == "__main__":
    # Générer toutes les prévisualisations
    generate_all_previews()
