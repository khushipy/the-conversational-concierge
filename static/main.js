// DOM Elements
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const chatMessages = document.getElementById('chat-messages');
const loadingIndicator = document.getElementById('loading');

// Global state
let conversationHistory = [];
let isProcessing = false;

// API endpoints
const API_BASE_URL = '/api';
const ENDPOINTS = {
    CHAT: `${API_BASE_URL}/chat`,
    WEATHER: `${API_BASE_URL}/weather`,
    SEARCH: `${API_BASE_URL}/search`,
    UPLOAD: `${API_BASE_URL}/documents/upload`,
    HEALTH: `${API_BASE_URL}/health`
};

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    // Check API health on load
    checkApiHealth();
    
    // Load initial weather
    updateWeather();
    
    // Set up event listeners
    chatForm.addEventListener('submit', handleSubmit);
    
    // Auto-resize textarea
    userInput.addEventListener('input', () => {
        userInput.style.height = 'auto';
        userInput.style.height = (userInput.scrollHeight) + 'px';
    });
});

// Check if the API is available
async function checkApiHealth() {
    try {
        const response = await fetch(ENDPOINTS.HEALTH);
        if (!response.ok) {
            throw new Error('API is not available');
        }
        return true;
    } catch (error) {
        console.error('API health check failed:', error);
        showError('Unable to connect to the server. Please try again later.');
        return false;
    }
}

// Handle form submission
async function handleSubmit(e) {
    e.preventDefault();
    
    const message = userInput.value.trim();
    if (!message || isProcessing) return;
    
    // Clear input
    userInput.value = '';
    userInput.style.height = 'auto';
    
    // Add user message to chat
    addMessage('user', message);
    
    // Show loading indicator
    showLoading(true);
    isProcessing = true;
    
    try {
        // Prepare messages for the API
        const messages = [
            ...conversationHistory.map(msg => ({
                role: msg.role,
                content: msg.content
            })),
            { role: 'user', content: message }
        ];
        
        // Send message to backend
        const response = await fetch(ENDPOINTS.CHAT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                messages: messages,
                location: 'Napa,CA,US' // Default location, can be made dynamic
            })
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to get response from server');
        }
        
        const data = await response.json();
        
        // Add assistant's response to chat
        addMessage('assistant', data.response);
        
        // Log the tool used if any
        if (data.tool_used) {
            console.log(`Tool used: ${data.tool_used}`);
        }
        
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Sorry, I encountered an error. Please try again.');
    } finally {
        showLoading(false);
        isProcessing = false;
    }
}

// Add a message to the chat
function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `flex items-start ${role === 'user' ? 'justify-end' : ''} message-${role}`;
    
    const bubbleClass = role === 'user' 
        ? 'bg-purple-600 text-white rounded-l-lg rounded-tr-lg' 
        : 'bg-purple-100 text-gray-800 rounded-r-lg rounded-tl-lg';
    
    // Sanitize content to prevent XSS
    const sanitizedContent = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;')
        .replace(/\n/g, '<br>');
    
    // Convert markdown links to HTML
    const formattedContent = sanitizedContent.replace(
        /\[([^\]]+)\]\(([^)]+)\)/g, 
        '<a href="$2" target="_blank" class="text-purple-600 hover:underline">$1</a>'
    );
    
    messageDiv.innerHTML = `
        <div class="max-w-3xl w-full">
            <div class="${bubbleClass} p-3">
                <p class="${role === 'assistant' ? 'font-medium text-purple-800' : 'font-medium text-white'}">
                    ${role === 'assistant' ? 'Wine Concierge' : 'You'}
                </p>
                <div class="whitespace-pre-wrap">${formattedContent}</div>
            </div>
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Add to conversation history
    conversationHistory.push({ role, content });
}

// Show error message
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'bg-red-100 border-l-4 border-red-500 text-red-700 p-3 mb-4 rounded';
    errorDiv.role = 'alert';
    errorDiv.innerHTML = `
        <p class="font-bold">Error</p>
        <p>${message}</p>
    `;
    chatMessages.appendChild(errorDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Update weather information
async function updateWeather() {
    try {
        const response = await fetch(ENDPOINTS.WEATHER + '?location=Napa,CA,US');
        if (response.ok) {
            const data = await response.json();
            const weatherElement = document.querySelector('#weather-info');
            if (weatherElement && data.weather) {
                weatherElement.innerHTML = `
                    <i class="fas fa-${getWeatherIcon(data.weather.toLowerCase())} mr-1"></i>
                    <span>${data.weather}</span>
                `;
            }
        }
    } catch (error) {
        console.error('Error fetching weather:', error);
    }
}

// Get weather icon based on weather condition
function getWeatherIcon(weather) {
    if (weather.includes('sun') || weather.includes('clear')) {
        return 'sun text-yellow-500';
    } else if (weather.includes('cloud')) {
        return 'cloud text-gray-400';
    } else if (weather.includes('rain')) {
        return 'cloud-rain text-blue-400';
    } else if (weather.includes('snow')) {
        return 'snowflake text-blue-200';
    } else if (weather.includes('storm') || weather.includes('thunder')) {
        return 'bolt text-yellow-400';
    } else {
        return 'cloud-sun text-gray-400';
    }
}

// Show/hide loading indicator
function showLoading(show) {
    if (loadingIndicator) {
        loadingIndicator.style.display = show ? 'flex' : 'none';
    }
    
    // Disable/enable the form during loading
    if (chatForm) {
        const submitButton = chatForm.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = show;
        }
    }
}

// Handle suggested queries
window.suggestQuery = function(query) {
    if (isProcessing) return;
    userInput.value = query;
    userInput.focus();
    // Auto-submit after a short delay
    setTimeout(() => {
        const event = new Event('submit', { cancelable: true });
        chatForm.dispatchEvent(event);
    }, 100);
};
