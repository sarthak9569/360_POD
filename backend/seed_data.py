import asyncio
from database import beneficiaries_collection

seed_data = [
    {
        "tag_no": "106208111223",
        "farmer_name": "Dashri Potai",
        "spouse_name": "Apurv / Etturam Potai",
        "village": "Ghodagaon",
        "cattle_feed_kg": 25,
        "silage_kg": 50
    },
    {
        "tag_no": "106296833111",
        "farmer_name": "Dashri Potai",
        "spouse_name": "Apurv / Etturam Potai",
        "village": "Ghodagaon",
        "cattle_feed_kg": 20,
        "silage_kg": 40
    },
    {
        "tag_no": "106296201654",
        "farmer_name": "Ogarn Gawde",
        "spouse_name": "Spouse 1",
        "village": "Dhoragaon",
        "cattle_feed_kg": 30,
        "silage_kg": 60
    },
    {
        "tag_no": "106296201046",
        "farmer_name": "Ramu Kaka",
        "spouse_name": "Spouse 2",
        "village": "Alor",
        "cattle_feed_kg": 15,
        "silage_kg": 30
    },
    {
        "tag_no": "106296833268",
        "farmer_name": "Shamrao",
        "spouse_name": "Spouse 3",
        "village": "Masra",
        "cattle_feed_kg": 10,
        "silage_kg": 20
    }
]

async def seed_db():
    print("Clearing existing beneficiaries...")
    await beneficiaries_collection.delete_many({})
    
    print("Inserting seed data...")
    result = await beneficiaries_collection.insert_many(seed_data)
    print(f"Successfully inserted {len(result.inserted_ids)} beneficiaries.")

if __name__ == "__main__":
    asyncio.run(seed_db())
