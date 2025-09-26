// --- Interactivity Setup ---
// Ripple Effect Implementation
document.querySelectorAll('.ripple').forEach(btn => {
    btn.addEventListener('click', function(e){
        let circle = document.createElement('span');
        let rect = this.getBoundingClientRect();
        
        // Calculate position relative to the button
        circle.style.left = e.clientX - rect.left + "px";
        circle.style.top = e.clientY - rect.top + "px";
        
        this.appendChild(circle);
        setTimeout(() => circle.remove(), 600);
    });
});

// Confetti Burst Implementation (Fires on successful virtual "Submit")
function launchConfetti(){
    const confetti = document.getElementById("confetti");
    const colors = ["#f87171", "#34d399", "#60a5fa", "#fde047", "#a78bfa"]; // Tailwind colors
    for(let i=0; i < 40; i++){
        let piece = document.createElement("div");
        piece.classList.add("confetti-piece");
        piece.style.left = Math.random() * 100 + "vw";
        piece.style.setProperty('--c', colors[Math.floor(Math.random() * colors.length)]);
        piece.style.animationDelay = Math.random() * 0.5 + "s";
        confetti.appendChild(piece);
        setTimeout(() => piece.remove(), 3000);
    }
}

// --- Core Application Logic ---
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('image-upload');
    const uploadLabel = document.getElementById('upload-label');
    const submitButton = document.getElementById('submit-button');
    const uploadText = document.getElementById('upload-text');
    const languageSelect = document.getElementById('language-select');
    const loadingIndicator = document.getElementById('loading');
    const resultsDiv = document.getElementById('results');
    const summaryContent = document.getElementById('summary-content');
    const translationContent = document.getElementById('translation-content');
    
    // Placeholder text for demo purposes until backend is ready
    const MOCK_SUMMARY = "You **CAN** park here from 8 AM to 6 PM on weekdays. Parking is restricted on Tuesdays and Fridays between 11 AM and 1 PM for street cleaning. Always check the sign for temporary changes!";
    const MOCK_TRANSLATION_ES = "Usted **PUEDE** estacionar aquí de 8 AM a 6 PM los días de semana. Estacionar está restringido los martes y viernes de 11 AM a 1 PM para limpieza de calles. ¡Siempre revise el letrero por cambios temporales!";

    // --- Drag & Drop Event Handlers ---
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadLabel.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults (e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Note: drag-over class is handled in CSS/JS now to give the cool effect
    uploadLabel.addEventListener('dragenter', () => uploadLabel.classList.add('drag-over'), false);
    uploadLabel.addEventListener('dragover', () => uploadLabel.classList.add('drag-over'), false);
    uploadLabel.addEventListener('dragleave', () => uploadLabel.classList.remove('drag-over'), false);
    
    uploadLabel.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        uploadLabel.classList.remove('drag-over');
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            fileInput.files = files; // Assign dropped files to the file input
            uploadText.textContent = `File selected: ${files[0].name}. Click Submit.`;
        }
    }


    submitButton.addEventListener('click', async (event) => {
        const file = fileInput.files[0];
        if (!file) {
            console.warn("No file selected.");
            uploadText.textContent = 'Please select an image first.';
            return;
        }

        resultsDiv.classList.add('hidden');
        loadingIndicator.classList.remove('hidden');
        uploadText.textContent = 'Uploading...';

        // --- Simulated Backend Calls (replace with actual fetch for /backend/upload) ---
        try {
            // Simulate API latency for OCR (1.5 seconds)
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // Simulate fetching raw text
            const rawText = "NO STANDING ANY TIME EXCEPT SUNDAY 8AM-6PM";
            
            // Simulate API latency for summarization (2 seconds)
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            const language = languageSelect.value;
            let summaryText = MOCK_SUMMARY;
            let translatedText = language === 'es' ? MOCK_TRANSLATION_ES : MOCK_SUMMARY; // Simple language mock

            // Step 3: Display results
            loadingIndicator.classList.add('hidden');
            resultsDiv.classList.remove('hidden');
            launchConfetti(); // Confetti on "success"

            // Reset content and apply typing animation class
            summaryContent.textContent = '';
            summaryContent.classList.remove('summary-ready');
            summaryContent.classList.add('summary-content-typing');
            
            // Typing effect function
            let i = 0;
            const speed = 20; // Typing speed in ms
            function typeWriter() {
                if (i < summaryText.length) {
                    // Using innerHTML to display bold/italic markdown in the mock summary
                    summaryContent.innerHTML += summaryText.charAt(i); 
                    i++;
                    setTimeout(typeWriter, speed);
                } else {
                    summaryContent.classList.remove('summary-content-typing');
                    summaryContent.classList.add('summary-ready');
                    
                    // Display translation after typing animation completes
                    translationContent.innerHTML = translatedText;
                }
            }
            typeWriter();
            
            uploadText.textContent = 'Drag & Drop or Click to Select Image';

        } catch (error) {
            loadingIndicator.classList.add('hidden');
            resultsDiv.classList.add('hidden');
            uploadText.textContent = 'Upload failed: Please check console for errors.';
            console.error('Error during processing (MOCK FAILURE):', error);
        }
    });

    // Handle file selection change to update upload text
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            uploadText.textContent = `File selected: ${fileInput.files[0].name}. Click Submit.`;
        } else {
            uploadText.textContent = 'Drag & Drop or Click to Select Image';
        }
    });
});
