import requests
import json

def fetch_hotels(location="new york", page="1", api_key="00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5"):
    """
    Fetch hotel data from TripAdvisor API.
    
    Args:
        location (str): The location to search for hotels
        page (str): The page number of results to fetch
        api_key (str): Your RapidAPI key
    
    Returns:
        dict: The JSON response from the API
    """
    url = "https://tripadvisor-scraper.p.rapidapi.com/hotels/list"
    
    querystring = {"query": location, "page": page}
    
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

def format_hotel_data(hotel_data):
    """
    Format hotel data into a readable list.
    
    Args:
        hotel_data (dict): The JSON response from the TripAdvisor API
    
    Returns:
        str: Formatted hotel information
    """
    if not hotel_data or 'results' not in hotel_data:
        return "No hotel data available or invalid response format."
    
    result = f"Found {hotel_data.get('total_items_count', 0)} hotels in total. Showing page {hotel_data.get('current_page', 1)} of {hotel_data.get('total_pages', 1)}.\n\n"
    
    for i, hotel in enumerate(hotel_data['results'], 1):
        name = hotel.get('name', 'Unknown Hotel')
        rating = hotel.get('rating', 'N/A')
        
        # Handle price range
        price_range = hotel.get('price_range_usd', {})
        min_price = price_range.get('min', 'N/A')
        max_price = price_range.get('max', 'N/A')
        price_str = f"Price: {min_price}-{max_price}" if min_price != 'N/A' and max_price != 'N/A' else "Price: N/A"
        
        # Get hotel ID
        hotel_id = hotel.get('id', 'N/A')
        
        result += f"{i}. {name} - Rating: {rating} - {price_str} - ID: {hotel_id}\n"
    
    return result

def main():
    """
    Main function to run the hotel data fetcher.
    """
    location = input("Enter location to search for hotels (default: new york): ") or "new york"
   
    
    print(f"\nFetching hotel data for {location}\n")
    
    hotel_data = fetch_hotels(location)
    
    if hotel_data:
        formatted_data = format_hotel_data(hotel_data)
        print(formatted_data)
        
        # Optionally save the results to a file
        save_option = input("\nWould you like to save the results to a file? (y/n): ").lower()
        if save_option == 'y':
            filename = input("Enter filename (default: hotel_results.txt): ") or "hotel_results.txt"
            with open(filename, 'w') as f:
                f.write(formatted_data)
            print(f"Results saved to {filename}")
            
            # Also save the raw JSON for reference
            with open(f"raw_{filename.split('.')[0]}.json", 'w') as f:
                json.dump(hotel_data, f, indent=2)
            print(f"Raw data saved to raw_{filename.split('.')[0]}.json")

if __name__ == "__main__":
    main()