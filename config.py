# S3 Configuration
import os
from dotenv import load_dotenv
load_dotenv()
S3_CONFIG = {
    'aws_access_key_id': os.getenv('aws_access_key_id'),
    'aws_secret_access_key': os.getenv('aws_secret_access_key'),
    'bucket_name': 'ethos-style-images',
    'prefix': 'Styles/'
}

# Algorithm Parameters
ALGORITHM_PARAMS = {
    'W_LIKE': 1.0,
    'W_DISLIKE': -0.5,
    'DECAY_FACTOR': 0.98,
    'BASELINE': 0.5,
    'RECENCY_WEIGHT': 1.2,
    'EXPLORATION_FACTOR': 0.2
}