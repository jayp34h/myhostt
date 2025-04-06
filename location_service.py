import requests
from math import radians, sin, cos, sqrt, atan2

def get_user_location():
    """
    Get user's location based on IP address using ip-api.com
    Returns a dictionary with location information or None if unsuccessful
    """
    try:
        headers = {
            "User-Agent": "myMedihelp/1.0 (jayp52025@gmail.com)",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9"
        }
        response = requests.get("http://ip-api.com/json/", headers=headers, timeout=10)
        
        # Check for rate limiting or server errors
        if response.status_code == 429:
            print("IP-API rate limit reached. Please try again later.")
            return None
        elif response.status_code != 200:
            print(f"IP-API returned status code {response.status_code}")
            return None
            
        try:
            data = response.json()
        except ValueError:
            print("Invalid JSON response from IP-API")
            return None
        if data["status"] == "success":
            return {
                "latitude": data["lat"],
                "longitude": data["lon"],
                "city": data["city"],
                "region": data["regionName"],
                "country": data["country"]
            }
        else:
            print("Failed to get location: API returned unsuccessful status")
            return None
    except Exception as e:
        print(f"Error getting location: {str(e)}")
        return None

def find_nearby_hospitals(latitude=None, longitude=None, radius=5000, limit=5):
    """
    Find nearby hospitals and clinics using OpenStreetMap Nominatim API
    
    Args:
        latitude (float): Latitude coordinate (if None, will use user's detected location)
        longitude (float): Longitude coordinate (if None, will use user's detected location)
        radius (int): Search radius in meters (default: 5000 meters = 5km)
        limit (int): Maximum number of results to return (default: 5)
        
    Returns:
        list: List of dictionaries containing hospital information
    """
    try:
        # If coordinates not provided, get user's location
        if latitude is None or longitude is None:
            user_location = get_user_location()
            if not user_location:
                return {"error": "Could not determine your location. Please provide your location manually."}
            
            latitude = user_location["latitude"]
            longitude = user_location["longitude"]
        
        # Prepare the Overpass API query
        # This query searches for hospitals and clinics within the specified radius
        overpass_url = "https://overpass-api.de/api/interpreter"
        overpass_query = f"""
        [out:json];
        (
          node["amenity"="hospital"](around:{radius},{latitude},{longitude});
          way["amenity"="hospital"](around:{radius},{latitude},{longitude});
          relation["amenity"="hospital"](around:{radius},{latitude},{longitude});
          node["amenity"="clinic"](around:{radius},{latitude},{longitude});
          way["amenity"="clinic"](around:{radius},{latitude},{longitude});
          relation["amenity"="clinic"](around:{radius},{latitude},{longitude});
        );
        out center body {limit};
        """
        
        # Make the request to Overpass API with proper headers
        headers = {
            "User-Agent": "myMedihelp/1.0 (jayp52025@gmail.com)",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9"
        }
        response = requests.post(overpass_url, data={"data": overpass_query}, headers=headers, timeout=30)
        
        # Check for rate limiting or server errors
        if response.status_code == 429:
            return {"error": "Too many requests. Please try again in a few minutes."}
        elif response.status_code != 200:
            return {"error": f"Server returned status code {response.status_code}. Please try again later."}
        
        # Ensure we got valid JSON response
        try:
            data = response.json()
        except ValueError:
            return {"error": "Invalid response from server. Please try again later."}
        data = response.json()
        
        # Process the results
        hospitals = []
        for element in data.get("elements", []):
            # Extract hospital information
            hospital_info = {
                "id": element.get("id"),
                "type": element.get("type"),
                "name": element.get("tags", {}).get("name", "Unnamed Hospital/Clinic"),
                "amenity": element.get("tags", {}).get("amenity"),
                "phone": element.get("tags", {}).get("phone"),
                "website": element.get("tags", {}).get("website"),
                "address": {}
            }
            
            # Get coordinates
            if element.get("type") == "node":
                hospital_info["latitude"] = element.get("lat")
                hospital_info["longitude"] = element.get("lon")
            elif "center" in element:
                hospital_info["latitude"] = element.get("center", {}).get("lat")
                hospital_info["longitude"] = element.get("center", {}).get("lon")
            
            # Extract address components
            tags = element.get("tags", {})
            address_components = [
                "addr:housenumber", "addr:street", "addr:city", 
                "addr:postcode", "addr:suburb", "addr:state"
            ]
            
            for component in address_components:
                if component in tags:
                    key = component.replace("addr:", "")
                    hospital_info["address"][key] = tags[component]
            
            # Calculate distance from user (in kilometers)
            if "latitude" in hospital_info and "longitude" in hospital_info:
                hospital_info["distance"] = calculate_distance(
                    latitude, longitude, 
                    hospital_info["latitude"], hospital_info["longitude"]
                )
            
            hospitals.append(hospital_info)
        
        # Sort hospitals by distance
        hospitals.sort(key=lambda x: x.get("distance", float("inf")))
        
        # Limit the number of results
        hospitals = hospitals[:limit]
        
        if not hospitals:
            return {"message": "No hospitals or clinics found in your area. Try increasing the search radius."}
        
        return hospitals
    
    except Exception as e:
        print(f"Error finding nearby hospitals: {str(e)}")
        return {"error": f"Error finding nearby hospitals: {str(e)}"}

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points using the Haversine formula
    Returns distance in kilometers
    """
    # Convert coordinates from degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    radius = 6371  # Radius of Earth in kilometers
    
    # Calculate the distance
    distance = radius * c
    
    return round(distance, 2)  # Round to 2 decimal places

def format_hospital_results(hospitals):
    """
    Format hospital results into a readable string
    """
    if isinstance(hospitals, dict) and "error" in hospitals:
        return hospitals["error"]
    
    if isinstance(hospitals, dict) and "message" in hospitals:
        return hospitals["message"]
    
    result = "Nearby hospitals and clinics:\n\n"
    
    for i, hospital in enumerate(hospitals, 1):
        name = hospital.get("name", "Unnamed Hospital/Clinic")
        distance = hospital.get("distance", "Unknown")
        
        # Format address
        address_parts = []
        if hospital.get("address"):
            addr = hospital["address"]
            if "housenumber" in addr and "street" in addr:
                address_parts.append(f"{addr['housenumber']} {addr['street']}")
            elif "street" in addr:
                address_parts.append(addr["street"])
            
            if "city" in addr:
                address_parts.append(addr["city"])
            
            if "postcode" in addr:
                address_parts.append(addr["postcode"])
        
        address = ", ".join(address_parts) if address_parts else "Address not available"
        
        # Format phone
        phone = hospital.get("phone", "Phone not available")
        
        # Format website
        website = hospital.get("website", "Website not available")
        
        # Add to result
        result += f"{i}. {name}\n"
        result += f"   Distance: {distance} km\n"
        result += f"   Address: {address}\n"
        result += f"   Phone: {phone}\n"
        result += f"   Website: {website}\n\n"
    
    return result