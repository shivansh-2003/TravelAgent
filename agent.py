import os
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

# LangChain and LangGraph imports
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import tool
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, HumanMessage
from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.callbacks.tracers import ConsoleCallbackHandler

# Import existing functions
from flight_search import search_flights_from_query, parse_flight_query, search_flights
from hotel_details import fetch_hotels, format_hotel_data, fetch_hotel_details, extract_key_info
from restaurants import fetch_restaurants, format_restaurant_data, fetch_restaurant_details
from travel import fetch_places, get_place_details

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise EnvironmentError("OPENAI_API_KEY environment variable is not set")

# Define Pydantic models for structured data
class Location(BaseModel):
    """Model representing a geographic location."""
    city: str
    country: Optional[str] = None
    
    @validator('city')
    def city_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('City cannot be empty')
        return v.strip()

class TravelDates(BaseModel):
    """Model representing travel dates."""
    start_date: str
    end_date: Optional[str] = None
    flexible: bool = False
    
    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        if v and v.strip():
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError('Date must be in YYYY-MM-DD format')
        return v

class TravelPreferences(BaseModel):
    """Model representing traveler preferences."""
    budget_level: str = Field(description="Budget level: economy, mid-range, luxury")
    interests: List[str] = Field(description="List of traveler interests (e.g., 'food', 'history', 'nature')")
    accommodation_type: Optional[str] = None
    dietary_restrictions: Optional[List[str]] = None
    
    @validator('interests')
    def interests_must_not_be_empty(cls, v):
        if not v:
            return ["general"]
        return v

class TravelPlan(BaseModel):
    """Comprehensive travel plan model."""
    destination: Location
    dates: TravelDates
    preferences: TravelPreferences
    flights: Optional[List[Dict[str, Any]]] = None
    hotels: Optional[List[Dict[str, Any]]] = None
    restaurants: Optional[List[Dict[str, Any]]] = None
    attractions: Optional[List[Dict[str, Any]]] = None
    itinerary: Optional[List[Dict[str, Any]]] = None

class AgentState(BaseModel):
    """State representation for the travel planning workflow."""
    travel_plan: TravelPlan
    messages: List[BaseMessage]
    current_step: str = "initialize"
    next_steps: List[str] = []
    error: Optional[str] = None

# Define tools that wrap existing functions with better error handling
@tool
def search_flights_tool(query: str) -> str:
    """
    Search for flights based on a natural language query.
    
    Args:
        query: A natural language query about flight search, e.g.,
              "Find flights from New York to London on April 15, 2025"
    
    Returns:
        A formatted string with flight information
    """
    try:
        flights = search_flights_from_query(query)
        
        if not flights:
            return "No flights found for your query. Please try different parameters."
        
        result = "Here are the flights that match your criteria:\n\n"
        
        for i, flight in enumerate(flights[:5], 1):  # Limit to top 5 flights
            result += f"{i}. {flight['carrier']}\n"
            result += f"   From {flight['origin']} to {flight['destination']}\n"
            result += f"   Departure: {flight['departure_time']}\n"
            result += f"   Arrival: {flight['arrival_time']}\n"
            result += f"   Duration: {flight['duration']}\n"
            result += f"   Price: {flight['price_formatted']}\n"
            result += f"   Stops: {flight['stops']}\n\n"
        
        return result
    except Exception as e:
        return f"Error searching for flights: {str(e)}. Please try a different query format."

@tool
def search_hotels_tool(
    location: str, 
    check_in_date: Optional[str] = None, 
    check_out_date: Optional[str] = None
) -> str:
    """
    Search for hotels in a specified location.
    
    Args:
        location: The city or location to search for hotels
        check_in_date: Optional check-in date in YYYY-MM-DD format
        check_out_date: Optional check-out date in YYYY-MM-DD format
    
    Returns:
        A formatted string with hotel information
    """
    try:
        hotel_data = fetch_hotels(location)
        
        if not hotel_data:
            return "No hotels found for this location. Please try a different location."
        
        formatted_data, _ = format_hotel_data(hotel_data)
        return formatted_data
    except Exception as e:
        return f"Error searching for hotels: {str(e)}. Please try a different location."

