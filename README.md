# Générateur de Lettre de Motivation Intelligent (LaTeX + AI)

Ce projet est un outil complet permettant de générer automatiquement des lettres de motivation ultra-personnalisées au format PDF. Il combine la puissance de l'IA (Google Gemini) pour l'analyse d'annonces et la rédaction, avec la qualité typographique de LaTeX pour une mise en page professionnelle.

## 🚀 Fonctionnalités

*   **Analyse d'annonce par IA** : Extrait automatiquement les compétences clés, le poste, l'entreprise, le secteur et le ton de l'annonce.
*   **Rédaction personnalisée** : Génère un corps de lettre unique et pertinent, mettant en avant l'adéquation entre votre profil (défini dans `config.json`) et l'offre.
*   **Rendu PDF Professionnel** : Utilise des templates LaTeX dynamiques (Moderne, Élégant, Minimaliste) sélectionnés automatiquement selon le ton de l'annonce.
*   **Interface Web & Dashboard** :
    *   Génération simple via formulaire (texte ou fichier).
    *   Tableau de bord pour suivre l'historique des candidatures.
    *   Gestion des statuts (En préparation, Envoyée, Entretien, etc.).
*   **Intégration Gmail** : Prépare en un clic un brouillon d'email prêt à envoyer, avec le CV et la lettre de motivation en pièces jointes.
*   **Mode CLI (Batch)** : Possibilité de traiter plusieurs annonces simultanément via la ligne de commande.

## 🛠️ Prérequis

Avant de commencer, assurez-vous d'avoir installé :

