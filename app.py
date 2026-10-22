"""
WanderAI - Next-Gen AI Travel Companion & Itinerary Architect
A production-ready SaaS application for personalized travel curation,
geographic transit optimization, dynamic activity swapping, and offline travel guides.
Powered by Google Gemini 2.5 Flash with intelligent offline fallback.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import re
import os
import io
import datetime
import sqlite3
from typing import Dict, List, Any

# Google GenAI import
try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# ReportLab imports for automated PDF export
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & BRANDING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="WanderAI — Intelligent Trip Architect",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. MODERN CONSUMER SAAS STYLING (Wanderlust Premium Glassmorphism)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    .main {
        background: radial-gradient(circle at 10% 20%, rgba(14, 23, 42, 0.95), rgba(7, 11, 22, 1));
        color: #f1f5f9;
    }

    /* Glassmorphism Metric Cards */
    .metric-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 18px 22px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        backdrop-filter: blur(8px);
        margin-bottom: 14px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(56, 189, 248, 0.3);
    }
    .metric-title {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94a3b8;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.65rem;
        font-weight: 700;
        background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-subtitle {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 4px;
    }

    /* Status Pills */
    .pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        margin-right: 6px;
    }
    .pill-blue { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
    .pill-purple { background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }
    .pill-emerald { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .pill-amber { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }

    /* Timeline Slot Card */
    .slot-card {
        background: rgba(15, 23, 42, 0.7);
        border-left: 4px solid #38bdf8;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 14px;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    .slot-time {
        font-weight: 700;
        font-size: 0.85rem;
        color: #38bdf8;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .slot-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 4px 0 8px 0;
    }
    .slot-desc {
        font-size: 0.92rem;
        color: #cbd5e1;
        line-height: 1.5;
    }
    .slot-meta {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 10px;
        font-size: 0.82rem;
        color: #94a3b8;
    }

    /* Geographic Cluster Highlight */
    .cluster-banner {
        background: linear-gradient(90deg, rgba(30, 58, 138, 0.35) 0%, rgba(15, 23, 42, 0.6) 100%);
        border: 1px dashed rgba(56, 189, 248, 0.4);
        border-radius: 10px;
        padding: 12px 18px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. DATABASE INITIALIZATION (SQLite Local Persistence)
# -----------------------------------------------------------------------------
DB_PATH = "travel_planner.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id TEXT PRIMARY KEY,
            title TEXT,
            destination TEXT,
            duration INTEGER,
            budget_tier TEXT,
            travel_party TEXT,
            pace TEXT,
            interests TEXT,
            total_cost_usd REAL,
            total_cost_inr REAL,
            created_at TIMESTAMP,
            itinerary_json TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def save_trip_to_db(trip_data: Dict[str, Any]):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO trips (
            id, title, destination, duration, budget_tier, travel_party, pace,
            interests, total_cost_usd, total_cost_inr, created_at, itinerary_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        trip_data["id"],
        trip_data["title"],
        trip_data["destination"],
        trip_data["duration"],
        trip_data["budget_tier"],
        trip_data["travel_party"],
        trip_data["pace"],
        ", ".join(trip_data["interests"]),
        trip_data["total_cost_usd"],
        trip_data["total_cost_inr"],
        trip_data["created_at"],
        json.dumps(trip_data)
    ))
    conn.commit()
    conn.close()

def load_trips_from_db() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT itinerary_json FROM trips ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [json.loads(row[0]) for row in rows]

def delete_trip_from_db(trip_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
    conn.commit()
    conn.close()

# -----------------------------------------------------------------------------
# 4. CURATED DESTINATION REPOSITORY (High-Fidelity Offline Templates)
# -----------------------------------------------------------------------------
USD_TO_INR = 83.5

CURATED_DESTINATIONS = {
    "Kyoto, Japan": {
        "vibe": "Cultural & Heritage",
        "best_season": "Spring (Cherry Blossoms) & Autumn (Foliage)",
        "weather_tag": "Mild 16°C • Clear Skies",
        "highlights": ["Fushimi Inari Taisha", "Arashiyama Bamboo Grove", "Gion Geisha District", "Kinkaku-ji Golden Pavilion"],
        "base_cost_usd": 150,
        "match_score": 98,
        "why_match": "Immersive cultural preservation, walkable temple clusters, world-renowned matcha and kaiseki cuisine.",
        "emergency": {"police": "110", "ambulance": "119", "tourist_helpline": "+81-75-343-0548", "embassy": "+81-3-3224-5000"},
        "packing": ["Walking slip-on shoes", "Layered garments", "Universal power plug (Type A)", "Pocket Wi-Fi / e-SIM", "Hand towel"],
        "default_cluster": "Higashiyama Historical Heritage District",
        "days": [
            {
                "day": 1,
                "theme": "Sacred Shrines & Historic Southern Higashiyama",
                "district": "Southern Higashiyama & Gion",
                "transit_saved_mins": 55,
                "walking_km": 4.2,
                "activities": [
                    {
                        "slot": "Morning Sightseeing (09:00 - 12:00)",
                        "title": "Fushimi Inari Taisha - Thousand Vermilion Torii Gates",
                        "category": "Culture",
                        "location": "Fushimi Ward, Kyoto",
                        "description": "Walk the mystical sacred mountain path flanked by 10,000 vivid vermilion torii gates winding through tranquil cedar woods.",
                        "tip": "Hike beyond the Yotsutsuji intersection for breathtaking city views and uncrowded photo spots.",
                        "cost_usd": 0,
                        "cost_inr": 0
                    },
                    {
                        "slot": "Lunch Recommendation (12:30 - 14:00)",
                        "title": "Nezameya Traditional Unagi & Handmade Kitsune Udon",
                        "category": "Gastronomy",
                        "location": "Near Inari Station",
                        "description": "Historic restaurant founded in 1540 serving sweet-soy glazed charbroiled eel over rice and fried tofu udon.",
                        "tip": "Try the seasoned inari sushi parcels wrapped in simmered abura-age.",
                        "cost_usd": 18,
                        "cost_inr": 1500
                    },
                    {
                        "slot": "Afternoon Culture & Leisure (14:30 - 17:30)",
                        "title": "Kiyomizu-dera Temple & Ninenzaka Stone Cobblestone Walk",
                        "category": "Scenic",
                        "location": "Higashiyama District",
                        "description": "Stand on the majestic wooden temple stage built without a single nail overlooking maple forests, then stroll stone-paved preserved merchant streets.",
                        "tip": "Drink from the Otowa Waterfall streams representing health, longevity, or success in studies.",
                        "cost_usd": 6,
                        "cost_inr": 500
                    },
                    {
                        "slot": "Evening Dining & Entertainment (18:30 - 21:30)",
                        "title": "Gion Lantern-Lit Evening Walk & Pontocho Alley Dining",
                        "category": "Nightlife",
                        "location": "Pontocho & Gion Hanamikoji",
                        "description": "Atmospheric narrow cobblestone alley lined with historic wooden machiya teahouses and riverside terraces over the Kamogawa River.",
                        "tip": "Keep voices respectful and follow local photography etiquette in preservation zones.",
                        "cost_usd": 40,
                        "cost_inr": 3340
                    }
                ]
            },
            {
                "day": 2,
                "theme": "Zen Bamboo Forest, River Gorges & Temple Gardens",
                "district": "Western Arashiyama & Sagano",
                "transit_saved_mins": 45,
                "walking_km": 3.8,
                "activities": [
                    {
                        "slot": "Morning Sightseeing (09:00 - 12:00)",
                        "title": "Arashiyama Bamboo Grove & Tenryu-ji Zen Temple",
                        "category": "Nature",
                        "location": "Ukyo Ward, Arashiyama",
                        "description": "Towering emerald green bamboo stalks swaying with the mountain breeze, leading to a UNESCO World Heritage 14th-century pond garden.",
                        "tip": "Arrive before 08:30 AM to catch natural morning sunlight filtering through the bamboo canes.",
                        "cost_usd": 5,
                        "cost_inr": 420
                    },
                    {
                        "slot": "Lunch Recommendation (12:30 - 14:00)",
                        "title": "Shigetsu Buddhist Shojin Ryori Vegan Banquet",
                        "category": "Gastronomy",
                        "location": "Inside Tenryu-ji Temple grounds",
                        "description": "Zen vegetarian multi-course cuisine prepared with seasonal mountain vegetables, fresh yuba (tofu skin), and sesame tofu.",
                        "tip": "Must reserve online or arrive right at opening for garden-view tatami seating.",
                        "cost_usd": 32,
                        "cost_inr": 2670
                    },
                    {
                        "slot": "Afternoon Culture & Leisure (14:30 - 17:30)",
                        "title": "Okochi Sanso Villa & Sagano Romantic Scenic Railway",
                        "category": "Culture",
                        "location": "Sagano Hills",
                        "description": "Exquisite mountain retreat built by silent film actor Denjiro Okochi, accompanied by traditional matcha and Japanese confection.",
                        "tip": "Enjoy the panoramic tea terrace looking toward Mt. Hiei and the Kyoto basin.",
                        "cost_usd": 12,
                        "cost_inr": 1000
                    },
                    {
                        "slot": "Evening Dining & Entertainment (18:30 - 21:30)",
                        "title": "Togetsukyo Bridge Sunset & Artisanal Craft Sake Tasting",
                        "category": "Leisure",
                        "location": "Oi River Waterfront",
                        "description": "Sunset views along the historic wooden bridge spanning the river, followed by flights of local Fushimi junmai daiginjo sake.",
                        "tip": "Pick up locally roasted hojicha soft serve from riverside vendors.",
                        "cost_usd": 28,
                        "cost_inr": 2340
                    }
                ]
            },
            {
                "day": 3,
                "theme": "Golden Splendor, Zen Rock Gardens & Market Feasts",
                "district": "Northern Kita Ward & Downtown Nakagyo",
                "transit_saved_mins": 50,
                "walking_km": 3.5,
                "activities": [
                    {
                        "slot": "Morning Sightseeing (09:00 - 12:00)",
                        "title": "Kinkaku-ji (Golden Pavilion) & Ryoan-ji Rock Garden",
                        "category": "Culture",
                        "location": "Kita Ward, Kyoto",
                        "description": "Breathtaking top two floors covered in pure gold leaf reflecting onto the Mirror Pond, followed by the world's most celebrated 15-stone Zen meditation dry landscape.",
                        "tip": "Notice how all 15 stones cannot be viewed simultaneously from any angle on the viewing deck.",
                        "cost_usd": 8,
                        "cost_inr": 670
                    },
                    {
                        "slot": "Lunch Recommendation (12:30 - 14:00)",
                        "title": "Nishiki Market Culinary Safari - 'Kyoto's Kitchen'",
                        "category": "Gastronomy",
                        "location": "Nakagyo Ward",
                        "description": "Five-block historic covered market bursting with over 130 stalls: freshly grilled baby octopus skewers, wagyu beef cubes, and dashi tamagoyaki.",
                        "tip": "Eat near the shop where you bought food rather than walking while eating.",
                        "cost_usd": 22,
                        "cost_inr": 1840
                    },
                    {
                        "slot": "Afternoon Culture & Leisure (14:30 - 17:30)",
                        "title": "Nijo Castle & Nightingales Chirping Floors",
                        "category": "Culture",
                        "location": "Nijojo-cho",
                        "description": "The formidable residence of the Tokugawa Shoguns featuring squeaking 'nightingale' wooden floorboards designed to detect ninja intruders.",
                        "tip": "Take the English audio guide to understand the painted Kano school screen masterpieces.",
                        "cost_usd": 9,
                        "cost_inr": 750
                    },
                    {
                        "slot": "Evening Dining & Entertainment (18:30 - 21:30)",
                        "title": "Ramen Sen-no-Kaze & Downtown Kyoto Craft Beer Tasting",
                        "category": "Nightlife",
                        "location": "Shijo Kawaramachi",
                        "description": "Rich tonkotsu broth ramen with melt-in-mouth chashu pork, followed by flights of local Japanese craft ales.",
                        "tip": "Put your name on the queue ticket machine early to avoid wait times.",
                        "cost_usd": 25,
                        "cost_inr": 2080
                    }
                ]
            }
        ]
    },
    "Amalfi Coast, Italy": {
        "vibe": "Romantic Coastal & Gourmet",
        "best_season": "Late Spring (May) & Early Autumn (September-October)",
        "weather_tag": "Sunny 23°C • Coastal Breeze",
        "highlights": ["Positano Cliffside Villages", "Ravello Villa Rufolo Gardens", "Path of the Gods Hike", "Capri Blue Grotto"],
        "base_cost_usd": 240,
        "match_score": 96,
        "why_match": "Dramatic Mediterranean cliff drops, pastel villages, scented lemon groves, and world-class fresh seafood pasta.",
        "emergency": {"police": "112", "ambulance": "118", "tourist_helpline": "+39-089-871107", "embassy": "+39-06-46741"},
        "packing": ["Linen shirts & summer dresses", "Grippy boat shoes", "High SPF mineral sunscreen", "Seasickness wristbands", "Light windbreaker"],
        "default_cluster": "Positano Coastal Cliffs & Waterfront",
        "days": [
            {
                "day": 1,
                "theme": "Vertical Marvels of Positano & Sunset Aperitivo",
                "district": "Positano Village & Spiaggia Grande",
                "transit_saved_mins": 60,
                "walking_km": 3.6,
                "activities": [
                    {
                        "slot": "Morning Sightseeing (09:00 - 12:00)",
                        "title": "Positano Cascade Stroll & Chiesa di Santa Maria Assunta",
                        "category": "Scenic",
                        "location": "Positano Center",
                        "description": "Descend winding floral stairways through pastel houses draped in purple bougainvillea to visit the Byzantine Black Madonna church.",
                        "tip": "Stop at handmade leather sandal shops to have custom gladiator sandals crafted in 15 minutes.",
                        "cost_usd": 0,
                        "cost_inr": 0
                    },
                    {
                        "slot": "Lunch Recommendation (12:30 - 14:00)",
                        "title": "Chez Black - Legendary Spaghetti alle Vongole",
                        "category": "Gastronomy",
                        "location": "Spiaggia Grande Waterfront",
                        "description": "Iconic beachside restaurant famous for heart-shaped seafood pizzas, fresh clams, and chilled Greco di Tufo white wine.",
                        "tip": "Request a beachfront table overlooking the colorful umbrellas and fishing boats.",
                        "cost_usd": 45,
                        "cost_inr": 3750
                    },
                    {
                        "slot": "Afternoon Culture & Leisure (14:30 - 17:30)",
                        "title": "Private Gozzo Wooden Boat Cruise along Sea Caves",
                        "category": "Adventure",
                        "location": "Positano Marina Pier",
                        "description": "Sail past towering sea cliffs, secluded pebble coves, and swim in the crystal turquoise waters of the Grotta dello Smeraldo.",
                        "tip": "Bring your snorkel mask for vibrant marine life around the Li Galli islands.",
                        "cost_usd": 75,
                        "cost_inr": 6260
                    },
                    {
                        "slot": "Evening Dining & Entertainment (18:30 - 21:30)",
                        "title": "Franco's Bar Cliffside Aperitivo & Limoncello Digestif",
                        "category": "Nightlife",
                        "location": "Via Cristoforo Colombo",
                        "description": "Golden hour drinks on a panoramic terrace listening to ambient lounge beats as the pastel cliffside lights flicker to life.",
                        "tip": "Arrive 30 minutes before opening at 5:00 PM for the front-row cliff edge tables.",
                        "cost_usd": 35,
                        "cost_inr": 2920
                    }
                ]
            },
            {
                "day": 2,
                "theme": "Dramatic Vistas of Ravello & Historic Amalfi Cathedral",
                "district": "Ravello Hilltop & Amalfi Town",
                "transit_saved_mins": 50,
                "walking_km": 4.0,
                "activities": [
                    {
                        "slot": "Morning Sightseeing (09:00 - 12:00)",
                        "title": "Villa Rufolo & Infinity Terrace at Villa Cimbrone",
                        "category": "Culture",
                        "location": "Ravello Mountain Summit",
                        "description": "Walk among classical marble busts poised 365 meters above the azure Gulf of Salerno on the legendary 'Terrace of Infinity'.",
                        "tip": "Villa Rufolo's gardens inspired composer Richard Wagner's opera Parsifal.",
                        "cost_usd": 16,
                        "cost_inr": 1340
                    },
                    {
                        "slot": "Lunch Recommendation (12:30 - 14:00)",
                        "title": "Trattoria Da Cumpa' Cosimo - Nonna Netta's Homemade Pasta",
                        "category": "Gastronomy",
                        "location": "Piazza Duomo, Ravello",
                        "description": "Family-run institution serving a famous tasting plate of five fresh handmade pastas with wild herbs and tomato ragù.",
                        "tip": "Ask Nonna Netta for the lemon-infused house dessert and local olive oil.",
                        "cost_usd": 38,
                        "cost_inr": 3170
                    },
                    {
                        "slot": "Afternoon Culture & Leisure (14:30 - 17:30)",
                        "title": "Duomo di Sant'Andrea & Cloister of Paradise in Amalfi",
                        "category": "Culture",
                        "location": "Piazza Duomo, Amalfi",
                        "description": "Climb the 62 steps to the 9th-century Arab-Norman cathedral with its striped marble facade and Moorish cloister.",
                        "tip": "Sample fresh lemon granita served inside giant hollowed Amalfi sfusato lemons.",
                        "cost_usd": 5,
                        "cost_inr": 420
                    },
                    {
                        "slot": "Evening Dining & Entertainment (18:30 - 21:30)",
                        "title": "Ristorante Marina Grande Waterfront Candlelit Dinner",
                        "category": "Gastronomy",
                        "location": "Amalfi Beachfront",
                        "description": "Candlelight dining on the pier listening to gentle Mediterranean waves while savoring salt-crusted sea bass.",
                        "tip": "Pair with a crisp glass of local Fiano di Avellino white wine.",
                        "cost_usd": 55,
                        "cost_inr": 4590
                    }
                ]
            }
        ]
    },
    "Jaipur & Rajasthan, India": {
        "vibe": "Royal Palaces & Desert Heritage",
        "best_season": "Winter (October to March)",
        "weather_tag": "Pleasant 22°C • Clear Sunny Days",
        "highlights": ["Amer Fort Mirror Palace", "Hawa Mahal Facade", "City Palace Royal Residence", "Nahargarh Sunset Fort"],
        "base_cost_usd": 75,
        "match_score": 99,
        "why_match": "Majestic Rajput architecture, vibrant pink sandstone city walls, opulent textiles, and royal Rajasthani thali feasts.",
        "emergency": {"police": "112", "ambulance": "108", "tourist_helpline": "1363", "embassy": "New Delhi Consulates"},
        "packing": ["Cotton breathable kurtas/shirts", "Sun hat and polarized sunglasses", "Comfortable walking sneakers", "Hand sanitizer", "Camera zoom lens"],
        "default_cluster": "Walled Pink City & Johari Bazaar",
        "days": [
            {
                "day": 1,
                "theme": "Walled Pink City, Royal Astronomical Yantras & Palaces",
                "district": "Old Pink City & Badi Chaupar",
                "transit_saved_mins": 65,
                "walking_km": 3.2,
                "activities": [
                    {
                        "slot": "Morning Sightseeing (09:00 - 12:00)",
                        "title": "Hawa Mahal (Palace of Winds) & City Palace Museum",
                        "category": "Culture",
                        "location": "Badi Chaupar, Jaipur",
                        "description": "Marvel at the 953 honeycombed jharokha stone windows designed for royal women to observe street processions, then tour the Maharaja's armory and courtyards.",
                        "tip": "Visit the Tattoo Cafe across the street for an uninterrupted morning frontal photograph.",
                        "cost_usd": 12,
                        "cost_inr": 1000
                    },
                    {
                        "slot": "Lunch Recommendation (12:30 - 14:00)",
                        "title": "LMB (Laxmi Mishthan Bhandar) Royal Rajasthani Thali",
                        "category": "Gastronomy",
                        "location": "Johari Bazaar",
                        "description": "Historic multi-course banquet featuring authentic Dal Baati Churma, Ker Sangri desert beans, Gatte ki Sabzi, and hot ghewar.",
                        "tip": "Save room for their signature Paneer Ghewar dessert soaked in saffron syrup.",
                        "cost_usd": 15,
                        "cost_inr": 1250
                    },
                    {
                        "slot": "Afternoon Culture & Leisure (14:30 - 17:30)",
                        "title": "Jantar Mantar UNESCO Observatory & Artisan Block Printing",
                        "category": "Culture",
                        "location": "Tripolia Bazaar",
                        "description": "Stand before the world's largest stone sundial measuring time to two-second accuracy, followed by a live demonstration of natural indigo block printing.",
                        "tip": "Hire a government-certified guide to explain the fascinating shadow geometry of the instruments.",
                        "cost_usd": 8,
                        "cost_inr": 670
                    },
                    {
                        "slot": "Evening Dining & Entertainment (18:30 - 21:30)",
                        "title": "Nahargarh Fort Sunset Terrace & Padao Open-Air Cafe",
                        "category": "Scenic",
                        "location": "Aravalli Hills",
                        "description": "Watch the sunset glow cast golden hues across the entire pink city expanse from the ramparts of the Tiger Fort.",
                        "tip": "Bring a light jacket as mountain breezes pick up quickly after dusk.",
                        "cost_usd": 18,
                        "cost_inr": 1500
                    }
                ]
            },
            {
                "day": 2,
                "theme": "Hilltop Forts, Mirror Palaces & Royal Stepwells",
                "district": "Amer & Maota Lake Region",
                "transit_saved_mins": 55,
                "walking_km": 4.1,
                "activities": [
                    {
                        "slot": "Morning Sightseeing (09:00 - 12:00)",
                        "title": "Amer Fort Sheesh Mahal & Panna Meena ka Kund Stepwell",
                        "category": "Culture",
                        "location": "Amer, Jaipur",
                        "description": "Explore the opulent Hall of Mirrors where a single candle illuminates the entire chamber, followed by the geometric crisscrossing steps of the ancient stepwell.",
                        "tip": "Take the pedestrian walking ramp up through the Sun Gate (Suraj Pol) for majestic lake vistas.",
                        "cost_usd": 14,
                        "cost_inr": 1170
                    },
                    {
                        "slot": "Lunch Recommendation (12:30 - 14:00)",
                        "title": "1135 AD - Royal Dining Inside the Ramparts of Amer Fort",
                        "category": "Gastronomy",
                        "location": "Amer Fort Upper Level",
                        "description": "Dine under silver leaf ceilings and crystal chandeliers savoring rich Lal Maas mutton curry and Mughlai delicacies.",
                        "tip": "Live classical sitar melodies accompany the lunchtime service.",
                        "cost_usd": 30,
                        "cost_inr": 2500
                    },
                    {
                        "slot": "Afternoon Culture & Leisure (14:30 - 17:30)",
                        "title": "Jaigarh Fort & the World's Largest Cannon on Wheels (Jaivana)",
                        "category": "History",
                        "location": "Cheel ka Teela (Hill of Eagles)",
                        "description": "Walk the military stronghold connected to Amer by secret subterranean passageways, housing the 50-ton Jaivana cannon.",
                        "tip": "Walk along the fortified battlements for the ultimate defensive panorama.",
                        "cost_usd": 5,
                        "cost_inr": 420
                    },
                    {
                        "slot": "Evening Dining & Entertainment (18:30 - 21:30)",
                        "title": "Jal Mahal Lake Promenade & Handloom Bazaar Walk",
                        "category": "Leisure",
                        "location": "Man Sagar Lake",
                        "description": "Stroll the illuminated promenade admiring the floating Water Palace, followed by shopping for blue pottery and lac bangles.",
                        "tip": "Bargaining is expected in roadside handicrafts markets—aim for 20-30% below initial quotes.",
                        "cost_usd": 15,
                        "cost_inr": 1250
                    }
                ]
            }
        ]
    },
    "Swiss Alps (Interlaken & Zermatt), Switzerland": {
        "vibe": "Alpine Mountain Adventure",
        "best_season": "Summer (June to September) & Winter (Ski season)",
        "weather_tag": "Crisp 14°C • Mountain Sun",
        "highlights": ["Jungfraujoch Top of Europe", "Matterhorn Viewpoint", "Lake Thun Paddle", "Grindelwald First Cliff Walk"],
        "base_cost_usd": 280,
        "match_score": 95,
        "why_match": "Pristine turquoise glacial lakes, cogwheel mountain trains, snow-capped peaks, and cozy cheese fondue chalets.",
        "emergency": {"police": "117", "ambulance": "144", "mountain_rescue_rega": "1414", "embassy": "+41-31-357-7011"},
        "packing": ["Waterproof hiking boots", "Thermal windbreaker", "High UV sunglasses", "Swiss Travel Pass", "Reusable water canteen"],
        "default_cluster": "Jungfrau Glacial Region & Grindelwald Valley",
        "days": [
            {
                "day": 1,
                "theme": "Top of Europe Glacier Summit & Ice Palace",
                "district": "Jungfraujoch & Lauterbrunnen Valley",
                "transit_saved_mins": 40,
                "walking_km": 3.0,
                "activities": [
                    {
                        "slot": "Morning Sightseeing (09:00 - 12:00)",
                        "title": "Eiger Express Tricable Gondola to Jungfraujoch Glacier",
                        "category": "Adventure",
                        "location": "Grindelwald Terminal to Eigergletscher",
                        "description": "Glissade through the air past the sheer Eiger North Face up to 3,454 meters to explore the perpetual ice palace tunnels.",
                        "tip": "Step onto the Sphinx Observatory viewing platform for 360-degree views of the Great Aletsch Glacier.",
                        "cost_usd": 95,
                        "cost_inr": 7930
                    },
                    {
                        "slot": "Lunch Recommendation (12:30 - 14:00)",
                        "title": "Restaurant Crystal - High Altitude Alpine Rösti",
                        "category": "Gastronomy",
                        "location": "Jungfraujoch Complex",
                        "description": "Golden pan-fried Swiss potato rösti topped with melted Gruyère cheese, fried egg, and smoked ham with glacier views.",
                        "tip": "Drink plenty of water to adjust comfortably to the high elevation.",
                        "cost_usd": 35,
                        "cost_inr": 2920
                    },
                    {
                        "slot": "Afternoon Culture & Leisure (14:30 - 17:30)",
                        "title": "Lauterbrunnen Valley of 72 Waterfalls & Staubbach Falls",
                        "category": "Nature",
                        "location": "Lauterbrunnen Valley",
                        "description": "Stroll through the fairy-tale valley that inspired Tolkien's Rivendell, watching Staubbach Falls plunge 300 meters from limestone cliffs.",
                        "tip": "Walk up the gallery trail carved right behind the cascading curtain of water.",
                        "cost_usd": 0,
                        "cost_inr": 0
                    },
                    {
                        "slot": "Evening Dining & Entertainment (18:30 - 21:30)",
                        "title": "Bebbis Restaurant Traditional Swiss Fondue & Folk Music",
                        "category": "Gastronomy",
                        "location": "Interlaken Central",
                        "description": "Communal pot of bubbling Gruyère and Vacherin cheese fondue with crusty rustic bread, kirsch schnapps, and live alphorn music.",
                        "tip": "Dip your bread cube with a figure-eight stir to keep the melted cheese silky smooth.",
                        "cost_usd": 48,
                        "cost_inr": 4000
                    }
                ]
            }
        ]
    }
}

# -----------------------------------------------------------------------------
# 5. SIDEBAR: INTUITIVE SAAS CONTROLS & AUTOMATIC API DETECTION
# -----------------------------------------------------------------------------
# Check if API Key is already fed into system environment or secrets
DETECTED_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
if not DETECTED_GEMINI_KEY:
    try:
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            DETECTED_GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
            <span style="font-size: 2.2rem;">✈️</span>
            <div>
                <h2 style="margin: 0; font-size: 1.45rem; font-weight: 800; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">WanderAI</h2>
                <span style="font-size: 0.78rem; color: #94a3b8; font-weight: 600;">Intelligent Trip Architect</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # API Engine Status & Settings
    active_api_key = DETECTED_GEMINI_KEY
    with st.expander("⚙️ AI Engine Settings", expanded=False):
        if DETECTED_GEMINI_KEY:
            st.success("🟢 Gemini 2.5 Flash Connected")
            use_custom = st.checkbox("Use a different API key", value=False)
            if use_custom:
                custom_key = st.text_input("Enter Gemini API Key", type="password")
                if custom_key:
                    active_api_key = custom_key
        else:
            custom_key = st.text_input(
                "Optional Gemini API Key",
                type="password",
                help="Optional. Leave blank to use WanderAI's built-in intelligent engine with zero setup."
            )
            if custom_key:
                active_api_key = custom_key
            st.caption("Status: Built-in Smart Engine Active")

    st.markdown("### 🧳 Trip Preferences")

    destination_input = st.selectbox(
        "Target Destination",
        options=["✨ Discover via Recommender (Tab 1)", "Kyoto, Japan", "Amalfi Coast, Italy", "Jaipur & Rajasthan, India", "Swiss Alps (Interlaken & Zermatt), Switzerland", "Custom Destination..."],
        index=1
    )

    custom_dest = ""
    if destination_input == "Custom Destination...":
        custom_dest = st.text_input("Type Destination Name", value="Barcelona, Spain")
        selected_destination = custom_dest
    elif destination_input == "✨ Discover via Recommender (Tab 1)":
        selected_destination = "Kyoto, Japan"
    else:
        selected_destination = destination_input

    col_dur, col_party = st.columns(2)
    with col_dur:
        trip_duration = st.slider("Duration (Days)", min_value=1, max_value=7, value=3)
    with col_party:
        travel_party = st.selectbox(
            "Travel Party",
            ["Solo Explorer", "Romantic Couple", "Family with Kids", "Friends Group"]
        )

    col_bud, col_pace = st.columns(2)
    with col_bud:
        budget_tier = st.selectbox(
            "Budget Tier",
            ["Budget (Value)", "Moderate (Comfort)", "Luxury (Premium)"],
            index=1
        )
    with col_pace:
        travel_pace = st.selectbox(
            "Pace",
            ["Relaxed (Leisurely)", "Moderate (Balanced)", "Fast-Paced (High Energy)"],
            index=1
        )

    interests = st.multiselect(
        "Interests & Vibes",
        ["Food & Gastronomy", "Architecture & Heritage", "Nature & Outdoors", "Scenic Photography", "Nightlife & Social", "Art & Local Markets"],
        default=["Food & Gastronomy", "Architecture & Heritage", "Scenic Photography"]
    )

    currency_pref = st.radio("Display Currency", ["USD ($)", "INR (₹)"], horizontal=True)

    st.markdown("---")
    generate_btn = st.button("🚀 Generate / Update Itinerary", type="primary", use_container_width=True)

# -----------------------------------------------------------------------------
# 6. SESSION STATE MANAGEMENT
# -----------------------------------------------------------------------------
if "current_itinerary" not in st.session_state:
    st.session_state.current_itinerary = None

if "saved_trips" not in st.session_state:
    st.session_state.saved_trips = load_trips_from_db()

# -----------------------------------------------------------------------------
# 7. AI ENGINE GENERATION LOGIC (Gemini 2.5 Flash + Intelligent Fallback)
# -----------------------------------------------------------------------------
def call_gemini_generate_itinerary(dest_name: str, duration: int, party: str, budget: str, pace: str, user_interests: List[str], api_key: str):
    """Generate itinerary dynamically using Google Gemini 2.5 Flash with structured JSON."""
    client = genai.Client(api_key=api_key)

    prompt = f"""
    Act as a master luxury travel architect and geographic transit optimization expert.
    Create a highly detailed, realistic {duration}-day travel itinerary for {dest_name}.

    Traveler Profile:
    - Travel Party: {party}
    - Budget Tier: {budget}
    - Travel Pace: {pace}
    - Core Interests: {', '.join(user_interests)}

    Key Rules:
    1. GEOGRAPHIC CLUSTERING: Each day MUST focus on a distinct neighborhood/district to eliminate transit fatigue and prevent backtracking across the city.
    2. Exactly 4 activities per day:
       - Morning Sightseeing (09:00 - 12:00)
       - Lunch Recommendation (12:30 - 14:00) [specific authentic restaurant name and dish]
       - Afternoon Culture & Leisure (14:30 - 17:30)
       - Evening Dining & Entertainment (18:30 - 21:30) [specific dinner spot and evening atmosphere]
    3. Realistic costs in USD ($) and INR (₹).

    Return ONLY a single valid JSON object with this exact structure (no markdown fences, no explanatory text):
    {{
      "title": "{duration}-Day Curated Journey in {dest_name}",
      "cluster_name": "Primary Historic & Cultural Core",
      "emergency": {{"police": "112", "ambulance": "112", "tourist_helpline": "Local Helpline", "embassy": "Diplomatic Consulate"}},
      "packing": ["item 1", "item 2", "item 3", "item 4", "item 5"],
      "days": [
        {{
          "day": 1,
          "theme": "Day theme description",
          "district": "Specific District / Neighborhood Name",
          "transit_saved_mins": 50,
          "walking_km": 3.5,
          "activities": [
            {{
              "slot": "Morning Sightseeing (09:00 - 12:00)",
              "title": "Specific Attraction Name",
              "category": "Culture",
              "location": "Exact Area or Landmark",
              "description": "Engaging 2-sentence description of the experience.",
              "tip": "Insider pro-tip for traveler.",
              "cost_usd": 15,
              "cost_inr": 1250
            }},
            {{
              "slot": "Lunch Recommendation (12:30 - 14:00)",
              "title": "Restaurant Name & Signature Dish",
              "category": "Gastronomy",
              "location": "Neighborhood",
              "description": "Description of cuisine and specialty.",
              "tip": "Dining tip (reservations, seating).",
              "cost_usd": 25,
              "cost_inr": 2080
            }},
            {{
              "slot": "Afternoon Culture & Leisure (14:30 - 17:30)",
              "title": "Afternoon Experience Name",
              "category": "Scenic",
              "location": "Neighborhood",
              "description": "Description of visit.",
              "tip": "Insider advice.",
              "cost_usd": 12,
              "cost_inr": 1000
            }},
            {{
              "slot": "Evening Dining & Entertainment (18:30 - 21:30)",
              "title": "Dinner & Evening Venue",
              "category": "Nightlife",
              "location": "Neighborhood",
              "description": "Atmosphere and culinary highlights.",
              "tip": "Evening recommendation.",
              "cost_usd": 40,
              "cost_inr": 3340
            }}
          ]
        }}
      ]
    }}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    raw_text = response.text.strip()
    # Strip optional markdown codeblock syntax
    clean_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    clean_text = re.sub(r"\s*```$", "", clean_text).strip()

    data = json.loads(clean_text)

    # Compute financial metrics
    act_cost_usd = sum(sum(a.get("cost_usd", 15) for a in d.get("activities", [])) for d in data.get("days", []))
    base_stay = duration * (180 if "Moderate" in budget else (85 if "Budget" in budget else 380))
    total_usd = round(act_cost_usd + base_stay)
    total_inr = round(total_usd * USD_TO_INR)

    return {
        "id": f"trip_gemini_{datetime.datetime.now().strftime('%Y%m%d%H%M')}",
        "title": data.get("title", f"{duration}-Day Itinerary for {dest_name}"),
        "destination": dest_name,
        "duration": duration,
        "budget_tier": budget,
        "travel_party": party,
        "pace": pace,
        "interests": user_interests,
        "total_cost_usd": total_usd,
        "total_cost_inr": total_inr,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "cluster_name": data.get("cluster_name", f"{dest_name} Central District"),
        "emergency": data.get("emergency", {"police": "112", "ambulance": "112", "tourist_helpline": "Dial local 011", "embassy": "Consulate"}),
        "packing": data.get("packing", ["Comfortable walking shoes", "Light jacket", "Passport & IDs", "Power bank"]),
        "days": data.get("days", [])
    }

