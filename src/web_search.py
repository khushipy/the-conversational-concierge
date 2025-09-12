import os
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Data class to store search result information."""
    title: str
    url: str
    snippet: str
    source: str = "web"
    timestamp: datetime = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the search result to a dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchResult':
        """Create a SearchResult from a dictionary."""
        return cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            snippet=data.get("snippet", ""),
            source=data.get("source", "web"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None
        )

class WebSearcher:
    """
    A class to handle web search functionality for the Wine Concierge.
    Supports both search engine APIs and direct web scraping when needed.
    """
    
    def __init__(self, api_key: Optional[str] = None, search_engine_id: Optional[str] = None):
        """
        Initialize the WebSearcher.
        
        Args:
            api_key: API key for the search engine (Google Custom Search JSON API)
            search_engine_id: Custom Search Engine ID
        """
        self.api_key = api_key or os.getenv("GOOGLE_SEARCH_API_KEY")
        self.search_engine_id = search_engine_id or os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.cache = {}
        self.cache_duration = timedelta(hours=24)  # Cache search results for 24 hours
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    def search(self, query: str, num_results: int = 5, use_api: bool = True) -> List[SearchResult]:
        """
        Perform a web search.
        
        Args:
            query: The search query
            num_results: Number of results to return
            use_api: Whether to use the search API (falls back to scraping if False or API fails)
            
        Returns:
            List of search results
        """
        # Check cache first
        cache_key = f"search_{query}_{num_results}"
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if datetime.now() - cached_data["timestamp"] < self.cache_duration:
                logger.debug(f"Returning cached search results for: {query}")
                return [SearchResult.from_dict(r) for r in cached_data["results"]]
        
        try:
            if use_api and self.api_key and self.search_engine_id:
                results = self._search_with_api(query, num_results)
            else:
                logger.warning("API key or search engine ID not provided. Falling back to direct search.")
                results = self._search_with_scraping(query, num_results)
            
            # Cache the results
            self.cache[cache_key] = {
                "results": [r.to_dict() for r in results],
                "timestamp": datetime.now()
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error performing web search: {str(e)}")
            # Fall back to scraping if API fails
            if use_api:
                return self._search_with_scraping(query, num_results)
            raise
    
    def _search_with_api(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """
        Perform a search using the Google Custom Search JSON API.
        
        Args:
            query: The search query
            num_results: Number of results to return (max 10 for free tier)
            
        Returns:
            List of search results
        """
        try:
            # Google Custom Search JSON API endpoint
            url = "https://www.googleapis.com/customsearch/v1"
            
            params = {
                "key": self.api_key,
                "cx": self.search_engine_id,
                "q": query,
                "num": min(num_results, 10)  # Free tier has a max of 10 results
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("items", [])[:num_results]:
                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="google",
                    timestamp=datetime.now()
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error with Google Search API: {str(e)}")
            raise Exception(f"Search API error: {str(e)}")
    
    def _search_with_scraping(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """
        Perform a search by scraping a search engine results page.
        This is a fallback method when API is not available.
        
        Args:
            query: The search query
            num_results: Number of results to return
            
        Returns:
            List of search results
        """
        try:
            # Use DuckDuckGo as it's more permissive with scraping
            search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
            
            response = requests.get(search_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # DuckDuckGo result selectors
            result_elements = soup.select('.result')
            
            for result in result_elements[:num_results]:
                title_elem = result.select_one('.result__a')
                snippet_elem = result.select_one('.result__snippet')
                url_elem = result.select_one('.result__url')
                
                if not (title_elem and url_elem):
                    continue
                
                title = title_elem.get_text(strip=True)
                url = url_elem.get('href', '')
                
                # Clean the URL
                if url.startswith('//'):
                    url = 'https:' + url
                elif url.startswith('/'):
                    url = 'https://duckduckgo.com' + url
                
                # Follow redirects to get the actual URL
                try:
                    response = requests.head(url, headers=self.headers, allow_redirects=True, timeout=5)
                    final_url = response.url
                except:
                    final_url = url
                
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                results.append(SearchResult(
                    title=title,
                    url=final_url,
                    snippet=snippet,
                    source="duckduckgo",
                    timestamp=datetime.now()
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error with web scraping search: {str(e)}")
            raise Exception(f"Web search failed: {str(e)}")
    
    def get_webpage_content(self, url: str, max_length: int = 5000) -> str:
        """
        Fetch and extract main content from a webpage.
        
        Args:
            url: The URL to fetch content from
            max_length: Maximum length of the returned content
            
        Returns:
            Extracted content as a string
        """
        try:
            # Check cache first
            if url in self.cache and "content" in self.cache[url]:
                cached_content = self.cache[url]["content"]
                if datetime.now() - cached_content["timestamp"] < self.cache_duration:
                    logger.debug(f"Returning cached content for: {url}")
                    return cached_content["text"][:max_length]
            
            # Fetch the webpage
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Try to find the main content
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup
            
            # Get text and clean it up
            text = ' '.join(main_content.stripped_strings)
            text = ' '.join(text.split())  # Remove extra whitespace
            
            # Cache the content
            if url not in self.cache:
                self.cache[url] = {}
            
            self.cache[url]["content"] = {
                "text": text,
                "timestamp": datetime.now()
            }
            
            return text[:max_length]
            
        except Exception as e:
            logger.error(f"Error fetching webpage content from {url}: {str(e)}")
            return f"[Could not retrieve content from {url}: {str(e)}]"

# Example usage
if __name__ == "__main__":
    # Initialize the web searcher
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    
    searcher = WebSearcher(api_key=api_key, search_engine_id=search_engine_id)
    
    # Perform a search
    query = "best Napa Valley wineries 2023"
    print(f"Searching for: {query}\n")
    
    try:
        results = searcher.search(query, num_results=3)
        
        if not results:
            print("No results found.")
        else:
            print(f"Found {len(results)} results:\n")
            
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.title}")
                print(f"   URL: {result.url}")
                print(f"   {result.snippet}\n")
                
                # Get and display the first paragraph of the content
                if i == 1:  # Just show for the first result to save time
                    print("Fetching content from the first result...\n")
                    content = searcher.get_webpage_content(result.url, max_length=500)
                    print(f"First 500 chars of content:\n{content}\n" + "-" * 80 + "\n")
    
    except Exception as e:
        print(f"Error performing search: {str(e)}")
