import os
import json
import time
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pytesseract
from PIL import Image
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024   
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
GEMINI_API_KEY = ""
MODEL_NAME = "gemini-2.5-flash-preview-05-20"

# Create upload folder
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def simplify_parking_text(text):
    if not text:
        return "No text found"
    text = text.lower()
    
    if 'no parking' in text:
        return "No Parking"
    elif 'parking' in text:
        return "parking Allowed"
    else:
        return f"Sign says: {text[:50]}"

# AI API utility function
def _call_gemini_api(payload, is_grounded=True, max_retries=5, model_name=MODEL_NAME):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}

    if is_grounded:
        if 'tools' not in payload:
            payload['tools'] = [{ "google_search": {} }]

    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            
            candidate = result.get('candidates', [None])[0]
            if not candidate:
                 raise ValueError("API response contained no candidates or was empty.")

            text = candidate.get('content', {}).get('parts', [{}])[0].get('text', '').strip()
            
            sources = []
            grounding_metadata = candidate.get('groundingMetadata')
            if is_grounded and grounding_metadata and grounding_metadata.get('groundingAttributions'):
                sources = [
                    {'uri': attr.get('web', {}).get('uri'), 'title': attr.get('web', {}).get('title')}
                    for attr in grounding_metadata['groundingAttributions']
                    if attr.get('web', {}).get('uri') and attr.get('web', {}).get('title')
                ]

            return text, sources

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                return None, []
        except ValueError as e:
            return None, []

    return None, []

@app.route('/')
def home():
    return render_template('index.html')
@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "running",
        "message": "Parking Sign Reader & AI API",
        "endpoints": {
            "upload": "/upload",
            "summarize": "/backend/summarize"
        }
    })

# OCR endpoint
@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        if 'image' not in request.files or request.files['image'].filename == '':
            return jsonify({'error': 'No image provided'}), 400

        file = request.files['image']

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
                
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        try:
            image = Image.open(filepath)
            raw_text = pytesseract.image_to_string(image)
            simplified = simplify_parking_text(raw_text)
            
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'raw_text': raw_text.strip(),
                'simplified': simplified,
                'message': 'Sign processed successfully'
            })
            
        except Exception as ocr_error:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'OCR failed: {str(ocr_error)}'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# AI summarization and translation endpoint
@app.route('/summarize', methods=['POST'])
def summarize_and_translate():
    data = request.get_json()
    raw_text = data.get('raw_text', '').strip()

    if not raw_text:
        return jsonify({
            "error": "No text provided for summarization. Please provide text extracted from the parking sign.",
        }), 400

    # Summarization with AI
    summary_system_prompt = (
        "You are an expert transportation analyst. Your job is to analyze the parking sign text "
        "and provide a concise, unambiguous summary of the key parking rules and restrictions. "
        "The summary MUST be short, readable, and directly address what the driver is permitted or restricted from doing. "
        "Start the summary with 'Key Rule: '."
    )
    summary_user_query = f"Analyze the following OCR text and provide the summary: {raw_text}"

    summary_payload = {
        "contents": [{"parts": [{"text": summary_user_query}]}],
        "systemInstruction": {"parts": [{"text": summary_system_prompt}]}
    }

    summary_text, sources = _call_gemini_api(summary_payload, is_grounded=True)

    if not summary_text:
        error_message = "Failed to generate summary from the text using the AI service."
        return jsonify({"error": error_message}), 500

    # Translation with structured JSON output
    translation_system_prompt = (
        "You are a professional, accurate translator. Your task is to translate the provided text "
        "into Spanish ('es') and French ('fr'). Respond ONLY with a JSON object. "
        "The JSON MUST have keys matching the two-letter language codes: 'es' and 'fr'."
    )
    translation_user_query = f"Translate the following text into Spanish and French: {summary_text}"

    translation_payload = {
        "contents": [{"parts": [{"text": translation_user_query}]}],
        "systemInstruction": {"parts": [{"text": translation_system_prompt}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "es": {"type": "STRING", "description": "Spanish translation"},
                    "fr": {"type": "STRING", "description": "French translation"}
                }
            }
        }
    }

    translation_json_str, _ = _call_gemini_api(translation_payload, is_grounded=False)
    
    translations = {}
    if translation_json_str:
        try:
            translations = json.loads(translation_json_str)
        except json.JSONDecodeError:
            translations = {'es': 'Translation error (JSON parse failed).', 'fr': 'Erreur de traduction (JSON parse failed).'}
    else:
         translations = {'es': 'Translation unavailable.', 'fr': 'Traduction indisponible.'}

    return jsonify({
        "summary": summary_text,
        "translation_es": translations.get('es', "Translation unavailable."),
        "translation_fr": translations.get('fr', "Translation unavailable."),
        "sources": sources
    }), 200

if __name__ == '__main__':
    print("Parking Sign Reader & AI API Starting...")
    print("OCR endpoint: http://localhost:5000/upload")
    print("AI endpoint: http://localhost:5000/backend/summarize")
    app.run(debug=True, port=5000)