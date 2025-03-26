import json
import folium
import requests
from IPython.display import display, HTML
import os
import subprocess

# Add LangChain imports for GPT-4-mini integration
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("LangChain not installed. Install with: pip install langchain langchain-openai")

class HotelFinder:
    def __init__(self):
        self.api_key = "00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5"  # Replace with your actual RapidAPI key
        self.base_url = "https://tripadvisor-scraper.p.rapidapi.com"
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "tripadvisor-scraper.p.rapidapi.com"
        }
        self.hotel_data = None
        self.cached_details = {}  # Cache for hotel details to avoid redundant API calls
        
        # Initialize LangChain model if available
        if LANGCHAIN_AVAILABLE:
            try:
                openai_api_key = os.environ.get("OPENAI_API_KEY", "")
                if openai_api_key:
                    self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
                    self.keyword_prompt = ChatPromptTemplate.from_template(
                        "Based on these keywords about a hotel: {keywords}\n\n"
                        "Please provide a concise, helpful summary of what guests typically mention about this hotel. "
                        "Focus on both positive and negative aspects, and give potential guests useful insights. "
                        "Keep your response to 3-4 sentences maximum."
                    )
                else:
                    print("OpenAI API key not found. Set the OPENAI_API_KEY environment variable.")
                    self.llm = None
            except Exception as e:
                print(f"Error initializing LangChain: {e}")
                self.llm = None
        else:
            self.llm = None
    
    def search_hotels_api(self, city, page=1):
        """
        Search for hotels in a specified city using the test2.py script
        """
        print(f"Searching hotels in {city}...")
        try:
            # Path to test2.py
            script_path = os.path.join(os.path.dirname(__file__), "test2.py")
            if not os.path.exists(script_path):
                script_path = "test2.py"  # Try current directory
                
            # Read original content
            with open(script_path, 'r') as f:
                original_content = f.read()
                
            # Modify the script to use our city query
            modified_content = original_content.replace(
                'querystring = {"query":"new york","page":"1"}',
                f'querystring = {{"query":"{city}","page":"{page}"}}'
            )
            
            # Write the modified script
            with open(script_path, 'w') as f:
                f.write(modified_content)
                
            # Execute the script
            result = subprocess.run(['python', script_path], capture_output=True, text=True)
            
            # Restore original content
            with open(script_path, 'w') as f:
                f.write(original_content)
                
            # Process the results
            if result.stdout:
                try:
                    # Parse JSON response
                    self.hotel_data = json.loads(result.stdout)
                    
                    # Save the raw JSON for debugging if needed
                    try:
                        with open(f"hotel_search_{city.replace(' ', '_')}.json", 'w') as f:
                            json.dump(self.hotel_data, f, indent=2)
                    except Exception as e:
                        print(f"Warning: Couldn't save search results: {e}")
                    
                    return self.hotel_data
                except json.JSONDecodeError:
                    print(f"Error: Failed to parse API response as JSON")
                    print(f"Response preview: {result.stdout[:200]}")
                    return None
            else:
                print(f"Error: No output from API call")
                if result.stderr:
                    print(f"Error details: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Error executing API request: {e}")
            return None
    
    def get_hotel_details_api(self, hotel_id):
        """
        Get detailed information about a specific hotel using the test.py script
        """
        # Check cache first
        if hotel_id in self.cached_details:
            print(f"Using cached details for hotel ID: {hotel_id}")
            return self.cached_details[hotel_id]
            
        print(f"Fetching details for hotel ID: {hotel_id}")
        try:
            # Path to test.py
            script_path = os.path.join(os.path.dirname(__file__), "test.py")
            if not os.path.exists(script_path):
                script_path = "test.py"  # Try current directory
                
            # Read original content
            with open(script_path, 'r') as f:
                original_content = f.read()
                
            # Modify the script to use our hotel ID
            modified_content = original_content.replace(
                'querystring = {"id":"10131859"}',
                f'querystring = {{"id":"{hotel_id}"}}'
            )
            
            # Write the modified script
            with open(script_path, 'w') as f:
                f.write(modified_content)
                
            # Execute the script
            result = subprocess.run(['python', script_path], capture_output=True, text=True)
            
            # Restore original content
            with open(script_path, 'w') as f:
                f.write(original_content)
                
            # Process the results
            if result.stdout:
                try:
                    # Parse JSON response
                    details = json.loads(result.stdout)
                    
                    # Save the raw JSON for debugging if needed
                    try:
                        with open(f"hotel_details_{hotel_id}.json", 'w') as f:
                            json.dump(details, f, indent=2)
                    except Exception as e:
                        print(f"Warning: Couldn't save hotel details: {e}")
                    
                    # Cache the results
                    self.cached_details[hotel_id] = details
                    return details
                except json.JSONDecodeError:
                    print(f"Error: Failed to parse API response as JSON")
                    print(f"Response preview: {result.stdout[:200]}")
                    return None
            else:
                print(f"Error: No output from API call")
                if result.stderr:
                    print(f"Error details: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Error executing API request: {e}")
            return None
    
    def format_price_range(self, price_data):
        """Format price range as 200-330 without $ symbol"""
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
    
    def create_hotel_map(self, hotels=None):
        """Create a folium map with hotel locations"""
        if hotels is None and self.hotel_data:
            if 'results' in self.hotel_data:
                hotels = self.hotel_data['results']
            else:
                print("Invalid hotel data format")
                return None
        elif hotels is None:
            print("No hotel data available")
            return None
        
        # Process hotels to ensure they have proper coordinates
        valid_hotels = []
        for hotel in hotels:
            if hotel.get('latitude') and hotel.get('longitude'):
                try:
                    lat = float(hotel['latitude'])
                    lng = float(hotel['longitude'])
                    hotel['_processed_lat'] = lat
                    hotel['_processed_lng'] = lng
                    valid_hotels.append(hotel)
                except (ValueError, TypeError):
                    print(f"Invalid coordinates for hotel: {hotel.get('name', 'Unknown')}")
        
        if not valid_hotels:
            print("No hotels with valid location data available")
            return None
        
        # Calculate the average latitude and longitude to center the map
        lats = [h['_processed_lat'] for h in valid_hotels]
        lngs = [h['_processed_lng'] for h in valid_hotels]
        
        avg_lat = sum(lats) / len(lats)
        avg_lng = sum(lngs) / len(lngs)
        
        # Create the map
        hotel_map = folium.Map(location=[avg_lat, avg_lng], zoom_start=14)
        
        # Add markers for each hotel
        for hotel in valid_hotels:
            price_range = self.format_price_range(hotel.get('price_range_usd', {}))
            
            # Extract address
            address = hotel.get('detailed_address', {})
            if address:
                full_address = f"{address.get('street', '')}, {address.get('city', '')}, {address.get('state', '')} {address.get('postal_code', '')}"
            else:
                full_address = hotel.get('address', 'Address not available')
            
            hotel_id = hotel.get('id', '')
            
            popup_content = f"""
            <strong>{hotel.get('name', 'Unknown Hotel')}</strong><br>
            Rating: {hotel.get('rating', 'N/A')} ⭐ ({hotel.get('reviews', '0')} reviews)<br>
            Price Range: {price_range}<br>
            Address: {full_address}<br>
            Coordinates: {hotel['_processed_lat']}, {hotel['_processed_lng']}<br>
            <a href="{hotel.get('link', '#')}" target="_blank">View Hotel</a><br>
            <button onclick="window.open('?hotel_id={hotel_id}', '_blank')">View Details</button>
            """
            
            folium.Marker(
                location=[hotel['_processed_lat'], hotel['_processed_lng']],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=hotel.get('name', 'Hotel'),
                icon=folium.Icon(color='red', icon='home')
            ).add_to(hotel_map)
        
        return hotel_map
    
    def summarize_keywords_with_langchain(self, keywords):
        """Use LangChain with GPT-4-mini to summarize review keywords"""
        if not keywords or len(keywords) == 0:
            return "No review keyword data available."
            
        # If LangChain and OpenAI are available, use the LLM for summarization
        if self.llm:
            try:
                # Prepare the keywords string for the prompt
                keywords_text = ", ".join(keywords)
                
                # Create the chain and run it
                chain = self.keyword_prompt | self.llm
                response = chain.invoke({"keywords": keywords_text})
                
                # Return the generated summary
                return response.content
            except Exception as e:
                print(f"Error generating summary with LangChain: {e}")
                # Fall back to basic summarization if LangChain fails
                return self.summarize_keywords_basic(keywords)
        else:
            # Fall back to basic summarization if LangChain is not available
            return self.summarize_keywords_basic(keywords)
    
    def summarize_keywords_basic(self, keywords):
        """Basic fallback method to summarize keywords without LLM"""
        if len(keywords) <= 5:
            return f"Based on guest reviews, this hotel is most often mentioned for: {', '.join(keywords)}."
        
        # For larger sets, show top keywords
        top_keywords = keywords[:5]
        remaining_count = len(keywords) - 5
        
        summary = f"Based on {len(keywords)} review keywords, this hotel is primarily known for: {', '.join(top_keywords)}"
        
        if remaining_count > 0:
            summary += f" and {remaining_count} other features."
        else:
            summary += "."
            
        summary += "\n\nThese keywords represent the most commonly mentioned terms in guest reviews."
        
        return summary
    
    def extract_hotel_ids(self):
        """Extract all hotel IDs from the current search results"""
        if not self.hotel_data or 'results' not in self.hotel_data:
            return []
            
        return [hotel.get('id') for hotel in self.hotel_data['results'] if hotel.get('id')]
        
    def store_hotel_id(self, hotel_id, filename="selected_hotel_id.txt"):
        """Store a hotel ID for later use"""
        try:
            with open(filename, 'w') as f:
                f.write(str(hotel_id))
            return True
        except Exception as e:
            print(f"Error storing hotel ID: {e}")
            return False
    
    def display_hotel_info(self, hotel_id=None, hotel=None, use_api=True):
        """Display comprehensive hotel information from API response data"""
        if hotel is None and hotel_id is None:
            print("No hotel specified")
            return
            
        if hotel is None:
            # First, check if we already have details in the cache
            if hotel_id in self.cached_details:
                details = self.cached_details[hotel_id]
                hotel = details
            # Try to find the hotel in our search results
            elif self.hotel_data and 'results' in self.hotel_data:
                hotel = next((h for h in self.hotel_data['results'] if str(h['id']) == str(hotel_id)), None)
            
            # If we still don't have hotel data, fetch it directly
            if hotel is None:
                print(f"Fetching details for hotel ID: {hotel_id}")
                hotel_details = self.get_hotel_details_api(hotel_id)
                if not hotel_details:
                    print(f"Hotel with ID {hotel_id} not found")
                    return
                hotel = hotel_details
        
        # Store the hotel ID for later use
        self.store_hotel_id(hotel_id or hotel.get('id'))
        
        # If we have a complete hotel object from API, use it directly
        details = hotel if 'featured_image' in hotel else self.get_hotel_details_api(hotel.get('id'))
        
        # Format the price range as 200-330
        price_range = self.format_price_range(hotel.get('price_range_usd', {}))
        
        # Handle detailed address properly
        address = hotel.get('detailed_address', {})
        if address:
            # Construct full address from components
            full_address = f"{address.get('street', '')}, {address.get('city', '')}, {address.get('state', '')} {address.get('postal_code', '')}"
        else:
            full_address = hotel.get('address', 'Address not available')
        
        # Get latitude and longitude
        latitude = hotel.get('latitude', 'Not available')
        longitude = hotel.get('longitude', 'Not available')
        
        # Get phone and email - prioritize from details or fall back to hotel data
        phone = details.get('phone', hotel.get('phone', 'Not available'))
        email = details.get('email', 'Not available')
        
        # Get website - prioritize from details or fall back to hotel link
        website = details.get('website', hotel.get('link', '#'))
        
        # Get hotel name
        hotel_name = hotel.get('name', details.get('name', 'Unknown Hotel'))
        
        # Prepare output HTML with enhanced styling - using standard string formatting to avoid f-string issue
        output = """
        <div style="padding: 20px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
            <h2 style="color: #2c3e50;">{0}</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div>
                    <p><strong>Rating:</strong> {1} ⭐ ({2} reviews)</p>
                    <p><strong>Price Range:</strong> {3}</p>
                    <p><strong>Address:</strong> {4}</p>
                    <p><strong>Coordinates:</strong> {5}, {6}</p>
                </div>
                <div>
                    <p><strong>Phone:</strong> {7}</p>
                    <p><strong>Email:</strong> {8}</p>
                    <p><strong>Website:</strong> <a href="{9}" target="_blank" style="color: #3498db;">Visit Website</a></p>
                    <p><strong>Hotel ID:</strong> {10}</p>
                </div>
            </div>
        """.format(
            hotel_name, 
            hotel.get('rating', details.get('rating', 'N/A')), 
            hotel.get('reviews', details.get('reviews', '0')), 
            price_range, 
            full_address, 
            latitude, 
            longitude, 
            phone, 
            email, 
            website,
            hotel.get('id', details.get('id', 'N/A'))
        )
        
        # Add amenities if available
        amenities = hotel.get('amenities', details.get('amenities', []))
        if amenities:
            output += "<p><strong>Amenities:</strong> {}</p>".format(', '.join(amenities))
        
        # Add featured image if available
        featured_image = details.get('featured_image', hotel.get('featured_image', ''))
        if featured_image:
            output += """<div style="margin: 15px 0;"><img src="{0}" alt="{1}" style="max-width: 100%; max-height: 300px; border-radius: 5px;"></div>""".format(featured_image, hotel_name)
        
        # Add hotel description if available
        description = details.get('description')
        if description:
            output += """<div style="margin: 10px 0;">
                <h4 style="color: #2c3e50; margin-top: 0;">Hotel Description</h4>
                <p>{0}</p>
            </div>""".format(description)
        
        # Add review keywords summary using LangChain with GPT-4-mini when available
        keywords = details.get('review_keywords', [])
        if keywords:
            # Use the LangChain summarization if available
            summary = self.summarize_keywords_with_langchain(keywords)
            output += """<div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 10px;">
                <h4 style="color: #2c3e50; margin-top: 0;">Review Highlights (AI-Generated)</h4>
                <p>{0}</p>
                <p style="font-size: 0.8em; color: #7f8c8d;">Common keywords: {1}</p>
            </div>""".format(summary.replace('\n', '<br>'), ', '.join(keywords[:10]))
        
        output += "</div>"
        
        # Display the hotel information
        display(HTML(output))
        
        # Create and display a map focused on this hotel
        if latitude != 'Not available' and longitude != 'Not available':
            try:
                # Convert coordinates to float if they're not already
                lat_float = float(latitude) if isinstance(latitude, (int, float, str)) and str(latitude).strip() else None
                lng_float = float(longitude) if isinstance(longitude, (int, float, str)) and str(longitude).strip() else None
                
                if lat_float is not None and lng_float is not None:
                    single_hotel_map = folium.Map(location=[lat_float, lng_float], zoom_start=16)
                    
                    # Add a red pin marker for the hotel location
                    folium.Marker(
                        location=[lat_float, lng_float],
                        popup="<strong>{}</strong><br>{}".format(hotel_name, full_address),
                        tooltip=hotel_name,
                        icon=folium.Icon(color='red', icon='map-pin', prefix='fa')
                    ).add_to(single_hotel_map)
                    
                    # Add a circle to highlight the area
                    folium.Circle(
                        location=[lat_float, lng_float],
                        radius=200,
                        color='red',
                        fill=True,
                        fill_opacity=0.1
                    ).add_to(single_hotel_map)
                    
                    display(single_hotel_map)
                else:
                    print("Could not convert coordinates to proper format.")
            except Exception as e:
                print(f"Error creating map: {e}")
        else:
            print("Location data not available for this hotel.")
            
        return hotel


