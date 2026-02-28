from pymongo import MongoClient
from app.config import settings

client = MongoClient(settings.MONGO_URI)

db = client[settings.MONGO_DB]

# Collections
users_collection = db["users"]
items_collection = db["items"]
scan_logs_collection = db["scan_logs"]
violation_logs_collection = db["violation_logs"]
notifications_collection = db["notifications"]