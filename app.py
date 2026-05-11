import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

from apps.gradio_main import demo

# Expose the Gradio ASGI app for Vercel
app = demo.app
