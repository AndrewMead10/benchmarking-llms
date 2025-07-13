import openai
import time
import os
from typing import Optional, Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

class LLMJudge:
    def __init__(self):
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
    
    def get_client(self, judge_config: Dict[str, Any]) -> openai.OpenAI:
        api_endpoint = judge_config.get("api_endpoint")
        api_key_name = judge_config.get("api_key_name")
        
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
    
    def evaluate_with_rubric(self, prompt: str, response: str, rubric: str, judge_model_name: str, judge_config: Dict[str, Any]) -> Tuple[float, str, int, float, int]:
        client = self.get_client(judge_config)
        
        judge_prompt = f"""You are an expert evaluator. Please evaluate the following response according to the given rubric.

ORIGINAL PROMPT:
{prompt}

RESPONSE TO EVALUATE:
{response}

EVALUATION RUBRIC:
{rubric}

Please provide:
1. A score from 0.0 to 1.0 (where 1.0 is perfect)
2. Your reasoning for this score

Format your response as:
SCORE: [0.0-1.0]
REASONING: [Your detailed reasoning here]"""
        
        start_time = time.time()
        
        try:
            judge_response = client.chat.completions.create(
                model=judge_model_name,
                messages=[
                    {"role": "user", "content": judge_prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            end_time = time.time()
            judge_time_ms = int((end_time - start_time) * 1000)
            
            judge_text = judge_response.choices[0].message.content
            judge_tokens = judge_response.usage.completion_tokens + judge_response.usage.prompt_tokens
            judge_cost = self.calculate_cost(judge_model_name, judge_response.usage.prompt_tokens, judge_response.usage.completion_tokens)
            
            score, reasoning = self.parse_judge_response(judge_text)
            
            return score, reasoning, judge_tokens, judge_cost, judge_time_ms
            
        except Exception as e:
            end_time = time.time()
            judge_time_ms = int((end_time - start_time) * 1000)
            return 0.0, f"Judge evaluation failed: {str(e)}", 0, 0.0, judge_time_ms
    
    def parse_judge_response(self, judge_text: str) -> Tuple[float, str]:
        try:
            lines = judge_text.strip().split('\n')
            score = 0.0
            reasoning = ""
            
            for line in lines:
                if line.startswith("SCORE:"):
                    score_str = line.replace("SCORE:", "").strip()
                    score = float(score_str)
                    score = max(0.0, min(1.0, score))
                elif line.startswith("REASONING:"):
                    reasoning = line.replace("REASONING:", "").strip()
            
            if not reasoning:
                reasoning = judge_text
            
            return score, reasoning
            
        except Exception:
            return 0.0, judge_text
    
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

class TextEvaluator:
    def __init__(self):
        self.llm_judge = LLMJudge()
    
    def evaluate_response(self, response_text: str, prompt_text: str = None, rubric: str = None, 
                         judge_model_name: str = None, judge_config: Dict[str, Any] = None) -> Tuple[Optional[float], str, int, float, int]:
        if not response_text or response_text.startswith("Error:"):
            return 0.0, "Response was empty or contained an error", 0, 0.0, 0
        
        if rubric and judge_model_name and judge_config and prompt_text:
            return self.llm_judge.evaluate_with_rubric(prompt_text, response_text, rubric, judge_model_name, judge_config)
        else:
            simple_score = min(1.0, len(response_text) / 1000.0)
            return simple_score, "Simple length-based scoring (no rubric provided)", 0, 0.0, 0

class VisionEvaluator:
    def __init__(self):
        self.llm_judge = LLMJudge()
    
    def evaluate_response(self, response_text: str, prompt_text: str = None, rubric: str = None, 
                         judge_model_name: str = None, judge_config: Dict[str, Any] = None) -> Tuple[Optional[float], str, int, float, int]:
        if rubric and judge_model_name and judge_config and prompt_text:
            return self.llm_judge.evaluate_with_rubric(prompt_text, response_text, rubric, judge_model_name, judge_config)
        else:
            return None, "Vision evaluation requires rubric and judge model", 0, 0.0, 0

class AgentEvaluator:
    def __init__(self):
        self.llm_judge = LLMJudge()
    
    def evaluate_response(self, response_text: str, prompt_text: str = None, rubric: str = None, 
                         judge_model_name: str = None, judge_config: Dict[str, Any] = None) -> Tuple[Optional[float], str, int, float, int]:
        if rubric and judge_model_name and judge_config and prompt_text:
            return self.llm_judge.evaluate_with_rubric(prompt_text, response_text, rubric, judge_model_name, judge_config)
        else:
            return None, "Agent evaluation requires rubric and judge model", 0, 0.0, 0

def get_evaluator(eval_type: str):
    evaluators = {
        "text": TextEvaluator,
        "vision": VisionEvaluator,
        "agent": AgentEvaluator
    }
    return evaluators.get(eval_type, TextEvaluator)