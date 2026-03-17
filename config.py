import os

POSTGRES_URL = "postgresql+psycopg://postgres:postgres@postgres:5432/cars"

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")

REDIS_HOST = "redis"

S3_ENDPOINT = "http://seaweedfs:8888"
S3_BUCKET = "car-images"
S3_ACCESS_KEY = "admin"
S3_SECRET_KEY = "admin"