def generate_itinerary_fallback(dest_name: str, duration: int, party: str, budget: str, pace: str, user_interests: List[str]):
    """Offline high-fidelity generator when Gemini API is offline or not configured."""
    if dest_name in CURATED_DESTINATIONS:
        curated = CURATED_DESTINATIONS[dest_name]
        days_slice = curated["days"][:duration]
        while len(days_slice) < duration:
            extra_day_idx = len(days_slice) + 1
            days_slice.append({
                "day": extra_day_idx,
                "theme": f"Hidden Gems & Local Culinary Immersion (Day {extra_day_idx})",
                "district": f"{dest_name} Heritage Outskirts",
                "transit_saved_mins": 45,
                "walking_km": 3.4,
                "activities": [
                    {
                        "slot": "Morning Sightseeing (09:00 - 12:00)",
                        "title": f"Scenic Mountain Vista & Hidden Artisan Workshops",
                        "category": "Culture",
                        "location": f"{dest_name} Countryside",
                        "description": f"Escape the bustling central corridor to visit multi-generational ceramic and woodblock print workshops.",
                        "tip": "Pick up handcrafted souvenirs directly from local master artisans.",
                        "cost_usd": 15,
                        "cost_inr": 1250
                    },
                    {
                        "slot": "Lunch Recommendation (12:30 - 14:00)",
                        "title": f"Farm-to-Table Seasonal Tasting Cafe",
                        "category": "Gastronomy",
                        "location": "Local Valley Center",
                        "description": "Organic local produce, freshly pressed herbal juices, and wood-fired flatbreads.",
                        "tip": "Ask for the daily chef seasonal special.",
                        "cost_usd": 25,
                        "cost_inr": 2080
                    },
                    {
                        "slot": "Afternoon Culture & Leisure (14:30 - 17:30)",
                        "title": f"Botanical Garden & Historic Tea Sanctuary",
                        "category": "Nature",
                        "location": f"Botanical Sanctuary, {dest_name}",
                        "description": "Serene trails lined with native florals, tranquil ponds, and shaded reading pavilions.",
                        "tip": "Ideal spot for afternoon meditation or journaling.",
                        "cost_usd": 10,
                        "cost_inr": 830
                    },
                    {
                        "slot": "Evening Dining & Entertainment (18:30 - 21:30)",
                        "title": f"Rooftop Sunset Lounge & Local Gastronomy",
                        "category": "Nightlife",
                        "location": "Skyline Promenade",
                        "description": "Panoramic night views paired with regional tasting flights and signature mocktails/cocktails.",
                        "tip": "Reserve ahead for corner sunset seating.",
                        "cost_usd": 40,
                        "cost_inr": 3340
                    }
                ]
            })

        cost_multiplier = 0.7 if "Budget" in budget else (1.0 if "Moderate" in budget else 1.8)
        act_cost_usd = sum(sum(a["cost_usd"] for a in d["activities"]) for d in days_slice)
        base_stay = curated["base_cost_usd"] * duration * cost_multiplier
        total_usd = round(act_cost_usd + base_stay)
        total_inr = round(total_usd * USD_TO_INR)

        return {
            "id": f"trip_{dest_name[:4].lower()}_{datetime.datetime.now().strftime('%Y%m%d%H%M')}",
            "title": f"{duration}-Day {budget.split()[0]} Itinerary for {dest_name}",
            "destination": dest_name,
            "duration": duration,
            "budget_tier": budget,
            "travel_party": party,
            "pace": pace,
            "interests": user_interests,
            "total_cost_usd": total_usd,
            "total_cost_inr": total_inr,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "cluster_name": curated["default_cluster"],
            "emergency": curated["emergency"],
            "packing": curated["packing"],
            "days": days_slice
        }
    else:
        days = []
        for i in range(1, duration + 1):
            days.append({
                "day": i,
                "theme": f"Exploring Historic & Cultural Highlights of {dest_name} (Day {i})",
                "district": f"{dest_name} Historic Central District",
                "transit_saved_mins": 45,
                "walking_km": 3.8,
                "activities": [
                    {
                        "slot": "Morning Sightseeing (09:00 - 12:00)",
                        "title": f"Iconic Landmarks & Architectural Walking Tour",
                        "category": "Culture",
                        "location": f"Central Square, {dest_name}",
                        "description": f"Guided orientation of major historic monuments, cathedrals, and city plazas.",
                        "tip": "Purchase fast-track tickets online in advance to bypass long queues.",
                        "cost_usd": 20,
                        "cost_inr": 1670
                    },
                    {
                        "slot": "Lunch Recommendation (12:30 - 14:00)",
                        "title": f"Bustling Local Food Market & Delicacies",
                        "category": "Gastronomy",
                        "location": f"Old Town Market, {dest_name}",
                        "description": "Authentic regional street delicacies, fresh fruits, and artisan bakery treats.",
                        "tip": "Look for stalls with long lines of local residents.",
                        "cost_usd": 22,
                        "cost_inr": 1840
                    },
                    {
                        "slot": "Afternoon Culture & Leisure (14:30 - 17:30)",
                        "title": f"Fine Arts Museum & Waterfront Gardens",
                        "category": "Scenic",
                        "location": f"Art District, {dest_name}",
                        "description": "World-class art collections, sculptures, and tranquil botanical gardens.",
                        "tip": "Enjoy the outdoor courtyard cafe for espresso and pastries.",
                        "cost_usd": 15,
                        "cost_inr": 1250
                    },
                    {
                        "slot": "Evening Dining & Entertainment (18:30 - 21:30)",
                        "title": f"Traditional Dinner & Historic Old Town Stroll",
                        "category": "Nightlife",
                        "location": f"Riverfront / Old Quarter, {dest_name}",
                        "description": "Dinner at a beloved neighborhood bistro followed by illuminated evening walk.",
                        "tip": "Try the signature local dessert and regional wine/cider.",
                        "cost_usd": 40,
                        "cost_inr": 3340
                    }
                ]
            })

        total_usd = duration * (180 if "Moderate" in budget else (90 if "Budget" in budget else 350))
        total_inr = round(total_usd * USD_TO_INR)

        return {
            "id": f"trip_custom_{datetime.datetime.now().strftime('%Y%m%d%H%M')}",
            "title": f"{duration}-Day Curated Journey in {dest_name}",
            "destination": dest_name,
            "duration": duration,
            "budget_tier": budget,
            "travel_party": party,
            "pace": pace,
            "interests": user_interests,
            "total_cost_usd": total_usd,
            "total_cost_inr": total_inr,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "cluster_name": f"{dest_name} Heritage Core",
            "emergency": {"police": "112 / 911", "ambulance": "112 / 911", "tourist_helpline": "Dial local 011", "embassy": "Capital Consulate"},
            "packing": ["Universal Travel Adapter", "Comfortable walking shoes", "Light rain jacket", "Local currency cash", "Power bank"],
            "days": days
        }

