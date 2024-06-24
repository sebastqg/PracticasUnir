from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
import os
import PyPDF2
from docx import Document
from transformers import pipeline
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
SUMMARY_FOLDER = 'summaries'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SUMMARY_FOLDER'] = SUMMARY_FOLDER

# Credenciales de servicio de Google Cloud
credentials_info = {
    "type": "service_account",
    "project_id": "sixth-oxygen-424603-h5",
    "private_key_id": "4953372373a092f873c88a2f9386a1365dfc01af",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDPxKUAKGVt3FVA\nSEWPCsPS4J2KB0H93aDNIIl+2trNWZYIxkb3wWGyfb9yqvYzbcyaOWyI7Knxqgzz\n1lWRH/AJ4cmaL91IxHX2hPZBbGOzQhv91wiFsDVx1snRf6fLYMW0CFcezix4oRqe\nnnnSRuRMniO/izacxkibXUpvv7YoY3a4oSZBnWERvt0WJ4SPXXQnJwbTK0dXACCJ\nPAKVbGVyugqyS8LdsTGiFdgtcJYsiSBSuEhi9kb6LFPL2IB8RSpo8Ii6Uf7EW+yE\ndlEOmnO6BFPNhrxs/S1SxXq7XlOCXczO3gSBcgLpzswbtza53DzeWj6dOr/ZkQVJ\nn1iKIbV1AgMBAAECggEAXHigmXPhROayOMSR1OrNIj+fTk4RpHwuM+3d1Exy4r+T\nI7+f2WhD483M1ivaHSSq0h9pu31d2/W8AxCrj8Zfrv5DnLDd86Og/wHJmm+z5hYv\n4CgDHoFBIDQhKfF/jGi7RXgK0maf62aEswFEpf6wYJtnvLooqdkkeqWoWhlA6TMi\nR9DgCQGHuCy355hiEZqFyqdRCOjgOU8vWI8bxIfU71uAh7eRXrBrfzwhrJbekTvn\nDmnmGWomnFHSL1d6NPnVBoNqoP2WXREdWKLDZt1wfVNd8+PLaf+TqV8nC+dW6NxH\nAF/mjVlJbOVRNRF9qQcpPHpg/uO6/tD9dSxYFULFpwKBgQDs2boIpDOi0YDO6RTN\n+zeMjK7gbIIJuqII5u0Nb6i0/8vd5vt0lxUh8696/siVxK+hGORRZx3hS69jS/EJ\nnrOL5FN63JBTqF1XjPeNJMlHXsL8PPoi3b4i+LskEPQjhPYAK/lGwu5cR/EtIk59\niXO3KbhBbqNK9ls8j0o4+NBlxwKBgQDgkPp8pzvGF032Vgop0eG+AnQUlSJJRxTy\nZI6GCf6RO7wlHxyaI29UaMzklwbvxMtBIPSdE/hPBCysUBed3Vy7QQIHELCHbCEa\n+o6nrG0c1S5P3GYTo62g42VKg5VxzKQeIUgcQvIWt26a4Gg/WRAio3t4AO8Oh7bZ\nqS4vB/Ta4wKBgF+B0IWJiRTfvDwzOuNwqM6xMBdpSeqYapyCWhav7uzFtTSO3tj9\nz1S4igtj0AisnlGs0uyMUz01Is08oz7I0wfXE16YsE47tyAFxRESQ2PXL3M9N3R1\nzCUX/Yamm3vzMquRD9zb3/gwPm1/xvzSP2odlaI09f3VZ6b89OYSVx6jAoGAPXAs\nt7HhLp7tm3mKqkpbomp1a7QpfzbNSkusmotddEqNfPJ4FsufB87sT5XqNer3WMg1\nZEw0YRnZRwNakrwfRLPSZDByu3ofzIvEP6dy6rKASyUXYEQlmqDb83jwiAPe2sds\nPR8rsH9a6VB/9OTe/zsO6pQG00jaA86/beqVWNUCgYBRKuCF4rrXzYE4nC7SX1sk\net+c+lF8dAODdYbPcCtim57pWo7jmXw6if3VfM3POnRUeFsJVCQ75UIuptMjXPwN\nwzKAC5uxBYVAP/xtl2NOzHDHJ3yJBaUYXInK8eohnfPSUahFjdlD4kl0Zv2cjD7o\nWoDV0Po0dk/WqX8eJYM8fQ==\n-----END PRIVATE KEY-----\n",
    "client_email": "practicas@sixth-oxygen-424603-h5.iam.gserviceaccount.com",
    "client_id": "107911297455640839393",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/practicas%40sixth-oxygen-424603-h5.iam.gserviceaccount.com"
}

credentials = service_account.Credentials.from_service_account_info(credentials_info)

# ID de la carpeta de Google Drive donde se subirán los archivos
DRIVE_FOLDER_ID = '1-Z7aX66Cz4xIxsiXEaMkZ58ldW4PEA8n'

# Cargar el modelo preentrenado para resumen de textos
model_name = "sshleifer/distilbart-cnn-12-6"
summarizer = pipeline("summarization", model=model_name)

def summarize_text(text):
    summary = summarizer(text, max_length=150, min_length=30, do_sample=False)
    return summary[0]['summary_text']

def read_pdf(file_path):
    pdf_reader = PyPDF2.PdfFileReader(open(file_path, 'rb'))
    text = ''
    for page in range(pdf_reader.numPages):
        text += pdf_reader.getPage(page).extract_text()
    return text

def read_word(file_path):
    doc = Document(file_path)
    text = ''
    for para in doc.paragraphs:
        text += para.text
    return text

def read_text(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()
    return text

def upload_to_drive(file_path, filename):
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    service = build('drive', 'v3', credentials=credentials)

    # Metadatos del archivo incluyendo el ID de la carpeta
    file_metadata = {
        'name': filename,
        'parents': [DRIVE_FOLDER_ID]
    }
    media = MediaFileUpload(file_path, mimetype='text/plain')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return 'No file part', 400
        file = request.files['file']
        if file.filename == '':
            return 'No selected file', 400
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            if filename.endswith('.pdf'):
                text = read_pdf(file_path)
            elif filename.endswith('.docx'):
                text = read_word(file_path)
            elif filename.endswith('.txt'):
                text = read_text(file_path)
            else:
                return 'Unsupported file type', 400
            
            summary = summarize_text(text)
            summary_file = os.path.join(app.config['SUMMARY_FOLDER'], f"{filename}_summary.txt")
            with open(summary_file, 'w', encoding='utf-8') as file:
                file.write(summary)

            drive_file_id = upload_to_drive(summary_file, f"{filename}_summary.txt")
            
            return jsonify(summary=summary, summary_file=summary_file, drive_file_id=drive_file_id)
    except Exception as e:
        print(f"Error: {e}")
        return str(e), 500

@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(SUMMARY_FOLDER):
        os.makedirs(SUMMARY_FOLDER)
    app.run(debug=True)
