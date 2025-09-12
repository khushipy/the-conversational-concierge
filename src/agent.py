from typing import Dict, List, TypedDict, Annotated, Optional, Union
from enum import Enum
import logging
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our modules
from .document_retriever import DocumentRetriever
from .weather import WeatherService
from .web_search import WebSearcher, SearchResult

# Define the state structure for our agent
class AgentState(TypedDict):
    """The state of our agent."""
    messages: Annotated[List[Union[HumanMessage, AIMessage, SystemMessage]], lambda x, y: x + y]
    context: str
    current_tool: Optional[str] = None
    tool_result: Optional[str] = None

# Define tools the agent can use
class ToolType(str, Enum):
    DOCUMENT_RETRIEVAL = "document_retrieval"
    WEB_SEARCH = "web_search"
    WEATHER = "weather"
    RESPOND = "respond"

# Define the tool selection model
class ToolSelection(BaseModel):
    """The tool to use and the input to the tool."""
    tool: ToolType = Field(..., description="The tool to use")
    tool_input: str = Field(..., description="The input to the tool")

class WineConciergeAgent:
    """
    A conversational agent for the Wine Concierge that can answer questions about wine,
    perform web searches, and provide weather information.
    """
    
    def __init__(self):
        # Initialize the LLM
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.2,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize components
        self.document_retriever = DocumentRetriever()
        self.weather_service = WeatherService()
        self.web_searcher = WebSearcher()
        
        # Initialize the graph
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow for the agent."""
        # Define the nodes
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("route", self._route)
        workflow.add_node("document_retrieval", self._retrieve_documents)
        workflow.add_node("web_search", self._perform_web_search)
        workflow.add_node("weather", self._get_weather)
        workflow.add_node("respond", self._respond)
        
        # Define the edges
        workflow.add_conditional_edges(
            "route",
            self._decide_next_step,
            {
                ToolType.DOCUMENT_RETRIEVAL: "document_retrieval",
                ToolType.WEB_SEARCH: "web_search",
                ToolType.WEATHER: "weather",
                ToolType.RESPOND: "respond"
            }
        )
        
        # Connect the tool nodes back to the router
        workflow.add_edge("document_retrieval", "respond")
        workflow.add_edge("web_search", "respond")
        workflow.add_edge("weather", "respond")
        
        # Set the entry point
        workflow.set_entry_point("route")
        
        # Compile the workflow
        return workflow.compile()
    
    def _route(self, state: AgentState) -> ToolSelection:
        """Determine which tool to use based on the conversation."""
        # Get the last user message
        user_message = state["messages"][-1].content if state["messages"] else ""
        
        # Create a prompt to decide which tool to use
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful assistant that decides which tool to use to answer the user's question.
            
            Available tools:
            - document_retrieval: For questions about wine, winery, or general knowledge that should be in the knowledge base.
            - web_search: For current events, latest information, or specific queries that might need up-to-date information.
            - weather: For questions about the current or future weather in a specific location.
            - respond: When no tool is needed and you can answer directly.
            
            Respond with a JSON object containing the tool name and the input to the tool.
            
            Example 1:
            User: What are the best wine pairings for salmon?
            {{"tool": "document_retrieval", "tool_input": "best wine pairings for salmon"}}
            
            Example 2:
            User: What's the weather like in Napa?
            {{"tool": "weather", "tool_input": "Napa,CA,US"}}
            
            Example 3:
            User: Find me the latest reviews for Opus One 2020
            {{"tool": "web_search", "tool_input": "Opus One 2020 reviews"}}
            
            Example 4:
            User: Hello, how are you?
            {{"tool": "respond", "tool_input": ""}}
            """),
            ("user", "{input}")
        ])
        
        # Create the chain
        chain = prompt | self.llm | JsonOutputParser(pydantic_object=ToolSelection)
        
        # Get the tool selection
        try:
            tool_selection = chain.invoke({"input": user_message})
            logger.info(f"Selected tool: {tool_selection.tool}")
            return tool_selection
        except Exception as e:
            logger.error(f"Error selecting tool: {str(e)}")
            # Default to respond if there's an error
            return ToolSelection(tool=ToolType.RESPOND, tool_input="")
    
    def _decide_next_step(self, state: AgentState) -> str:
        """Determine the next step based on the tool selection."""
        if "tool" not in state:
            return ToolType.RESPOND.value
        return state["tool"]
    
    async def _retrieve_documents(self, state: AgentState) -> AgentState:
        """Retrieve relevant documents based on the query."""
        try:
            query = state["tool_input"]
            logger.info(f"Retrieving documents for query: {query}")
            
            # Get relevant documents
            docs = self.document_retriever.similarity_search(query, k=3)
            
            # Format the documents
            context = "\n\n".join([f"Document {i+1}:\n{doc.page_content}" for i, doc in enumerate(docs)])
            
            # Update the state with the context
            return {
                "messages": state["messages"],
                "context": context,
                "current_tool": "document_retrieval",
                "tool_result": context
            }
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            return {
                "messages": state["messages"],
                "context": "Error retrieving documents. Please try again.",
                "current_tool": "document_retrieval",
                "tool_result": "Error retrieving documents."
            }
    
    async def _perform_web_search(self, state: AgentState) -> AgentState:
        """Perform a web search based on the query."""
        try:
            query = state["tool_input"]
            logger.info(f"Performing web search: {query}")
            
            # Perform the search
            results = self.web_searcher.search(query, num_results=3)
            
            # Format the results
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_results.append(
                    f"Result {i}: {result.title}\n"
                    f"URL: {result.url}\n"
                    f"Snippet: {result.snippet}"
                )
            
            context = "\n\n".join(formatted_results)
            
            return {
                "messages": state["messages"],
                "context": context,
                "current_tool": "web_search",
                "tool_result": context
            }
            
        except Exception as e:
            logger.error(f"Error performing web search: {str(e)}")
            return {
                "messages": state["messages"],
                "context": "Error performing web search. Please try again.",
                "current_tool": "web_search",
                "tool_result": "Error performing web search."
            }
    
    async def _get_weather(self, state: AgentState) -> AgentState:
        """Get weather information for a location."""
        try:
            location = state["tool_input"] or "Napa,CA,US"
            logger.info(f"Getting weather for: {location}")
            
            # Get weather information
            weather_info = self.weather_service.get_weather_summary(location)
            
            return {
                "messages": state["messages"],
                "context": weather_info,
                "current_tool": "weather",
                "tool_result": weather_info
            }
            
        except Exception as e:
            logger.error(f"Error getting weather: {str(e)}")
            return {
                "messages": state["messages"],
                "context": "Error getting weather information. Please try again.",
                "current_tool": "weather",
                "tool_result": "Error getting weather information."
            }
    
    async def _respond(self, state: AgentState) -> AgentState:
        """Generate a response based on the conversation and context."""
        try:
            # Get the conversation history
            messages = state["messages"]
            context = state.get("context", "")
            tool_used = state.get("current_tool")
            tool_result = state.get("tool_result", "")
            
            # Create the system message based on the tool used
            if tool_used == "document_retrieval":
                system_message = f"""You are a knowledgeable wine concierge. Use the following information to answer the user's question. 
                If you don't know the answer, say so. Don't make up information.
                
                Relevant information:
                {context}"""
            elif tool_used == "web_search":
                system_message = f"""You are a helpful assistant. Use the following search results to answer the user's question. 
                Be concise and provide sources when possible.
                
                Search results:
                {context}"""
            elif tool_used == "weather":
                system_message = f"""You are a helpful assistant providing weather information. 
                Here's the current weather information:
                {context}"""
            else:
                system_message = """You are a friendly and knowledgeable wine concierge. 
                Answer the user's questions about wine, wineries, or related topics. 
                If you don't know the answer, you can say so or offer to look it up."""
            
            # Create the prompt
            prompt = [
                ("system", system_message),
                *[(msg.type, msg.content) for msg in messages],
                ("assistant", "")
            ]
            
            # Generate the response
            response = await self.llm.agenerate([prompt])
            response_text = response.generations[0][0].text
            
            # Add the assistant's response to the messages
            new_messages = messages + [AIMessage(content=response_text)]
            
            return {
                "messages": new_messages,
                "context": context,
                "current_tool": None,
                "tool_result": None
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            error_message = "I'm sorry, I encountered an error while generating a response. Please try again."
            
            return {
                "messages": messages + [AIMessage(content=error_message)],
                "context": context,
                "current_tool": None,
                "tool_result": None
            }
    
    async def process_message(self, message: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Process a user message and return the assistant's response.
        
        Args:
            message: The user's message
            conversation_history: List of previous messages in the conversation
            
        Returns:
            A dictionary containing the assistant's response and any additional metadata
        """
        try:
            # Convert conversation history to Message objects
            messages = []
            if conversation_history:
                for msg in conversation_history:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    else:
                        messages.append(AIMessage(content=msg["content"]))
            
            # Add the new user message
            messages.append(HumanMessage(content=message))
            
            # Initialize the state
            state = {
                "messages": messages,
                "context": "",
                "current_tool": None,
                "tool_result": None
            }
            
            # Run the workflow
            result = await self.workflow.ainvoke(state)
            
            # Get the last assistant message
            assistant_message = result["messages"][-1].content
            
            return {
                "response": assistant_message,
                "context": result.get("context", ""),
                "tool_used": result.get("current_tool"),
                "tool_result": result.get("tool_result", "")
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "response": "I'm sorry, I encountered an error while processing your request. Please try again.",
                "error": str(e)
            }

# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Initialize the agent
        agent = WineConciergeAgent()
        
        # Example conversation
        queries = [
            "What's the weather like in Napa?",
            "What are some good wine pairings for seafood?",
            "Find me the latest reviews for Opus One 2020"
        ]
        
        conversation_history = []
        
        for query in queries:
            print(f"\nUser: {query}")
            
            # Process the query
            result = await agent.process_message(query, conversation_history)
            
            # Print the response
            print(f"\nAssistant: {result['response']}")
            
            # Update conversation history
            conversation_history.append({"role": "user", "content": query})
            conversation_history.append({"role": "assistant", "content": result['response']})
            
            # Print debug info
            if result.get('tool_used'):
                print(f"\n[Used tool: {result['tool_used']}]")
    
    # Run the example
    asyncio.run(main())