def get_itinerary(dest_name: str, duration: int, party: str, budget: str, pace: str, user_interests: List[str], api_key: str):
    """Wrapper that tries Gemini first if key available, then gracefully falls back."""
    if api_key and HAS_GENAI:
        try:
            return call_gemini_generate_itinerary(dest_name, duration, party, budget, pace, user_interests, api_key)
        except Exception as e:
            st.warning(f"Note: Gemini Live API returned a notice ({e}). Seamlessly using intelligent fallback engine.")
            return generate_itinerary_fallback(dest_name, duration, party, budget, pace, user_interests)
    else:
        return generate_itinerary_fallback(dest_name, duration, party, budget, pace, user_interests)

# Pre-load initial default trip if empty
if st.session_state.current_itinerary is None:
    st.session_state.current_itinerary = generate_itinerary_fallback(
        "Kyoto, Japan", 3, "Romantic Couple", "Moderate (Comfort)", "Moderate (Balanced)",
        ["Food & Gastronomy", "Architecture & Heritage", "Scenic Photography"]
    )

if generate_btn:
    with st.spinner(f"Generating personalized {trip_duration}-day itinerary for {selected_destination}..."):
        new_trip = get_itinerary(
            selected_destination, trip_duration, travel_party, budget_tier, travel_pace, interests, active_api_key
        )
        st.session_state.current_itinerary = new_trip
        save_trip_to_db(new_trip)
        st.session_state.saved_trips = load_trips_from_db()
        st.toast(f"Generated new itinerary for {selected_destination}!", icon="✈️")
        st.rerun()

