#!/usr/bin/env python3
import json
import os
import subprocess
from IPython.display import display, HTML
import folium

def fetch_hotels_by_city(city):
    """
    Fetch a list of hotels in a city using test2.py
    Returns the parsed JSON data of hotels
    """
    print(f"Searching for hotels in {city}...")
    
    # Path to test2.py
    script_path = "test2.py"
    
    # Read the original content
    with open(script_path, "r") as f:
        original_content = f.read()
    
    try:
        # Modify the query in test2.py
        modified_content = original_content.replace(
            'querystring = {"query":"new york","page":"1"}',
            f'querystring = {{"query":"{city}","page":"1"}}'
        )
        
        # Write the modified content
        with open(script_path, "w") as f:
            f.write(modified_content)
        
        # Execute test2.py
        result = subprocess.run(["python", script_path], capture_output=True, text=True)
        
        # Restore the original content
        with open(script_path, "w") as f:
            f.write(original_content)
        
        # Try to parse the JSON
        try:
            hotels_data = json.loads(result.stdout)
            
            # Save the results to a file for reference
            with open(f"hotels_in_{city.replace(' ', '_')}.json", "w") as f:
                json.dump(hotels_data, f, indent=2)
                
            return hotels_data
            
        except json.JSONDecodeError:
            print("Error: Failed to parse API response")
            print(f"Response preview: {result.stdout[:200]}")
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        # Ensure we restore the original content
        with open(script_path, "w") as f:
            f.write(original_content)
        return None


def fetch_hotel_details(hotel_id):
    """
    Fetch detailed information for a specific hotel using test.py
    Returns the parsed JSON data of hotel details
    """
    print(f"Fetching details for hotel ID: {hotel_id}")
    
    # Path to test.py
    script_path = "test.py"
    
    # Read the original content
    with open(script_path, "r") as f:
        original_content = f.read()
    
    try:
        # Modify the query in test.py
        modified_content = original_content.replace(
            'querystring = {"id":"10131859"}',
            f'querystring = {{"id":"{hotel_id}"}}'
        )
        
        # Write the modified content
        with open(script_path, "w") as f:
            f.write(modified_content)
        
        # Execute test.py
        result = subprocess.run(["python", script_path], capture_output=True, text=True)
        
        # Restore the original content
        with open(script_path, "w") as f:
            f.write(original_content)
        
        # Try to parse the JSON
        try:
            hotel_data = json.loads(result.stdout)
            
            # Save the details to a file for reference
            with open(f"hotel_details_{hotel_id}.json", "w") as f:
                json.dump(hotel_data, f, indent=2)
                
            return hotel_data
            
        except json.JSONDecodeError:
            print("Error: Failed to parse API response")
            print(f"Response preview: {result.stdout[:200]}")
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        # Ensure we restore the original content
        with open(script_path, "w") as f:
            f.write(original_content)
        return None


def format_price_range(price_data):
    """Format price range without $ symbol"""
    if not price_data:
        return "Price not available"
        
    min_price = price_data.get('min', '')
    max_price = price_data.get('max', '')
    
    if min_price and max_price:
        return f"{min_price}-{max_price}"
    elif min_price:
        return f"{min_price}+"
    elif max_price:
        return f"Up to {max_price}"
    else:
        return "Price not available"


def create_hotel_map(hotels):
    """Create a folium map with hotel locations"""
    if not hotels:
        print("No hotels to display on map")
        return None
        
    # Process hotels to ensure valid coordinates
    valid_hotels = []
    for hotel in hotels:
        if hotel.get('latitude') and hotel.get('longitude'):
            try:
                hotel['_lat'] = float(hotel['latitude'])
                hotel['_lng'] = float(hotel['longitude'])
                valid_hotels.append(hotel)
            except (ValueError, TypeError):
                pass
                
    if not valid_hotels:
        print("No hotels have valid coordinates for mapping")
        return None
        
    # Calculate map center
    avg_lat = sum(h['_lat'] for h in valid_hotels) / len(valid_hotels)
    avg_lng = sum(h['_lng'] for h in valid_hotels) / len(valid_hotels)
    
    # Create map
    hotel_map = folium.Map(location=[avg_lat, avg_lng], zoom_start=13)
    
    # Add markers
    for hotel in valid_hotels:
        popup_html = f"""
        <strong>{hotel.get('name', 'Unknown')}</strong><br>
        Rating: {hotel.get('rating', 'N/A')} ⭐<br>
        Address: {hotel.get('address', 'Address not available')}<br>
        <a href="#" onclick="alert('Hotel ID: {hotel.get('id')}')">View Details</a>
        """
        
        folium.Marker(
            location=[hotel['_lat'], hotel['_lng']],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=hotel.get('name', 'Hotel'),
            icon=folium.Icon(color='red', icon='home')
        ).add_to(hotel_map)
    
    # Save the map to an HTML file for viewing
    map_filename = "hotel_map.html"
    hotel_map.save(map_filename)
    print(f"Map saved to {map_filename}")
    
    return hotel_map


