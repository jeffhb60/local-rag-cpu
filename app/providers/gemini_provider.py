import google.generativeai as genai
from app.config import GEMINI_API_KEY
from .base import LLMProvider

class GeminiProvider(LLMProvider):
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)

    def generate(self, system_prompt, user_prompt, model, temperature):
        # Gemini combines system and user
        combined = f"{system_prompt}\n\n{user_prompt}"
        generation_config = {"temperature": temperature}
        model_instance = genai.GenerativeModel(model, generation_config=generation_config)
        response = model_instance.generate_content(combined)
        return response.text