# -----------------------------------------------------------------------------
# 8. REPORTLAB PROFESSIONAL PDF TRAVEL GUIDE
# -----------------------------------------------------------------------------
def generate_itinerary_pdf(trip: Dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#0f172a'),
        alignment=0
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#475569')
    )

    heading2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0284c7'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )

    bold_body_style = ParagraphStyle(
        'BoldBodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#0f172a')
    )

    story = []

    # Title & Metadata Banner
    story.append(Paragraph(f"✈️ {trip['title']}", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"<b>Destination:</b> {trip['destination']} &nbsp;|&nbsp; "
        f"<b>Duration:</b> {trip['duration']} Days &nbsp;|&nbsp; "
        f"<b>Travel Party:</b> {trip['travel_party']} &nbsp;|&nbsp; "
        f"<b>Budget Tier:</b> {trip['budget_tier']}",
        subtitle_style
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"<b>Trip Reference:</b> WNDR-{trip['id'][-8:].upper()} &nbsp;|&nbsp; "
        f"Generated: {trip['created_at']} &nbsp;|&nbsp; Certified Offline Travel Guide",
        ParagraphStyle('ProofStyle', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#64748b'))
    ))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284c7'), spaceAfter=14))

    # Executive Summary Table
    story.append(Paragraph("1. Trip & Financial Summary", heading2_style))
    summary_data = [
        ["Parameter", "Details", "Financial Metric", "Value"],
        ["Target Destination", trip["destination"], "Total Budget (USD)", f"${trip['total_cost_usd']:,}"],
        ["Trip Duration", f"{trip['duration']} Days", "Total Budget (INR)", f"₹{trip['total_cost_inr']:,}"],
        ["Travel Party", trip["travel_party"], "Average Daily Spend", f"${round(trip['total_cost_usd']/trip['duration'])} (₹{round(trip['total_cost_inr']/trip['duration']):,})"],
        ["Geographic Cluster", trip.get("cluster_name", "Central District"), "Transit Optimization", "Grouped by neighborhood"]
    ]
    summary_table = Table(summary_data, colWidths=[1.8*inch, 2.2*inch, 1.8*inch, 1.4*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    # Day by Day Itinerary
    story.append(Paragraph("2. Optimized Day-by-Day Schedule", heading2_style))

    for day in trip["days"]:
        day_header = [
            [f"DAY {day['day']}: {day['theme']}"],
            [f"📍 Cluster: {day['district']} | ⚡ Transit Saved: ~{day['transit_saved_mins']} mins | 🚶 Walking: {day['walking_km']} km"]
        ]
        dh_table = Table(day_header, colWidths=[7.2*inch])
        dh_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0284c7')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e0f2fe')),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#0369a1')),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Oblique'),
            ('FONTSIZE', (0, 1), (-1, 1), 8.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(dh_table)

        act_rows = [["Time Slot", "Activity & Location", "Insider Advice & Tip", "Est. Cost"]]
        for act in day["activities"]:
            act_rows.append([
                Paragraph(f"<b>{act['slot']}</b>", bold_body_style),
                Paragraph(f"<b>{act['title']}</b><br/><font color='#64748b'>{act['location']}</font><br/>{act['description']}", body_style),
                Paragraph(f"💡 <i>{act['tip']}</i>", body_style),
                Paragraph(f"<b>${act['cost_usd']}</b><br/><font color='#059669'>₹{act['cost_inr']:,}</font>", bold_body_style)
            ])

        act_table = Table(act_rows, colWidths=[1.5*inch, 2.7*inch, 2.1*inch, 0.9*inch])
        act_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8.5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(act_table)
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 6))
    story.append(Paragraph("3. Emergency Protocol & Packing Guide", heading2_style))
    
    em = trip.get("emergency", {"police": "112", "ambulance": "112", "tourist_helpline": "1363", "embassy": "Consulate"})
    packing_items = ", ".join(trip.get("packing", ["Passport", "Charger", "Walking Shoes"]))

    em_data = [
        ["Police Hotline", em.get("police", "112"), "Tourist Assistance", em.get("tourist_helpline", "Local Helpline")],
        ["Medical Emergency", em.get("ambulance", "112"), "Diplomatic Embassy", em.get("embassy", "Consular Office")],
        ["Smart Packing Kit", packing_items, "", ""]
    ]
    em_table = Table(em_data, colWidths=[1.8*inch, 2.0*inch, 1.8*inch, 1.6*inch])
    em_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('SPAN', (1, 2), (3, 2)),
    ]))
    story.append(em_table)

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Curated with WanderAI — Intelligent Travel Companion & Itinerary Architect. Have a safe and memorable journey!",
        ParagraphStyle('FooterNotice', fontName='Helvetica-Oblique', fontSize=8, textColor=colors.HexColor('#64748b'), alignment=1)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# -----------------------------------------------------------------------------
