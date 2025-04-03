from fastapi import FastAPI
import sqlite3
import json
import ollama
from pydantic import BaseModel
import requests
from fastapi.middleware.cors import CORSMiddleware


UNSPLASH_ACCESS_KEY = "eIaqCQxyf7UZQmWLLRMNOxLNgszGSC4dqH2q20pxK3g"

# Initialize FastAPI app
app = FastAPI()

# Connect to SQLite Database
conn = sqlite3.connect("farming_data.db", check_same_thread=False)
cursor = conn.cursor()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Create Farmer Data Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS farmer_data (
    Farm_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Soil_pH REAL,
    Soil_Moisture REAL,
    Temperature_C REAL,
    Rainfall_mm REAL,
    Crop_Type TEXT,
    Fertilizer_Usage_kg REAL,
    Pesticide_Usage_kg REAL,
    Crop_Yield_ton REAL,
    Sustainability_Score REAL
);
""")

# Create Market Data Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS market_data (
    Market_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Product TEXT,
    Market_Price_per_ton REAL,
    Demand_Index REAL,
    Supply_Index REAL,
    Competitor_Price_per_ton REAL,
    Economic_Indicator REAL,
    Weather_Impact_Score REAL,
    Seasonal_Factor TEXT,
    Consumer_Trend_Index REAL
);
""")

conn.commit()


# Farmer Data Model
class FarmerData(BaseModel):
    Soil_pH: float
    Soil_Moisture: float
    Temperature_C: float
    Rainfall_mm: float
    Crop_Type: str
    Fertilizer_Usage_kg: float
    Pesticide_Usage_kg: float
    Crop_Yield_ton: float
    Sustainability_Score: float


# Market Data Model
class MarketData(BaseModel):
    Product: str
    Market_Price_per_ton: float
    Demand_Index: float
    Supply_Index: float
    Competitor_Price_per_ton: float
    Economic_Indicator: float
    Weather_Impact_Score: float
    Seasonal_Factor: str
    Consumer_Trend_Index: float


# API: Upload Farmer Data
@app.post("/upload/farmer_data")
def upload_farmer_data(data: FarmerData):
    cursor.execute("""
    INSERT INTO farmer_data (Soil_pH, Soil_Moisture, Temperature_C, Rainfall_mm, Crop_Type, Fertilizer_Usage_kg, Pesticide_Usage_kg, Crop_Yield_ton, Sustainability_Score) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tuple(data.dict().values()))
    conn.commit()
    return {"message": "Farmer data added successfully"}


# API: Upload Market Data
@app.post("/upload/market_data")
def upload_market_data(data: MarketData):
    cursor.execute("""
    INSERT INTO market_data (Product, Market_Price_per_ton, Demand_Index, Supply_Index, Competitor_Price_per_ton, Economic_Indicator, Weather_Impact_Score, Seasonal_Factor, Consumer_Trend_Index)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tuple(data.dict().values()))
    conn.commit()
    return {"message": "Market data added successfully"}


# API: Fetch All Farmer Data
@app.get("/farmers")
def get_all_farmers():
    cursor.execute("SELECT * FROM farmer_data")
    rows = cursor.fetchall()
    farmers = [
        {
            "Farm_ID": row[0],
            "Soil_pH": row[1],
            "Soil_Moisture": row[2],
            "Temperature_C": row[3],
            "Rainfall_mm": row[4],
            "Crop_Type": row[5],
            "Fertilizer_Usage_kg": row[6],
            "Pesticide_Usage_kg": row[7],
            "Crop_Yield_ton": row[8],
            "Sustainability_Score": row[9]
        }
        for row in rows
    ]
    return farmers if farmers else {"message": "No farmer data found"}


# API: Fetch All Market Data
@app.get("/markets")
def get_all_markets():
    cursor.execute("SELECT * FROM market_data")
    rows = cursor.fetchall()
    markets = [
        {
            "Market_ID": row[0],
            "Product": row[1],
            "Market_Price_per_ton": row[2],
            "Demand_Index": row[3],
            "Supply_Index": row[4],
            "Competitor_Price_per_ton": row[5],
            "Economic_Indicator": row[6],
            "Weather_Impact_Score": row[7],
            "Seasonal_Factor": row[8],
            "Consumer_Trend_Index": row[9]
        }
        for row in rows
    ]
    return markets if markets else {"message": "No market data found"}

def fetch_image_urls(query):
    url = f"https://api.unsplash.com/search/photos?query={query}&client_id={UNSPLASH_ACCESS_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        image_urls = [img["urls"]["regular"] for img in data["results"][:3]]  # Get top 3 images
        return image_urls
    return []

# Function to fetch dynamic videos and articles
def fetch_dynamic_content(query):
    # YouTube & Web Search Query
    search_query = query.replace(" ", "+")
    
    # Dynamic YouTube Search URL (Example - Replace with actual API)
    youtube_search_url = f"https://www.youtube.com/results?search_query={search_query}"
    
    # Web Search Links (Example - Replace with API-based search if needed)
    search_links = [
        f"https://www.google.com/search?q={search_query}+best+practices",
        f"https://www.agriculture.com/search?q={search_query}"
    ]
    
    # Image placeholders (Replace with API-based image search if needed)
    image_links = fetch_image_urls(query)
    
    return youtube_search_url, search_links, image_links

@app.get("/advise/{farm_id}")
def get_advice(farm_id: int):
    # Fetch farmer data
    cursor.execute("SELECT * FROM farmer_data WHERE Farm_ID = ?", (farm_id,))
    farm_data = cursor.fetchone()
    if not farm_data:
        return {"message": "Farm not found"}
    
    # Fetch market data for the given crop
    cursor.execute("SELECT * FROM market_data WHERE Product = ?", (farm_data[5],))
    market_data = cursor.fetchone()

    # 🛠️ Extracting necessary data for AI model
    input_data = {
        "Soil_pH": farm_data[1],
        "Soil_Moisture": farm_data[2],
        "Temperature_C": farm_data[3],
        "Rainfall_mm": farm_data[4],
        "Crop_Type": farm_data[5],
        "Market_Price": market_data[2] if market_data else "N/A",
        "Demand_Index": market_data[3] if market_data else "N/A"
    }

    # 🧠 AI Model Processing
    response = ollama.chat(model="tinyllama", messages=[
        {"role": "system", "content": "You are an advanced AI farm and market advisor."},
        {"role": "user", "content": f"Based on this data: {input_data}, provide best farming strategies, market advice, and sustainability tips."}
    ])

    # 🔍 Fetching dynamic learning resources
    youtube_url, search_links, image_links = fetch_dynamic_content(farm_data[5] + " farming best practices")

    return {
        "recommendation": response["message"],  # AI-generated advice
        "videos": youtube_url,  # Dynamic video link
        "useful_links": search_links,  # Informational links
        "images": image_links  # Related images
    }

# Run API Server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
