document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const locationInput = document.getElementById('location-input');
    const getWeatherBtn = document.getElementById('get-weather');
    const weatherResult = document.getElementById('weather-result');
    const searchQuery = document.getElementById('search-query');
    const searchBtn = document.getElementById('search-btn');
    const searchResults = document.getElementById('search-results');

    // Add message to chat
    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user' : 'bot'}`;
        messageDiv.innerHTML = `<p>${message}</p>`;
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Send message to the API
    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        // Add user message to chat
        addMessage(message, true);
        userInput.value = '';

        // Show loading indicator
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot';
        loadingDiv.id = 'loading';
        loadingDiv.innerHTML = '<div class="loading"></div>';
        chatContainer.appendChild(loadingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            
            // Remove loading indicator
            document.getElementById('loading')?.remove();
            
            // Add bot response
            addMessage(data.response || "I'm sorry, I couldn't process your request.");
        } catch (error) {
            console.error('Error:', error);
            document.getElementById('loading')?.remove();
            addMessage("Sorry, I'm having trouble connecting to the server.");
        }
    }

    // Get weather for location
    async function getWeather() {
        const location = locationInput.value.trim();
        if (!location) return;

        weatherResult.innerHTML = 'Fetching weather...';
        
        try {
            const response = await fetch(`/weather?location=${encodeURIComponent(location)}`);
            const data = await response.json();
            
            if (data.error) {
                weatherResult.innerHTML = `Error: ${data.error}`;
                return;
            }
            
            weatherResult.innerHTML = `
                <div class="font-medium">${data.location}</div>
                <div>🌡️ ${data.temperature}°C (${data.condition})</div>
                <div>💧 Humidity: ${data.humidity}%</div>
                <div>💨 Wind: ${data.wind_speed} m/s</div>
            `;
        } catch (error) {
            console.error('Error:', error);
            weatherResult.innerHTML = 'Failed to fetch weather data.';
        }
    }

    // Perform web search
    async function performSearch() {
        const query = searchQuery.value.trim();
        if (!query) return;

        searchResults.innerHTML = '<div class="text-center py-2">Searching...</div>';
        
        try {
            const response = await fetch(`/search?query=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            if (!data.results || data.results.length === 0) {
                searchResults.innerHTML = '<div class="text-center py-2 text-gray-500">No results found.</div>';
                return;
            }
            
            searchResults.innerHTML = data.results.map(result => `
                <div class="search-result">
                    <h4>${result.title}</h4>
                    <p>${result.snippet}</p>
                    <a href="${result.link}" target="_blank" rel="noopener noreferrer">Read more →</a>
                </div>
            `).join('');
        } catch (error) {
            console.error('Error:', error);
            searchResults.innerHTML = '<div class="text-center py-2 text-red-500">Error performing search.</div>';
        }
    }

    // Event Listeners
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    getWeatherBtn.addEventListener('click', getWeather);
    locationInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') getWeather();
    });

    searchBtn.addEventListener('click', performSearch);
    searchQuery.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });
});
