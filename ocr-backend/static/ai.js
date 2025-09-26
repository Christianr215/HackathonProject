const fileInput = document.getElementById('image-upload');

//Send over data to get raw text
document.getElementById('submit-button').addEventListener('click', async () => {
    try {
        const file = fileInput.files[0]; //To keep uploaded files in an array
        const formData = new FormData(); //Easier to send data to backstie
        formData.append('image', file);

        const response = await fetch ('/upload', {
            method: 'POST', 
            body: formData //The data were sending over
        });

        const data = await response.json(); //backend returns text
        const rawText = data.raw_text; //whatever the json file is called

        //Send over data to summarize
        const summaryResponse = await fetch('/process_text', {
            method: 'POST',
            headers: {'Content-Type':'application/json'}, //makes sure the backend is accept json and doesnt read it as raw text
            body: JSON.stringify({ text: rawText }) //makes it easier for the backend to parse
        });

        const summaryData = await summaryResponse.json();
        const summary = summaryData.summary;

        //Send over data to translate
        const translationResponse = await fetch('/translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: summary, target_lang: 'es' })
        });

        const translatedData = await translationResponse.json(); // { translated: "..." }
        document.getElementById('translated-summary').innerText = translatedData.translated;
        
        } catch (err) {
            document.getElementById('summary').innerText = "Error processing image.";
            console.error(err);
        }
    });