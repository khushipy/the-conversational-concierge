import os
import requests
from typing import Dict, Optional, Union
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WeatherService:
    """
    A service to fetch weather information using the OpenWeatherMap API.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the WeatherService.
        
        Args:
            api_key: OpenWeatherMap API key. If not provided, will try to get from environment variables.
        """
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY")
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
        self.cache = {}
        self.cache_duration = timedelta(minutes=30)  # Cache weather data for 30 minutes
    
    def get_weather(self, location: str) -> Dict[str, Any]:
        """
        Get current weather for a location.
        
        Args:
            location: City name, state code, and country code divided by comma (e.g., "Napa,CA,US")
            
        Returns:
            Dictionary containing weather information
        """
        if not self.api_key:
            logger.error("OpenWeatherMap API key not provided")
            return {"error": "Weather service is not properly configured. Missing API key."}
        
        # Check cache first
        cache_key = f"weather_{location}"
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if datetime.now() - cached_data["timestamp"] < self.cache_duration:
                logger.debug(f"Returning cached weather data for {location}")
                return cached_data["data"]
        
        try:
            # Make API request
            params = {
                "q": location,
                "appid": self.api_key,
                "units": "imperial",  # Use Fahrenheit
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            # Format the response
            weather_info = {
                "location": f"{data.get('name', 'Unknown')}, {data.get('sys', {}).get('country', '')}",
                "temperature": round(data["main"]["temp"]),
                "feels_like": round(data["main"]["feels_like"]),
                "humidity": data["main"]["humidity"],
                "wind_speed": round(data["wind"]["speed"], 1),
                "description": data["weather"][0]["description"].capitalize(),
                "icon": data["weather"][0]["icon"],
                "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M"),
                "sunset": datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M"),
                "timestamp": datetime.now()
            }
            
            # Cache the result
            self.cache[cache_key] = {
                "data": weather_info,
                "timestamp": datetime.now()
            }
            
            return weather_info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching weather data: {str(e)}")
            return {"error": f"Failed to fetch weather data: {str(e)}"}
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing weather data: {str(e)}")
            return {"error": "Failed to parse weather data. The API response format may have changed."}
    
    def get_weather_summary(self, location: str) -> str:
        """
        Get a human-readable weather summary for a location.
        
        Args:
            location: City name, state code, and country code divided by comma
            
        Returns:
            Formatted weather summary string
        """
        weather = self.get_weather(location)
        
        if "error" in weather:
            return f"I couldn't retrieve the weather information. {weather['error']}"
        
        try:
            summary = (
                f"Current weather in {weather['location']}: {weather['description']} "
                f"with a temperature of {weather['temperature']}°F "
                f"(feels like {weather['feels_like']}°F). "
                f"Humidity is at {weather['humidity']}% and wind speed is {weather['wind_speed']} mph. "
                f"Sunrise was at {weather['sunrise']} and sunset will be at {weather['sunset']}."
            )
            
            # Add some wine-related advice based on weather
            temp = weather["temperature"]
            if temp > 80:
                summary += " It's quite warm - a chilled white or rosé wine would be refreshing!"
            elif temp < 50:
                summary += " It's a bit chilly - perfect for a bold red wine to warm you up!"
            else:
                summary += " The weather is pleasant - a nice medium-bodied wine would be perfect!"
                
            return summary
            
        except KeyError as e:
            logger.error(f"Error formatting weather summary: {str(e)}")
            return "I couldn't format the weather information properly. Please try again later."

# Example usage
if __name__ == "__main__":
    # Get API key from environment variable or prompt
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        api_key = input("Enter your OpenWeatherMap API key: ")
    
    # Initialize weather service
    weather_service = WeatherService(api_key=api_key)
    
    # Get weather for Napa Valley
    location = "Napa,CA,US"
    print(f"\nFetching weather for {location}...\n")
    
    # Get detailed weather
    weather = weather_service.get_weather(location)
    if "error" in weather:
        print(f"Error: {weather['error']}")
    else:
        print("Detailed Weather Data:")
        for key, value in weather.items():
            if key != "timestamp":  # Skip timestamp for cleaner output
                print(f"{key.replace('_', ' ').title()}: {value}")
    
    # Get weather summary
    print("\nWeather Summary:")
    print(weather_service.get_weather_summary(location))
