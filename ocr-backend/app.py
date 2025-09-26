from flask import Flask, request, jsonify
from flask_cors import CORS
import pytesseract
from PIL import Image
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

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
    
@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "message": "Parking Sign Reader API",
        "upload_url": "/upload"
    })

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        # FILE UPLOAD HANDLING
        # Check if image was uploaded
        if 'image' not in request.files or request.files['image'].filename == '':
            return jsonify({'error': 'No image provided'}), 400

        file = request.files['image']

        # Check file type
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
                
        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        #OCR PROCESSING
        try:
            image = Image.open(filepath)
            raw_text = pytesseract.image_to_string(image)
            simplified = simplify_parking_text(raw_text)
            
            #Clean up
            os.remove(filepath)
            
            #CLEAN JSON RESPONSE
            return jsonify({
                'success': True,
                'raw_text': raw_text.strip(),
                'simplified': simplified,
                'message': 'Sign processed successfully'
            })
            
        except Exception as ocr_error:
            #Clean up on error
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'OCR failed: {str(ocr_error)}'}), 500
            
    except Exception as e:
        #ERROR MANAGEMENT
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    print("Parking Sign Reader API Starting...")
    print("Upload to: http://localhost:5000/upload")
    app.run(debug=True, port=5000)