from flask import request, jsonify
from image_processor import process_and_upload_image
import json
from openai import OpenAI
import boto3
import concurrent.futures
from threading import Thread
import os
from dotenv import load_dotenv
load_dotenv()
# Constants
CLASSIFICATION_PROMPT = """
Refined Prompt:

"You are given an image to classify. Your tasks are:

1. Identify what type of image it is and categorize it as accurately as possible.
2. If the image includes any clothing items, identify:
   • The pattern (e.g., striped, polka-dotted, plain, etc.).
   • The color (e.g., red, blue, black, etc.).
   • The material (e.g., cotton, polyester, denim, etc.).
3. Provide multiple predictions or labels that the image might fall under, each with an associated confidence score. Use a numeric value between 0.0 and 1.0 for the score, where 0.0 indicates no confidence and 1.0 indicates maximum confidence.
4. Only return your response in valid JSON. Do not include any additional explanations, text, or formatting outside the JSON structure.

Your JSON output should follow this structure exactly:

{
  "predictions": [
    {
      "label": "string",
      "score": float,
      "pattern": "string",
      "color": "string",
      "material": "string"
    }
  ]
}

- 'predictions' must be an array.
- Each element in the 'predictions' array is an object with:
  • "label" (the category name as a string)
  • "score" (a floating-point number)
  • "pattern" (the clothing pattern as a string)
  • "color" (the color of the clothing item as a string)
  • "material" (the clothing material as a string)

You may return as many predictions as needed (including clothing pattern, color, and material, if relevant).
Ensure you do not return any text outside this JSON.

If you cannot comply with these instructions or if the image cannot be classified, return a valid JSON object with an 'error' key. For example:

{
  "error": "Could not classify image"
}

Remember:
• Output must always be valid JSON.
• No additional commentary or explanation beyond the JSON structure.

Sample valid outputs:

{
  "predictions": [
    {
      "label": "dress",
      "score": 0.92,
      "pattern": "striped",
      "color": "blue",
      "material": "cotton"
    },
    {
      "label": "summer attire",
      "score": 0.85,
      "pattern": "plain",
      "color": "white",
      "material": "linen"
    }
  ]
}

Or:

{
  "error": "Could not classify image"
}

That is all. Thank you."
"""

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def process_single_image(image_url):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": CLASSIFICATION_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }],
        )
        return {
            "image_url": image_url,
            "analysis": json.loads(response.choices[0].message.content)
        }
    except Exception as e:
        return {"image_url": image_url, "error": str(e)}

def setup_image_routes(app):
    @app.route('/analyze-image', methods=['POST'])
    def analyze_image():
        try:
            data = request.json
            image_url = data.get('image_url')
            return jsonify(process_single_image(image_url))
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route('/analyze-images', methods=['POST'])
    def analyze_images():
        try:
            data = request.json
            image_urls = data.get('image_urls', [])
            
            if not image_urls:
                return jsonify({"error": "No images provided"}), 400

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(process_single_image, image_urls))

            return jsonify({"results": results})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route('/remove-background', methods=['GET', 'POST'])
    def remove_background():
        try:
            return_base64 = request.args.get('return_base64', 'false').lower() == 'true'
            results = {}

            if request.is_json:
                data = request.get_json()
                if 'urls' in data:
                    # Handle multiple URLs
                    urls = data.get('urls', [])
                    for url in urls:
                        if url:
                            filename, result = process_and_upload_image(
                                url,
                                bucket_name="haider-bhai",
                                is_url=True,
                                return_base64=return_base64
                            )
                            results[filename] = result
                    
                    return jsonify({
                        "success": True,
                        "results": results
                    })
                
                elif 'image_url' in data:
                    # Handle single URL from JSON body
                    image_url = data.get('image_url')
                    filename, result = process_and_upload_image(
                        image_url,
                        bucket_name="haider-bhai",
                        is_url=True,
                        return_base64=return_base64
                    )
                    results[filename] = result
                    return jsonify({
                        "success": True,
                        "results": results
                    })

            elif 'images' in request.files:
                # Handle file uploads
                files = request.files.getlist('images')
                for file in files:
                    if file:
                        filename, result = process_and_upload_image(
                            file,
                            bucket_name="haider-bhai",
                            is_url=False,
                            return_base64=return_base64
                        )
                        results[filename] = result
                
                return jsonify({
                    "success": True,
                    "results": results
                })
            
            elif 'image_url' in request.args:
                # Handle single URL from query params
                image_url = request.args.get('image_url')
                filename, result = process_and_upload_image(
                    image_url,
                    bucket_name="haider-bhai",
                    is_url=True,
                    return_base64=return_base64
                )
                results[filename] = result
                return jsonify({
                    "success": True,
                    "results": results
                })
            
            else:
                return jsonify({"error": "No images or URLs provided"}), 400

        except Exception as e:
            print(f"Error in remove_background: {str(e)}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500