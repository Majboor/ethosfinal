from collections import defaultdict
import random
import time
import uuid
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from s3_handler import S3Handler
from config import ALGORITHM_PARAMS
from components.score_manager import ScoreManager
from components.image_selector import ImageSelector
from components.results_manager import ResultsManager
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)  # Add this line after creating the Flask app

# In-memory storage using pandas DataFrames
preferences_df = pd.DataFrame(columns=['preference_id', 'access_id', 'ai_id', 'gender', 'current_iteration', 'completed', 'algorithm'])
selections_df = pd.DataFrame(columns=['preference_id', 'iteration', 'image', 'style', 'feedback', 'score_change', 'current_score'])
profiles_df = pd.DataFrame(columns=['preference_id', 'top_styles', 'selection_history'])

class StylePreferenceAlgorithm:
    def __init__(self):
        self.s3_handler = S3Handler()
        self.score_manager = ScoreManager(ALGORITHM_PARAMS)
        self.image_selector = ImageSelector(ALGORITHM_PARAMS)
        self.results_manager = ResultsManager()
        self.user_selections = []

    def select_next_image(self, gender, available_images):
        exploration_scores, current_time = self.image_selector.calculate_exploration_scores(
            available_images,
            self.score_manager.style_scores,
            self.score_manager.style_interaction_count,
            self.score_manager.style_last_shown
        )
        
        selected_style = self.image_selector.select_style(exploration_scores, available_images)
        self.score_manager.style_last_shown[selected_style] = current_time
        
        selected_image = self.image_selector.select_image(available_images, selected_style)
        if not selected_image:
            return None, None
            
        return selected_image, selected_style

    def update_scores(self, style, feedback, image_key):
        adjusted_weight = self.score_manager.update_scores(style, feedback)
        current_score = self.score_manager.style_scores[style]
        
        self.user_selections.append({
            'image': image_key,
            'style': style,
            'feedback': 'Like' if feedback == 'like' else 'Dislike',
            'score_change': adjusted_weight,
            'current_score': current_score,
            'timestamp': time.time()
        })

    def get_selection_history(self):
        return self.user_selections

    def get_top_styles(self):
        return self.results_manager.normalize_scores(self.score_manager.style_scores)

def run_style_quiz():
    while True:
        gender = input("Please enter your gender (men/women): ").lower()
        if gender in ['men', 'women']:
            break
        print("Invalid input. Please enter 'men' or 'women'.")

    algorithm = StylePreferenceAlgorithm()
    available_images = algorithm.s3_handler.get_available_images(gender)
    
    if not available_images:
        print("No images available. Please check the connection and try again.")
        return

    for i in range(30):
        image_key, style = algorithm.select_next_image(gender, available_images)
        if not image_key:
            print("No more unique images available.")
            break

        url = algorithm.s3_handler.get_image_url(image_key)
        if not url:
            continue

        print(f"\nImage {i+1}/30")
        print(f"Please view the image at: {url}")
        
        feedback = get_user_feedback()
        algorithm.update_scores(style, feedback, image_key)

    display_results(algorithm.get_top_styles(), algorithm.get_selection_history())

def generate_ai_id(access_id):
    return f"AI_{access_id}_{str(uuid.uuid4())[:8]}"

# Add this new endpoint to your Flask app
@app.route('/api')
def health_check():
    return jsonify({'status': 'ok'})

@app.route('/api/preference', methods=['POST'])
def create_preference():
    data = request.get_json()
    access_id = data.get('access_id')
    gender = data.get('gender')
    
    if not access_id or gender not in ['men', 'women']:
        return jsonify({'error': 'Invalid parameters'}), 400
    
    ai_id = generate_ai_id(access_id)
    preference_id = str(uuid.uuid4())
    
    algorithm = StylePreferenceAlgorithm()
    
    # Store preference information
    new_preference = pd.DataFrame([{
        'preference_id': preference_id,
        'access_id': access_id,
        'ai_id': ai_id,
        'gender': gender,
        'current_iteration': 0,
        'completed': False,
        'algorithm': algorithm
    }])
    
    global preferences_df
    preferences_df = pd.concat([preferences_df, new_preference], ignore_index=True)
    
    return jsonify({
        'preference_id': preference_id,
        'ai_id': ai_id
    })

