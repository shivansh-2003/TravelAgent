import requests
import json
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import CommaSeparatedListOutputParser

def fetch_hotel_details(hotel_id, api_key="00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5"):
    """
    Fetch detailed information about a specific hotel using its TripAdvisor ID.
    
    Args:
        hotel_id (str): The TripAdvisor ID of the hotel
        api_key (str): Your RapidAPI key
    
    Returns:
        dict: The JSON response containing hotel details
    """
    url = "https://tripadvisor-scraper.p.rapidapi.com/hotels/detail"
    
    querystring = {"id": str(hotel_id)}
    
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "tripadvisor-scraper.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making the request: {e}")
        return None

def fetch_hotel_reviews(hotel_id, api_key="00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5", limit=5):
    """
    Fetch reviews for a specific hotel using its TripAdvisor ID.
    
    Args:
        hotel_id (str): The TripAdvisor ID of the hotel
        api_key (str): Your RapidAPI key
        limit (int): Maximum number of reviews to fetch
    
    Returns:
        list: A list of review texts
    """
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
    
    # Extract the required information
    key_info = {
        "hotel_id": hotel_data.get("id", "N/A"),
        "name": hotel_data.get("name", "N/A"),
        "address": hotel_data.get("address", "N/A"),
        "website": hotel_data.get("website", "N/A"),
        "email": hotel_data.get("email", "N/A"),
        "phone": hotel_data.get("phone", "N/A"),
        "coordinates": {
            "latitude": hotel_data.get("latitude", "N/A"),
            "longitude": hotel_data.get("longitude", "N/A")
        },
        "rating": hotel_data.get("rating", "N/A"),
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
    summary = f"Hotel Summary: {key_info['name']}\n"
    summary += "=" * (15 + len(key_info['name'])) + "\n\n"
    
    # Basic information
    summary += f"Contact Information:\n"
    summary += f"- Address: {key_info['address']}\n"
    summary += f"- Phone: {key_info['phone']}\n"
    summary += f"- Email: {key_info['email']}\n"
    summary += f"- Website: {key_info['website']}\n\n"
    
    # Location information
    summary += f"Location:\n"
    summary += f"- Coordinates: {key_info['coordinates']['latitude']}, {key_info['coordinates']['longitude']}\n"
    summary += f"- Ranking: #{key_info['ranking']} of {key_info['total_hotels']} hotels in the area\n\n"
    
    # Keywords for contextual information
    if key_info['keywords']:
        summary += "Key Features (AI-generated keywords):\n"
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
    
    summary += f"\nRating: {key_info['rating']} (Based on TripAdvisor reviews)\n"
    summary += f"\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    return summary

def save_hotel_info(key_info, summary, save_raw=True):
    """
    Save hotel information to files.
    
    Args:
        key_info (dict): Extracted key information
        summary (str): Generated summary
        save_raw (bool): Whether to save the raw key info
    
    Returns:
        tuple: Paths to the saved files
    """
    # Create filenames based on hotel ID
    hotel_id = key_info.get("hotel_id", "unknown")
    summary_filename = f"hotel_{hotel_id}_summary.txt"
    json_filename = f"hotel_{hotel_id}_info.json"
    
    # Save summary to text file
    with open(summary_filename, 'w') as f:
        f.write(summary)
    
    # Save key info to JSON file if requested
    if save_raw:
        with open(json_filename, 'w') as f:
            json.dump(key_info, f, indent=2)
        return summary_filename, json_filename
    
    return summary_filename, None

def main():
    """
    Main function to run the hotel detail fetcher with LangChain and GPT-4 mini integration.
    """
    print("TripAdvisor Hotel Detail Fetcher with LangChain and GPT-4 Mini")
    print("=" * 60)
    
    hotel_id = input("Enter hotel ID to fetch details: ")
    
    # Ask for OpenAI API key
    openai_api_key = input("Enter your OpenAI API key: ")
    if not openai_api_key:
        print("Warning: No OpenAI API key provided. Will use existing keywords if available.")
    
    print(f"\nFetching details for hotel ID {hotel_id}...\n")
    
    # Fetch hotel details
    hotel_data = fetch_hotel_details(hotel_id)
    
    if not hotel_data:
        print("Failed to fetch hotel data. Please check the hotel ID and try again.")
        return
    
    # Generate keywords with GPT-4 mini if API key is provided
    generated_keywords = None
    if openai_api_key:
        print("Fetching reviews to generate keywords...")
        reviews = fetch_hotel_reviews(hotel_id)
        
        if reviews:
            print(f"Generating keywords using LangChain and GPT-4 mini based on {len(reviews)} reviews...")
            generated_keywords = generate_keywords_with_gpt4mini(hotel_data, reviews, openai_api_key)
            print(f"Generated {len(generated_keywords)} keywords.")
        else:
            print("No reviews found. Will use existing keywords if available.")
    
    # Extract key information
    key_info = extract_key_info(hotel_data, generated_keywords)
    
    # Generate and display summary
    summary = generate_hotel_summary(key_info)
    print("\nHotel Summary:")
    print("-" * 15)
    print(summary)
    
    # Ask if user wants to save the information
    save_option = input("\nWould you like to save this information? (y/n): ").lower()
    if save_option == 'y':
        save_raw = input("Save raw data as JSON as well? (y/n): ").lower() == 'y'
        summary_file, json_file = save_hotel_info(key_info, summary, save_raw)
        
        print(f"\nSummary saved to {summary_file}")
        if json_file:
            print(f"Raw data saved to {json_file}")

if __name__ == "__main__":
    main()