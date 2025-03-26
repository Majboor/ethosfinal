import random
import time

class ImageSelector:
    def __init__(self, params):
        self.params = params
        self.shown_images = set()

    def calculate_exploration_scores(self, available_images, style_scores, style_interaction_count, style_last_shown):
        current_time = time.time()
        exploration_scores = {}
        
        for style in available_images:
            time_since_last_shown = current_time - style_last_shown.get(style, 0)
            interaction_count = style_interaction_count[style]
            
            base_score = max(style_scores[style] + self.params['BASELINE'], 0)
            exploration_bonus = self.params['EXPLORATION_FACTOR'] * (1.0 / (interaction_count + 1))
            time_bonus = 0.1 * min(time_since_last_shown / 3600, 1.0)
            
            exploration_scores[style] = base_score + exploration_bonus + time_bonus
            
        return exploration_scores, current_time

    def select_style(self, exploration_scores, available_images):
        total_score = sum(exploration_scores.values())
        if total_score == 0:
            return random.choice(list(available_images.keys()))
        
        weights = [exploration_scores[style] for style in available_images.keys()]
        return random.choices(list(available_images.keys()), weights=weights, k=1)[0]

    def select_image(self, available_images, style):
        available = [img for img in available_images[style] if img not in self.shown_images]
        if not available:
            return None
        
        selected_image = random.choice(available)
        self.shown_images.add(selected_image)
        return selected_image