import requests
import json
import logging
import traceback
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_flight_query(query: str) -> Dict[str, Any]:
    """
    Parse a natural language flight query and extract search parameters.
    
    Args:
        query: Natural language query about flight search
               e.g. "What are the cheapest flights from Delhi to Mumbai on April 15th, 2025 in economy class?"
        
    Returns:
        Dictionary with extracted parameters:
        - from_entity_id: Origin location ID or name
        - to_entity_id: Destination location ID or name (or None for "everywhere")
        - depart_date: Departure date in YYYY-MM-DD format (or None for "anytime")
        - cabin_class: Cabin class (economy, premium_economy, business, first)
        - adults: Number of adult passengers
        - children: Number of children
        - infants: Number of infants
        - whole_month: Boolean flag for whole month search
        - sort: Sort preference (e.g., "cheapest_first")
    """
    logger.info(f"Parsing flight query: {query}")
    
    # Initialize default parameters
    params = {
        "from_entity_id": None,
        "to_entity_id": None,
        "depart_date": None,
        "cabin_class": "economy",
        "adults": 1,
        "children": 0,
        "infants": 0,
        "whole_month": False,
        "sort": "cheapest_first"
    }
    
    # Extract origin location
    # Look for patterns like "from Delhi" or "from PARI"
    from_match = re.search(r'from\s+([A-Za-z\s]+)', query, re.IGNORECASE)
    if from_match:
        from_location = from_match.group(1).strip()
        params["from_entity_id"] = from_location
    
    # Extract destination location
    # Look for patterns like "to Mumbai" or "to MSYA"
    to_match = re.search(r'to\s+([A-Za-z\s]+)', query, re.IGNORECASE)
    if to_match:
        to_location = to_match.group(1).strip()
        params["to_entity_id"] = to_location
    
    # Extract date patterns
    # Look for specific date formats or month names with day numbers and year
    date_patterns = [
        # DD-MM-YYYY or DD/MM/YYYY
        r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})',
        # Month name + day + year (e.g., "April 15th, 2025" or "April 15 2025")
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})',
        # Day + Month name + year (e.g., "15 April 2025" or "15th April 2025")
        r'(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December),?\s+(\d{4})'
    ]
    
    for pattern in date_patterns:
        date_match = re.search(pattern, query, re.IGNORECASE)
        if date_match:
            try:
                # Format depends on which pattern matched
                if pattern == date_patterns[0]:  # DD-MM-YYYY
                    day, month, year = date_match.groups()
                    depart_date = f"{year}-{int(month):02d}-{int(day):02d}"
                elif pattern == date_patterns[1]:  # Month name + day + year
                    month_name, day, year = date_match.groups()
                    month_num = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, 
                                 "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12}
                    month = month_num[month_name.lower()]
                    depart_date = f"{year}-{month:02d}-{int(day):02d}"
                else:  # Day + Month name + year
                    day, month_name, year = date_match.groups()
                    month_num = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, 
                                 "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12}
                    month = month_num[month_name.lower()]
                    depart_date = f"{year}-{month:02d}-{int(day):02d}"
                
                params["depart_date"] = depart_date
                break
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse date: {e}")
    
    # Check for whole month queries
    whole_month_match = re.search(r'(in|during|for)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', query, re.IGNORECASE)
    if whole_month_match:
        try:
            _, month_name, year = whole_month_match.groups()
            month_num = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, 
                         "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12}
            month = month_num[month_name.lower()]
            params["whole_month"] = True
            params["depart_date"] = f"{year}-{month:02d}"
        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to parse whole month: {e}")
    
    # Extract cabin class
    cabin_class_patterns = {
        "economy": r'\b(economy)(?:\s+class)?\b',
        "premium_economy": r'\b(premium(?:\s+economy)|economy\s+premium)(?:\s+class)?\b',
        "business": r'\b(business)(?:\s+class)?\b',
        "first": r'\b(first)(?:\s+class)?\b'
    }
    
    for class_type, pattern in cabin_class_patterns.items():
        if re.search(pattern, query, re.IGNORECASE):
            params["cabin_class"] = class_type
            break
    
    # Extract passenger count
    # Adults
    adult_match = re.search(r'(\d+)\s+adult', query, re.IGNORECASE)
    if adult_match:
        params["adults"] = int(adult_match.group(1))
    
    # Children
    child_match = re.search(r'(\d+)\s+child(?:ren)?', query, re.IGNORECASE)
    if child_match:
        params["children"] = int(child_match.group(1))
    
    # Infants
    infant_match = re.search(r'(\d+)\s+infant', query, re.IGNORECASE)
    if infant_match:
        params["infants"] = int(infant_match.group(1))
    
    # Extract sort preference (defaulting to cheapest)
    if re.search(r'cheap(?:est)?', query, re.IGNORECASE):
        params["sort"] = "cheapest_first"
    elif re.search(r'fast(?:est)?|quick(?:est)?|short(?:est)?', query, re.IGNORECASE):
        params["sort"] = "duration"  # Assuming this is the key for sorting by duration
    
    logger.info(f"Extracted parameters: {params}")
    return params

