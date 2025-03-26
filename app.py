import streamlit as st
import folium
from streamlit_folium import folium_static
from hotel_finder import HotelFinder
import pandas as pd
import time

# Set page configuration
st.set_page_config(
    page_title="TripAdvisor Hotel Finder",
    page_icon="🏨",
    layout="wide"
)

# Initialize the HotelFinder
@st.cache_resource
def get_hotel_finder():
    # You would replace this with your actual API key in a production application
    api_key = st.secrets["RAPIDAPI_KEY"] if "RAPIDAPI_KEY" in st.secrets else "YOUR_RAPIDAPI_KEY"
    return HotelFinder(api_key=api_key)

finder = get_hotel_finder()

# App title and description
st.title("🏨 TripAdvisor Hotel Finder")
st.markdown("""
    Search for hotels in any city worldwide and filter by price, rating, and amenities.
    Get detailed information including contact details, amenities, and guest reviews.
""")

# Search bar for city
with st.container():
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("Enter city or location", "New York")
    with col2:
        if st.button("Search", type="primary"):
            with st.spinner("Searching for hotels..."):
                # Make the API call to search for hotels
                search_results = finder.search_hotels(search_query)
                if search_results and 'results' in search_results:
                    st.session_state.search_results = search_results
                    st.session_state.filtered_hotels = search_results['results']
                    st.session_state.search_location = search_query
                    st.success(f"Found {search_results['items_count']} hotels in {search_query}")
                else:
                    st.error("No hotels found or API error occurred. Please try again.")

# Initialize session state for hotel data
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
    
if 'filtered_hotels' not in st.session_state:
    st.session_state.filtered_hotels = []
    
if 'search_location' not in st.session_state:
    st.session_state.search_location = ""
    
if 'selected_hotel' not in st.session_state:
    st.session_state.selected_hotel = None

