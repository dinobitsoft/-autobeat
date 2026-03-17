import boto3
import hashlib
from config import *

s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY
)


def upload_image(data):

    sha = hashlib.sha256(data).hexdigest()

    key = f"{sha}.jpg"

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=data
    )

    return sha, key