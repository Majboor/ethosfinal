from config import ALGORITHM_PARAMS

def get_user_feedback():
    while True:
        response = input("Do you like this style? (y/n): ").lower()
        if response in ['y', 'n']:
            return 'like' if response == 'y' else 'dislike'
        print("Invalid input. Please enter 'y' for like or 'n' for dislike.")

def display_results(top_styles, selection_history):
    print("\nYour Style Analysis:")
    print("-" * 50)
    if top_styles:
        print(f"Primary Style: {top_styles[0][0]} (Score: {top_styles[0][1]:.2f}/10)")
        if len(top_styles) > 1:
            print(f"Secondary Style: {top_styles[1][0]} (Score: {top_styles[1][1]:.2f}/10)")
    
    print("\nYour Selection History:")
    print("-" * 50)
    for idx, selection in enumerate(selection_history, 1):
        print(f"{idx}. Style: {selection['style']}")
        print(f"   Response: {'👍 Like' if selection['feedback'] == 'like' else '👎 Dislike'}")
        print(f"   Score Change: {selection['score_change']:.2f}")
        print(f"   Image: {selection['image']}")
        print("-" * 30)