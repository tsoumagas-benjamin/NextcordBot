# Common utilities that may be shared across files
from pymongo import MongoClient
from os import getenv

# Database config
client = MongoClient(getenv("CONN_STRING"))

# Name our access to our client database
db = client.NextcordBot

# Get all the existing collections
collections = db.list_collection_names()
collection_names = [
    "sales",
    "worldstate",
    "sales_channels",
    "levels",
    "daily_channels",
    "languages",
    "birthdays",
    "warframe_channels",
    "audit_logs",
    "rules",
]
