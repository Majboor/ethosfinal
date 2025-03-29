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
from image_analysis import setup_image_routes
import os
import json  # Added json import
from dotenv import load_dotenv
load_dotenv()

preferences_df = pd.DataFrame(columns=['preference_id', 'access_id', 'ai_id', 'gender', 'current_iteration', 'completed', 'algorithm'])
selections_df = pd.DataFrame(columns=['preference_id', 'iteration', 'image', 'style', 'feedback', 'score_change', 'current_score'])
profiles_df = pd.DataFrame(columns=['preference_id', 'top_styles', 'selection_history'])

CSV_DIR = './'
os.makedirs(CSV_DIR, exist_ok=True)

PREFERENCES_CSV = os.path.join(CSV_DIR, 'preferences.csv')
SELECTIONS_CSV = os.path.join(CSV_DIR, 'selections.csv')
PROFILES_CSV = os.path.join(CSV_DIR, 'profiles.csv')

if os.path.exists(PREFERENCES_CSV):
    preferences_df = pd.read_csv(PREFERENCES_CSV)
if os.path.exists(SELECTIONS_CSV):
    selections_df = pd.read_csv(SELECTIONS_CSV)
# Near the top of the file, after DataFrame declarations
if os.path.exists(PROFILES_CSV):
    profiles_df = pd.read_csv(PROFILES_CSV)
    # Convert string representations back to Python objects with error handling
    def safe_json_loads(x):
        try:
            if pd.isna(x):
                return {}
            return json.loads(str(x).replace("'", '"'))
        except:
            return {}
    
    profiles_df['top_styles'] = profiles_df['top_styles'].apply(safe_json_loads)
    profiles_df['selection_history'] = profiles_df['selection_history'].apply(safe_json_loads)

