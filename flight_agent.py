import os
import re
from typing import Dict, List, Any, TypedDict, Annotated, Sequence
from datetime import datetime

# Import the functions from the provided flight_search.py file
from flight_search import parse_flight_query, get_city_skyid, search_flights, search_flights_from_query

# Import LangGraph components
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent

# Define state types
class AgentState(TypedDict):
    messages: List[Dict[str, Any]]
    flight_query: str
    parsed_params: Dict[str, Any]
    from_city_id: str
    to_city_id: str
    flights: List[Dict[str, Any]]
    error: str

# Define the initial state
def create_initial_state() -> AgentState:
    return {
        "messages": [],
        "flight_query": "",
        "parsed_params": {},
        "from_city_id": "",
        "to_city_id": "",
        "flights": [],
        "error": ""
    }

# Node 1: Parse the flight query
def parse_query(state: AgentState) -> AgentState:
    flight_query = state["flight_query"]
    print(f"🔍 Parsing query: {flight_query}")
    
    try:
        parsed_params = parse_flight_query(flight_query)
        state["parsed_params"] = parsed_params
        print(f"✅ Query parsed successfully: {parsed_params}")
    except Exception as e:
        state["error"] = f"Error parsing query: {str(e)}"
        print(f"❌ {state['error']}")
    
    return state

# Node 2: Get city IDs
def get_city_ids(state: AgentState) -> AgentState:
    if state["error"]:
        return state
    
    params = state["parsed_params"]
    
    try:
        # Get origin city ID
        if params["from_entity_id"]:
            print(f"🔍 Looking up SkyID for origin: {params['from_entity_id']}")
            from_city_id = get_city_skyid(params["from_entity_id"])
            if from_city_id:
                state["from_city_id"] = from_city_id
                print(f"✅ Found origin SkyID: {from_city_id}")
            else:
                state["error"] = f"Could not find SkyID for origin city: {params['from_entity_id']}"
                print(f"❌ {state['error']}")
                return state
        else:
            state["error"] = "No origin location specified in the query"
            print(f"❌ {state['error']}")
            return state
        
        # Get destination city ID
        if params["to_entity_id"]:
            print(f"🔍 Looking up SkyID for destination: {params['to_entity_id']}")
            to_city_id = get_city_skyid(params["to_entity_id"])
            if to_city_id:
                state["to_city_id"] = to_city_id
                print(f"✅ Found destination SkyID: {to_city_id}")
            else:
                state["error"] = f"Could not find SkyID for destination city: {params['to_entity_id']}"
                print(f"❌ {state['error']}")
                return state
        else:
            state["error"] = "No destination location specified in the query"
            print(f"❌ {state['error']}")
            return state
    except Exception as e:
        state["error"] = f"Error getting city IDs: {str(e)}"
        print(f"❌ {state['error']}")
    
    return state

# Node 3: Search for flights
def search_for_flights(state: AgentState) -> AgentState:
    if state["error"]:
        return state
    
    params = state["parsed_params"]
    from_entity_id = state["from_city_id"]
    to_entity_id = state["to_city_id"]
    
    try:
        print(f"🔍 Searching for flights from {from_entity_id} to {to_entity_id}")
        
        flights = search_flights(
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            depart_date=params["depart_date"],
            cabin_class=params["cabin_class"],
            adults=params["adults"],
            children=params["children"],
            infants=params["infants"],
            whole_month_depart=params["depart_date"] if params.get("whole_month", False) else None,
            sort=params["sort"]
        )
        
        if flights:
            state["flights"] = flights
            print(f"✅ Found {len(flights)} flights")
        else:
            state["error"] = "No flights found matching your criteria"
            print(f"❌ {state['error']}")
    except Exception as e:
        state["error"] = f"Error searching for flights: {str(e)}"
        print(f"❌ {state['error']}")
    
    return state

# Node 4: Format flight results
def format_flight_results(state: AgentState) -> AgentState:
    flights = state["flights"]
    
    if not flights:
        if not state["error"]:
            state["error"] = "No flights found"
        return state
    
    # Sort flights by price
    try:
        flights = sorted(flights, key=lambda x: extract_price(x['price_formatted']))
        state["flights"] = flights
    except Exception as e:
        print(f"⚠️ Warning: Could not sort flights by price: {str(e)}")
    
    # Add formatted flight output to messages
    formatted_output = format_flights_table(flights)
    
    state["messages"].append({
        "role": "assistant",
        "content": formatted_output
    })
    
    return state

# Helper function to extract price as a number
def extract_price(price_str: str) -> float:
    try:
        # Remove currency symbol and commas, then convert to float
        price = re.sub(r'[^\d.]', '', price_str)
        return float(price) if price else float('inf')
    except:
        return float('inf')  # Return infinity if conversion fails