@tool
def get_hotel_details_tool(hotel_id: str) -> str:
    """
    Get detailed information about a specific hotel.
    
    Args:
        hotel_id: The TripAdvisor ID of the hotel
    
    Returns:
        A formatted string with detailed hotel information
    """
    try:
        hotel_details = fetch_hotel_details(hotel_id)
        
        if not hotel_details:
            return "Could not retrieve details for this hotel."
        
        key_info = extract_key_info(hotel_details)
        
        result = f"Hotel: {key_info.get('name', 'Unknown')}\n"
        result += f"Rating: {key_info.get('rating', 'N/A')}\n"
        result += f"Address: {key_info.get('address', 'N/A')}\n"
        result += f"Price Range: {key_info.get('price_range', 'N/A')}\n"
        
        if key_info.get('keywords'):
            result += f"Keywords: {', '.join(key_info.get('keywords')[:5])}\n"
        
        return result
    except Exception as e:
        return f"Error retrieving hotel details: {str(e)}. Please try a different hotel."

@tool
def search_restaurants_tool(location: str) -> str:
    """
    Search for restaurants in a specified location.
    
    Args:
        location: The city or location to search for restaurants
    
    Returns:
        A formatted string with restaurant information
    """
    try:
        restaurant_data = fetch_restaurants(location)
        
        if not restaurant_data:
            return "No restaurants found for this location. Please try a different location."
        
        formatted_data, _ = format_restaurant_data(restaurant_data)
        return formatted_data
    except Exception as e:
        return f"Error searching for restaurants: {str(e)}. Please try a different location."

@tool
def find_attractions_tool(city: str) -> str:
    """
    Find tourist attractions in a specified city.
    
    Args:
        city: The city to search for attractions
    
    Returns:
        A formatted string with attraction information
    """
    try:
        places = fetch_places(city)
        
        if not places:
            return "No attractions found for this city. Please try a different city."
        
        result = f"Top attractions in {city}:\n\n"
        
        for i, place in enumerate(places[:5], 1):  # Limit to top 5 attractions
            place_name = place.get("name", "Unknown")
            place_details = get_place_details(place_name)
            
            result += f"{i}. {place_name}\n"
            result += f"   Rating: {place.get('rating', 'N/A')}/5\n"
            result += f"   Address: {place.get('formatted_address', 'N/A')}\n"
            
            if isinstance(place_details, str) and len(place_details) > 200:
                result += f"   Description: {place_details[:200]}...\n\n"
            else:
                result += f"   Description: {place_details}\n\n"
        
        return result
    except Exception as e:
        return f"Error finding attractions: {str(e)}. Please try a different city."

@tool
def create_itinerary_tool(
    destination: str,
    start_date: str,
    end_date: str,
    interests: List[str]
) -> str:
    """
    Create a day-by-day itinerary for a trip.
    
    Args:
        destination: The city or location for the trip
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        interests: List of traveler interests (e.g., 'food', 'history', 'nature')
    
    Returns:
        A formatted string with a day-by-day itinerary
    """
    try:
        # Get list of attractions
        places = fetch_places(destination)
        
        # Calculate number of days
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            num_days = (end - start).days + 1
        except ValueError:
            return "Invalid date format. Please use YYYY-MM-DD format."
        
        if num_days <= 0:
            return "End date must be after start date."
        
        # Create a daily itinerary
        llm = ChatOpenAI(api_key=OPENAI_API_KEY)
        
        # Get a list of attractions as a string
        attractions_list = "\n".join([f"- {place.get('name', 'Unknown')}" for place in places[:10]])
        
        prompt = f"""
        Create a {num_days}-day itinerary for a trip to {destination} from {start_date} to {end_date}.
        The traveler is interested in: {', '.join(interests)}
        
        Here are some popular attractions in {destination}:
        {attractions_list}
        
        Please create a day-by-day itinerary that includes:
        - Morning, afternoon, and evening activities
        - Suggestions for meals
        - A good mix of activities based on the interests
        
        Format as a day-by-day plan.
        """
        
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"Error creating itinerary: {str(e)}. Please provide valid travel details."

