import boto3
from botocore.exceptions import ClientError
from collections import defaultdict
from config import S3_CONFIG
import os
from dotenv import load_dotenv
load_dotenv()
class S3Handler:
    def __init__(self):
        self.s3_client = boto3.client('s3', **{
            k: v for k, v in S3_CONFIG.items() 
            if k.startswith('aws_')
        })
        self.bucket_name = S3_CONFIG['bucket_name']
        self.prefix = S3_CONFIG['prefix']

    def get_available_images(self, gender):
        images_by_style = defaultdict(list)
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=self.prefix)
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        parts = key.split('/')
                        if len(parts) >= 4 and parts[1] == gender:
                            style = parts[2].replace('-style', '')
                            images_by_style[style].append(key)
            
            return images_by_style
        except ClientError as e:
            print(f"Error accessing S3: {e}")
            return {}

    def get_image_url(self, image_key):
        try:
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': image_key},
                ExpiresIn=3600
            )
        except ClientError as e:
            print(f"Error generating URL: {e}")
            return None