from collections import defaultdict
import time

class ScoreManager:
    def __init__(self, params):
        self.params = params
        self.style_scores = defaultdict(float)
        self.style_interaction_count = defaultdict(int)
        self.style_last_shown = defaultdict(float)

    def get_feedback_weight(self, feedback):
        feedback_weights = {
            'like': self.params['W_LIKE'],
            'dislike': self.params['W_DISLIKE']
        }
        return feedback_weights.get(feedback, self.params['W_LIKE'])

    def calculate_decay(self, style, current_time):
        time_since_last = current_time - self.style_last_shown.get(style, current_time)
        return max(0.5, min(1.0, time_since_last / 3600))

    def update_scores(self, style, feedback):
        current_time = time.time()
        self.style_interaction_count[style] += 1
        
        decay_modifier = self.calculate_decay(style, current_time)
        for s in self.style_scores:
            if s != style:
                self.style_scores[s] *= (self.params['DECAY_FACTOR'] ** decay_modifier)
        
        base_weight = self.get_feedback_weight(feedback)
        recency_multiplier = self.params['RECENCY_WEIGHT']
        interaction_factor = min(1.0, 1.0 / max(1, self.style_interaction_count[style]))
        
        adjusted_weight = base_weight * recency_multiplier * (1 + interaction_factor)
        self.style_scores[style] = (self.style_scores[style] * self.params['DECAY_FACTOR']) + adjusted_weight
        
        return adjusted_weight