# Loading LLM Config from data_models.py requires to have dotenv imported first
# and to have it loaded

import dotenv
import os

if os.getenv("ENHANCED_LOAD_DOTENV", "0") == "1":
    dotenv.load_dotenv(override=False)
