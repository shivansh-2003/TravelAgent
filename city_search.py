import requests
import json

def search_location(query):
    """
    Search for a location and return information about it
    
    Args:
        query (str): The location to search for (e.g., "New York")
        
    Returns:
        list: A list of dictionaries containing information about the matched locations
    """
    url = "https://sky-scanner3.p.rapidapi.com/flights/auto-complete"
    
    querystring = {"query": query}
    
    headers = {
        "x-rapidapi-key": "00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5",
        "x-rapidapi-host": "sky-scanner3.p.rapidapi.com"
    }
    
    response = requests.get(url, headers=headers, params=querystring)
    
    if response.status_code == 200:
        return response.json()["data"]
    else:
        print(f"Error: {response.status_code}")
        return []

def get_sky_id(location_name, entity_type=None):
    """
    Get the skyId for a given location name
    
    Args:
        location_name (str): The name of the location to search for
        entity_type (str, optional): Specify the type of location to match 
                                     (e.g., 'CITY', 'AIRPORT'). Defaults to None.
        
    Returns:
        str: The skyId for the location, or None if no match is found
    """
    # Validate input
    if not location_name or not isinstance(location_name, str):
        print("Error: Invalid location name provided.")
        return None
    
    # Search for locations
    results = search_location(location_name)
    
    if not results:
        print(f"No locations found for '{location_name}'.")
        return None
    
    # Filter results based on entity type if specified
    if entity_type:
        filtered_results = [
            result for result in results 
            if result["navigation"]["entityType"].upper() == entity_type.upper()
        ]
        # If filtered results are empty, use original results
        results = filtered_results if filtered_results else results
    
    # Matching strategies
    strategies = [
        # 1. Exact match with specified entity type
        lambda r: (r["presentation"]["title"].lower() == location_name.lower() and 
                   (not entity_type or r["navigation"]["entityType"].upper() == entity_type.upper())),
        
        # 2. Partial match (contains location name)
        lambda r: location_name.lower() in r["presentation"]["title"].lower(),
        
        # 3. First result if no other match found
        lambda r: True
    ]
    
    # Apply matching strategies
    for strategy in strategies:
        matches = list(filter(strategy, results))
        if matches:
            # Return only the skyId
            return matches[0]["navigation"]["relevantFlightParams"]["skyId"]
    
    print(f"No matching location found for '{location_name}'.")
    return None

# Example usage
if __name__ == "__main__":
    
    city_name = input("\nEnter a city name to search (or 'quit' to exit): ")
    sky_id = get_sky_id(city_name)
    print(f"SkyId for {city_name}: {sky_id}")
    # Interactive search
   