def find_hotels_by_city(city, use_api=True):
    """User-friendly function to find hotels by city name"""
    finder = HotelFinder()
    data = finder.search_hotels_api(city, use_api=use_api)
    
    if data and 'results' in data and len(data['results']) > 0:
        print(f"Found {data.get('items_count', len(data['results']))} hotels in {city}")
        
        # Create and display a map with all hotels
        try:
            hotel_map = finder.create_hotel_map()
            if hotel_map:
                display(hotel_map)
        except Exception as e:
            print(f"Error creating map: {e}")
            print("Continuing with hotel display...")
            
        # Display the first hotel by default
        if len(data['results']) > 0:
            sample_hotel_id = data['results'][0]['id']
            finder.display_hotel_info(hotel_id=sample_hotel_id, use_api=use_api)
        
        return finder, data
    else:
        print(f"No hotels found in {city}")
        return None, None


def find_hotel_by_id(hotel_id, use_api=True):
    """Function to find and display a specific hotel by its ID"""
    finder = HotelFinder()
    hotel_data = finder.display_hotel_info(hotel_id=hotel_id, use_api=use_api)
    return finder, hotel_data


def execute_api_request(query=None, hotel_id=None, type="search"):
    """Execute API request using Python subprocess to call test.py or test2.py"""
    if type == "search" and query:
        # Use test2.py to search for hotels
        try:
            script_path = os.path.join(os.path.dirname(__file__), "test2.py")
            # Modify test2.py temporarily to use the query
            with open(script_path, 'r') as f:
                content = f.read()
            
            # Replace the query parameter
            modified_content = content.replace('querystring = {"query":"new york","page":"1"}', 
                                              f'querystring = {{"query":"{query}","page":"1"}}')
            
            # Write the modified file
            with open(script_path, 'w') as f:
                f.write(modified_content)
                
            # Execute the script
            result = subprocess.run(['python', script_path], capture_output=True, text=True)
            
            # Restore the original content
            with open(script_path, 'w') as f:
                f.write(content)
                
            return result.stdout
            
        except Exception as e:
            print(f"Error executing API request: {e}")
            return None
    
    elif type == "details" and hotel_id:
        # Use test.py to get hotel details
        try:
            script_path = os.path.join(os.path.dirname(__file__), "test.py")
            # Modify test.py temporarily to use the hotel ID
            with open(script_path, 'r') as f:
                content = f.read()
            
            # Replace the ID parameter
            modified_content = content.replace('querystring = {"id":"10131859"}', 
                                              f'querystring = {{"id":"{hotel_id}"}}')
            
            # Write the modified file
            with open(script_path, 'w') as f:
                f.write(modified_content)
                
            # Execute the script
            result = subprocess.run(['python', script_path], capture_output=True, text=True)
            
            # Restore the original content
            with open(script_path, 'w') as f:
                f.write(content)
                
            return result.stdout
            
        except Exception as e:
            print(f"Error executing API request: {e}")
            return None
    
    return None


