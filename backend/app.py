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
    creds = service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)

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
