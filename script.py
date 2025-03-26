import boto3
from botocore.exceptions import ClientError
from collections import defaultdict
import os
from dotenv import load_dotenv

load_dotenv()

def fetch_s3_category_counts():
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('aws_access_key_id'),
        aws_secret_access_key=os.getenv('aws_secret_access_key')
    )


    bucket_name = 'ethos-style-images'
    prefix = 'Styles/'
    
    # Initialize counters
    category_counts = defaultdict(int)

    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if key == prefix:
                        continue
                    
                    # Extract category path (e.g., 'women/street-style')
                    parts = key.split('/')
                    if len(parts) >= 4:  # Ensure we have enough parts in the path
                        category = f"{parts[1]}/{parts[2]}"
                        category_counts[category] += 1

        print("\nFile counts by category:")
        print("-" * 40)
        for category, count in sorted(category_counts.items()):
            print(f"{category}: {count} files")
        
        total_files = sum(category_counts.values())
        print("-" * 40)
        print(f"Total files: {total_files}")

    except ClientError as e:
        print(f"Error accessing S3: {e}")

def get_s3_image_urls():
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('aws_access_key_id'),
        aws_secret_access_key=os.getenv('aws_secret_access_key')
    )

    bucket_name = 'ethos-style-images'
    prefix = 'Styles/'
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        print("\nImage URLs by category:")
        print("-" * 80)
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if key == prefix or not any(key.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                        continue
                    
                    # Generate presigned URL (valid for 1 hour)
                    url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': bucket_name, 'Key': key},
                        ExpiresIn=3600
                    )
                    
                    print(f"File: {key}")
                    print(f"URL: {url}")
                    print("-" * 80)

    except ClientError as e:
        print(f"Error accessing S3: {e}")

if __name__ == "__main__":
    fetch_s3_category_counts()
    get_s3_image_urls()
