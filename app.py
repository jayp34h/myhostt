from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from location_service import find_nearby_hospitals, format_hospital_results
import os

app = Flask(__name__)
# Enable CORS with proper configuration
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:*", "http://127.0.0.1:*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Serve the HTML file
@app.route('/')
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'index.html')

@app.route("/location", methods=["POST", "OPTIONS"])
def receive_location():
    """Receive user location from frontend and find nearby hospitals"""
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "error": "Invalid JSON data received",
                "formatted_results": "Error: Invalid JSON data received"
            }), 400
            
        lat = data.get("latitude")
        lon = data.get("longitude")
        
        if lat is None or lon is None:
            return jsonify({
                "error": "Missing latitude or longitude in request",
                "formatted_results": "Error: Missing latitude or longitude in request"
            }), 400
        
        print(f"📍 Received user location: {lat}, {lon}")
        
        # Find nearby hospitals using the provided coordinates
        hospitals = find_nearby_hospitals(
            latitude=lat,
            longitude=lon,
            radius=5000,  # 5km radius
            limit=5  # Top 5 results
        )
        
        # Handle different return types from find_nearby_hospitals
        if isinstance(hospitals, dict) and ("error" in hospitals or "message" in hospitals):
            # If hospitals contains an error or message, use it directly
            error_message = hospitals.get("error") or hospitals.get("message")
            formatted_results = error_message
            hospital_list = []
        else:
            # If hospitals is a list, format it normally
            hospital_list = hospitals
            formatted_results = format_hospital_results(hospitals)
        
        return jsonify({
            "message": "Location received!",
            "hospitals": hospital_list,
            "formatted_results": formatted_results
        })
    except Exception as e:
        return jsonify({
            "error": f"Server error: {str(e)}",
            "formatted_results": f"Error: {str(e)}"
        }), 500

if __name__ == "__main__":
    app.run(debug=True)