# 9. MAIN INTERFACE & TABS (Clean 4 Core Tabs)
# -----------------------------------------------------------------------------
st.markdown("""
<div style="background: linear-gradient(135deg, rgba(14, 165, 233, 0.15) 0%, rgba(99, 102, 241, 0.15) 100%); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 16px; padding: 24px 30px; margin-bottom: 24px;">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
        <div>
            <h1 style="margin: 0; font-size: 2.2rem; font-weight: 800; color: #f8fafc; letter-spacing: -0.02em;">
                Personalized Travel Itinerary Planner
            </h1>
            <p style="margin: 6px 0 0 0; color: #94a3b8; font-size: 1.02rem;">
                Intelligent vacation curation with <b>Geographic Clustering</b>, dynamic activity swapping, budget forecasting & offline PDF export.
            </p>
        </div>
        <div style="text-align: right;">
            <span class="pill pill-blue">✨ Gemini 2.5 Active</span>
            <span class="pill pill-purple">⚡ Transit Clustered</span>
            <span class="pill pill-emerald">📄 Offline PDF Ready</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Clean 4-Tab Navigation
tab1, tab2, tab3, tab4 = st.tabs([
    "🧭 Explore & Recommend",
    "📅 Day-by-Day Itinerary",
    "⚡ Dynamic Vibe & Activity Swap",
    "💾 My Trips & Offline Travel Guide"
])

# =============================================================================
# TAB 1: EXPLORE & RECOMMEND
# =============================================================================
with tab1:
    st.markdown("### 🧭 Discover Curated Destinations")
    st.markdown("Find vacation destinations mathematically matched to your travel party, budget tier, and preferred vibe.")

    col_filter1, col_filter2 = st.columns([3, 1])
    with col_filter1:
        st.markdown(f"**Current Criteria:** Budget: `{budget_tier}` &nbsp;|&nbsp; Party: `{travel_party}` &nbsp;|&nbsp; Pace: `{travel_pace}` &nbsp;|&nbsp; Vibes: `{', '.join(interests)}`")
    with col_filter2:
        if st.button("🔄 Refresh Recommendations", use_container_width=True):
            st.toast("Refreshed matching destinations!", icon="✨")

    st.markdown("#### Top Curated Destinations for You:")

    rec_cols = st.columns(3)
    dest_keys = list(CURATED_DESTINATIONS.keys())[:3]

    for idx, d_name in enumerate(dest_keys):
        dest_info = CURATED_DESTINATIONS[d_name]
        with rec_cols[idx]:
            st.markdown(f"""
            <div class="metric-card" style="height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span class="pill pill-emerald">{dest_info['match_score']}% Match</span>
                    <span style="font-size: 0.8rem; color: #94a3b8;">{dest_info['vibe']}</span>
                </div>
                <h3 style="margin: 0 0 8px 0; font-size: 1.35rem; color: #f8fafc;">{d_name}</h3>
                <div style="font-size: 0.85rem; color: #38bdf8; font-weight: 600; margin-bottom: 6px;">
                    🌤️ {dest_info['weather_tag']}
                </div>
                <div style="font-size: 0.85rem; color: #cbd5e1; margin-bottom: 12px; line-height: 1.4;">
                    {dest_info['why_match']}
                </div>
                <div style="margin-bottom: 14px;">
                    <span style="font-size: 0.78rem; color: #94a3b8; font-weight: 600; text-transform: uppercase;">Top Highlights:</span><br>
                    {' '.join([f"<span class='pill pill-blue' style='margin-top: 4px;'>{h}</span>" for h in dest_info['highlights'][:3]])}
                </div>
                <div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 10px; margin-top: 10px;">
                    <div style="font-size: 0.85rem; color: #94a3b8;">Estimated Daily Spend:</div>
                    <div style="font-size: 1.25rem; font-weight: 700; color: #f1f5f9;">
                        ${dest_info['base_cost_usd']} <span style="font-size: 0.85rem; color: #34d399; font-weight: 500;">(₹{round(dest_info['base_cost_usd']*USD_TO_INR):,})</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"🚀 Plan Trip to {d_name.split(',')[0]}", key=f"btn_sel_{idx}", use_container_width=True):
                with st.spinner(f"Generating personalized {trip_duration}-day itinerary..."):
                    new_trip = get_itinerary(
                        d_name, trip_duration, travel_party, budget_tier, travel_pace, interests, active_api_key
                    )
                    st.session_state.current_itinerary = new_trip
                    save_trip_to_db(new_trip)
                    st.session_state.saved_trips = load_trips_from_db()
                    st.success(f"Selected {d_name}! Switch to the 'Day-by-Day Itinerary' tab to explore your schedule.")