def search_flights(
    from_entity_id: str,
    to_entity_id: Optional[str] = None,
    depart_date: Optional[str] = None,
    cabin_class: str = "economy",
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    market: str = "US",
    locale: str = "en-US",
    currency: str = "USD",
    stops: Optional[str] = None,
    include_origin_nearby_airports: bool = False,
    include_destination_nearby_airports: bool = False,
    sort: str = "cheapest_first",
    airlines: Optional[str] = None,
    whole_month_depart: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for flights using the SkyScanner API and return simplified flight information.
    
    Args:
        from_entity_id: Origin location ID (e.g., "PARI" for Paris)
        to_entity_id: Destination location ID (optional, use None for "everywhere")
        depart_date: Departure date in YYYY-MM-DD format (optional)
        cabin_class: Cabin class (economy, premium_economy, business, first)
        adults: Number of adult passengers
        children: Number of children (2-12 years)
        infants: Number of infants (under 2 years)
        market: Market country code (e.g., "US")
        locale: Locale for response (e.g., "en-US")
        currency: Currency for prices (e.g., "USD")
        stops: Filter by number of stops (e.g., "direct,1stop")
        include_origin_nearby_airports: Whether to include nearby airports for origin
        include_destination_nearby_airports: Whether to include nearby airports for destination
        sort: Sort preference (e.g., "cheapest_first")
        airlines: Filter by airlines (comma separated IDs)
        whole_month_depart: Search for the whole month (YYYY-MM format)
        
    Returns:
        List of dictionaries containing flight information (carrier, id, duration, price)
    """
    url = "https://sky-scanner3.p.rapidapi.com/flights/search-one-way"
    
    # If no date provided or date is in the past, use a future date
    if not depart_date and not whole_month_depart:
        # If no date is provided, use a default future date (30 days from now)
        depart_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    elif depart_date and not whole_month_depart:
        # If a date is provided, ensure it's not in the past
        try:
            date_obj = datetime.strptime(depart_date, "%Y-%m-%d").date()
            if date_obj < datetime.now().date():
                logger.warning(f"Provided date {depart_date} is in the past. Using default future date.")
                depart_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        except ValueError:
            logger.warning(f"Invalid date format: {depart_date}. Using default future date.")
            depart_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Build query parameters
    querystring = {
        "fromEntityId": from_entity_id,
        "cabinClass": cabin_class,
        "adults": str(adults),
        "market": market,
        "locale": locale,
        "currency": currency
    }
    
    # Add optional parameters if provided
    if to_entity_id:
        querystring["toEntityId"] = to_entity_id
    
    if depart_date:
        querystring["departDate"] = depart_date
    
    if whole_month_depart:
        querystring["wholeMonthDepart"] = whole_month_depart
    
    if children > 0:
        querystring["children"] = str(children)
    
    if infants > 0:
        querystring["infants"] = str(infants)
    
    if stops:
        querystring["stops"] = stops
    
    if include_origin_nearby_airports:
        querystring["includeOriginNearbyAirports"] = "true"
    
    if include_destination_nearby_airports:
        querystring["includeDestinationNearbyAirports"] = "true"
    
    if sort:
        querystring["sort"] = sort
    
    if airlines:
        querystring["airlines"] = airlines
    
    # Remove None values from querystring
    querystring = {k: v for k, v in querystring.items() if v is not None}
    
    headers = {
        "x-rapidapi-key": "00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5",
        "x-rapidapi-host": "sky-scanner3.p.rapidapi.com"
    }
    
    try:
        logger.info(f"Searching flights with parameters: {querystring}")
        
        response = requests.get(url, headers=headers, params=querystring, timeout=30)
        
        # Log full response details for debugging
        logger.info(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Log raw response text for debugging
        raw_response = response.text
        logger.debug(f"Raw response: {raw_response}")
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON. Raw response: {raw_response}")
            return []
        
        # Detailed logging of response structure
        logger.debug(f"Response data keys: {data.keys() if data else 'No data'}")
        
        # Check for API errors
        if not data.get("status", False):
            logger.error(f"API Error: {data.get('message', 'Unknown error')}")
            logger.error(f"Errors: {data.get('errors', 'No specific errors')}")
            return []
        
        # Validate response structure
        if not data:
            logger.error("Empty response received")
            return []
        
        if 'data' not in data:
            logger.error(f"No 'data' key in response. Full response: {data}")
            return []
        
        # Check if the search is incomplete
        context = data.get("data", {}).get("context", {})
        logger.debug(f"Context: {context}")
        
        if context.get("status") == "incomplete":
            logger.warning("Search results are incomplete. Using search-incomplete endpoint for complete results.")
            
            # Get the session token from the context
            session_token = context.get("sessionToken")
            if session_token:
                # Use the search-incomplete endpoint to get complete results
                complete_data = complete_search(session_token, headers)
                if complete_data:
                    data = complete_data
                else:
                    logger.warning("Failed to get complete search results. Using initial incomplete results.")
        
        # Extract and format flight information
        flights = extract_flight_info(data)
        
        if not flights:
            logger.warning("No flights found in the API response")
            logger.debug(f"Full response data: {data}")
        
        return flights
    
    except requests.exceptions.Timeout:
        logger.error("API request timed out")
    except requests.exceptions.ConnectionError:
        logger.error("Connection error occurred")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
    
    return []

def complete_search(session_token: str, headers: Dict[str, str], max_attempts: int = 10, delay_seconds: int = 2) -> Dict[str, Any]:
    """
    Complete an incomplete search by polling the search-incomplete endpoint.
    
    Args:
        session_token: Session token from the initial search response
        headers: API request headers
        max_attempts: Maximum number of polling attempts
        delay_seconds: Delay between polling attempts
        
    Returns:
        Complete flight search data or None if unsuccessful
    """
    url = "https://sky-scanner3.p.rapidapi.com/flights/search-incomplete"
    
    querystring = {
        "sessionToken": session_token
    }
    
    logger.info(f"Completing search with session token: {session_token}")
    
    for attempt in range(1, max_attempts + 1):
        logger.debug(f"Search completion attempt {attempt}/{max_attempts}")
        
        try:
            response = requests.get(url, headers=headers, params=querystring, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check if we have all results
            context = data.get("data", {}).get("context", {})
            status = context.get("status")
            
            if status == "complete":
                logger.info("Search completed successfully")
                return data
            elif status == "incomplete":
                logger.debug(f"Search still incomplete. Waiting {delay_seconds} seconds before next attempt.")
                time.sleep(delay_seconds)
            else:
                logger.warning(f"Unexpected status: {status}")
                return None
                
        except Exception as e:
            logger.error(f"Error polling search-incomplete endpoint: {e}")
            return None
    
    logger.warning(f"Search did not complete after {max_attempts} attempts")
    return None

def extract_flight_info(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract key flight information from the SkyScanner API response.
    
    Args:
        api_response: Raw API response from SkyScanner
        
    Returns:
        List of dictionaries with simplified flight information
    """
    flight_info = []
    
    try:
        # Validate response structure
        if not api_response or 'data' not in api_response:
            logger.error("Invalid API response structure in extract_flight_info")
            return []
        
        # Check if data and itineraries exist
        itineraries = api_response.get("data", {}).get("itineraries", [])
        
        logger.debug(f"Number of itineraries found: {len(itineraries)}")
        
        if not itineraries:
            logger.warning("No itineraries found in the API response")
            return []
        
        for itinerary in itineraries:
            # Get information from the first leg (for one-way flights)
            if not itinerary.get("legs"):
                logger.warning("No legs found for itinerary")
                continue
                
            leg = itinerary["legs"][0]
            duration_minutes = leg.get("durationInMinutes", 0)
            
            # Format duration as hours and minutes
            hours, minutes = divmod(duration_minutes, 60)
            duration_formatted = f"{hours}h {minutes}m"
            
            # Extract origin and destination
            origin = leg.get("origin", {}).get("city", "Unknown Origin")
            destination = leg.get("destination", {}).get("city", "Unknown Destination")
            
            # Extract carrier information
            carriers = []
            if leg.get("carriers", {}).get("marketing"):
                for carrier in leg["carriers"]["marketing"]:
                    carriers.append(carrier.get("name", "Unknown Carrier"))
            
            # Get stop count
            stop_count = leg.get("stopCount", 0)
            
            # Get departure and arrival times
            departure_time = leg.get("departure", "")
            arrival_time = leg.get("arrival", "")
            
            # Format times if they exist
            formatted_departure_time = ""
            formatted_arrival_time = ""
            
            if departure_time:
                try:
                    dt = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
                    formatted_departure_time = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    pass
                    
            if arrival_time:
                try:
                    dt = datetime.fromisoformat(arrival_time.replace('Z', '+00:00'))
                    formatted_arrival_time = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    pass
            
            # Create flight information dictionary
            flight = {
                "carrier": ", ".join(carriers),
                "duration": duration_formatted,
                "price_formatted": itinerary.get("price", {}).get("formatted", "$0"),
                "origin": origin,
                "destination": destination,
                "stops": stop_count,
                "departure_time": formatted_departure_time,
                "arrival_time": formatted_arrival_time
            }
            
            flight_info.append(flight)
        
        return flight_info
    
    except Exception as e:
        logger.error(f"Error extracting flight information: {e}")
        logger.error(traceback.format_exc())
        return []

def get_city_skyid(city_name: str) -> Optional[str]:
    """
    Convert a city name to a SkyScanner entity ID (SkyID) using the auto-complete API.
    
    Args:
        city_name: The name of the city to search for
        
    Returns:
        SkyScanner entity ID or None if not found
    """
    url = "https://sky-scanner3.p.rapidapi.com/flights/auto-complete"
    
    # Validate input to prevent complex queries
    city_name = city_name.split()[0] if len(city_name.split()) > 0 else city_name
    
    querystring = {
        "query": city_name,
        "type": "PLACE"  # Search for places (cities, airports, etc.)
    }
    
    headers = {
        "x-rapidapi-key": "00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5",
        "x-rapidapi-host": "sky-scanner3.p.rapidapi.com"
    }
    
    try:
        logger.info(f"Searching for SkyID for city: {city_name}")
        
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        logger.debug(f"Auto-complete response: {data}")
        
        # Check if the response is valid and has data
        if not data.get("status", False):
            logger.error(f"API error for city: {city_name}")
            return None
        
        # Handle different possible response structures
        results = None
        if isinstance(data.get("data"), dict):
            results = data["data"].get("presentation", [])
        elif isinstance(data.get("data"), list):
            results = data["data"]
        
        if not results:
            logger.warning(f"No results found for city: {city_name}")
            return None
        
        # Try multiple ways to extract the skyId
        for result in results:
            if isinstance(result, dict):
                skyid = (
                    result.get("id") or 
                    result.get("skyId") or 
                    result.get("presentation", {}).get("id") or 
                    result.get("presentation", {}).get("skyId")
                )
                if skyid:
                    logger.info(f"Found SkyID for {city_name}: {skyid}")
                    return skyid
        
        logger.warning(f"SkyID not found in results for city: {city_name}")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error getting SkyID for city {city_name}: {e}")
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON response for city {city_name}")
    except Exception as e:
        logger.error(f"Unexpected error getting SkyID for city {city_name}: {e}")
        logger.error(traceback.format_exc())
    
    return None

def search_flights_from_query(query: str) -> List[Dict[str, Any]]:
    """
    Parse a natural language query and search for flights matching the criteria.
    
    Args:
        query: Natural language query about flight search
        
    Returns:
        List of dictionaries containing flight information
    """
    # Parse the query to extract parameters
    params = parse_flight_query(query)
    
    # Convert city names to SkyIDs
    from_entity_id = None
    to_entity_id = None
    
    if params["from_entity_id"]:
        from_entity_id = get_city_skyid(params["from_entity_id"])
        if not from_entity_id:
            logger.error(f"Could not find SkyID for origin city: {params['from_entity_id']}")
            return []
    else:
        logger.error("No origin location specified in the query")
        return []
    
    if params["to_entity_id"]:
        to_entity_id = get_city_skyid(params["to_entity_id"])
        # If destination is not found, we can still search for "everywhere"
        if not to_entity_id:
            logger.warning(f"Could not find SkyID for destination city: {params['to_entity_id']}")
            # We'll proceed without the to_entity_id, which will search "everywhere"
    
    # Search for flights with the extracted parameters and converted SkyIDs
    return search_flights(
        from_entity_id=from_entity_id,
        to_entity_id=to_entity_id,
        depart_date=params["depart_date"],
        cabin_class=params["cabin_class"],
        adults=params["adults"],
        children=params["children"],
        infants=params["infants"],
        whole_month_depart=params["depart_date"] if params["whole_month"] else None,
        sort=params["sort"]
    )

# Example usage
if __name__ == "__main__":
    # Example 1: Search for flights from Paris to New Orleans
    
    
    # Example 2: Search using natural language query
    query = "What are the cheapest flights from Delhi to Mumbai on April 15th, 2025 in economy class?"
    flights_from_query = search_flights_from_query(query)
    
    # Print flight information in a tabular format
    if flights_from_query:
        print(f"{'Carrier':<40} {'Duration':<10} {'Price':<10} {'Stops':<5} {'Departure':<20} {'Arrival':<20}")
        print("-" * 120)
        
        for flight in flights_from_query:
            print(f"{flight['carrier']:<40} {flight['duration']:<10} {flight['price_formatted']:<10} {flight['stops']:<5} {flight['departure_time']:<20} {flight['arrival_time']:<20}")
    else:
        print("No flights found or an error occurred.")  