# Streamlined main function
def main():
    print("Welcome to Hotel Finder")
    print("=======================")
    
    # Step 1: Ask for city name
    city = input("Enter a city to search for hotels: ")
    
    # Step 2: Use test2.py to fetch hotels in that city
    finder = HotelFinder()
    hotel_data = finder.search_hotels_api(city)
    
    if not hotel_data or 'results' not in hotel_data or not hotel_data['results']:
        print(f"No hotels found in {city}")
        return
    
    # Step 3: Display the list of hotels with details
    hotels = hotel_data['results']
    print(f"\nFound {len(hotels)} hotels in {city}")
    
    # Create and display a map with all hotels
    try:
        finder.hotel_data = hotel_data  # Set the data
        hotel_map = finder.create_hotel_map()
        if hotel_map:
            display(hotel_map)
            print("\nMap displaying all hotels in the city")
    except Exception as e:
        print(f"Error creating city map: {e}")
    
    # List all hotels with their details
    print("\nAvailable hotels:")
    for i, hotel in enumerate(hotels):
        price_range = finder.format_price_range(hotel.get('price_range_usd', {}))
        print(f"{i+1}. {hotel.get('name', 'Unknown')} - Rating: {hotel.get('rating', 'N/A')} - Price: {price_range}")
    
    # Step 4: Let user select a hotel to view details
    try:
        selection = int(input("\nEnter hotel number to view details (or 0 to exit): "))
        if selection == 0:
            print("Exiting. Thank you for using Hotel Finder!")
            return
            
        if selection < 1 or selection > len(hotels):
            print("Invalid selection. Please try again.")
            return
            
        # Get selected hotel and its ID
        selected_hotel = hotels[selection - 1]
        hotel_id = selected_hotel['id']
        
        # Step 5: Use test.py to fetch detailed information using the hotel ID
        hotel_details = finder.get_hotel_details_api(hotel_id)
        
        if not hotel_details:
            print(f"Could not fetch details for hotel ID: {hotel_id}")
            return
        
        # Step 6: Display the detailed hotel information
        print(f"\nShowing detailed information for {selected_hotel.get('name')}")
        
        # Combine the data from search and details
        combined_hotel = {**selected_hotel, **hotel_details}
        
        # Display comprehensive hotel information
        finder.display_hotel_info(hotel=combined_hotel, use_api=False)
        
    except ValueError:
        print("Please enter a valid number")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()