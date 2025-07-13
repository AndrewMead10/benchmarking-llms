import openai
import time
import os
from typing import Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

class BenchmarkRunner:
    def __init__(self):
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
    
    def get_client(self, model_config: Dict[str, Any]) -> openai.OpenAI:
        api_endpoint = model_config.get("api_endpoint")
        api_key_name = model_config.get("api_key_name")
        
        if api_endpoint and api_key_name:
            api_key = os.getenv(api_key_name)
            return openai.OpenAI(
                api_key=api_key,
                base_url=api_endpoint
            )
        else:
            return openai.OpenAI(
                api_key=self.openrouter_api_key,
                base_url=self.openrouter_base_url
            )
    
    def run_benchmark(self, prompt_content: str, model_name: str, model_config: Dict[str, Any]) -> Tuple[str, int, int, float, int]:
        client = self.get_client(model_config)
        
        start_time = time.time()
        
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt_content}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            end_time = time.time()
            run_time_ms = int((end_time - start_time) * 1000)
            
            response_text = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            cost_usd = self.calculate_cost(model_name, input_tokens, output_tokens)
            
            return response_text, input_tokens, output_tokens, cost_usd, run_time_ms
            
        except Exception as e:
            end_time = time.time()
            run_time_ms = int((end_time - start_time) * 1000)
            return f"Error: {str(e)}", 0, 0, 0.0, run_time_ms
    
    def calculate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        }
        
        model_pricing = pricing.get(model_name, {"input": 0.001, "output": 0.002})
        
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
        
        return input_cost + output_cost