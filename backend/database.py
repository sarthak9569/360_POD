from motor.motor_asyncio import AsyncIOMotorClient
import os

# Use an environment variable for the connection string, fallback to localhost for development
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "pod2_db")

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]

# Collections
beneficiaries_collection = db.get_collection("beneficiaries")
deliveries_collection = db.get_collection("deliveries")
