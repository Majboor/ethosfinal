



import requests
import time

BASE_URL = 'http://192.168.100.9:5020/api'

def print_response_details(response):
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Raw Response: {response.text}")
    try:
        print(f"JSON Response: {response.json()}")
    except Exception as e:
        print(f"Could not parse JSON: {str(e)}")

def check_server_status():
    try:
        response = requests.get(BASE_URL)
        return True
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to the Flask server!")
        print("Please ensure:")
        print("1. The Flask server is running")
        print("2. The server is accessible at http://localhost:5000")
        print("3. No firewall is blocking the connection")
        print("\nTo start the server, run:")
        print("python /Users/terminator/Downloads/Data/haider-bhai/algo/style_algorithm.py")
        return False

def test_style_preference_api():
    if not check_server_status():
        return

    # Step 1: Create a new preference
    print("\n1. Creating new preference...")
    try:
        create_response = requests.post(
            f'{BASE_URL}/preference',
            json={
                'access_id': 'test_user_123',
                'gender': 'women'
            }
        )
        
        if create_response.status_code != 200:
            print("Error creating preference:")
            print_response_details(create_response)
            return
        
        preference_data = create_response.json()
        preference_id = preference_data['preference_id']
        ai_id = preference_data['ai_id']
        
        print(f"Preference created successfully!")
        print(f"Preference ID: {preference_id}")
        print(f"AI ID: {ai_id}")

    except requests.exceptions.ConnectionError:
        print("Failed to connect to the server. Make sure the Flask API is running.")
        return
    except Exception as e:
        print(f"Unexpected error during preference creation: {str(e)}")
        return

    # Step 2: Process iterations
    # In the test_style_preference_api function, update the iteration loop:
    print("\n2. Processing iterations...")
    last_style = None
    last_image_key = None
    
    for iteration in range(1, 31):
        print(f"\nProcessing iteration {iteration}/30")
        try:
            feedback_data = {'feedback': 'like' if iteration % 2 == 0 else 'dislike'}
            
            # Add style and image_key for the last iteration
            if iteration == 30 and last_style and last_image_key:
                feedback_data.update({
                    'style': last_style,
                    'image_key': last_image_key
                })
            
            iteration_response = requests.post(
                f'{BASE_URL}/preference/{preference_id}/iteration/{iteration}',
                headers={'AI-ID': ai_id},
                json=feedback_data
            )
            
            if iteration_response.status_code != 200:
                print(f"Error in iteration {iteration}:")
                print_response_details(iteration_response)
                return
            
            result = iteration_response.json()
            if result.get('image_url'):
                print(f"Image URL: {result['image_url']}")
                last_style = result.get('style')
                last_image_key = result.get('image_key')
            print(f"Completed: {result['completed']}")
            
        except Exception as e:
            print(f"Error during iteration {iteration}: {str(e)}")
            return
        
        time.sleep(1)

    # Step 3: Save the profile
    print("\n3. Saving profile...")
    try:
        save_response = requests.post(
            f'{BASE_URL}/preference/{preference_id}/profile',
            headers={'AI-ID': ai_id}
        )
        
        if save_response.status_code != 200:
            print("Error saving profile:")
            print_response_details(save_response)
            return
        
        print("Profile saved successfully!")

    except Exception as e:
        print(f"Error during profile saving: {str(e)}")
        return

    # Step 4: Retrieve the profile
    print("\n4. Retrieving profile...")
    try:
        get_response = requests.get(
            f'{BASE_URL}/preference/{preference_id}/profile',
            headers={'AI-ID': ai_id}
        )
        
        if get_response.status_code != 200:
            print("Error retrieving profile:")
            print_response_details(get_response)
            return
        
        profile_data = get_response.json()
        print("\nTop Styles:")
        for style, score in profile_data['top_styles'].items():
            print(f"- {style}: {score}")
        
        print("\nSelection History:")
        for selection in profile_data['selection_history']:
            print(f"- Image: {selection['image']}")
            print(f"  Style: {selection['style']}")
            print(f"  Feedback: {selection['feedback']}")
            print(f"  Score Change: {selection['score_change']}")
            print(f"  Current Score: {selection['current_score']}")
            print("  ---")

    except Exception as e:
        print(f"Error during profile retrieval: {str(e)}")
        return

if __name__ == "__main__":
    test_style_preference_api()