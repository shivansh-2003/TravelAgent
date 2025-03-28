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

def fetch_hotels(location="new york", page="1", api_key=None):
    """
    Fetch hotel data from TripAdvisor API.
    
    Args:
        location (str): The location to search for hotels
        page (str): The page number of results to fetch
        api_key (str): Your RapidAPI key
    
    Returns:
        dict: The JSON response from the API
    """
    if api_key is None:
        api_key ="00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5"
        
    url = "https://tripadvisor-scraper.p.rapidapi.com/hotels/list"
    
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

def format_hotel_data(hotel_data):
    """
    Format hotel data into a readable list and store IDs separately.
    
    Args:
        hotel_data (dict): The JSON response from the TripAdvisor API
    
    Returns:
        tuple: (formatted_result, hotel_ids_dict)
            - formatted_result: String with formatted hotel info (without IDs)
            - hotel_ids_dict: Dictionary mapping hotel numbers to their IDs
    """
    if not hotel_data or 'results' not in hotel_data:
        return "No hotel data available or invalid response format.", {}
    
    result = f"Found {hotel_data.get('total_items_count', 0)} hotels in total. Showing page {hotel_data.get('current_page', 1)} of {hotel_data.get('total_pages', 1)}.\n\n"
    
    # Dictionary to store hotel IDs (not displayed)
    hotel_ids = {}
    
    for i, hotel in enumerate(hotel_data['results'], 1):
        name = hotel.get('name', 'Unknown Hotel')
        rating = hotel.get('rating', 'N/A')
        
        # Handle price range
        price_range = hotel.get('price_range_usd', {})
        min_price = price_range.get('min', 'N/A')
        max_price = price_range.get('max', 'N/A')
        price_str = f"Price: {min_price}-{max_price}" if min_price != 'N/A' and max_price != 'N/A' else "Price: N/A"
        
        # Store hotel ID in dictionary but don't display it in results
        hotel_id = hotel.get('id', 'N/A')
        hotel_ids[i] = hotel_id
        
        # Display hotel info without the ID
        result += f"{i}. {name} - Rating: {rating} - {price_str}\n"
    
    return result, hotel_ids

def fetch_hotel_details(hotel_id, api_key=None):
    """
    Fetch detailed information about a specific hotel using its TripAdvisor ID.
    
    Args:
        hotel_id (str): The TripAdvisor ID of the hotel
        api_key (str): Your RapidAPI key
    
    Returns:
        dict: The JSON response containing hotel details
    """
    if api_key is None:
        api_key = "00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5"
        
    url = "https://tripadvisor-scraper.p.rapidapi.com/hotels/detail"
    
    querystring = {"id": str(hotel_id)}
    
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

def fetch_hotel_reviews(hotel_id, api_key=None, limit=5):
    """
    Fetch reviews for a specific hotel using its TripAdvisor ID.
    
    Args:
        hotel_id (str): The TripAdvisor ID of the hotel
        api_key (str): Your RapidAPI key
        limit (int): Maximum number of reviews to fetch
    
    Returns:
        list: A list of review texts
    """
    if api_key is None:
        api_key ="00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5"
        
    url = "https://tripadvisor-scraper.p.rapidapi.com/hotels/reviews"
    
    querystring = {"id": str(hotel_id), "limit": str(limit), "page": "1"}
    
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "tripadvisor-scraper.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json()
        
        # Extract review texts from the response
        reviews = []
        if "results" in data:
            for review in data["results"]:
                if "text" in review:
                    reviews.append(review["text"])
        
        return reviews
    except requests.exceptions.RequestException as e:
        print(f"Error fetching reviews: {e}")
        return []

