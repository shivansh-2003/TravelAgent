import requests
import json
import os
import dotenv
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import CommaSeparatedListOutputParser

# Load environment variables from .env file
dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5")

def fetch_restaurants(location="new york", page="1", api_key=None):
    """
    Fetch restaurant data from TripAdvisor API.
    
    Args:
        location (str): The location to search for restaurants
        page (str): The page number of results to fetch
        api_key (str): Your RapidAPI key
    
    Returns:
        dict: The JSON response from the API
    """
    if api_key is None:
        api_key = "00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5"
        
    url = "https://tripadvisor-scraper.p.rapidapi.com/restaurants/list"
    
    querystring = {"query": location, "page": page}
    
    headers = {
        "x-rapidapi-key": "00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5",
        "x-rapidapi-host": "tripadvisor-scraper.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making the request: {e}")
        return None

def format_restaurant_data(restaurant_data):
    """
    Format restaurant data into a readable list and store IDs separately.
    
    Args:
        restaurant_data (dict): The JSON response from the TripAdvisor API
    
    Returns:
        tuple: (formatted_result, restaurant_ids_dict)
            - formatted_result: String with formatted restaurant info (without IDs)
            - restaurant_ids_dict: Dictionary mapping restaurant numbers to their IDs
    """
    if not restaurant_data or 'results' not in restaurant_data:
        return "No restaurant data available or invalid response format.", {}
    
    result = f"Found {restaurant_data.get('total_items_count', 0)} restaurants in total. Showing page {restaurant_data.get('current_page', 1)} of {restaurant_data.get('total_pages', 1)}.\n\n"
    
    # Dictionary to store restaurant IDs (not displayed)
    restaurant_ids = {}
    
    for i, restaurant in enumerate(restaurant_data['results'], 1):
        name = restaurant.get('name', 'Unknown Restaurant')
        rating = restaurant.get('rating', 'N/A')
        
        cuisines = ", ".join(restaurant.get('cuisines', ['N/A']))
        
        # Store restaurant ID in dictionary but don't display it in results
        restaurant_id = restaurant.get('id', 'N/A')
        restaurant_ids[i] = restaurant_id
        
        # Display restaurant info without the ID
        result += f"{i}. {name} - Rating: {rating} - Cuisine: {cuisines}\n"
    
    return result, restaurant_ids

def fetch_restaurant_details(restaurant_id, api_key=None):
    """
    Fetch detailed information about a specific restaurant using its TripAdvisor ID.
    
    Args:
        restaurant_id (str): The TripAdvisor ID of the restaurant
        api_key (str): Your RapidAPI key
    
    Returns:
        dict: The JSON response containing restaurant details
    """
    if api_key is None:
        api_key = "00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5"
        
    url = "https://tripadvisor-scraper.p.rapidapi.com/restaurants/detail"
    
    querystring = {"id": str(restaurant_id)}
    
    headers = {
        "x-rapidapi-key": "00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5",
        "x-rapidapi-host": "tripadvisor-scraper.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making the request: {e}")
        return None

def generate_keywords_with_gpt4mini(restaurant_details, openai_api_key):
    """
    Generate keywords using GPT-4 mini via LangChain based on restaurant details.
    
    Args:
        restaurant_details (dict): Restaurant details data
        openai_api_key (str): OpenAI API key
    
    Returns:
        list: Generated keywords
    """
    # Initialize the output parser
    output_parser = CommaSeparatedListOutputParser()
    
    # Prepare a summary of the restaurant
    restaurant_name = restaurant_details.get("name", "Unknown Restaurant")
    restaurant_location = restaurant_details.get("address", "Unknown Location")
    restaurant_rating = restaurant_details.get("rating", "Unknown Rating")
    restaurant_cuisines = ", ".join(restaurant_details.get("cuisines", ["Unknown Cuisine"]))
    
    # Create the prompt template
    template = """
    You are a food and dining expert specializing in extracting key information from restaurant data. 
    Based on the following restaurant details, generate a list of 10-15 important keywords 
    that capture the essence of the restaurant, its cuisine, location, and dining experience.
    
    Restaurant Name: {restaurant_name}
    Location: {restaurant_location}
    Rating: {restaurant_rating}
    Cuisines: {restaurant_cuisines}
    
    Generate a comma-separated list of keywords that would be useful for diners considering this restaurant.
    Focus on cuisine type, location advantages, price level, unique dishes, and standout features.
    
    KEYWORDS:
    """
    
    prompt = ChatPromptTemplate.from_template(template)
    
    # Initialize the LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",  # Using GPT-4 mini
        temperature=0.2,      # Lower temperature for more focused results
        api_key=openai_api_key
    )
    
    # Create the chain
    chain = prompt | llm | output_parser
    
    # Run the chain
    try:
        result = chain.invoke({
            "restaurant_name": restaurant_name,
            "restaurant_location": restaurant_location,
            "restaurant_rating": restaurant_rating,
            "restaurant_cuisines": restaurant_cuisines
        })
        
        # Clean up the keywords
        keywords = [keyword.strip() for keyword in result]
        return keywords
    except Exception as e:
        print(f"Error generating keywords with GPT-4 mini: {e}")
        # Return any existing keywords from the restaurant data as fallback
        return restaurant_details.get("review_keywords", [])

