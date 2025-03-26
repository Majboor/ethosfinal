from rembg import remove
from PIL import Image
import os
import tempfile
import requests
from urllib.parse import urlparse
import base64
from io import BytesIO
from typing import Tuple
from s3_operations import upload_to_s3

def download_image(url: str) -> tuple:
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to download image from {url}")
    
    filename = os.path.basename(urlparse(url).path)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1])
    tmp.write(response.content)
    tmp.close()
    
    return tmp.name, filename

def process_and_upload_image(input_data, bucket_name: str, is_url: bool = False, return_base64: bool = False) -> Tuple[str, str]:
    temp_path = None
    temp_output_path = None
    
    try:
        if is_url:
            temp_path, filename = download_image(input_data)
        else:
            temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(input_data.filename)[1]).name
            input_data.save(temp_path)
            filename = input_data.filename
        
        image = Image.open(temp_path)
        output_image = remove(image)
        
        if return_base64:
            buffered = BytesIO()
            output_image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return filename, img_str
        
        output_filename = f"no_bg_{os.path.splitext(filename)[0]}.png"
        temp_output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
        output_image.save(temp_output_path)
        
        s3_url = upload_to_s3(temp_output_path, bucket_name, output_filename)
        
        return filename, s3_url
        
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        if temp_output_path and os.path.exists(temp_output_path):
            os.unlink(temp_output_path)