1.  **Python 3.8+**
2.  **Une distribution LaTeX** (indispensable pour la compilation `pdflatex`) :
    *   Windows : [MiKTeX](https://miktex.org/) ou [TeX Live](https://www.tug.org/texlive/).
    *   Linux : `sudo apt-get install texlive-full` (ou `texlive-latex-base` + `texlive-latex-extra`).
    *   macOS : [MacTeX](https://www.tug.org/mactex/).
3.  **Clé API Google Gemini** : À récupérer gratuitement sur [Google AI Studio](https://aistudio.google.com/).
4.  **Credentials Gmail (Optionnel)** : Pour utiliser la fonctionnalité de création de brouillons (fichier `credentials.json` OAuth2).

## 📦 Installation

1.  **Cloner le projet**
    ```bash
    git clone <votre-repo-url>
    cd "Latex_lettre de motivation generator"
    ```

2.  **Créer un environnement virtuel**
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```

3.  **Installer les dépendances**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration**
    *   **Variables d'environnement** : Créez un fichier `.env` à la racine (basé sur `.env.example`) :
        ```ini
        GEMINI_API_KEY=votre_clé_api_ici
        FLASK_SECRET_KEY=une_clé_secrète_aléatoire_pour_flask
        ```
    *   **Profil Candidat** : Créez un fichier `config.json` à la racine (basé sur `config.example`) et remplissez vos informations :
        ```json
        {
            "nom_complet": "Jean Dupont",
            "adresse": "123 Rue de l'Exemple, 75000 Paris",
            "telephone": "06 12 34 56 78",
            "email": "jean.dupont@email.com",
            "resume_personnel": "Étudiant en ingénierie logicielle passionné par l'IA...",
            "competences_cles": ["Python", "Machine Learning", "Gestion de projet"],
            "json_export": true
        }
        ```

## 💻 Utilisation

### 1. Interface Web (Recommandé)

Lancez l'application Flask :
```bash
python web_app.py
```
Ouvrez votre navigateur sur `http://127.0.0.1:5000`.

*   **Générer** : Collez le texte d'une annonce ou uploadez un fichier `.txt`. Vous pouvez ajouter des instructions spécifiques pour l'IA.
*   **Dashboard** : Consultez vos lettres générées, téléchargez les PDF et gérez le statut de vos candidatures.
*   **Email** : Depuis le dashboard, cliquez sur "Préparer Email" pour générer un brouillon Gmail avec pièces jointes.

### 2. Ligne de Commande (CLI)

Pour générer des lettres en masse :
1.  Placez vos fichiers d'annonces (`.txt`) dans le dossier `input/`.
2.  Lancez le script :
    ```bash
    python main.py
    ```
3.  Les lettres générées (PDF) et les fichiers sources (.tex) seront disponibles dans le dossier `output/`.

## 📂 Structure du Projet

```
/
|-- input/                  # Dossier d'entrée pour les annonces (CLI)
|-- output/                 # Dossier de sortie (PDF, Logs, Metadata)
|-- templates/              # Modèles LaTeX (.tex)
|-- web_templates/          # Templates HTML (Flask)
|-- web_static/             # Fichiers statiques (CSS)
|-- main.py                 # Cœur du générateur (Logique IA + LaTeX)
|-- web_app.py              # Serveur Web Flask & Base de données
|-- gmail_utils.py          # Module de gestion de l'API Gmail
|-- config.json             # Configuration utilisateur (Profil)
|-- .env                    # Secrets (API Keys)
|-- requirements.txt        # Liste des dépendances
```

## 🛡️ Dépannage

*   **Erreur `pdflatex not found`** : Vérifiez que votre distribution LaTeX est bien installée et que la commande `pdflatex` est accessible dans votre terminal (PATH).
*   **Erreur API Gemini** : Vérifiez que votre clé API dans `.env` est valide et que vous avez accès à internet.
*   **Problème d'encodage** : Assurez-vous que vos fichiers d'annonces sont enregistrés en UTF-8.
*   **Gmail Error** : Si l'envoi de brouillon échoue, vérifiez la présence et la validité du fichier `credentials.json` et `token.json`.

---
*Projet développé pour automatiser et optimiser la recherche d'emploi.*

## 🚀 Roadmap & Idées Futures

Voici des pistes d'amélioration et d'outils supplémentaires envisagés pour enrichir le projet :

### 🧠 Intelligence Artificielle & Analyse
*   **Support Multi-LLM** : Intégration d'autres modèles (OpenAI GPT-4, Claude, Mistral) pour comparer les résultats ou réduire les coûts.
*   **Analyse de CV (CV Parsing)** : Utiliser l'IA pour analyser le CV du candidat et suggérer des adaptations spécifiques pour l'offre visée.
*   **Simulateur d'Entretien** : Générer une liste de questions probables et de réponses types basées sur l'analyse de l'annonce.
*   **Score de Pertinence Avancé** : Affiner l'algorithme de matching avec une analyse sémantique plus poussée.

### 🌐 Intégrations & Automatisation
*   **Scraping d'Annonces** : Module pour extraire automatiquement le texte d'une annonce depuis une URL (LinkedIn, Indeed, Welcome to the Jungle).
*   **Envoi d'Emails Automatisé** : Possibilité d'envoyer directement la candidature via SMTP ou API Gmail (avec validation humaine préalable).
*   **Suivi des Relances** : Système d'alerte dans le dashboard pour rappeler de relancer un recruteur après X jours sans réponse.
*   **Export Notion/Trello** : Synchroniser les candidatures avec des outils de productivité externes.

### 🎨 Interface & Expérience Utilisateur (UX)
*   **Éditeur de Template WYSIWYG** : Interface graphique pour personnaliser les couleurs, polices et marges des templates LaTeX sans toucher au code.
*   **Aperçu Live** : Visualisation en temps réel de la lettre (rendu HTML approximatif) avant la compilation PDF finale.
*   **Mode Sombre (Dark Mode)** : Thème sombre pour l'interface web.
*   **Profils Multiples** : Gérer plusieurs configurations (ex: un profil "Data Scientist" et un profil "Chef de Projet") dans le même outil.

### 🛠️ Technique & Déploiement
*   **Dockerisation** : Création d'un `Dockerfile` et `docker-compose.yml` pour déployer l'application facilement sur n'importe quel serveur.
*   **Base de Données Robuste** : Migration de SQLite vers PostgreSQL pour gérer un grand volume de candidatures.
*   **Tests Automatisés** : Ajout de tests unitaires et d'intégration (pytest) pour garantir la stabilité lors des évolutions.

## 🌟 Extensions du Dashboard & Nouveaux Modules

Pour aller plus loin, voici des idées concrètes pour enrichir le dashboard et transformer l'outil en une véritable suite de gestion de carrière :

### 📊 Analytics & Statistiques
*   **Vue d'ensemble** : Graphiques montrant le nombre de candidatures par semaine/mois.
*   **Taux de conversion** : Calcul automatique du ratio "Candidatures envoyées" vs "Entretiens décrochés".
*   **Répartition** : Camemberts par type de poste ou par secteur d'activité.

### ⚙️ Gestion de Profil (Settings)
*   **Interface d'édition** : Une page dédiée pour modifier le fichier `config.json` directement depuis le navigateur (plus besoin d'éditer le fichier à la main).
*   **Gestion des compétences** : Ajouter/Supprimer des compétences clés via une interface tags.
*   **Profils Multiples** : Switcher facilement entre plusieurs configurations (ex: "Profil Dev Python" vs "Profil Chef de Projet").

### 📝 Éditeur de Templates
*   **Customisation Visuelle** : Un module permettant de changer la couleur principale, la police ou les marges des templates LaTeX sans toucher au code `.tex`.
*   **Preview en direct** : Voir l'impact des changements de style en temps réel.

### 📅 Vue Calendrier & Suivi
*   **Agenda des Relances** : Une vue calendrier affichant les dates limites pour relancer les recruteurs (ex: J+7 après envoi).
*   **Planification d'entretiens** : Ajouter les dates d'entretiens directement dans le dashboard avec synchronisation Google Calendar.

### 📋 Kanban Board
*   **Drag & Drop** : Remplacer la liste simple par un tableau Kanban (colonnes : "À faire", "Envoyé", "Entretien", "Offre", "Refus") pour déplacer les cartes de candidature visuellement.
