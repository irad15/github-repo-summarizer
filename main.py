from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv

from api.routes import router

import logging

# Load environment variables
load_dotenv()

# Configure basic logging so we can see logger.info() output in the terminal
logging.basicConfig(level=logging.INFO)

# Mute the extremely verbose httpx logs so they don't spam the terminal
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

app = FastAPI(title="GitHub Repo Summarizer API")

# Include the external routes
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
