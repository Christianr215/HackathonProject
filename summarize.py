# Import necessary classes from the Flask library for web server functionality.
from flask import Flask, request, jsonify
# Import the Google Generative AI library to interact with the Gemini API.
import google.generativeai as genai
# Import the Translator class from the googletrans library for language translation.
from googletrans import Translator

# Create an instance of the Flask web application.
app = Flask(__name__)

# --- IMPORTANT ---
# Set your Google API key. 
# It's recommended to use environment variables for security.
# For example: genai.configure(api_key=os.environ["GEMINI_API_KEY"])
# Configure the Gemini library with your specific API key.
genai.configure(api_key="")

# Initialize the translator
# Create an instance of the Translator class to be used for translations.
translator = Translator()

# Initialize the Gemini model
# You can choose the model that best suits your needs.
# 'gemini-pro' is a good choice for text-based tasks.
# Create an instance of the Gemini Pro model.
model = genai.GenerativeModel('gemini-pro')

# Define a route for the web server. This function will handle POST requests to the /process_text URL.
@app.route("/process_text", methods=["POST"])
def process_text(): # Define the function that will execute when the /process_text endpoint is called.
    """
    This endpoint receives text, summarizes it using the Gemini API,
    and optionally translates the summary.
    """
    # Get the JSON data sent in the POST request.
    data = request.json
    # Extract the value of the "text" key from the JSON data. If it doesn't exist, use an empty string.
    raw_text = data.get("text", "")
    # Extract the value of the "lang" key for the target translation language. This is optional.
    target_lang = data.get("lang")

    # Check if the 'raw_text' variable is empty.
    if not raw_text:
        # If no text was provided, return a JSON error message with a 400 Bad Request status code.
        return jsonify({"error": "No text provided"}), 400

    # --- Step 1: Summarize with Gemini API ---
    # Start a try block to handle potential errors during the API call.
    try:
        # Create the prompt for the model
        # Create the full prompt string to send to the Gemini model, including the user's text.
        prompt = f"Summarize this parking text in short, readable sentences: {raw_text}"
        
        # Generate content using the model
        # Send the prompt to the Gemini model and get the response.
        response = model.generate_content(prompt)
        
        # Extract the summarized text from the response
        # Get the text part of the model's response and remove any leading/trailing whitespace.
        summary = response.text.strip()

    # If an error occurs in the 'try' block...
    except Exception as e:
        # Handle potential API errors
        # ...return a JSON error message with a 500 Internal Server Error status code.
        return jsonify({"error": f"An error occurred with the Gemini API: {str(e)}"}), 500

    # --- Step 2: Translate if a target language is provided ---
    # Initialize the translation variable to None. It will only get a value if translation is requested.
    translation = None
    # Check if a target language was specified in the request.
    if target_lang:
        # Start a try block to handle potential errors during translation.
        try:
            # Use googletrans to translate the summary
            # Use the translator object to translate the summary to the target language.
            translated_text = translator.translate(summary, dest=target_lang)
            # Get the text of the translation.
            translation = translated_text.text
        # If an error occurs during translation...
        except Exception as e:
            # Handle translation errors
            # ...set the translation variable to an error message string.
            translation = f"Translation failed: {str(e)}"

    # --- Step 3: Return the result ---
    # Return the final summary and translation (if any) as a JSON object.
    return jsonify({"summary": summary, "translation": translation})

# Check if this script is being run directly (not imported).
if __name__ == "__main__":
    # Running the app in debug mode
    # Start the Flask development server in debug mode, which provides helpful error messages.
    app.run(debug=True)