def extract_key_info(restaurant_data, generated_keywords=None):
    """
    Extract key information from restaurant details data.
    
    Args:
        restaurant_data (dict): The JSON response from the TripAdvisor API
        generated_keywords (list): Keywords generated by GPT-4 mini
    
    Returns:
        dict: Extracted key information
    """
    if not restaurant_data:
        return {"error": "No restaurant data available or invalid response format."}
    
    # Use generated keywords if available, otherwise use the ones from API
    keywords = generated_keywords if generated_keywords else restaurant_data.get("review_keywords", [])
    
    # Extract basic info
    key_info = {
        "name": restaurant_data.get("name", "Unknown Restaurant"),
        "rating": restaurant_data.get("rating", "N/A"),
        "phone": restaurant_data.get("phone", "N/A"),
        "address": restaurant_data.get("address", "N/A"),
        "latitude": restaurant_data.get("latitude", "N/A"),
        "longitude": restaurant_data.get("longitude", "N/A"),
        "cuisines": restaurant_data.get("cuisines", []),
        "price_range": restaurant_data.get("price_range_usd", "N/A"),
        "menu_link": restaurant_data.get("menu_link", "Not available"),
        "image": restaurant_data.get("featured_image", "No image available"),
        "review_keywords": keywords,
        "website": restaurant_data.get("website", "Not available"),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return key_info

def generate_restaurant_summary(key_info):
    """
    Generate a user-friendly summary of the restaurant based on key information.
    
    Args:
        key_info (dict): Key information about the restaurant
    
    Returns:
        str: A formatted summary
    """
    if "error" in key_info:
        return key_info["error"]
    
    # Format cuisines as a string
    cuisines = ", ".join(key_info.get("cuisines", ["Not specified"]))
    
    # Format keywords as a string
    keywords = ", ".join(key_info.get("review_keywords", ["No keywords available"]))
    
    # Build the summary
    summary = f"""
=== {key_info['name']} ===
Rating: {key_info['rating']} ⭐
Cuisine: {cuisines}
Price Range: {key_info['price_range']}

Address: {key_info['address']}
Phone: {key_info['phone']}
Coordinates: {key_info['latitude']}, {key_info['longitude']}

Menu: {key_info['menu_link']}
Website: {key_info['website']}

Keywords: {keywords}

This information was retrieved on {key_info['timestamp']}.
"""
    
    return summary

def format_restaurant_details(key_info, summary):
    """
    Format restaurant details into a dictionary for easy use in other applications.
    
    Args:
        key_info (dict): Key information about the restaurant
        summary (str): Formatted summary text
    
    Returns:
        dict: A dictionary containing structured restaurant information
    """
    result = {
        "name": key_info.get("name"),
        "rating": key_info.get("rating"),
        "address": key_info.get("address"),
        "phone": key_info.get("phone"),
        "latitude": key_info.get("latitude"),
        "longitude": key_info.get("longitude"),
        "cuisines": key_info.get("cuisines"),
        "price_range": key_info.get("price_range"),
        "menu_link": key_info.get("menu_link"),
        "image": key_info.get("image"),
        "review_keywords": key_info.get("review_keywords"),
        "summary": summary,
        
    }
    
    return result

def save_restaurant_details(details, restaurant_id):
    """
    Save restaurant details to a JSON file.
    
    Args:
        details (dict): Restaurant details to save
        restaurant_id (str): Restaurant ID to use in the filename
    
    Returns:
        str: Path to the saved file
    """
    filename = f"restaurant_{restaurant_id}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(details, f, indent=2, ensure_ascii=False)
    
    return filename

def main():
    """Main function to run the restaurant search and detail retrieval."""
    
    # Get user input for location
    location = input("Enter a city to search for restaurants (e.g., 'New York'): ")
    page = "1"  # Start with the first page
    
    # Fetch restaurants for the location
    print(f"\nFetching restaurants in {location}...")
    restaurants_data = fetch_restaurants(location, page)
    
    if not restaurants_data:
        print("Could not retrieve restaurant data. Please try again later.")
        return
    
    # Format and display the restaurant list
    formatted_results, restaurant_ids = format_restaurant_data(restaurants_data)
    print("\n" + formatted_results)
    
    # Ask the user to select a restaurant
    while True:
        try:
            selection = int(input("\nEnter the number of the restaurant you want to know more about (or 0 to exit): "))
            if selection == 0:
                print("Exiting the program.")
                return
            
            if selection in restaurant_ids:
                restaurant_id = restaurant_ids[selection]
                break
            else:
                print(f"Invalid selection. Please enter a number between 1 and {len(restaurant_ids)}.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Fetch detailed information about the selected restaurant
    print(f"\nFetching details for the selected restaurant...")
    restaurant_details = fetch_restaurant_details(restaurant_id)
    
    if not restaurant_details:
        print("Could not retrieve restaurant details. Please try again later.")
        return
    
    # Generate keywords with GPT-4 mini if OpenAI API key is available
    keywords = None
    if OPENAI_API_KEY:
        print("Generating keywords based on restaurant information...")
        keywords = generate_keywords_with_gpt4mini(restaurant_details, OPENAI_API_KEY)
    
    # Extract key information
    print("Extracting key information...")
    key_info = extract_key_info(restaurant_details, keywords)
    
    # Generate a summary
    summary = generate_restaurant_summary(key_info)
    
    # Format the restaurant details
    formatted_details = format_restaurant_details(key_info, summary)
    
    # Save to file
    filename = save_restaurant_details(formatted_details, restaurant_id)
    
    # Display the summary
    print("\n" + summary)
    print(f"\nDetailed information has been saved to {filename}")

if __name__ == "__main__":
    main() 