# If we have search results, show the filtering options and hotel list
if st.session_state.search_results:
    # Create a container for the filters and results
    st.markdown(f"### Hotels in {st.session_state.search_location}")
    
    # Set up the layout with two columns: left for filters, right for results
    filter_col, results_col = st.columns([1, 3])
    
    with filter_col:
        st.subheader("Filter Options")
        
        # Get price range for all hotels
        all_hotels = st.session_state.search_results['results']
        min_prices = [h['price_range_usd']['min'] for h in all_hotels if 'price_range_usd' in h]
        max_prices = [h['price_range_usd']['max'] for h in all_hotels if 'price_range_usd' in h]
        
        min_price = min(min_prices) if min_prices else 0
        max_price = max(max_prices) if max_prices else 1000
        
        # Price range filter
        price_range = st.slider(
            "Price Range (USD)",
            min_value=int(min_price),
            max_value=int(max_price),
            value=(int(min_price), int(max_price))
        )
        
        # Rating filter
        all_ratings = sorted(list(set(h['rating'] for h in all_hotels if 'rating' in h)))
        min_rating = st.select_slider(
            "Minimum Rating",
            options=all_ratings,
            value=min(all_ratings) if all_ratings else 1
        )
        
        # Amenities filter
        all_amenities = set()
        for hotel in all_hotels:
            if 'amenities' in hotel and hotel['amenities']:
                all_amenities.update(hotel['amenities'])
        
        selected_amenities = st.multiselect(
            "Required Amenities",
            options=sorted(all_amenities),
            default=[]
        )
        
        # Apply filters button
        if st.button("Apply Filters"):
            with st.spinner("Filtering hotels..."):
                filtered_hotels = finder.filter_hotels(
                    min_price=price_range[0],
                    max_price=price_range[1],
                    min_rating=min_rating,
                    required_amenities=selected_amenities
                )
                
                st.session_state.filtered_hotels = filtered_hotels
                st.success(f"Found {len(filtered_hotels)} hotels matching your criteria")
    
    with results_col:
        # Create tabs for List View and Map View
        list_tab, map_tab = st.tabs(["List View", "Map View"])
        
        with list_tab:
            # Show the filtered hotels in a scrollable list
            if st.session_state.filtered_hotels:
                # Convert to DataFrame for easier display
                hotels_df = pd.DataFrame([
                    {
                        "id": h['id'],
                        "name": h['name'],
                        "rating": h.get('rating', 'N/A'),
                        "reviews": h.get('reviews', 0),
                        "price_min": h.get('price_range_usd', {}).get('min', 'N/A'),
                        "price_max": h.get('price_range_usd', {}).get('max', 'N/A'),
                        "amenities": ", ".join(h.get('amenities', []))[:50] + ("..." if len(", ".join(h.get('amenities', []))) > 50 else "")
                    }
                    for h in st.session_state.filtered_hotels
                ])
                
                # Format the DataFrame display
                hotels_df['price_range'] = hotels_df.apply(lambda x: f"${x['price_min']}-${x['price_max']}" if x['price_min'] != 'N/A' else 'N/A', axis=1)
                display_df = hotels_df[['name', 'rating', 'reviews', 'price_range', 'amenities']]
                
                # Show the DataFrame with clickable hotel names
                st.dataframe(
                    display_df,
                    column_config={
                        "name": st.column_config.TextColumn("Hotel Name"),
                        "rating": st.column_config.NumberColumn("Rating", format="%.1f ⭐"),
                        "reviews": st.column_config.NumberColumn("Reviews"),
                        "price_range": st.column_config.TextColumn("Price Range (USD)"),
                        "amenities": st.column_config.TextColumn("Amenities")
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # Hotel selection
                selected_hotel_name = st.selectbox(
                    "Select a hotel for detailed information",
                    options=hotels_df['name'].tolist()
                )
                
                if selected_hotel_name:
                    selected_hotel_id = hotels_df[hotels_df['name'] == selected_hotel_name]['id'].iloc[0]
                    if st.button("View Hotel Details", key="view_details"):
                        st.session_state.selected_hotel = selected_hotel_id
            else:
                st.info("No hotels match your current filters. Try adjusting your criteria.")
        
        with map_tab:
            # Create a map of the filtered hotels
            if st.session_state.filtered_hotels:
                with st.spinner("Loading map..."):
                    hotel_map = finder.create_hotel_map(st.session_state.filtered_hotels)
                    folium_static(hotel_map, width=800, height=600)
            else:
                st.info("No hotels to display on the map.")

    # Show detailed information for the selected hotel
    if st.session_state.selected_hotel:
        st.markdown("---")
        st.subheader("Hotel Details")
        
        with st.spinner("Loading hotel details..."):
            # Fetch detailed hotel information
            hotel_details = finder.get_hotel_details(st.session_state.selected_hotel)
            
            if hotel_details:
                # Find the basic hotel information from our filtered list
                basic_info = next(
                    (h for h in st.session_state.filtered_hotels if h['id'] == st.session_state.selected_hotel),
                    {}
                )
                
                # Combine the basic and detailed information
                hotel = {**basic_info, **hotel_details}
                
                # Layout the hotel details in columns
                col1, col2 = st.columns([3, 2])
                
                with col1:
                    st.header(hotel.get('name', 'Hotel Name Not Available'))
                    
                    # Rating and reviews
                    rating = hotel.get('rating', 'N/A')
                    reviews = hotel.get('reviews', 0)
                    st.markdown(f"**Rating:** {rating} ⭐ ({reviews} reviews)")
                    
                    # Price range
                    price_range = "Price not available"
                    if 'price_range_usd' in hotel:
                        price_range = f"${hotel['price_range_usd']['min']}-${hotel['price_range_usd']['max']}"
                    st.markdown(f"**Price Range:** {price_range}")
                    
                    # Address
                    address = hotel.get('address', 'Address not available')
                    st.markdown(f"**Address:** {address}")
                    
                    # Contact information
                    phone = hotel.get('phone', 'Not available')
                    email = hotel.get('email', 'Not available')
                    website = hotel.get('website', hotel.get('link', '#'))
                    
                    st.markdown(f"**Phone:** {phone}")
                    st.markdown(f"**Email:** {email}")
                    st.markdown(f"**Website:** [Visit Website]({website})")
                    
                    # Amenities
                    amenities = hotel.get('amenities', [])
                    if amenities:
                        st.markdown("**Amenities:**")
                        st.markdown(", ".join(amenities))
                    
                    # Review keywords
                    keywords = hotel.get('review_keywords', [])
                    if keywords:
                        st.markdown("**Review Highlights:**")
                        keyword_summary = finder.summarize_keywords(keywords)
                        st.markdown(keyword_summary)
                
                with col2:
                    # Featured image
                    featured_image = hotel.get('featured_image', '')
                    if featured_image:
                        st.image(featured_image, caption=hotel.get('name', ''), use_column_width=True)
                    
                    # Map location
                    if 'latitude' in hotel and 'longitude' in hotel:
                        st.markdown("**Hotel Location:**")
                        single_hotel_map = folium.Map(location=[hotel['latitude'], hotel['longitude']], zoom_start=15)
                        folium.Marker(
                            location=[hotel['latitude'], hotel['longitude']],
                            popup=hotel['name'],
                            tooltip=hotel['name'],
                            icon=folium.Icon(color='red', icon='info-sign')
                        ).add_to(single_hotel_map)
                        
                        folium_static(single_hotel_map, width=400, height=300)
            else:
                st.error("Could not fetch hotel details. Please try again.")
                
            # Button to clear selected hotel and go back to list
            if st.button("Back to List", key="back_button"):
                st.session_state.selected_hotel = None
                st.experimental_rerun()
else:
    # If no search has been performed yet, show some instructions or featured destinations
    st.info("Enter a city or location name in the search box above to find hotels.")
    
    # Suggest some popular destinations
    st.markdown("### Popular Destinations")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("New York", key="ny_button"):
            search_query = "New York"
            with st.spinner("Searching for hotels in New York..."):
                search_results = finder.search_hotels(search_query)
                if search_results and 'results' in search_results:
                    st.session_state.search_results = search_results
                    st.session_state.filtered_hotels = search_results['results']
                    st.session_state.search_location = search_query
                    st.experimental_rerun()
    
    with col2:
        if st.button("London", key="london_button"):
            search_query = "London"
            with st.spinner("Searching for hotels in London..."):
                search_results = finder.search_hotels(search_query)
                if search_results and 'results' in search_results:
                    st.session_state.search_results = search_results
                    st.session_state.filtered_hotels = search_results['results']
                    st.session_state.search_location = search_query
                    st.experimental_rerun()
    
    with col3:
        if st.button("Paris", key="paris_button"):
            search_query = "Paris"
            with st.spinner("Searching for hotels in Paris..."):
                search_results = finder.search_hotels(search_query)
                if search_results and 'results' in search_results:
                    st.session_state.search_results = search_results
                    st.session_state.filtered_hotels = search_results['results']
                    st.session_state.search_location = search_query
                    st.experimental_rerun()
    
    # Add a section showcasing app features
    st.markdown("---")
    st.markdown("### App Features")
    
    feature_col1, feature_col2, feature_col3 = st.columns(3)
    
    with feature_col1:
        st.markdown("#### 🔍 Search and Filter")
        st.markdown("""
        - Search for hotels in any city worldwide
        - Filter by price range, rating, and amenities
        - Sort results to find exactly what you need
        """)
    
    with feature_col2:
        st.markdown("#### 🗺️ Interactive Maps")
        st.markdown("""
        - View hotel locations on interactive maps
        - Explore neighborhoods and nearby attractions
        - Get a visual sense of the hotel's location
        """)
    
    with feature_col3:
        st.markdown("#### 📊 Detailed Information")
        st.markdown("""
        - Comprehensive hotel details and photos
        - Contact information and website links
        - Review highlights from actual guests
        """)
    
    # Add a quick start guide
    st.markdown("---")
    st.markdown("### Quick Start Guide")
    st.markdown("""
    1. **Enter a city name** in the search box at the top and click "Search"
    2. **Browse the results** in the list view or map view
    3. **Filter the results** using the options in the sidebar
    4. **Select a hotel** and click