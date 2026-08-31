import os
from pymongo import MongoClient
import uuid

# Connect to MongoDB Atlas instance
mongo_uri = os.getenv('MONGO_URI')
if not mongo_uri:
    raise ValueError("MONGO_URI environment variable is not set. Check your .env file or Vercel environment variables.")
client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)

# Select the library database
db = client['library_db']

# Collections
books_collection = db['books']
issues_collection = db['issues']
config_collection = db['config']

# Ensure indexes
books_collection.create_index('isbn', unique=True)
issues_collection.create_index('issue_id', unique=True)

# Helper function to get config
def get_config():
    config = config_collection.find_one({'_id': 'system_config'})
    if not config:
        config = {'_id': 'system_config', 'fine_per_day': 5}
        config_collection.insert_one(config)
    return config

def set_fine_rate(fine_per_day):
    config_collection.update_one(
        {'_id': 'system_config'},
        {'$set': {'fine_per_day': fine_per_day}},
        upsert=True
    )
    
def generate_uuid():
    return str(uuid.uuid4())
