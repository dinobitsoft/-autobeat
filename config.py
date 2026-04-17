import os

POSTGRES_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/cars"

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "admin")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "admin")

REDIS_HOST = "redis"

S3_ENDPOINT = "http://seaweedfs:8888"
S3_BUCKET = "car-images"
S3_ACCESS_KEY = "admin"
S3_SECRET_KEY = "admin"

DETAIL_VISIT_CHANCE = 0.3  # probability of visiting a random detail page after a listing page
HUMAN_DELAY_MAX_S = 60     # max random delay in seconds between page fetches