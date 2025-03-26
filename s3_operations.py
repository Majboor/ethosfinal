import boto3
from dotenv import load_dotenv

load_dotenv()
def get_s3_client():
    return boto3.client(
    's3',
    aws_access_key_id=os.getenv('aws_access_key_id'),
    aws_secret_access_key=os.getenv('aws_secret_access_key'),
    region_name='us-east-1',
    verify=True
    )

def upload_to_s3(file_path: str, bucket_name: str, output_filename: str) -> str:
    s3_client = get_s3_client()
    try:
        s3_client.upload_file(
            file_path, 
            bucket_name, 
            output_filename,
            ExtraArgs={'ACL': 'public-read', 'ContentType': 'image/png'}
        )
        return f"https://{bucket_name}.s3.amazonaws.com/{output_filename}"
    except Exception as s3_error:
        raise Exception(f"S3 upload failed: {str(s3_error)}")