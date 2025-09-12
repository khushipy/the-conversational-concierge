# 🍷 Wine Concierge Agent

A sophisticated conversational AI agent for wine businesses that can answer questions about wine, perform web searches, and provide weather updates. Built with LangGraph, LangChain, and FastAPI.

## ✨ Features

- **Wine Knowledge Base**: Answer questions using a comprehensive wine knowledge base
- **Web Search**: Perform real-time web searches for up-to-date information
- **Weather Integration**: Provide current weather information for wine-related recommendations
- **Interactive Web UI**: Modern, responsive interface for seamless interaction
- **Document Retrieval**: Smart document search for accurate information retrieval
- **Rate Limiting**: Configurable rate limiting to prevent abuse and ensure fair usage

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Required API Keys:
  - [OpenAI API Key](https://platform.openai.com/api-keys)
  - [OpenWeatherMap API Key](https://openweathermap.org/api)
  - [Google Custom Search JSON API Key](https://developers.google.com/custom-search/v1/introduction) (optional, for enhanced web search)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/wine-concierge.git
   cd wine-concierge
   ```

2. **Set up a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file and add your API keys.

### Running the Application

1. **Start the development server**
   ```bash
   uvicorn src.api:app --reload
   ```

2. **Access the web interface**
   Open your browser and navigate to [http://localhost:8000](http://localhost:8000)

## 🛠️ Project Structure

```
wine_concierge/
├── data/                   # Document storage for wine knowledge
│   └── wine_knowledge_base.md  # Sample wine knowledge base
├── src/                    # Source code
│   ├── __init__.py
│   ├── agent.py            # LangGraph agent implementation
│   ├── api.py              # FastAPI application
│   ├── config.py           # Application configuration
│   ├── document_retriever.py # Document processing and retrieval
│   ├── web_search.py       # Web search functionality
│   └── weather.py          # Weather service integration
├── static/                 # Static files (CSS, JS, images)
│   ├── main.js             # Frontend JavaScript
│   └── styles.css          # Custom styles
├── templates/              # HTML templates
│   ├── base.html           # Base template
│   └── index.html          # Main chat interface
├── .env.example            # Example environment variables
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## 🌐 API Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/` | GET | Serve the web interface | N/A |
| `/api/chat` | POST | Process chat messages | 10/minute |
| `/api/weather` | GET | Get weather information | 30/minute |
| `/api/search` | GET | Perform a web search | 30/minute |
| `/api/documents/upload` | POST | Upload documents to the knowledge base | 60/minute |
| `/api/health` | GET | Health check endpoint | 60/minute |

### Rate Limit Headers

When rate limits are approached or exceeded, the following headers are included in responses:

- `X-RateLimit-Limit`: Maximum number of requests allowed in the time window
- `X-RateLimit-Remaining`: Number of requests remaining in the current window
- `X-RateLimit-Reset`: Time when the rate limit will reset (UTC epoch seconds)
- `Retry-After`: Time to wait before making another request (when rate limit is exceeded)

## 📝 Usage Examples

### Chat with the Wine Concierge

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What wine pairs well with salmon?"}]}'
```

### Get Weather Information

```bash
curl "http://localhost:8000/api/weather?location=Napa,CA,US"
```

### Perform a Web Search

```bash
curl "http://localhost:8000/api/search?query=best%20Napa%20Valley%20wineries%202023&num_results=3"
```

## 🔧 Customization

### Adding to the Knowledge Base

1. Add your documents to the `data/` directory
2. The supported formats include:
   - Markdown (.md)
   - Text (.txt)
   - PDF (.pdf)
   - Word documents (.docx)
   - PowerPoint (.pptx)
   - Excel (.xlsx)
   - CSV (.csv)

2. Restart the application to process the new documents

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Yes | - |
| `OPENWEATHER_API_KEY` | OpenWeatherMap API key | Yes | - |
| `GOOGLE_SEARCH_API_KEY` | Google Custom Search API key | No | - |
| `GOOGLE_SEARCH_ENGINE_ID` | Google Custom Search Engine ID | No | - |
| `ENVIRONMENT` | Application environment | No | `development` |
| `DEBUG` | Enable debug mode | No | `False` |
| `PORT` | Port to run the server on | No | `8000` |
| `HOST` | Host to bind the server to | No | `0.0.0.0` |
| `RATE_LIMIT` | Rate limit for authenticated requests | No | `60/minute` |
| `RATE_LIMIT_AUTH` | Rate limit for authenticated requests | No | `5/minute` |
| `RATE_LIMIT_PUBLIC` | Rate limit for public requests | No | `30/minute` |
| `RATE_LIMIT_STRICT` | Rate limit for strict requests | No | `10/minute` |
| `RATE_LIMIT_STORAGE_URI` | Rate limit storage URI | No | `memory://` |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [LangGraph](https://langchain-ai.github.io/langgraph/), [LangChain](https://www.langchain.com/), and [FastAPI](https://fastapi.tiangolo.com/)
- Icons by [Font Awesome](https://fontawesome.com/)
- Styled with [Tailwind CSS](https://tailwindcss.com/)
