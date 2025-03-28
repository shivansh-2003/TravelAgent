import streamlit as st
import json
import datetime
import pandas as pd
import folium
from streamlit_folium import st_folium
from PIL import Image
from io import BytesIO
import base64
import re
import os
import random
from io import StringIO
import uuid
from dotenv import load_dotenv

# Import the custom header animation
from header import animated_text

# Import agent.py components for modular design
from agent import (
    search_flights_tool, 
    search_hotels_tool,
    search_restaurants_tool,
    find_attractions_tool,
    create_itinerary_tool,
    run_travel_planner,
    TravelPlan,
    Location,
    TravelDates,
    TravelPreferences,
    AgentState,
    HumanMessage,
    create_travel_agent
)

# Import your backend travel functions for direct access if needed
from flight_search import search_flights_from_query, search_flights
from hotel_details import fetch_hotels, format_hotel_data, fetch_hotel_details, extract_key_info
from restaurants import fetch_restaurants, format_restaurant_data, fetch_restaurant_details
from travel import fetch_places, get_place_details

# Import LangChain components
from langchain.agents import Tool, AgentExecutor, ZeroShotAgent, initialize_agent
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool
from typing import Optional, Type
from langchain.pydantic_v1 import BaseModel, Field

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure Streamlit page
st.set_page_config(
    page_title="AI Travel Buddy",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
def load_css():
    css = """
    <style>
        /* Main Styles */
        .main {
            background-color: #f8f9fa;
            padding: 2rem;
        }
        
        /* Cards */
        .card {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
            transition: transform 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
        }
        
        /* Animated Button */
        .animated-button {
            display: inline-block;
            padding: 12px 24px;
            background: linear-gradient(45deg, #00c2ff, #33ff8c, #ffc640, #e54cff);
            background-size: 300% 300%;
            color: white;
            border-radius: 50px;
            border: none;
            cursor: pointer;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s ease;
            animation: gradient-animation 5s ease infinite;
        }
        
        @keyframes gradient-animation {
            0% {
                background-position: 0% 50%;
            }
            50% {
                background-position: 100% 50%;
            }
            100% {
                background-position: 0% 50%;
            }
        }
        
        .animated-button:hover {
            transform: scale(1.05);
            box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
        }
        
        /* Chat UI */
        .chat-message {
            padding: 1.5rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            display: flex;
        }
        
        .chat-message.user {
            background-color: #2b313e;
            color: #fff;
            border-radius: 10px 10px 0 10px;
        }
        
        .chat-message.bot {
            background-color: #475063;
            color: #fff;
            border-radius: 10px 10px 10px 0;
        }
        
        .chat-message .avatar {
            width: 20%;
        }
        
        .chat-message .avatar img {
            max-width: 78px;
            max-height: 78px;
            border-radius: 50%;
            object-fit: cover;
        }
        
        .chat-message .message {
            width: 80%;
            padding: 0 1.5rem;
        }
        
        /* Flip Card */
        .flip-card {
            background-color: transparent;
            width: 100%;
            height: 400px;
            perspective: 1000px;
            margin-bottom: 20px;
        }
        
        .flip-card-inner {
            position: relative;
            width: 100%;
            height: 100%;
            text-align: center;
            transition: transform 0.6s;
            transform-style: preserve-3d;
            box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
        }
        
        .flip-card:hover .flip-card-inner {
            transform: rotateY(180deg);
        }
        
        .flip-card-front, .flip-card-back {
            position: absolute;
            width: 100%;
            height: 100%;
            -webkit-backface-visibility: hidden;
            backface-visibility: hidden;
            border-radius: 10px;
        }
        
        .flip-card-front {
            background-color: #fff;
            color: black;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        
        .flip-card-back {
            background: linear-gradient(45deg, #00c2ff, #33ff8c);
            color: white;
            transform: rotateY(180deg);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            overflow-y: auto;
        }
        
        /* Place cards */
        .place-card {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            transition: transform 0.3s ease;
        }
        
        .place-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        }
        
        .place-card img {
            width: 100%;
            height: 200px;
            object-fit: cover;
        }
        
        .place-card-content {
            padding: 15px;
        }
        
        .place-card-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .place-card-rating {
            color: #FFD700;
            margin-bottom: 10px;
        }
        
        .place-card-description {
            font-size: 14px;
            color: #555;
        }
        
        /* Animated title */
        .animated-title {
            font-size: 36px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 20px;
            animation: slideIn 2s ease-out;
        }

        @keyframes slideIn {
            from {
                transform: translateX(-100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        /* Timeline */
        .timeline {
            position: relative;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .timeline::after {
            content: '';
            position: absolute;
            width: 6px;
            background-color: #33ff8c;
            top: 0;
            bottom: 0;
            left: 50%;
            margin-left: -3px;
        }
        
        .timeline-container {
            padding: 10px 40px;
            position: relative;
            background-color: inherit;
            width: 50%;
        }
        
        .timeline-container::after {
            content: '';
            position: absolute;
            width: 25px;
            height: 25px;
            background-color: white;
            border: 4px solid #00c2ff;
            border-radius: 50%;
            top: 15px;
            z-index: 1;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'travel_plan' not in st.session_state:
    st.session_state.travel_plan = {}
if 'city' not in st.session_state:
    st.session_state.city = ""
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Chat"
if 'flights' not in st.session_state:
    st.session_state.flights = []
if 'hotels' not in st.session_state:
    st.session_state.hotels = []
if 'restaurants' not in st.session_state:
    st.session_state.restaurants = []
if 'attractions' not in st.session_state:
    st.session_state.attractions = []
if 'itinerary' not in st.session_state:
    st.session_state.itinerary = []
if 'agent' not in st.session_state:
    st.session_state.agent = None

# Load CSS
load_css()

# Initialize the agent if not already done
if st.session_state.agent is None:
    with st.spinner("Initializing AI Travel Agent..."):
        try:
            st.session_state.agent = create_travel_agent()
        except Exception as e:
            st.error(f"Error initializing agent: {str(e)}")
            st.session_state.agent = None

# Placeholder function for image display
def get_place_image(place_name, default_image=None):
    # In a real implementation, this would fetch actual images
    # For now, use placeholder images
    return default_image or f"https://placehold.co/600x400/skyblue/white?text={place_name.replace(' ', '+')}"

# UI Components
def render_chat_interface():
    st.markdown("<h1 class='animated-title'>AI Travel Buddy</h1>", unsafe_allow_html=True)
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("What's your travel plan?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process with agent
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Check if the query has specific travel planning intent
                    if any(keyword in prompt.lower() for keyword in ["trip", "travel", "plan", "itinerary", "visit"]):
                        # Use the more powerful run_travel_planner for comprehensive travel plans
                        response = run_travel_planner(prompt)
                    elif st.session_state.agent:
                        # Use the regular agent for simpler queries
                        response = st.session_state.agent.run(prompt)
                    else:
                        response = "I'm not fully initialized yet. Please try again in a moment."
                        
                    # Extract city from user message if present
                    city_match = re.search(r'to\s+([A-Za-z\s]+)', prompt, re.IGNORECASE)
                    if city_match:
                        city = city_match.group(1).strip()
                        st.session_state.city = city
                except Exception as e:
                    response = str(e)
                    if "Could not parse LLM output" in response:
                        response = "I'm having trouble understanding. Could you phrase that differently?"
                
                st.markdown(response)
                
                # Add assistant message to chat history
                st.session_state.messages.append({"role": "assistant", "content": response})

def render_dashboard():
    cols = st.columns([1, 2, 1])
    with cols[1]:
        animated_text("Your Travel Journey")
    
    # Destination overview
    st.markdown("## 🌍 Destination Overview")
    
    cols = st.columns(2)
    with cols[0]:
        destination = st.text_input("Where do you want to go?", value=st.session_state.city)
        if destination != st.session_state.city:
            st.session_state.city = destination
            # Clear previous data when destination changes
            st.session_state.flights = []
            st.session_state.hotels = []
            st.session_state.restaurants = []
            st.session_state.attractions = []
            st.session_state.itinerary = []
    
    with cols[1]:
        start_date = st.date_input("Start Date", value=datetime.datetime.now() + datetime.timedelta(days=30))
        end_date = st.date_input("End Date", value=datetime.datetime.now() + datetime.timedelta(days=33))
    
    if st.session_state.city:
        # Create tabs for different sections
        tabs = st.tabs(["Flights", "Hotels", "Restaurants", "Attractions", "Itinerary"])
        
        # Flights tab
        with tabs[0]:
            st.markdown("## ✈️ Flight Options")
            
            if not st.session_state.flights:
                origin_city = st.text_input("From city", "New York")
                if st.button("Search Flights"):
                    with st.spinner("Searching for flights..."):
                        try:
                            # Use the search_flights_tool from agent.py
                            query = f"Find flights from {origin_city} to {st.session_state.city}"
                            result = search_flights_tool(query)
                            
                            # Extract flights from result if available
                            if "No flights found" not in result:
                                # The flights should now be stored in session state via the tool
                                st.success("Flights found!")
                            else:
                                st.error("No flights found. Please try different cities.")
                        except Exception as e:
                            st.error(f"Error searching for flights: {str(e)}")
            else:
                for i, flight in enumerate(st.session_state.flights):
                    with st.container():
                        st.markdown(f"### {flight['carrier']}")
                        cols = st.columns(3)
                        with cols[0]:
                            st.markdown(f"**From:** {flight['origin']}")
                            st.markdown(f"**To:** {flight['destination']}")
                        with cols[1]:
                            st.markdown(f"**Departure:** {flight['departure_time']}")
                            st.markdown(f"**Arrival:** {flight['arrival_time']}")
                            st.markdown(f"**Duration:** {flight['duration']}")
                        with cols[2]:
                            st.markdown(f"**Price:** {flight['price_formatted']}")
                            st.markdown(f"**Stops:** {flight['stops']}")
                            st.button("Select", key=f"flight_{i}")
        
        # Hotels tab
        with tabs[1]:
            st.markdown("## 🏨 Hotel Options")
            
            if not st.session_state.hotels:
                if st.button("Search Hotels"):
                    with st.spinner("Searching for hotels..."):
                        try:
                            # Use the search_hotels_tool from agent.py
                            result = search_hotels_tool(st.session_state.city)
                            
                            # Extract hotel info if available
                            if "No hotels found" not in result:
                                # Parse hotel data and add to session state
                                hotel_data = fetch_hotels(st.session_state.city)
                                if hotel_data:
                                    _, hotel_ids = format_hotel_data(hotel_data)
                                    
                                    # Fetch details for top hotels
                                    hotels = []
                                    for i in range(1, min(4, len(hotel_ids) + 1)):
                                        if i in hotel_ids:
                                            hotel_id = hotel_ids[i]
                                            hotel_details = fetch_hotel_details(hotel_id)
                                            if hotel_details:
                                                info = extract_key_info(hotel_details)
                                                hotels.append({
                                                    "name": info.get("name", "Unknown Hotel"),
                                                    "rating": info.get("rating", "N/A"),
                                                    "address": info.get("address", "N/A"),
                                                    "price_range": info.get("price_range", "N/A"),
                                                    "amenities": info.get("keywords", [])[:5],
                                                    "image": info.get("featured_image", "")
                                                })
                                    
                                    st.session_state.hotels = hotels
                                    st.success("Hotels found!")
                            else:
                                st.error("No hotels found. Please try a different city.")
                        except Exception as e:
                            st.error(f"Error searching for hotels: {str(e)}")
            else:
                cols = st.columns(len(st.session_state.hotels))
                for i, hotel in enumerate(st.session_state.hotels):
                    with cols[i]:
                        st.markdown(f"### {hotel['name']}")
                        
                        # Display hotel image
                        image_url = hotel.get('image') or get_place_image(hotel['name'])
                        st.image(image_url, use_column_width=True)
                        
                        st.markdown(f"**Rating:** {'⭐' * int(float(hotel['rating']))}")
                        st.markdown(f"**Price:** {hotel['price_range']}")
                        st.markdown(f"**Address:** {hotel['address']}")
                        
                        if hotel.get('amenities'):
                            st.markdown("**Amenities:** " + ", ".join(hotel['amenities']))
                            
                        st.button("Select", key=f"hotel_{i}")
        
        # Restaurants tab
        with tabs[2]:
            st.markdown("## 🍽️ Restaurant Recommendations")
            
            if not st.session_state.restaurants:
                if st.button("Search Restaurants"):
                    with st.spinner("Searching for restaurants..."):
                        try:
                            # Use the search_restaurants_tool from agent.py
                            result = search_restaurants_tool(st.session_state.city)
                            
                            # Extract restaurant info if available
                            if "No restaurants found" not in result:
                                # Parse restaurant data and add to session state
                                restaurant_data = fetch_restaurants(st.session_state.city)
                                if restaurant_data:
                                    _, restaurant_ids = format_restaurant_data(restaurant_data)
                                    
                                    # Fetch details for top restaurants
                                    restaurants = []
                                    for i in range(1, min(4, len(restaurant_ids) + 1)):
                                        if i in restaurant_ids:
                                            restaurant_id = restaurant_ids[i]
                                            restaurant_details = fetch_restaurant_details(restaurant_id)
                                            if restaurant_details:
                                                cuisine_types = restaurant_details.get("cuisines", ["Unknown"])
                                                restaurants.append({
                                                    "name": restaurant_details.get("name", "Unknown Restaurant"),
                                                    "rating": restaurant_details.get("rating", "N/A"),
                                                    "cuisine": ", ".join(cuisine_types),
                                                    "price_level": "$$" if len(cuisine_types) > 1 else "$",
                                                    "address": restaurant_details.get("address", "N/A"),
                                                    "image": restaurant_details.get("featured_image", "")
                                                })
                                    
                                    st.session_state.restaurants = restaurants
                                    st.success("Restaurants found!")
                            else:
                                st.error("No restaurants found. Please try a different city.")
                        except Exception as e:
                            st.error(f"Error searching for restaurants: {str(e)}")
            else:
                cols = st.columns(len(st.session_state.restaurants))
                for i, restaurant in enumerate(st.session_state.restaurants):
                    with cols[i]:
                        st.markdown(f"### {restaurant['name']}")
                        
                        # Display restaurant image
                        image_url = restaurant.get('image') or get_place_image(restaurant['name'], "https://placehold.co/600x400/brown/white?text=Restaurant")
                        st.image(image_url, use_column_width=True)
                        
                        st.markdown(f"**Rating:** {'⭐' * int(float(restaurant['rating']))}")
                        st.markdown(f"**Cuisine:** {restaurant['cuisine']}")
                        st.markdown(f"**Price Level:** {restaurant['price_level']}")
                        st.markdown(f"**Address:** {restaurant['address']}")
                        
                        st.button("View Details", key=f"restaurant_{i}")
        
        # Attractions tab
        with tabs[3]:
            st.markdown("## 🏛️ Top Attractions")
            
            if not st.session_state.attractions:
                if st.button("Search Attractions"):
                    with st.spinner("Searching for attractions..."):
                        try:
                            # Use the find_attractions_tool from agent.py
                            result = find_attractions_tool(st.session_state.city)
                            
                            # Extract attraction info if available
                            if "No attractions found" not in result:
                                # Process the results
                                places = fetch_places(st.session_state.city)
                                
                                # Process attractions and store in session state
                                attractions = []
                                for i, place in enumerate(places[:5], 1):
                                    place_name = place.get("name", "Unknown")
                                    place_details = get_place_details(place_name)
                                    
                                    # Add to attractions list
                                    attractions.append({
                                        "name": place_name,
                                        "rating": place.get('rating', 4.5),
                                        "description": str(place_details)[:300] + "..." if len(str(place_details)) > 300 else place_details,
                                        "address": place.get('formatted_address', 'N/A'),
                                        "image": ""  # Placeholder for image URL
                                    })
                                
                                st.session_state.attractions = attractions
                                st.success("Attractions found!")
                            else:
                                st.error("No attractions found. Please try a different city.")
                        except Exception as e:
                            st.error(f"Error searching for attractions: {str(e)}")
            else:
                cols = st.columns(len(st.session_state.attractions))
                for i, attraction in enumerate(st.session_state.attractions):
                    with cols[i]:
                        st.markdown(f"### {attraction['name']}")
                        
                        # Display attraction image
                        image_url = attraction.get('image') or get_place_image(attraction['name'], "https://placehold.co/600x400/green/white?text=Attraction")
                        st.image(image_url, use_column_width=True)
                        
                        st.markdown(f"**Rating:** {'⭐' * int(float(attraction['rating']))}")
                        st.markdown(f"**Address:** {attraction['address']}")
                        
                        with st.expander("View Description"):
                            st.write(attraction['description'])
                            
                        st.button("Add to Itinerary", key=f"attraction_{i}")
        
        # Itinerary tab
        with tabs[4]:
            st.markdown("## 📅 Your Itinerary")
            
            if not st.session_state.itinerary:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Generate Itinerary"):
                        with st.spinner("Creating your itinerary..."):
                            try:
                                # Use the create_itinerary_tool from agent.py
                                # Calculate number of days
                                num_days = (end_date - start_date).days + 1
                                
                                # Format interests from user preferences or default ones
                                interests = ["food", "culture", "sightseeing"]  # Default interests
                                
                                result = create_itinerary_tool(
                                    destination=st.session_state.city,
                                    start_date=start_date.strftime("%Y-%m-%d"),
                                    end_date=end_date.strftime("%Y-%m-%d"),
                                    interests=interests
                                )
                                
                                if "Error creating itinerary" not in result:
                                    # Parse the generated itinerary
                                    # This is a simplified version that creates a structured itinerary
                                    itinerary = []
                                    for i in range(num_days):
                                        current_date = start_date + datetime.timedelta(days=i)
                                        date_str = current_date.strftime("%Y-%m-%d")
                                        
                                        day_plan = {
                                            "day": i + 1,
                                            "date": date_str,
                                            "activities": []
                                        }
                                        
                                        # Adding some default activities
                                        day_plan["activities"].append({
                                            "time": "09:00",
                                            "activity": f"Breakfast at hotel" if i == 0 else f"Breakfast at local café",
                                            "description": "Start your day with a delicious breakfast"
                                        })
                                        
                                        day_plan["activities"].append({
                                            "time": "10:30",
                                            "activity": f"Explore {st.session_state.city}",
                                            "description": f"Discover the beauty of {st.session_state.city}"
                                        })
                                        
                                        day_plan["activities"].append({
                                            "time": "13:00",
                                            "activity": "Lunch at local restaurant",
                                            "description": "Enjoy authentic local cuisine"
                                        })
                                        
                                        day_plan["activities"].append({
                                            "time": "15:00",
                                            "activity": f"Visit a landmark in {st.session_state.city}",
                                            "description": "Experience the local culture and history"
                                        })
                                        
                                        day_plan["activities"].append({
                                            "time": "19:00",
                                            "activity": "Dinner experience",
                                            "description": "Taste the local delicacies"
                                        })
                                        
                                        itinerary.append(day_plan)
                                    
                                    st.session_state.itinerary = itinerary
                                    st.success("Itinerary created!")
                                else:
                                    st.error("Failed to create itinerary. Please try again.")
                            except Exception as e:
                                st.error(f"Error creating itinerary: {str(e)}")
                with col2:
                    st.markdown("""
                    Your personalized itinerary will include:
                    - Day-by-day activities
                    - Recommended dining options
                    - Time management
                    - Transportation suggestions
                    - Cultural experiences
                    """)
            else:
                # Display the itinerary in a timeline format
                for day in st.session_state.itinerary:
                    with st.expander(f"Day {day['day']} - {day['date']}"):
                        for activity in day['activities']:
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.markdown(f"**{activity['time']}**")
                            with col2:
                                st.markdown(f"**{activity['activity']}**")
                                st.markdown(f"{activity['description']}")
                                st.markdown("---")
                
                # Add download button for the itinerary
                itinerary_text = "\n\n".join([
                    f"Day {day['day']} - {day['date']}:\n" + 
                    "\n".join([f"  {activity['time']} - {activity['activity']}: {activity['description']}" 
                               for activity in day['activities']])
                    for day in st.session_state.itinerary
                ])
                
                st.download_button(
                    label="Download Itinerary",
                    data=itinerary_text,
                    file_name=f"{st.session_state.city}_itinerary.txt",
                    mime="text/plain"
                )
                
                # Map view of the itinerary
                st.markdown("### Map View")
                try:
                    # Create a map centered on the destination
                    m = folium.Map(location=[35.6762, 139.6503], zoom_start=12)  # Default to Tokyo coordinates
                    
                    # In a real implementation, we would add actual attraction coordinates
                    # For now, add a few sample markers
                    for i, day in enumerate(st.session_state.itinerary):
                        for j, activity in enumerate(day['activities']):
                            if 'activity' in activity and not activity['activity'].startswith("Breakfast") and not activity['activity'].startswith("Lunch") and not activity['activity'].startswith("Dinner"):
                                # Add a slight offset for each day to spread markers
                                lat_offset = i * 0.01
                                lng_offset = j * 0.01
                                folium.Marker(
                                    [35.6762 + lat_offset, 139.6503 + lng_offset],
                                    popup=f"Day {day['day']}: {activity['activity']}",
                                    tooltip=activity['activity']
                                ).add_to(m)
                    
                    # Display the map
                    st_folium(m, width=800, height=500)
                except Exception as e:
                    st.error(f"Error displaying map: {str(e)}")
                    st.markdown("Map view is not available.")

def main():
    # State management
    if st.sidebar.button("New Trip"):
        st.session_state.messages = []
        st.session_state.travel_plan = {}
        st.session_state.city = ""
        st.session_state.flights = []
        st.session_state.hotels = []
        st.session_state.restaurants = []
        st.session_state.attractions = []
        st.session_state.itinerary = []
    
    # Sidebar navigation
    st.sidebar.title("AI Travel Buddy")
    
    # User profile section
    st.sidebar.markdown("## Your Profile")
    with st.sidebar.expander("Preferences"):
        st.multiselect(
            "Travel Interests",
            ["Culture", "Food", "History", "Nature", "Shopping", "Adventure", "Relaxation"],
            ["Culture", "Food"]
        )
        st.select_slider(
            "Budget Level",
            options=["Budget", "Mid-range", "Luxury"],
            value="Mid-range"
        )
        st.checkbox("Family-friendly")
    
    # Select application view
    app_view = st.sidebar.radio("View", ["Chat", "Dashboard"])
    
    # About section
    with st.sidebar.expander("About"):
        st.markdown("""
        **AI Travel Buddy** helps you plan the perfect trip using advanced AI.
        
        Features:
        - Flight and hotel search
        - Restaurant recommendations
        - Attraction suggestions
        - Personalized itineraries
        
        Version 1.0 - 2023
        """)
    
    # Render selected view
    if app_view == "Chat":
        render_chat_interface()
    else:
        render_dashboard()

if __name__ == "__main__":
    main()