# Helper function to format flight results as a table
def format_flights_table(flights: List[Dict[str, Any]]) -> str:
    output = []
    
    # Add header
    output.append(f"{'Carrier':<40} {'Duration':<10} {'Price':<10} {'Stops':<5} {'Departure':<20} {'Arrival':<20}")
    output.append("-" * 120)
    
    # Add flight information
    for flight in flights:
        output.append(f"{flight['carrier'][:39]:<40} {flight['duration']:<10} {flight['price_formatted']:<10} {flight['stops']:<5} {flight['departure_time']:<20} {flight['arrival_time']:<20}")
    
    # Add summary
    output.append(f"\nFound {len(flights)} flights matching your criteria.")
    
    if flights:
        # Add cheapest and fastest options
        cheapest = min(flights, key=lambda x: extract_price(x['price_formatted']))
        output.append(f"Cheapest option: {cheapest['carrier']} for {cheapest['price_formatted']} ({cheapest['duration']})")
        
        fastest = min(flights, key=lambda x: extract_minutes(x['duration']))
        output.append(f"Fastest option: {fastest['carrier']} in {fastest['duration']} ({fastest['price_formatted']})")
    
    return "\n".join(output)

# Helper function to extract total minutes from duration string
def extract_minutes(duration: str) -> int:
    try:
        # Extract hours and minutes using regex
        hours_match = re.search(r'(\d+)h', duration)
        minutes_match = re.search(r'(\d+)m', duration)
        
        hours = int(hours_match.group(1)) if hours_match else 0
        minutes = int(minutes_match.group(1)) if minutes_match else 0
        
        return hours * 60 + minutes
    except:
        return float('inf')  # Return infinity if conversion fails

# LangGraph workflow definition
def create_flight_search_agent():
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("parse_query", parse_query)
    workflow.add_node("get_city_ids", get_city_ids)
    workflow.add_node("search_for_flights", search_for_flights)
    workflow.add_node("format_flight_results", format_flight_results)
    
    # Define the edges
    workflow.add_edge("parse_query", "get_city_ids")
    workflow.add_edge("get_city_ids", "search_for_flights")
    workflow.add_edge("search_for_flights", "format_flight_results")
    workflow.add_edge("format_flight_results", END)
    
    # Define error handling
    workflow.add_conditional_edges(
        "parse_query",
        lambda state: "error" if state["error"] else "get_city_ids",
        {
            "error": END,
            "get_city_ids": "get_city_ids"
        }
    )
    
    workflow.add_conditional_edges(
        "get_city_ids",
        lambda state: "error" if state["error"] else "search_for_flights",
        {
            "error": END,
            "search_for_flights": "search_for_flights"
        }
    )
    
    workflow.add_conditional_edges(
        "search_for_flights",
        lambda state: "error" if state["error"] else "format_flight_results",
        {
            "error": END,
            "format_flight_results": "format_flight_results"
        }
    )
    
    # Set the entry point
    workflow.set_entry_point("parse_query")
    
    return workflow.compile()

# Main function to run the flight search agent
def run_flight_search(query: str) -> str:
    # Initialize the agent
    agent = create_flight_search_agent()
    
    # Create the initial state
    state = create_initial_state()
    state["flight_query"] = query
    
    # Execute the workflow
    result = agent.invoke(state)
    
    # Handle errors
    if result["error"]:
        return f"Error: {result['error']}"
    
    # Return the formatted flight results
    if result["messages"]:
        return result["messages"][-1]["content"]
    else:
        return "No results found."

# Alternative simpler implementation that uses the search_flights_from_query function directly
def simple_flight_search(query: str) -> str:
    try:
        print(f"🔍 Searching for flights: {query}")
        flights = search_flights_from_query(query)
        
        if not flights:
            return "No flights found matching your criteria."
        
        # Sort flights by price
        flights = sorted(flights, key=lambda x: extract_price(x['price_formatted']))
        
        # Format results as table
        return format_flights_table(flights)
    except Exception as e:
        return f"Error searching for flights: {str(e)}"

# Interactive CLI interface
def main():
    print("""
█▀▀ █░░ █ █▀▀ █░█ ▀█▀   █▀ █▀▀ ▄▀█ █▀█ █▀▀ █░█
█▀░ █▄▄ █ █▄█ █▀█ ░█░   ▄█ ██▄ █▀█ █▀▄ █▄▄ █▀█

Welcome to the LangGraph Flight Search Agent!
You can search for flights using natural language queries.
For example:
- "What are the cheapest flights from Delhi to Mumbai on April 15th, 2025 in economy class?"
- "Show me business class flights from New York to London next month"
- "Find flights from Tokyo to Los Angeles on December 25th, 2025 for 2 adults and 1 child"

Type 'exit' or 'quit' to end the session.
    """)
    
    while True:
        # Get user query
        query = input("\n🔍 Enter your flight search query: ")
        
        # Check if user wants to exit
        if query.lower() in ['exit', 'quit']:
            print("\nThank you for using the Flight Search Agent. Have a great day!")
            break
        
        print("\nSearching for flights, please wait...\n")
        
        # Process using the simpler implementation for now
        # We could switch between simple_flight_search and run_flight_search here
        results = simple_flight_search(query)
        print(results)

if __name__ == "__main__":
    main()