# Define the agent system with improved error handling
def create_travel_agent() -> AgentExecutor:
    """
    Create an agent executor that can use the travel planning tools.
    
    Returns:
        AgentExecutor: The configured agent executor
    """
    # Define tools
    tools = [
        search_flights_tool,
        search_hotels_tool,
        get_hotel_details_tool,
        search_restaurants_tool,
        find_attractions_tool,
        create_itinerary_tool
    ]
    
    # Define the system prompt
    system_prompt = """
    You are a sophisticated travel agent AI assistant that helps users plan their trips.
    
    You have access to the following tools:
    1. search_flights_tool: Search for flights based on user criteria
    2. search_hotels_tool: Find hotels in a location
    3. get_hotel_details_tool: Get detailed information about a specific hotel
    4. search_restaurants_tool: Find restaurants in a location
    5. find_attractions_tool: Discover tourist attractions in a city
    6. create_itinerary_tool: Create a day-by-day travel itinerary
    
    Guidelines:
    - Ask clarifying questions to understand the user's travel preferences.
    - Collect sufficient information before using tools.
    - Present information clearly and concisely.
    - Provide personalized recommendations based on the user's preferences.
    - Help the user compare options when appropriate.
    
    Required information for a complete travel plan:
    - Destination (city/country)
    - Travel dates
    - Budget level
    - Traveler interests
    - Number of travelers
    
    Remember to be helpful, informative, and considerate of the user's preferences and constraints.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    
    # Create the OpenAI tools agent with error handling
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini", 
            api_key=OPENAI_API_KEY,
            temperature=0.7
        )
        agent = create_openai_tools_agent(llm, tools, prompt)
        
        # Create the agent executor with callbacks for better debugging
        agent_executor = AgentExecutor(
            agent=agent, 
            tools=tools,
            verbose=True,
            handle_parsing_errors=True
        )
        
        return agent_executor
    except Exception as e:
        print(f"Error creating travel agent: {str(e)}")
        raise

# Define the LangGraph state machine with improved state transitions
def build_travel_planner_graph() -> StateGraph:
    """
    Build a state graph for the travel planning process.
    
    Returns:
        StateGraph: The configured state graph
    """
    # Initialize the state graph
    workflow = StateGraph(AgentState)
    
    # Define nodes for each planning stage with proper error handling
    def initialize(state: AgentState) -> AgentState:
        """Initialize the travel planning process"""
        try:
            agent = create_travel_agent()
            
            # Get the last message from the user
            if state.messages:
                last_message = state.messages[-1].content
            else:
                last_message = "I need help planning a trip."
            
            response = agent.invoke({"input": last_message})
            
            # Update the state with the agent's response
            state.messages.append(HumanMessage(content=response["output"]))
            
            # Determine next step based on content
            if "flights" in response["output"].lower():
                state.current_step = "flight_search"
            elif "hotel" in response["output"].lower():
                state.current_step = "hotel_search"
            elif "restaurant" in response["output"].lower():
                state.current_step = "restaurant_search"
            elif "attraction" in response["output"].lower():
                state.current_step = "attraction_search"
            elif "itinerary" in response["output"].lower():
                state.current_step = "create_itinerary"
            else:
                state.current_step = "general_assistance"
            
            return state
        except Exception as e:
            state.error = f"Error initializing travel planning: {str(e)}"
            state.current_step = "general_assistance"
            return state
    
    def flight_search(state: AgentState) -> AgentState:
        """Handle flight search requests"""
        try:
            agent = create_travel_agent()
            
            # Get the last message from the user
            if state.messages:
                last_message = state.messages[-1].content
            else:
                last_message = "I need help finding flights."
            
            # Append context that we're focused on flights
            focused_message = f"Focus on finding flights. {last_message}"
            
            response = agent.invoke({"input": focused_message})
            
            # Update the state with the agent's response
            state.messages.append(HumanMessage(content=response["output"]))
            
            # Extract flight information if possible and store in travel plan
            if "price" in response["output"].lower() and "departure" in response["output"].lower():
                # This is a simplification - in a production system, we would parse the flight data more carefully
                state.travel_plan.flights = [{"summary": response["output"]}]
            
            # Update next steps
            state.next_steps = ["hotel_search", "general_assistance"]
            
            return state
        except Exception as e:
            state.error = f"Error searching for flights: {str(e)}"
            state.next_steps = ["general_assistance"]
            return state
    
    def hotel_search(state: AgentState) -> AgentState:
        """Handle hotel search requests"""
        try:
            agent = create_travel_agent()
            
            # Get the last message from the user
            if state.messages:
                last_message = state.messages[-1].content
            else:
                last_message = "I need help finding hotels."
            
            # Append context that we're focused on hotels
            focused_message = f"Focus on finding hotels. {last_message}"
            
            response = agent.invoke({"input": focused_message})
            
            # Update the state with the agent's response
            state.messages.append(HumanMessage(content=response["output"]))
            
            # Extract hotel information if possible and store in travel plan
            if "hotel" in response["output"].lower() and "rating" in response["output"].lower():
                # This is a simplification - in a production system, we would parse the hotel data more carefully
                state.travel_plan.hotels = [{"summary": response["output"]}]
            
            # Update next steps
            state.next_steps = ["restaurant_search", "general_assistance"]
            
            return state
        except Exception as e:
            state.error = f"Error searching for hotels: {str(e)}"
            state.next_steps = ["general_assistance"]
            return state
    
    def restaurant_search(state: AgentState) -> AgentState:
        """Handle restaurant search requests"""
        try:
            agent = create_travel_agent()
            
            # Get the last message from the user
            if state.messages:
                last_message = state.messages[-1].content
            else:
                last_message = "I need help finding restaurants."
            
            # Append context that we're focused on restaurants
            focused_message = f"Focus on finding restaurants. {last_message}"
            
            response = agent.invoke({"input": focused_message})
            
            # Update the state with the agent's response
            state.messages.append(HumanMessage(content=response["output"]))
            
            # Extract restaurant information if possible and store in travel plan
            if "restaurant" in response["output"].lower() and "rating" in response["output"].lower():
                # This is a simplification - in a production system, we would parse the restaurant data more carefully
                state.travel_plan.restaurants = [{"summary": response["output"]}]
            
            # Update next steps
            state.next_steps = ["attraction_search", "general_assistance"]
            
            return state
        except Exception as e:
            state.error = f"Error searching for restaurants: {str(e)}"
            state.next_steps = ["general_assistance"]
            return state
    
    def attraction_search(state: AgentState) -> AgentState:
        """Handle attraction search requests"""
        try:
            agent = create_travel_agent()
            
            # Get the last message from the user
            if state.messages:
                last_message = state.messages[-1].content
            else:
                last_message = "I need help finding attractions."
            
            # Append context that we're focused on attractions
            focused_message = f"Focus on finding tourist attractions. {last_message}"
            
            response = agent.invoke({"input": focused_message})
            
            # Update the state with the agent's response
            state.messages.append(HumanMessage(content=response["output"]))
            
            # Extract attraction information if possible and store in travel plan
            if "attraction" in response["output"].lower() or "place" in response["output"].lower():
                # This is a simplification - in a production system, we would parse the attraction data more carefully
                state.travel_plan.attractions = [{"summary": response["output"]}]
            
            # Update next steps
            state.next_steps = ["create_itinerary", "general_assistance"]
            
            return state
        except Exception as e:
            state.error = f"Error searching for attractions: {str(e)}"
            state.next_steps = ["general_assistance"]
            return state
    
    def create_itinerary(state: AgentState) -> AgentState:
        """Create a comprehensive travel itinerary"""
        try:
            agent = create_travel_agent()
            
            # Get the last message from the user
            if state.messages:
                last_message = state.messages[-1].content
            else:
                last_message = "I need help creating an itinerary."
            
            # Append context that we're focused on creating an itinerary
            focused_message = f"Focus on creating a comprehensive travel itinerary. {last_message}"
            
            response = agent.invoke({"input": focused_message})
            
            # Update the state with the agent's response
            state.messages.append(HumanMessage(content=response["output"]))
            
            # Extract itinerary information if possible and store in travel plan
            if "day" in response["output"].lower() and "itinerary" in response["output"].lower():
                # This is a simplification - in a production system, we would parse the itinerary data more carefully
                state.travel_plan.itinerary = [{"summary": response["output"]}]
            
            # Update next steps - after itinerary, we're basically done
            state.next_steps = ["finalize_plan"]
            
            return state
        except Exception as e:
            state.error = f"Error creating itinerary: {str(e)}"
            state.next_steps = ["general_assistance"]
            return state
    
    def general_assistance(state: AgentState) -> AgentState:
        """Provide general travel assistance"""
        try:
            agent = create_travel_agent()
            
            # Get the last message from the user
            if state.messages:
                last_message = state.messages[-1].content
            else:
                last_message = "I need general travel assistance."
            
            # If there was an error in a previous step, include it in the message
            if state.error:
                last_message = f"{last_message} Note: There was an issue earlier: {state.error}"
                # Clear the error after addressing it
                state.error = None
            
            response = agent.invoke({"input": last_message})
            
            # Update the state with the agent's response
            state.messages.append(HumanMessage(content=response["output"]))
            
            # Determine next steps based on the response
            if "flight" in response["output"].lower():
                state.next_steps = ["flight_search"]
            elif "hotel" in response["output"].lower():
                state.next_steps = ["hotel_search"]
            elif "restaurant" in response["output"].lower():
                state.next_steps = ["restaurant_search"]
            elif "attraction" in response["output"].lower():
                state.next_steps = ["attraction_search"]
            elif "itinerary" in response["output"].lower():
                state.next_steps = ["create_itinerary"]
            else:
                state.next_steps = ["finalize_plan"]
            
            return state
        except Exception as e:
            state.error = f"Error providing general assistance: {str(e)}"
            state.next_steps = ["finalize_plan"]
            return state
    
    def finalize_plan(state: AgentState) -> AgentState:
        """Finalize the travel plan and provide a summary"""
        try:
            agent = create_travel_agent()
            
            summary_prompt = """
            Based on our conversation so far, please provide a comprehensive summary of the travel plan.
            Include details about flights, accommodations, restaurants, attractions, and the itinerary.
            """
            
            response = agent.invoke({"input": summary_prompt})
            
            # Update the state with the agent's response
            state.messages.append(HumanMessage(content=response["output"]))
            
            # End the workflow
            return state
        except Exception as e:
            state.error = f"Error finalizing travel plan: {str(e)}"
            # Still end the workflow even if there's an error
            state.messages.append(HumanMessage(content=f"I apologize, but I encountered an error while finalizing your travel plan: {str(e)}. Please review the information provided earlier or start a new planning session."))
            return state
    
    # Add nodes to the graph
    workflow.add_node("initialize", initialize)
    workflow.add_node("flight_search", flight_search)
    workflow.add_node("hotel_search", hotel_search)
    workflow.add_node("restaurant_search", restaurant_search)
    workflow.add_node("attraction_search", attraction_search)
    workflow.add_node("create_itinerary", create_itinerary)
    workflow.add_node("general_assistance", general_assistance)
    workflow.add_node("finalize_plan", finalize_plan)
    
    # Define conditional routing based on current_step
    def route_by_step(state: AgentState) -> str:
        """Route to the next step based on the current state."""
        # If there are explicit next steps defined, use the first one
        if state.next_steps:
            return state.next_steps[0]
        
        # Default routing based on current_step
        return state.current_step
    
    # Define the edges of the graph
    workflow.add_conditional_edges(
        "initialize",
        route_by_step,
        {
            "flight_search": "flight_search",
            "hotel_search": "hotel_search",
            "restaurant_search": "restaurant_search",
            "attraction_search": "attraction_search",
            "create_itinerary": "create_itinerary",
            "general_assistance": "general_assistance"
        }
    )
    
    workflow.add_conditional_edges(
        "flight_search",
        route_by_step,
        {
            "hotel_search": "hotel_search",
            "general_assistance": "general_assistance"
        }
    )
    
    workflow.add_conditional_edges(
        "hotel_search",
        route_by_step,
        {
            "restaurant_search": "restaurant_search",
            "general_assistance": "general_assistance"
        }
    )
    
    workflow.add_conditional_edges(
        "restaurant_search",
        route_by_step,
        {
            "attraction_search": "attraction_search",
            "general_assistance": "general_assistance"
        }
    )
    
    workflow.add_conditional_edges(
        "attraction_search",
        route_by_step,
        {
            "create_itinerary": "create_itinerary",
            "general_assistance": "general_assistance"
        }
    )
    
    workflow.add_conditional_edges(
        "create_itinerary",
        route_by_step,
        {
            "finalize_plan": "finalize_plan"
        }
    )
    
    workflow.add_conditional_edges(
        "general_assistance",
        route_by_step,
        {
            "flight_search": "flight_search",
            "hotel_search": "hotel_search",
            "restaurant_search": "restaurant_search",
            "attraction_search": "attraction_search",
            "create_itinerary": "create_itinerary",
            "finalize_plan": "finalize_plan"
        }
    )
    
    workflow.add_edge("finalize_plan", END)
    
    # Set the entry point
    workflow.set_entry_point("initialize")
    
    return workflow

# Create a function to run the travel planner with improved error handling
def run_travel_planner(user_input: str) -> str:
    """
    Run the travel planner workflow with the given user input.
    
    Args:
        user_input: The initial user query or request
        
    Returns:
        str: The final response from the travel planner
    """
    try:
        # Initialize the travel plan
        initial_travel_plan = TravelPlan(
            destination=Location(city=""),
            dates=TravelDates(start_date="", end_date=""),
            preferences=TravelPreferences(budget_level="", interests=[])
        )
        
        # Initialize the state
        initial_state = AgentState(
            travel_plan=initial_travel_plan,
            messages=[HumanMessage(content=user_input)],
            current_step="initialize",
            next_steps=[]
        )
        
        # Build and compile the graph
        graph = build_travel_planner_graph()
        app = graph.compile()
        
        # Run the workflow with timeout handling
        result = app.invoke(initial_state)
        
        # Extract the final response
        if result.messages:
            return result.messages[-1].content
        else:
            return "I couldn't generate a travel plan. Please try again with more details."
    except Exception as e:
        return f"An error occurred while planning your trip: {str(e)}. Please try again with more specific details."

# Example usage
if __name__ == "__main__":
    user_query = "I want to plan a trip to Tokyo for 5 days in April 2025. I'm interested in food, technology, and traditional culture. I need help with flights from New York, hotel recommendations, and an itinerary."
    
    try:
        response = run_travel_planner(user_query)
        print(response)
    except Exception as e:
        print(f"Error running travel planner: {str(e)}")