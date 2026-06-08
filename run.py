import sys
import os

# Add backend directory to Python path to allow imports to work
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from main import drishti
except ImportError as e:
    print(f"Error importing backend modules: {e}")
    sys.exit(1)

if __name__ == "__main__":
    drishti()