def create_app():
    app = Flask(__name__)
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    setup_image_routes(app)
   
    class StylePreferenceAlgorithm:
        def __init__(self):
            self.s3_handler = S3Handler()
            self.score_manager = ScoreManager(ALGORITHM_PARAMS)
            self.image_selector = ImageSelector(ALGORITHM_PARAMS)
            self.results_manager = ResultsManager()
            self.user_selections = []
            self.available_styles = set()
            self.used_styles = set()
            self.mandatory_styles = {'classic', 'creative', 'fashionista', 'modern', 'sophisticated', 'street'}
            self.current_cycle = 0
            self.styles_in_current_cycle = set()

        def select_next_image(self, gender, available_images):
            if not self.available_styles:
                self.available_styles = set(available_images.keys())
                for style in self.available_styles:
                    if style not in self.score_manager.style_scores:
                        self.score_manager.style_scores[style] = 0.0

            # Start new cycle if needed
            if not self.styles_in_current_cycle:
                self.styles_in_current_cycle = self.mandatory_styles.intersection(self.available_styles)
                self.current_cycle += 1

            # Try to use styles that haven't been shown in current cycle
            if self.styles_in_current_cycle:
                selected_style = random.choice(list(self.styles_in_current_cycle))
                if selected_style in available_images and available_images[selected_style]:
                    selected_image = self.image_selector.select_image(available_images, selected_style)
                    if selected_image:
                        self.styles_in_current_cycle.remove(selected_style)
                        self.used_styles.add(selected_style)
                        self.score_manager.style_last_shown[selected_style] = time.time()
                        return selected_image, selected_style

            # Fallback to normal selection if all mandatory styles used or no images available
            exploration_scores, current_time = self.image_selector.calculate_exploration_scores(
                available_images,
                self.score_manager.style_scores,
                self.score_manager.style_interaction_count,
                self.score_manager.style_last_shown
            )

            selected_style = self.image_selector.select_style(exploration_scores, available_images)
            selected_image = self.image_selector.select_image(available_images, selected_style)
            
            if not selected_image:
                # Try remaining styles with available images
                remaining_styles = [s for s in self.available_styles if available_images[s]]
                if remaining_styles:
                    selected_style = random.choice(remaining_styles)
                    selected_image = self.image_selector.select_image(available_images, selected_style)

            if selected_image:
                self.used_styles.add(selected_style)
                self.score_manager.style_last_shown[selected_style] = time.time()
                return selected_image, selected_style

            return None, None

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
        global preferences_df
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
    
        preferences_df = pd.concat([preferences_df, new_preference], ignore_index=True)
        preferences_df.to_csv(PREFERENCES_CSV, index=False)  # Save after concat
    
        return jsonify({
            'preference_id': preference_id,
            'ai_id': ai_id
        })

    @app.route('/api/preference/<preference_id>/next-image', methods=['GET'])
    def get_next_image(preference_id):
        ai_id = request.headers.get('AI-ID')
    
        try:
            preference_match = preferences_df[preferences_df['preference_id'] == preference_id]
            if preference_match.empty:
                return jsonify({'error': 'Preference not found'}), 404
            
            preference = preference_match.iloc[0]
            if preference['ai_id'] != ai_id:
                return jsonify({'error': 'Invalid AI ID'}), 401

            current_iteration = int(preference['current_iteration'])  # Convert to regular int
            if current_iteration >= 30:
                return jsonify({'error': 'Quiz completed'}), 400

            algorithm = preference['algorithm']
            available_images = algorithm.s3_handler.get_available_images(preference['gender'])
            image_key, style = algorithm.select_next_image(preference['gender'], available_images)
            
            if not image_key:
                return jsonify({'error': 'No more images available'}), 400

            url = algorithm.s3_handler.get_image_url(image_key)
            
            # Convert numeric values to Python native types
            return jsonify({
                'image_url': str(url),
                'iteration': int(current_iteration + 1),
                'style': str(style),
                'image_key': str(image_key)
            })
            
        except Exception as e:
            return jsonify({'error': f'Failed to get next image: {str(e)}'}), 400

    @app.route('/api/preference/<preference_id>/iteration/<int:iteration_id>', methods=['POST'])
    def process_iteration(preference_id, iteration_id):
        data = request.get_json()
        ai_id = request.headers.get('AI-ID')
        feedback = data.get('feedback')
        style = data.get('style')
        image_key = data.get('image_key')
    
        if not all([ai_id, feedback, style, image_key]) or feedback not in ['like', 'dislike']:
            return jsonify({'error': 'Invalid parameters'}), 400
    
        try:
            preference_match = preferences_df[preferences_df['preference_id'] == preference_id]
            if preference_match.empty:
                return jsonify({'error': 'Preference not found'}), 404
            
            preference = preference_match.iloc[0]
            if preference['ai_id'] != ai_id:
                return jsonify({'error': 'Invalid AI ID'}), 401
        
            if iteration_id != preference['current_iteration'] + 1:
                return jsonify({'error': 'Invalid iteration ID'}), 400
        
            algorithm = preference['algorithm']
            algorithm.update_scores(style, feedback, image_key)
            
            # Update current iteration
            preferences_df.loc[preferences_df['preference_id'] == preference_id, 'current_iteration'] = iteration_id
            
            selections_df.to_csv(SELECTIONS_CSV, index=False)  # Save selections_df after updating iteration
            
            # Check if quiz is completed
            if iteration_id == 30:
                preferences_df.loc[preferences_df['preference_id'] == preference_id, 'completed'] = True
            
            return jsonify({
                'iteration': iteration_id,
                'completed': iteration_id == 30
            })
            
        except Exception as e:
            return jsonify({'error': f'Failed to process iteration: {str(e)}'}), 400

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
        # Convert Python objects to JSON-compatible strings
        new_profile = pd.DataFrame([{
            'preference_id': preference_id,
            'top_styles': json.dumps(top_styles),
            'selection_history': json.dumps(algorithm.get_selection_history())
        }])
    
        global profiles_df
        profiles_df = pd.concat([profiles_df, new_profile], ignore_index=True)
        profiles_df.to_csv(PROFILES_CSV, index=False)  # Save profiles_df after concat
    
        return jsonify({'message': 'Profile saved successfully'})

    @app.route('/api/preference/<preference_id>/profile', methods=['GET'])
    def get_profile(preference_id):
        ai_id = request.headers.get('AI-ID')
    
        try:
            # Verify AI ID and preference
            preference_match = preferences_df[preferences_df['preference_id'] == preference_id]
            if preference_match.empty:
                return jsonify({'error': 'Preference not found'}), 404
            
            preference = preference_match.iloc[0]
            if preference['ai_id'] != ai_id:
                return jsonify({'error': 'Invalid AI ID'}), 401
            
            # Check if profile exists
            profile_match = profiles_df[profiles_df['preference_id'] == preference_id]
            if profile_match.empty:
                return jsonify({'error': 'Profile not found'}), 404
                
            profile = profile_match.iloc[0]
            
            # Parse the JSON strings back to Python objects
            try:
                top_styles = json.loads(profile['top_styles']) if isinstance(profile['top_styles'], str) else profile['top_styles']
                selection_history = json.loads(profile['selection_history']) if isinstance(profile['selection_history'], str) else profile['selection_history']
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid profile data format'}), 400
            
            return jsonify({
                'top_styles': top_styles,
                'selection_history': selection_history
            })
            
        except Exception as e:
            return jsonify({'error': f'Failed to retrieve profile: {str(e)}'}), 400

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=5020, debug=True)