def generate_keywords_with_gpt4mini(hotel_details, reviews, openai_api_key):
    """
    Generate keywords using GPT-4 mini via LangChain based on hotel details and reviews.
    
    Args:
        hotel_details (dict): Hotel details data
        reviews (list): List of review texts
        openai_api_key (str): OpenAI API key
    
    Returns:
        list: Generated keywords
    """
    # Initialize the output parser
    output_parser = CommaSeparatedListOutputParser()
    
    # Prepare a summary of the hotel
    hotel_name = hotel_details.get("name", "Unknown Hotel")
    hotel_location = hotel_details.get("address", "Unknown Location")
    hotel_rating = hotel_details.get("rating", "Unknown Rating")
    
    # Combine reviews into a single text
    reviews_text = "\n".join([f"- {review[:300]}..." for review in reviews])
    
    # Create the prompt template
    template = """
    You are a travel analyst specializing in extracting key information from hotel data. 
    Based on the following hotel details and reviews, generate a list of 15-20 important keywords 
    that capture the essence of the hotel, its location, amenities, and guest experiences.
    
    Hotel Name: {hotel_name}
    Location: {hotel_location}
    Rating: {hotel_rating}
    
    Sample Reviews:
    {reviews}
    
    Generate a comma-separated list of keywords that would be useful for travelers considering this hotel.
    Focus on location advantages, unique amenities, service quality, and standout features.
    
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
            "hotel_name": hotel_name,
            "hotel_location": hotel_location,
            "hotel_rating": hotel_rating,
            "reviews": reviews_text
        })
        
        # Clean up the keywords
        keywords = [keyword.strip() for keyword in result]
        return keywords
    except Exception as e:
        print(f"Error generating keywords with GPT-4 mini: {e}")
        # Return any existing keywords from the hotel data as fallback
        return hotel_details.get("review_keywords", [])

def extract_key_info(hotel_data, generated_keywords=None):
    """
    Extract key information from hotel details data.
    
    Args:
        hotel_data (dict): The JSON response from the TripAdvisor API
        generated_keywords (list): Keywords generated by GPT-4 mini
    
    Returns:
        dict: Extracted key information
    """
    if not hotel_data:
        return {"error": "No hotel data available or invalid response format."}
    
    # Use generated keywords if available, otherwise use the ones from API
    keywords = generated_keywords if generated_keywords else hotel_data.get("review_keywords", [])
    
    # Extract price range if available
    price_range = "N/A"
    if "price_range_usd" in hotel_data:
        min_price = hotel_data["price_range_usd"].get("min", "N/A")
        max_price = hotel_data["price_range_usd"].get("max", "N/A")
        if min_price != "N/A" and max_price != "N/A":
            price_range = f"${min_price}-${max_price}"
    
    # Extract the required information
    key_info = {
        "hotel_id": hotel_data.get("id", "N/A"),
        "name": hotel_data.get("name", "N/A"),
        "rating": hotel_data.get("rating", "N/A"),
        "address": hotel_data.get("address", "N/A"),
        "phone": hotel_data.get("phone", "N/A"),
        "price_range": price_range,
        "website": hotel_data.get("website", "N/A"),
        "email": hotel_data.get("email", "N/A"),
        "featured_image": hotel_data.get("featured_image", None),
        "link": hotel_data.get("link", "N/A"),
        "coordinates": {
            "latitude": hotel_data.get("latitude", "N/A"),
            "longitude": hotel_data.get("longitude", "N/A")
        },
        "ranking": hotel_data.get("ranking", {}).get("current_rank", "N/A"),
        "total_hotels": hotel_data.get("ranking", {}).get("total", "N/A"),
        "keywords": keywords
    }
    
    return key_info

def generate_hotel_summary(key_info):
    """
    Generate a summary of the hotel based on key information.
    
    Args:
        key_info (dict): Extracted key information about the hotel
    
    Returns:
        str: A summary description of the hotel
    """
    # Check if key_info contains error
    if "error" in key_info:
        return key_info["error"]
    
    # Create a summary based on available information
    summary = ""
    
    # Location information
    if key_info['coordinates']['latitude'] != "N/A" and key_info['coordinates']['longitude'] != "N/A":
        summary += f"Location coordinates: {key_info['coordinates']['latitude']}, {key_info['coordinates']['longitude']}\n"
    
    if key_info['ranking'] != "N/A" and key_info['total_hotels'] != "N/A":
        summary += f"Ranking: #{key_info['ranking']} of {key_info['total_hotels']} hotels in the area\n\n"
    
    # Keywords for contextual information
    if key_info['keywords']:
        summary += "Key Features:\n"
        # Group keywords into categories for better summary
        location_keywords = []
        amenities_keywords = []
        experience_keywords = []
        
        location_terms = ["station", "central", "square", "park", "building", "blocks", "avenue", "broadway", "jfk", "subway", "location", "united nations", "district", "neighborhood", "downtown", "uptown", "midtown"]
        amenity_terms = ["equipment", "mat", "table", "machine", "gym", "bagels", "bed", "closet", "conditioner", "breakfast", "wifi", "pool", "fitness", "restaurant", "bar", "lounge"]
        
        for keyword in key_info['keywords']:
            if any(term in keyword.lower() for term in location_terms):
                location_keywords.append(keyword)
            elif any(term in keyword.lower() for term in amenity_terms):
                amenities_keywords.append(keyword)
            else:
                experience_keywords.append(keyword)
        
        if location_keywords:
            summary += "- Location highlights: " + ", ".join(location_keywords[:5]) + "\n"
        
        if amenities_keywords:
            summary += "- Amenities highlighted: " + ", ".join(amenities_keywords[:5]) + "\n"
        
        if experience_keywords:
            summary += "- Guest experience notes: " + ", ".join(experience_keywords[:5]) + "\n"
    
    return summary

def format_hotel_details(key_info, summary):
    """
    Format hotel details in the requested format.
    
    Args:
        key_info (dict): Extracted key information about the hotel
        summary (str): Generated summary
    
    Returns:
        str: Formatted hotel details
    """
    details = "\n" + "=" * 60 + "\n"
    details += f"HOTEL INFORMATION\n"
    details += "=" * 60 + "\n\n"
    
    # Format exactly as requested
    details += f"Name: {key_info['name']}\n"
    details += f"Rating: {key_info['rating']} stars\n"
    details += f"Address: {key_info['address']}\n"
    details += f"Phone: {key_info['phone']}\n"
    details += f"Price Range: {key_info['price_range']}\n"
    details += f"Email: {key_info['email']}\n"
    details += f"Website: {key_info['website']}\n\n"
    
    details += "Summary:\n"
    details += "-" * 60 + "\n"
    details += summary
    
    # Add image URL if available
    if key_info['featured_image']:
        details += "\n\nImage URL:"
        details += f"\n{key_info['featured_image']}\n"
    
    details += "\n" + "=" * 60 + "\n"
    details += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    details += "=" * 60 + "\n"
    
    return details

def save_hotel_details(details, hotel_id):
    """
    Save hotel details to a file.
    
    Args:
        details (str): Formatted hotel details
        hotel_id (str): The ID of the hotel
    
    Returns:
        str: Path to the saved file
    """
    filename = f"hotel_{hotel_id}_details.txt"
    with open(filename, 'w') as f:
        f.write(details)
    return filename

def main():
    """
    Main function to fetch hotel data and retrieve detailed information.
    """
    print("\nTripAdvisor Hotel Information Retriever")
    print("=" * 40)
    
    # Get OpenAI API key from .env or environment
    openai_api_key = OPENAI_API_KEY
    if not openai_api_key:
        print("Note: OpenAI API key not found in .env file. Will use existing keywords from TripAdvisor.")
    
    # 1. Fetch list of hotels
    location = input("Enter location to search for hotels (default: new york): ") or "new york"
    print(f"\nFetching hotels in {location}...")
    
    # Use fetch_hotels from hotel_city.py
    hotel_data = fetch_hotels(location)
    
    if not hotel_data:
        print("Failed to fetch hotels. Please check your internet connection and try again.")
        return
    
    # 2. Format and display hotels
    formatted_data, hotel_ids = format_hotel_data(hotel_data)
    print(formatted_data)
    
    # 3. Let user select a hotel
    try:
        selection = int(input("\nEnter the number of the hotel you want details for: "))
        if selection not in hotel_ids:
            print("Invalid selection. Please select a valid hotel number.")
            return
    except ValueError:
        print("Invalid input. Please enter a number.")
        return
    
    selected_id = hotel_ids[selection]
    print(f"\nFetching details for hotel ID: {selected_id}...")
    
    # 4. Fetch detailed hotel information
    hotel_details_data = fetch_hotel_details(selected_id)
    
    if not hotel_details_data:
        print("Failed to fetch hotel details. Please try again.")
        return
    
    # 5. Process hotel details with or without OpenAI
    generated_keywords = None
    if openai_api_key:
        print("Generating keywords with OpenAI...")
        reviews = fetch_hotel_reviews(selected_id)
        if reviews:
            generated_keywords = generate_keywords_with_gpt4mini(hotel_details_data, reviews, openai_api_key)
            print(f"Generated {len(generated_keywords)} keywords")
    
    # 6. Extract key information
    key_info = extract_key_info(hotel_details_data, generated_keywords)
    
    # 7. Generate summary automatically (without asking)
    summary = generate_hotel_summary(key_info)
    
    # 8. Format hotel details in the requested format
    formatted_details = format_hotel_details(key_info, summary)
    
    # 9. Display the formatted details
    print(formatted_details)
    
    # 10. Save to file
    save_option = input("\nWould you like to save these details to a file? (y/n): ").lower()
    if save_option == 'y':
        filename = save_hotel_details(formatted_details, selected_id)
        print(f"Details saved to {filename}")

if __name__ == "__main__":
    main()