@app.route('/api/preference/<preference_id>/iteration/<int:iteration_id>', methods=['POST'])
def process_iteration(preference_id, iteration_id):
    data = request.get_json()
    ai_id = request.headers.get('AI-ID')
    feedback = data.get('feedback')
    
    if not ai_id or feedback not in ['like', 'dislike']:
        return jsonify({'error': 'Invalid parameters'}), 400
    
    # Verify AI ID and preference
    preference = preferences_df[preferences_df['preference_id'] == preference_id].iloc[0]
    if preference['ai_id'] != ai_id:
        return jsonify({'error': 'Invalid AI ID'}), 401
    
    if iteration_id != preference['current_iteration'] + 1:
        return jsonify({'error': 'Invalid iteration ID'}), 400
    
    algorithm = preference['algorithm']
    
    # Handle the last iteration differently
    if iteration_id == 30:
        # Just process the feedback for the last image
        algorithm.update_scores(data.get('style', 'unknown'), feedback, data.get('image_key', 'unknown'))
        preferences_df.loc[preferences_df['preference_id'] == preference_id, 'current_iteration'] = iteration_id
        preferences_df.loc[preferences_df['preference_id'] == preference_id, 'completed'] = True
        return jsonify({
            'image_url': None,
            'iteration': iteration_id,
            'completed': True
        })
    
    # Normal iteration processing
    available_images = algorithm.s3_handler.get_available_images(preference['gender'])
    image_key, style = algorithm.select_next_image(preference['gender'], available_images)
    if not image_key:
        return jsonify({'error': 'No more images available'}), 400
    
    url = algorithm.s3_handler.get_image_url(image_key)
    algorithm.update_scores(style, feedback, image_key)
    
    # Update current iteration
    preferences_df.loc[preferences_df['preference_id'] == preference_id, 'current_iteration'] = iteration_id
    
    return jsonify({
        'image_url': url,
        'iteration': iteration_id,
        'completed': iteration_id == 30,
        'style': style,
        'image_key': image_key
    })

@app.route('/api/preference/<preference_id>/profile', methods=['POST'])
def save_profile(preference_id):
    ai_id = request.headers.get('AI-ID')
    
    # Verify AI ID and preference
    preference = preferences_df[preferences_df['preference_id'] == preference_id].iloc[0]
    if preference['ai_id'] != ai_id:
        return jsonify({'error': 'Invalid AI ID'}), 401
    
    if not preference['completed']:
        return jsonify({'error': 'Profile not completed'}), 400
    
    algorithm = preference['algorithm']
    
    # Convert top_styles to dictionary if it's not already
    top_styles = algorithm.get_top_styles()
    if isinstance(top_styles, list):
        top_styles = {str(i): style for i, style in enumerate(top_styles)}
    
    # Save profile with properly formatted data
    new_profile = pd.DataFrame([{
        'preference_id': preference_id,
        'top_styles': top_styles,
        'selection_history': algorithm.get_selection_history()
    }])
    
    global profiles_df
    profiles_df = pd.concat([profiles_df, new_profile], ignore_index=True)
    
    return jsonify({'message': 'Profile saved successfully'})

@app.route('/api/preference/<preference_id>/profile', methods=['GET'])
def get_profile(preference_id):
    ai_id = request.headers.get('AI-ID')
    
    # Verify AI ID and preference
    preference = preferences_df[preferences_df['preference_id'] == preference_id].iloc[0]
    if preference['ai_id'] != ai_id:
        return jsonify({'error': 'Invalid AI ID'}), 401
    
    try:
        profile = profiles_df[profiles_df['preference_id'] == preference_id].iloc[0]
        
        # Ensure top_styles is a dictionary
        top_styles = profile['top_styles']
        if isinstance(top_styles, list):
            top_styles = {str(i): style for i, style in enumerate(top_styles)}
        
        return jsonify({
            'top_styles': top_styles,
            'selection_history': profile['selection_history']
        })
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve profile: {str(e)}'}), 400

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5020,debug=True)