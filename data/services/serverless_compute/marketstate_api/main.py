from fastapi import FastAPI, Depends, HTTPException
import asyncpg
import os
import colorlog
import uvicorn

# Configure logging
def color_logging():
    """Configure colored logging."""
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            },
        )
    )
    logger = colorlog.getLogger()
    logger.addHandler(handler)
    logger.setLevel('INFO')
    return logger

logger = color_logging()

app = FastAPI()


# CORS (Cross-Origin Resource Sharing) is a security feature
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with specific domains if needed
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)


USER = os.getenv("POSTGRES_ADMIN")
PASSWORD = os.getenv("POSTGRES_PASSWORD")
HOST = os.getenv("POSTGRES_HOST")
SQL_INSTANCE = 'marketstate'


# Enable for Cloud Run
DATABASE_URL = f'postgresql://{USER}:{PASSWORD}@/marketstate?host=/cloudsql/general-428410:us-central1:{SQL_INSTANCE}'
# Enable for Dev
# DATABASE_URL = f'postgresql://{USER}:{PASSWORD}@{HOST}:5432/{SQL_INSTANCE}'

# Database connection pool
async def get_db_pool():
    return await asyncpg.create_pool(DATABASE_URL)

@app.on_event("startup")
async def startup():
    app.state.db_pool = await get_db_pool()

@app.on_event("shutdown")
async def shutdown():
    await app.state.db_pool.close()

@app.get("/")
def read_root():
    return {"message": "PostgreSQL FastAPI is running"}

@app.get("/query")
async def query_db(query: str):
    """
    Query the database with a user-provided query.
    Example: /query?query=SELECT * FROM marketstateai.prod_mart.marketcapbycountry LIMIT 10
        curl "https://marketstate-api-318171260121.us-central1.run.app/query?query=SELECT%20*%20FROM%20prod_mart.marketcapbycountry%20LIMIT%202000"
    """
    try:
        async with app.state.db_pool.acquire() as connection:
            result = await connection.fetch(query)
            logger.info(result[:100])
            return {"data": [dict(record) for record in result]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 8080))  # Default to 8080 if PORT is not set
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
