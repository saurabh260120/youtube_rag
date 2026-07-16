import os
from pymongo import MongoClient
from pymongo.server_api import ServerApi
# load from .env file
from dotenv import load_dotenv
from utility.logger import log

load_dotenv()
uri = os.getenv("MONGO_DB_CONNECTION_URI")

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    log("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    log(f"MongoDB connection failed: {e}")