def display_hotel_info(hotel_details):
    """Display comprehensive hotel information"""
    if not hotel_details:
        print("No hotel details available")
        return
        
    # Extract key information
    name = hotel_details.get('name', 'Unknown Hotel')
    rating = hotel_details.get('rating', 'N/A')
    reviews = hotel_details.get('reviews', 0)
    address = hotel_details.get('address', 'Address not available')
    phone = hotel_details.get('phone', 'Not available')
    email = hotel_details.get('email', 'Not available')
    website = hotel_details.get('website', hotel_details.get('link', '#'))
    image = hotel_details.get('featured_image')
    
    # Format output
    output = [
        f"Hotel Name: {name}",
        f"Rating: {rating} ⭐ ({reviews} reviews)",
        f"Address: {address}",
        f"Phone: {phone}",
        f"Email: {email}",
        f"Website: {website}"
    ]
    
    # Add review keywords if available
    if 'review_keywords' in hotel_details and hotel_details['review_keywords']:
        keywords = hotel_details['review_keywords'][:10]
        output.append(f"Top Keywords: {', '.join(keywords)}")
    
    # Add amenities if available
    if 'amenities' in hotel_details and hotel_details['amenities']:
        amenities = hotel_details['amenities']
        output.append(f"Amenities: {', '.join(amenities)}")
    
    # Print the information
    print("\n=== HOTEL DETAILS ===")
    print("\n".join(output))
    print("====================")
    
    # Create individual hotel map if coordinates are available
    if hotel_details.get('latitude') and hotel_details.get('longitude'):
        try:
            lat = float(hotel_details['latitude'])
            lng = float(hotel_details['longitude'])
            
            hotel_map = folium.Map(location=[lat, lng], zoom_start=16)
            
            # Add marker
            folium.Marker(
                location=[lat, lng],
                popup=f"<strong>{name}</strong><br>{address}",
                tooltip=name,
                icon=folium.Icon(color='red', icon='map-pin', prefix='fa')
            ).add_to(hotel_map)
            
            # Add circle to highlight area
            folium.Circle(
                location=[lat, lng],
                radius=200,
                color='red',
                fill=True,
                fill_opacity=0.1
            ).add_to(hotel_map)
            
            # Save map to file
            detail_map_file = f"hotel_{hotel_details.get('id')}_map.html"
            hotel_map.save(detail_map_file)
            print(f"Detailed map saved to {detail_map_file}")
            
            return hotel_map
            
        except (ValueError, TypeError) as e:
            print(f"Could not create map: {e}")
    
    return None


def main():
    """Main function to run the hotel search demo"""
    print("=== HOTEL FINDER DEMO ===")
    print("This demo uses test2.py and test.py to find hotels and their details")
    
    # Step 1: Get city from user
    city = input("Enter a city to search for hotels: ")
    
    # Step 2: Fetch hotels in that city
    hotels_data = fetch_hotels_by_city(city)
    
    if not hotels_data or 'results' not in hotels_data or not hotels_data['results']:
        print(f"No hotels found in {city}")
        return
    
    hotels = hotels_data['results']
    print(f"\nFound {len(hotels)} hotels in {city}")
    
    # Step 3: Create and save a map with all hotels
    create_hotel_map(hotels)
    
    # Step 4: Display hotels with their basic information
    print("\nAvailable hotels:")
    for i, hotel in enumerate(hotels):
        price_range = format_price_range(hotel.get('price_range_usd', {}))
        print(f"{i+1}. {hotel.get('name', 'Unknown')} - Rating: {hotel.get('rating', 'N/A')} - Price: {price_range}")
    
    # Step 5: Let user select a hotel
    try:
        selection = int(input("\nEnter hotel number to view details (or 0 to exit): "))
        if selection == 0:
            print("Exiting.")
            return
        
        if selection < 1 or selection > len(hotels):
            print("Invalid selection.")
            return
        
        # Get the selected hotel
        selected_hotel = hotels[selection - 1]
        hotel_id = selected_hotel['id']
        
        # Store the hotel ID for future reference
        with open("selected_hotel_id.txt", "w") as f:
            f.write(str(hotel_id))
            
        print(f"Selected: {selected_hotel.get('name')}")
        
        # Step 6: Fetch detailed information for the selected hotel
        hotel_details = fetch_hotel_details(hotel_id)
        
        if not hotel_details:
            print(f"Could not fetch details for hotel ID: {hotel_id}")
            # Use basic information from search results
            print("Displaying basic information from search results:")
            display_hotel_info(selected_hotel)
            return
        
        # Step 7: Combine search data and details
        combined_hotel = {**selected_hotel, **hotel_details}
        
        # Step 8: Display detailed hotel information
        display_hotel_info(combined_hotel)
        
    except ValueError:
        print("Please enter a valid number")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main() 