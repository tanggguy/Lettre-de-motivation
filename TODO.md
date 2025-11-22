Définir le framework web: partir sur Flask (simple, adapté à un petit serveur local).
Réutiliser le moteur existant: garder toute la logique d’analyse d’annonce / génération LaTeX / PDF, sans la dupliquer.
Ajouter la notion de “prompt supplémentaire” pour le corps de lettre, passé depuis l’interface web.
Exposer un endpoint web pour lancer la génération et un endpoint pour télécharger le PDF.
Créer une page HTML unique avec formulaire: upload .txt ou collage du texte, zone “instructions supplémentaires”, bouton “Générer”, affichage du lien de téléchargement.
Modifications prévues par fichier existant

<!-- requirements.txt

Ajouter la dépendance Flask, par exemple:
Flask==3.0.0 (ou version compatible avec ton environnement).
main.py -->

<!-- Fonctions de génération
Adapter generate_letter_body(user_profile, job_ad_text, job_info=None) pour accepter un paramètre optionnel, par ex. custom_instructions: str | None = None.
Intégrer custom_instructions dans le prompt final, typiquement en les ajoutant à la fin sous forme:
“Instructions supplémentaires à respecter absolument : …”.
Orchestration de lettre
Adapter create_cover_letter(user_config, job_ad_path, templates_dict) →
Nouvelle signature: create_cover_letter(user_config, job_ad_path, templates_dict, custom_instructions=None).
Propager custom_instructions à generate_letter_body(...).
Faire en sorte que la fonction retourne des infos utiles (sans casser le fonctionnement actuel), par ex. un dict:
return {
    "success": success,
    "pdf_path": pdf_filepath,
    "tex_path": tex_filepath,
    "job_info": job_info,
    "match_info": match_info,
}
Fonction main() (mode CLI actuel)
Mettre à jour les appels à create_cover_letter(...) pour passer custom_instructions=None.
Optionnel: utiliser le retour pour afficher dans les logs le chemin du PDF généré.
Garder le comportement actuel (traitement de tous les .txt de input) pour ne pas casser ton workflow existant.
Nouveaux fichiers Python -->

<!-- web_app.py (nouvelle application Flask)
Initialisation Flask:
app = Flask(__name__, template_folder="web_templates") (pour séparer les templates HTML des .tex).
Configuration:
Charger la config via load_config() du module existant (from main import load_config, create_cover_letter).
Vérifier/Créer les dossiers input et output au démarrage si besoin (réutiliser la logique de main() ou la factoriser).
Routes:
GET /
Rendre la page principale avec le formulaire.
Passer éventuellement des variables de contexte (ex: dernier résultat, erreurs).
POST /generate
Récupérer:
job_file (fichier .txt uploadé, optionnel),
job_text (texte brut de l’annonce, optionnel),
custom_prompt (instructions supplémentaires, optionnel).
Construire le texte d’annonce effectif:
Si job_file fourni → lire son contenu,
Sinon, utiliser job_text.
Sauvegarder ce texte dans le dossier input sous un nom généré (ex: web_annonce_YYYYmmdd_HHMMSS.txt).
Appeler create_cover_letter(user_config, job_ad_path, templates_dict, custom_instructions=custom_prompt).
Si success est vrai, récupérer pdf_path et dériver un pdf_filename (ex: avec os.path.basename).
Rendre à nouveau index.html avec:
message de statut (succès/erreur),
lien vers /download/<pdf_filename>,
éventuellement afficher match_info (score, compétences manquantes).
GET /download/<filename>
Vérifier que filename pointe bien dans le dossier output.
Utiliser send_from_directory("output", filename, as_attachment=True) pour renvoyer le PDF. -->
<!-- Nouveaux fichiers HTML / assets

Dossier: web_templates/ (pour ne pas mélanger avec tes templates LaTeX dans templates/)

web_templates/index.html

Structure simple (Bootstrap optionnel):
Titre: “Générateur de lettre de motivation LaTeX”.
Formulaire (method="POST", enctype="multipart/form-data", action="/generate"):
Input type file pour uploader une annonce .txt (name="job_file").
OU grande textarea pour coller l’annonce (name="job_text").
textarea pour “Instructions supplémentaires pour le corps de la lettre” (name="custom_prompt").
Bouton “Générer la lettre”.
Zone de résultat (affichée si la génération a été faite):
Message de succès/erreur (utiliser les variables passées par Flask).
Si pdf_filename disponible:
lien <a href="{{ url_for('download', filename=pdf_filename) }}">Télécharger le PDF</a>.
Optionnel: affichage du score de match, des compétences manquantes, etc. -->
Optionnel:
Légendes / indications sur la priorité: le fichier uploadé prend le dessus sur le texte collé si les deux sont remplis.
web_static/style.css (optionnel)

Si tu veux un minimum de style sans Bootstrap:
largeur max du formulaire,
marges,
typographie.
Dans web_app.py, déclarer static_folder="web_static" si tu veux servir ce CSS via Flask.
Documentation

README.md
Ajouter une section “Interface web locale” avec:
Installation de Flask: pip install Flask (ou pip install -r requirements.txt après mise à jour).
Lancement du serveur:
python web_app.py
Accès via <http://localhost:5000>.
Description rapide du flux:
choisir annonce (upload ou texte),
optionnellement modifier le prompt,
cliquer sur “Générer”,
télécharger le PDF depuis le lien.
