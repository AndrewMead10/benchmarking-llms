from typing import Optional, Tuple
import openai
import os
import json
import re

class LLMJudgeEvaluator:
    def __init__(self, judge_model: str = "gpt-4"):
        self.judge_model = judge_model
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
    
    def get_client(self):
        return openai.OpenAI(
            api_key=self.openrouter_api_key,
            base_url=self.openrouter_base_url
        )
    
    def evaluate_response(self, response_text: str, original_prompt: str, rubric_prompt: str) -> Tuple[Optional[float], str]:
        if not response_text or response_text.startswith("Error:"):
            return 0.0, "Response contains errors"
        
        if not rubric_prompt:
            return None, "No rubric provided"
        
        judge_prompt = f"""You are an expert evaluator. Please evaluate the following response based on the given criteria.

Original Prompt:
{original_prompt}

Response to Evaluate:
{response_text}

Evaluation Criteria:
{rubric_prompt}

Please provide:
1. A score from 0.0 to 1.0 (where 1.0 is perfect)
2. Your reasoning for this score

Format your response as JSON:
{{
    "score": 0.85,
    "reasoning": "Your detailed explanation here..."
}}"""

        try:
            client = self.get_client()
            response = client.chat.completions.create(
                model=self.judge_model,
                messages=[{"role": "user", "content": judge_prompt}],
                max_tokens=500,
                temperature=0.1
            )
            
            judge_response = response.choices[0].message.content
            
            try:
                result = json.loads(judge_response)
                score = float(result.get("score", 0.0))
                reasoning = result.get("reasoning", "No reasoning provided")
                
                score = max(0.0, min(1.0, score))
                return score, reasoning
                
            except (json.JSONDecodeError, ValueError):
                score_match = re.search(r'"?score"?\s*:\s*([0-9]*\.?[0-9]+)', judge_response)
                if score_match:
                    score = float(score_match.group(1))
                    score = max(0.0, min(1.0, score))
                    return score, judge_response
                else:
                    return None, f"Could not parse judge response: {judge_response}"
                    
        except Exception as e:
            return None, f"Error during evaluation: {str(e)}"

class TextEvaluator:
    @staticmethod
    def evaluate_response(response_text: str, expected_output: str = None, criteria: str = None) -> Optional[float]:
        if not response_text or response_text.startswith("Error:"):
            return 0.0
        
        if expected_output:
            if response_text.strip().lower() == expected_output.strip().lower():
                return 1.0
            else:
                return 0.0
        
        return len(response_text) / 1000.0

class VisionEvaluator:
    @staticmethod
    def evaluate_response(response_text: str, expected_output: str = None, criteria: str = None) -> Optional[float]:
        return None

class AgentEvaluator:
    @staticmethod
    def evaluate_response(response_text: str, expected_output: str = None, criteria: str = None) -> Optional[float]:
        return None

def get_evaluator(eval_type: str):
    evaluators = {
        "text": TextEvaluator,
        "vision": VisionEvaluator,
        "agent": AgentEvaluator
    }
    return evaluators.get(eval_type, TextEvaluator)
