"""Wine Concierge Agent using GPT4All and DuckDuckGo."""
from typing import List, Dict, Any, Optional
from duckduckgo_search import DDGS
from gpt4all import GPT4All
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WineConciergeAgent:
    """Wine Concierge Agent using local LLM and free search."""
    
    def __init__(self, model_name: str = "orca-mini-3b-gguf2-q4_0.ggml"):
        """Initialize the agent with a local LLM model."""
        logger.info("Initializing Wine Concierge Agent with GPT4All...")
        self.llm = GPT4All(
            model_name=model_name,
            model_path="./models",
            allow_download=True
        )
        self.search_client = DDGS()
        logger.info("Agent initialization complete.")
    
    def search_web(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Search the web using DuckDuckGo."""
        try:
            results = self.search_client.text(query, max_results=max_results)
            return [{"title": r["title"], "link": r["href"], "snippet": r["body"]} for r in results]
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
    
    def generate_response(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """Generate a response using the local LLM."""
        try:
            response = self.llm.generate(
                prompt=prompt,
                temp=temperature,
                max_tokens=max_tokens
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            return "I'm sorry, I encountered an error while generating a response."
    
    def get_wine_recommendation(self, query: str) -> Dict[str, Any]:
        """Get a wine recommendation based on the query."""
        # First, search for relevant information
        search_results = self.search_web(f"wine recommendation {query}")
        
        # Build the prompt
        prompt = """You are a knowledgeable wine concierge. Provide a detailed wine recommendation based on the following query and search results.
        
        Query: {query}
        
        Search Results:
        {search_results}
        
        Please provide:
        1. Wine recommendation with details (grape, region, style)
        2. Tasting notes
        3. Food pairing suggestions
        4. Price range
        5. Any additional tips or information
        """.format(
            query=query,
            search_results="\n\n".join([f"- {r['title']}: {r['snippet']}" for r in search_results])
        )
        
        # Generate the response
        response = self.generate_response(prompt)
        
        return {
            "recommendation": response,
            "sources": [r["link"] for r in search_results[:3]]
        }

# Example usage
if __name__ == "__main__":
    agent = WineConciergeAgent()
    
    # Example query
    query = "I'm having grilled salmon for dinner. What wine would pair well?"
    result = agent.get_wine_recommendation(query)
    
    print("\nWine Recommendation:")
    print("-" * 50)
    print(result["recommendation"])
    print("\nSources:")
    for source in result["sources"]:
        print(f"- {source}")
