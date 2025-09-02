import os
from functools import lru_cache
import boto3
from botocore.config import Config

S3_BUCKET = os.getenv("S3_BUCKET", "ai-job-tracker-uploads")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION") or "us-east-1"

AWS_BOTO_CONFIG = Config(signature_version="s3v4", s3={"addressing_style": "virtual"})

@lru_cache
def s3_client():
    return boto3.client("s3", region_name=AWS_REGION, config=AWS_BOTO_CONFIG)
