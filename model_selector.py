"""
Terminal Model Selector - Similar to Ollama CLI
Uses arrow keys to navigate and Enter to select
"""

import inquirer

def select_model():
    """Display a model selection menu with arrow navigation"""
    
    # List of available models (customize this list)
    models = ['llama2', 'mistral', 'gemma', 'qwen', 'codellama', 'neural-chat']
    
    questions = [
        inquirer.List(
            'model',
            message="Select a model",
            choices=models,
        ),
    ]
    
    answers = inquirer.prompt(questions)
    
    if answers:
        selected_model = answers['model']
        print(f"\n✓ You selected: {selected_model}")
        return selected_model
    else:
        print("\nNo selection made")
        return None

if __name__ == "__main__":
    print("=" * 50)
    print("  Ollama-style Model Selector")
    print("=" * 50)
    print("\nUse ↑↓ arrows to navigate, Enter to select")
    print("=" * 50)
    
    selected = select_model()
    
    if selected:
        print(f"\nRunning with model: {selected}")
        # Add your model logic here