# =============================================================================
# TAB 2: DAY-BY-DAY ITINERARY
# =============================================================================
with tab2:
    current_trip = st.session_state.current_itinerary

    if current_trip is None:
        st.info("Loading itinerary...")
        current_trip = get_itinerary(selected_destination, trip_duration, travel_party, budget_tier, travel_pace, interests, active_api_key)
        st.session_state.current_itinerary = current_trip

    # Top KPI Metrics Row
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Destination</div>
            <div class="metric-value" style="font-size: 1.35rem;">{current_trip['destination'].split(',')[0]}</div>
            <div class="metric-subtitle">{current_trip['duration']} Days • {current_trip['travel_party']}</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi2:
        val_display = f"${current_trip['total_cost_usd']:,}" if currency_pref == "USD ($)" else f"₹{current_trip['total_cost_inr']:,}"
        sub_display = f"₹{current_trip['total_cost_inr']:,}" if currency_pref == "USD ($)" else f"${current_trip['total_cost_usd']:,}"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Estimated Budget</div>
            <div class="metric-value">{val_display}</div>
            <div class="metric-subtitle">{sub_display} • {current_trip['budget_tier']}</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi3:
        total_transit_saved = sum(d.get("transit_saved_mins", 45) for d in current_trip["days"])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Transit Time Saved</div>
            <div class="metric-value">~{total_transit_saved} Mins</div>
            <div class="metric-subtitle">Via Geographic Clustering</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi4:
        total_walking = sum(d.get("walking_km", 3.5) for d in current_trip["days"])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Active Walking</div>
            <div class="metric-value">{round(total_walking, 1)} km</div>
            <div class="metric-subtitle">Pedestrian Route Optimized</div>
        </div>
        """, unsafe_allow_html=True)

    # Geographic Clustering Banner
    st.markdown(f"""
    <div class="cluster-banner">
        <div>
            <span style="font-size: 1.05rem; font-weight: 700; color: #38bdf8;">📍 Geographic Clustering Active</span>
            <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 2px;">
                Activities are clustered by urban district to prevent zigzagging across the city and reduce transit fatigue.
            </div>
        </div>
        <div>
            <span class="pill pill-emerald">Optimized Route</span>
            <span class="pill pill-blue">Zero Backtracking</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_btn_gen, col_btn_save = st.columns([3, 1])
    with col_btn_gen:
        if st.button("✨ Regenerate Full Itinerary with Current Preferences", use_container_width=True):
            with st.spinner("AI is generating optimized district routes and schedules..."):
                new_trip = get_itinerary(selected_destination, trip_duration, travel_party, budget_tier, travel_pace, interests, active_api_key)
                st.session_state.current_itinerary = new_trip
                save_trip_to_db(new_trip)
                st.session_state.saved_trips = load_trips_from_db()
                st.rerun()
    with col_btn_save:
        if st.button("💾 Save Trip", use_container_width=True):
            save_trip_to_db(st.session_state.current_itinerary)
            st.session_state.saved_trips = load_trips_from_db()
            st.success("Trip saved successfully to your portfolio!")

    # Day-wise Timeline Render
    st.markdown("### 🗺️ Day-by-Day Schedule")

    for day in current_trip["days"]:
        with st.expander(f"📍 Day {day['day']}: {day['theme']} (Cluster: {day['district']})", expanded=(day['day'] == 1)):
            st.markdown(f"""
                <div style="display: flex; gap: 12px; margin-bottom: 12px;">
                    <span class="pill pill-blue">District: {day['district']}</span>
                    <span class="pill pill-emerald">⚡ Transit Saved: ~{day.get('transit_saved_mins', 45)} mins</span>
                    <span class="pill pill-purple">🚶 Walking: {day.get('walking_km', 3.5)} km</span>
                </div>
            """, unsafe_allow_html=True)

            for act in day["activities"]:
                cost_str = f"${act['cost_usd']} (₹{act['cost_inr']:,})" if currency_pref == "USD ($)" else f"₹{act['cost_inr']:,} (${act['cost_usd']})"
                st.markdown(f"""
                <div class="slot-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="slot-time">{act['slot']}</span>
                        <span class="pill pill-amber">{act['category']}</span>
                    </div>
                    <div class="slot-title">{act['title']}</div>
                    <div class="slot-desc">{act['description']}</div>
                    <div class="slot-meta">
                        <span>📍 <b>Location:</b> {act['location']}</span>
                        <span>💡 <b>Tip:</b> {act['tip']}</span>
                        <span>💰 <b>Est. Cost:</b> <span style="color: #34d399; font-weight: 700;">{cost_str}</span></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # Budget Analytics Chart
    st.markdown("---")
    st.markdown("### 📊 Budget & Expense Breakdown")

    col_chart1, col_chart2 = st.columns([3, 2])

    with col_chart1:
        day_names = [f"Day {d['day']}" for d in current_trip["days"]]
        day_costs = [sum(a["cost_usd"] for a in d["activities"]) for d in current_trip["days"]]
        cum_costs = [sum(day_costs[:i+1]) for i in range(len(day_costs))]

        fig_cum = go.Figure()
        fig_cum.add_trace(go.Scatter(
            x=day_names,
            y=cum_costs,
            mode='lines+markers+text',
            name='Cumulative Spend (USD)',
            line=dict(color='#38bdf8', width=3),
            marker=dict(size=8, color='#818cf8'),
            text=[f"${c}" for c in cum_costs],
            textposition="top left"
        ))
        fig_cum.update_layout(
            title="Cumulative Itinerary Spending ($ USD)",
            template="plotly_dark",
            paper_bgcolor="rgba(15, 23, 42, 0.4)",
            plot_bgcolor="rgba(15, 23, 42, 0.4)",
            font=dict(family="Plus Jakarta Sans", color="#94a3b8"),
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_cum, use_container_width=True)

    with col_chart2:
        categories = ["Accommodation", "Dining & Food", "Activities & Entry", "Local Transit & Buffer"]
        pcts = [45, 25, 20, 10]
        fig_pie = px.pie(
            values=pcts,
            names=categories,
            hole=0.55,
            color_discrete_sequence=['#38bdf8', '#818cf8', '#c084fc', '#34d399'],
            title="Budget Allocation Ratio"
        )
        fig_pie.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(15, 23, 42, 0.4)",
            font=dict(family="Plus Jakarta Sans", color="#94a3b8"),
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_pie, use_container_width=True)

# =============================================================================
# TAB 3: DYNAMIC VIBE & ACTIVITY SWAP
# =============================================================================
with tab3:
    st.markdown("### ⚡ Dynamic Vibe & Activity Swap")
    st.markdown("Customize your trip in real time! Swap individual slots with curated vibe alternatives or custom instructions **without affecting the rest of your multi-day schedule**.")

    cur_trip = st.session_state.current_itinerary

    col_target1, col_target2 = st.columns(2)
    with col_target1:
        swap_day_num = st.selectbox(
            "Select Day to Modify",
            options=[d["day"] for d in cur_trip["days"]],
            format_func=lambda x: f"Day {x}: {cur_trip['days'][x-1]['theme'][:40]}..."
        )
    with col_target2:
        target_day_data = cur_trip["days"][swap_day_num - 1]
        swap_slot_idx = st.selectbox(
            "Select Time Slot to Swap",
            options=list(range(len(target_day_data["activities"]))),
            format_func=lambda x: f"{target_day_data['activities'][x]['slot']}: {target_day_data['activities'][x]['title'][:35]}..."
        )

    current_slot = target_day_data["activities"][swap_slot_idx]

    st.markdown(f"""
    <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px; margin: 12px 0;">
        <span style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Currently Scheduled Activity:</span>
        <h4 style="margin: 4px 0; color: #f8fafc;">{current_slot['title']}</h4>
        <p style="margin: 0; font-size: 0.88rem; color: #cbd5e1;">{current_slot['description']}</p>
        <span style="font-size: 0.8rem; color: #38bdf8; font-weight: 600;">Location: {current_slot['location']} • Est. Cost: ${current_slot['cost_usd']} (₹{current_slot['cost_inr']:,})</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### Choose Replacement:")
    swap_mode = st.radio(
        "Replacement Method",
        ["Curated Vibe Presets (1-Click Swap)", "Custom Prompt Instruction (Gemini Powered)"],
        horizontal=True
    )

    if swap_mode == "Curated Vibe Presets (1-Click Swap)":
        preset_choice = st.selectbox(
            "Select Desired Vibe",
            [
                "🍜 Bustling Street Food Bazaar & Night Market",
                "🧘 Peaceful Zen Garden & Traditional Tea House",
                "🧗 High-Adrenaline Outdoor Adventure & Viewpoint Hike",
                "🎨 Hidden Artisan Workshops & Modern Art Gallery",
                "☕ Cozy Local Roastery & Indie Bookstore Cafe",
                "👶 Family & Kid-Friendly Interactive Science / Wildlife Experience"
            ]
        )
    else:
        custom_swap_prompt = st.text_input(
            "Custom Swap Prompt",
            placeholder="e.g., Replace this slot with a relaxing sunset rooftop jazz lounge and vegetarian tapas"
        )

    if st.button("⚡ Apply Dynamic Slot Swap", type="primary", use_container_width=True):
        new_act = None
        # Try custom Gemini swap if prompt is provided and API key exists
        if swap_mode != "Curated Vibe Presets (1-Click Swap)" and custom_swap_prompt and active_api_key and HAS_GENAI:
            try:
                client = genai.Client(api_key=active_api_key)
                swap_prompt = f"""
                You are a travel itinerary planner. Replace the following activity:
                Current slot: {current_slot['slot']}
                City: {cur_trip['destination']}
                District: {target_day_data['district']}
                User Instruction: {custom_swap_prompt}

                Return ONLY a JSON object:
                {{
                  "title": "Specific New Activity Name",
                  "category": "Custom",
                  "location": "{target_day_data['district']} Local Spot",
                  "description": "2-sentence compelling description of the replacement activity.",
                  "tip": "Practical insider tip.",
                  "cost_usd": 25,
                  "cost_inr": 2080
                }}
                """
                resp = client.models.generate_content(model="gemini-2.5-flash", contents=swap_prompt)
                clean_json = re.sub(r"^```(?:json)?\s*", "", resp.text.strip())
                clean_json = re.sub(r"\s*```$", "", clean_json).strip()
                parsed = json.loads(clean_json)
                new_act = {
                    "slot": current_slot["slot"],
                    "title": parsed.get("title", f"Custom: {custom_swap_prompt[:30]}"),
                    "category": parsed.get("category", "Custom"),
                    "location": parsed.get("location", f"{target_day_data['district']} Area"),
                    "description": parsed.get("description", custom_swap_prompt),
                    "tip": parsed.get("tip", "Ask locals for secret seating."),
                    "cost_usd": parsed.get("cost_usd", 25),
                    "cost_inr": parsed.get("cost_inr", 2080)
                }
            except Exception:
                pass

        if new_act is None:
            if swap_mode == "Curated Vibe Presets (1-Click Swap)":
                if "Street Food" in preset_choice:
                    new_act = {
                        "slot": current_slot["slot"],
                        "title": "Bustling Local Street Food Bazaar & Night Market",
                        "category": "Gastronomy",
                        "location": f"{target_day_data['district']} Night Market",
                        "description": "Indulge in authentic regional delicacies, sizzling street skewers, and artisanal sweet pastries amidst lively lantern stalls.",
                        "tip": "Bring local cash for smaller street vendors.",
                        "cost_usd": 18,
                        "cost_inr": 1500
                    }
                elif "Zen Garden" in preset_choice:
                    new_act = {
                        "slot": current_slot["slot"],
                        "title": "Tranquil Zen Meditation Garden & Matcha Whisking",
                        "category": "Culture",
                        "location": f"{target_day_data['district']} Heritage Cloister",
                        "description": "Quiet contemplative stroll along moss-draped courtyards followed by ceremonial tea whisking led by a resident master.",
                        "tip": "Turn off mobile phones to fully immerse in the meditative acoustics.",
                        "cost_usd": 14,
                        "cost_inr": 1170
                    }
                elif "Outdoor Adventure" in preset_choice:
                    new_act = {
                        "slot": current_slot["slot"],
                        "title": "Panoramic Ridge Trail & Cliffside Lookout Point",
                        "category": "Adventure",
                        "location": f"{target_day_data['district']} Mountain Foot",
                        "description": "Invigorating scenic trek along elevated natural trails offering panoramic aerial views over the entire valley and coastline.",
                        "tip": "Wear sturdy trail footwear and carry water.",
                        "cost_usd": 0,
                        "cost_inr": 0
                    }
                elif "Artisan" in preset_choice:
                    new_act = {
                        "slot": current_slot["slot"],
                        "title": "Independent Artisan Craft Guild & Gallery Walk",
                        "category": "Culture",
                        "location": f"{target_day_data['district']} Artisan Quarter",
                        "description": "Tour authentic workshops observing master glassblowers, ceramicists, and textile weavers at work.",
                        "tip": "Items purchased here come with authentic certified master seals.",
                        "cost_usd": 20,
                        "cost_inr": 1670
                    }
                elif "Cozy" in preset_choice:
                    new_act = {
                        "slot": current_slot["slot"],
                        "title": "Specialty Single-Origin Coffee Roastery & Book Sanctuary",
                        "category": "Leisure",
                        "location": f"{target_day_data['district']} Bohemian Lane",
                        "description": "Relax with pour-over Ethiopian coffees, homemade cardamom buns, and a curated library of regional art books.",
                        "tip": "Try their cold brew cascara infusion.",
                        "cost_usd": 12,
                        "cost_inr": 1000
                    }
                else:
                    new_act = {
                        "slot": current_slot["slot"],
                        "title": "Interactive Wildlife & Hands-On Science Pavilion",
                        "category": "Leisure",
                        "location": f"{target_day_data['district']} Waterfront Park",
                        "description": "Engaging discovery displays, botanical petting greenhouse, and child-friendly science experiments.",
                        "tip": "Great for families with young children.",
                        "cost_usd": 16,
                        "cost_inr": 1340
                    }
            else:
                new_act = {
                    "slot": current_slot["slot"],
                    "title": f"Custom: {custom_swap_prompt[:40]}",
                    "category": "Custom",
                    "location": f"{target_day_data['district']} Local Spot",
                    "description": f"Tailored activity honoring request: '{custom_swap_prompt}'. Personalized route avoiding tourist congestion.",
                    "tip": "Ask local staff for hidden recommendations on the day.",
                    "cost_usd": 25,
                    "cost_inr": 2080
                }

        cur_trip["days"][swap_day_num - 1]["activities"][swap_slot_idx] = new_act

        # Recalculate totals
        act_cost_usd = sum(sum(a["cost_usd"] for a in d["activities"]) for d in cur_trip["days"])
        cur_trip["total_cost_usd"] = act_cost_usd + (120 * cur_trip["duration"])
        cur_trip["total_cost_inr"] = round(cur_trip["total_cost_usd"] * USD_TO_INR)

        st.session_state.current_itinerary = cur_trip
        save_trip_to_db(cur_trip)
        st.session_state.saved_trips = load_trips_from_db()
        st.toast(f"Successfully swapped '{new_act['title']}' into Day {swap_day_num}!", icon="⚡")
        st.rerun()

# =============================================================================
# TAB 4: MY TRIPS & OFFLINE TRAVEL GUIDE (PDF EXPORT)
# =============================================================================
with tab4:
    st.markdown("### 💾 Saved Trips & Offline Travel Guide")
    st.markdown("Manage your trip portfolio and export a clean, beautifully formatted **offline PDF travel guide**.")

    col_pdf1, col_pdf2 = st.columns([3, 2])

    with col_pdf1:
        st.markdown("#### 📄 1-Click Offline PDF Travel Guide")
        st.markdown("""
        Download an offline travel guide ready for your phone or printing:
        - Executive Trip Summary & Multi-Currency Breakdown (USD & INR)
        - Day-by-Day Schedule with Time Slots, Districts, and Cost Estimates
        - Emergency Hotlines (Police, Medical, Tourist Helpline, Embassies)
        - Curated Destination Packing & Weather Essentials
        """)

        active_trip = st.session_state.current_itinerary
        if active_trip:
            pdf_bytes = generate_itinerary_pdf(active_trip)
            file_name = f"WanderAI_{active_trip['destination'].split(',')[0].replace(' ', '_')}_{active_trip['duration']}Days.pdf"
            
            st.download_button(
                label=f"📥 Download Travel Guide PDF ({round(len(pdf_bytes)/1024, 1)} KB)",
                data=pdf_bytes,
                file_name=file_name,
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
            st.caption("✨ Fully formatted offline PDF document.")

    with col_pdf2:
        st.markdown("#### 🗄️ Saved Trips Portfolio")
        trips_list = st.session_state.saved_trips
        if not trips_list:
            st.info("No saved trips yet. Click 'Save Trip' in the Day-by-Day Itinerary tab to store trips.")
        else:
            for s_trip in trips_list:
                with st.container():
                    st.markdown(f"""
                    <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between;">
                            <b>{s_trip['destination']} ({s_trip['duration']}D)</b>
                            <span style="color: #38bdf8; font-weight: 700;">${s_trip['total_cost_usd']}</span>
                        </div>
                        <div style="font-size: 0.8rem; color: #94a3b8; margin: 4px 0;">{s_trip.get('title', 'Curated Itinerary')}</div>
                        <div style="font-size: 0.75rem; color: #64748b;">Saved: {s_trip.get('created_at', 'Recently')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    col_ld, col_del = st.columns(2)
                    with col_ld:
                        if st.button("Load Trip", key=f"ld_{s_trip['id']}", use_container_width=True):
                            st.session_state.current_itinerary = s_trip
                            st.rerun()
                    with col_del:
                        if st.button("Delete", key=f"del_{s_trip['id']}", use_container_width=True):
                            delete_trip_from_db(s_trip['id'])
                            st.session_state.saved_trips = load_trips_from_db()
                            st.rerun()
