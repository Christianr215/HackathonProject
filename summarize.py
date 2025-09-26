import os
import json
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- Configuration ---
app = Flask(__name__)
# Enable CORS for communication with the frontend (required when testing locally)
CORS(app)

# NOTE: The API key is left empty here, as per environment instructions.
GEMINI_API_KEY = ""
# Using the recommended model for text generation tasks
MODEL_NAME = "gemini-2.5-flash-preview-05-20"

# --- Utility Function: Call Gemini API with Exponential Backoff ---
def _call_gemini_api(payload, is_grounded=True, max_retries=5, model_name=MODEL_NAME):
    """
    Handles API call logic, including exponential backoff for reliability.
    """
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}

    # Add grounding tool if required (used for summarization to enhance accuracy)
    if is_grounded:
        if 'tools' not in payload:
            payload['tools'] = [{ "google_search": {} }]

    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            result = response.json()
            
            # Check for candidate content
            candidate = result.get('candidates', [None])[0]
            if not candidate:
                 raise ValueError("API response contained no candidates or was empty.")

            text = candidate.get('content', {}).get('parts', [{}])[0].get('text', '').strip()
            
            # Extract grounding sources if used
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
                # Do not log retries as errors in the console per instructions
                time.sleep(wait_time)
            else:
                print(f"Final attempt failed. Could not reach Gemini API. Error: {e}")
                return None, []
        except ValueError as e:
            # Handle JSON decoding error or missing content
            print(f"Error processing API response: {e}")
            return None, []

    return None, [] # Should be unreachable if max_retries > 0

# --- Core Business Logic: Summarization and Translation ---

@app.route('/backend/summarize', methods=['POST'])
def summarize_and_translate():
    """
    Takes raw OCR text, generates a summary using Gemini, and translates the summary using Gemini.
    """
    data = request.get_json()
    raw_text = data.get('raw_text', '').strip()

    if not raw_text:
        return jsonify({
            "error": "No text provided for summarization. Please provide text extracted from the parking sign.",
        }), 400

    print(f"Processing raw text (first 50 chars): {raw_text[:50]}...")

    # 1. Summarization (using Google Search grounding for enhanced accuracy)
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

    # 2. Translation (using structured JSON output for easy parsing)
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
            print("Warning: Failed to parse translation JSON from API response.")
            # Fallback in case of parsing failure
            translations = {'es': 'Translation error (JSON parse failed).', 'fr': 'Erreur de traduction (JSON parse failed).'}
    else:
         translations = {'es': 'Translation unavailable.', 'fr': 'Traduction indisponible.'}


    # 3. Return Final Results
    return jsonify({
        "summary": summary_text,
        "translation_es": translations.get('es', "Translation unavailable."),
        "translation_fr": translations.get('fr', "Translation unavailable."),
        "sources": sources
    }), 200

# --- Server Startup ---
if __name__ == '__main__':
    # Flask runs on 5000 by default.
    print("Starting Flask server for AI summarization and translation...")
    app.run(debug=True, port=5000)
