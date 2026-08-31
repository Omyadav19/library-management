import os
from pymongo import MongoClient
import uuid

mongo_uri = os.getenv('MONGO_URI')

if mongo_uri:
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
else:
    client = None
    db = None
    books_collection = None
    issues_collection = None
    config_collection = None

def get_config():
    if config_collection is None:
        return {'_id': 'system_config', 'fine_per_day': 5}
    try:
        config = config_collection.find_one({'_id': 'system_config'})
        if not config:
            config = {'_id': 'system_config', 'fine_per_day': 5}
            config_collection.insert_one(config)
        return config
    except Exception:
        return {'_id': 'system_config', 'fine_per_day': 5}

def set_fine_rate(fine_per_day):
    if config_collection is not None:
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
