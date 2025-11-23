import os
import base64
import mimetypes
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes required for creating drafts
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']

def get_gmail_service():
    """Authenticates and returns the Gmail API service."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("Le fichier 'credentials.json' est introuvable. Veuillez le télécharger depuis la console Google Cloud.")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def create_draft(to_email, subject, body, attachment_paths=None):
    """Creates a draft email with attachments."""
    service = get_gmail_service()
    if not service:
        return {"success": False, "error": "Impossible d'initialiser le service Gmail."}

    try:
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to_email
        message['Subject'] = subject

        if attachment_paths:
            for path in attachment_paths:
                if not path or not os.path.exists(path):
                    continue
                
                ctype, encoding = mimetypes.guess_type(path)
                if ctype is None or encoding is not None:
                    # No guess could be made, or the file is encoded (compressed), so
                    # use a generic bag-of-bits type.
                    ctype = 'application/octet-stream'
                
                maintype, subtype = ctype.split('/', 1)
                
                with open(path, 'rb') as f:
                    file_data = f.read()
                    filename = os.path.basename(path)
                    message.add_attachment(file_data,
                                           maintype=maintype,
                                           subtype=subtype,
                                           filename=filename)

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {
            'message': {
                'raw': encoded_message
            }
        }

        draft = service.users().drafts().create(userId="me", body=create_message).execute()
        return {"success": True, "draft_id": draft['id']}

    except HttpError as error:
        return {"success": False, "error": f"Erreur API Gmail: {error}"}
    except Exception as e:
        return {"success": False, "error": f"Erreur inattendue: {e}"}
