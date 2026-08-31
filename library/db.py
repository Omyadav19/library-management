import os
from pymongo import MongoClient
import uuid

# Fallback URI if environment variable is not explicitly injected in Vercel UI
DEFAULT_MONGO_URI = "mongodb+srv://ryadavom94_db_user:BwEBqDgtkexAOE0X@cluster1.9irbojt.mongodb.net/?appName=Cluster1"
mongo_uri = os.getenv('MONGO_URI') or DEFAULT_MONGO_URI

try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client['library_db']
    books_collection = db['books']
    issues_collection = db['issues']
    config_collection = db['config']
    try:
        books_collection.create_index('isbn', unique=True)
        issues_collection.create_index('issue_id', unique=True)
    except Exception:
        pass
except Exception as e:
    print(f"MongoDB connection error: {e}")
    client = MongoClient(DEFAULT_MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['library_db']
    books_collection = db['books']
    issues_collection = db['issues']
    config_collection = db['config']

def get_config():
    try:
        config = config_collection.find_one({'_id': 'system_config'})
        if not config:
            config = {'_id': 'system_config', 'fine_per_day': 5}
            config_collection.insert_one(config)
        return config
    except Exception:
        return {'_id': 'system_config', 'fine_per_day': 5}

def set_fine_rate(fine_per_day):
    try:
        config_collection.update_one(
            {'_id': 'system_config'},
            {'$set': {'fine_per_day': fine_per_day}},
            upsert=True
        )
    except Exception:
        pass
    
def generate_uuid():
    return str(uuid.uuid4())
