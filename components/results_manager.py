class ResultsManager:
    def normalize_scores(self, style_scores):
        if not style_scores:
            return []
            
        max_score = max(abs(score) for score in style_scores.values())
        if max_score == 0:
            return sorted(style_scores.items(), key=lambda x: x[1], reverse=True)
            
        normalized_scores = {
            style: (score / max_score) * 10
            for style, score in style_scores.items()
        }
        
        sorted_styles = sorted(normalized_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_styles[:2] if len(sorted_styles) >= 2 else sorted_styles