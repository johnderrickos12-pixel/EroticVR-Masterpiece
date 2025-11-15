
document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generate-btn');
    const promptInput = document.getElementById('prompt-input');
    const gallery = document.getElementById('video-gallery');
    const loadingIndicator = document.getElementById('loading-indicator');

    // Function to add a new video to the gallery
    const addVideoToGallery = (videoUrl) => {
        const videoContainer = document.createElement('div');
        videoContainer.className = 'video-item';
        
        const video = document.createElement('video');
        video.src = videoUrl;
        video.controls = true;
        video.loop = true;
        video.autoplay = true; // For immediate playback
        video.muted = true; // Mute autoplayed videos as per browser policy

        videoContainer.appendChild(video);
        // Add the new video at the beginning of the gallery
        gallery.prepend(videoContainer);
    };

    // Handle the generate button click
    generateBtn.addEventListener('click', async () => {
        const prompt = promptInput.value.trim();
        if (!prompt) {
            alert('Please enter a prompt.');
            return;
        }

        // Show loading indicator and disable button
        loadingIndicator.style.display = 'block';
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt: prompt }),
            });

            if (!response.ok) {
                throw new Error('Server error');
            }

            const data = await response.json();
            
            // Add the new video to the gallery
            // In a real app, the URL would come from the response, e.g., data.videoUrl
            // For this simulation, we'll use a placeholder.
            addVideoToGallery('https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4');
            
            // Clear the input
            promptInput.value = '';

        } catch (error) {
            console.error('Failed to generate video:', error);
            alert('Failed to generate video. Please try again.');
        } finally {
            // Hide loading indicator and re-enable button
            loadingIndicator.style.display = 'none';
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate';
        }
    });

    // Load initial videos on page load (optional)
    // For now, let's add a few placeholders to show how the gallery looks
    addVideoToGallery('https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4');
    addVideoToGallery('https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4');
});
