from typing import Optional, Tuple, List
import openai
import os
import json
import re
import asyncio

class LLMJudgeEvaluator:
    def __init__(self, judge_model: str = "gpt-4", judge_base_url: Optional[str] = None):
        self.judge_model = judge_model
        self.judge_base_url = judge_base_url or "https://openrouter.ai/api/v1"
        self.api_key = self._get_api_key()
        self._semaphore = asyncio.Semaphore(5)
    
    def _get_api_key(self):
        if "localhost" in self.judge_base_url or "127.0.0.1" in self.judge_base_url:
            return "dummy"
        return os.getenv("OPENROUTER_API_KEY")
    
    def get_client(self):
        return openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.judge_base_url
        )
    
    async def evaluate_response(self, response_text: str, original_prompt: str, rubric_prompt: str) -> Tuple[Optional[float], str]:
        async with self._semaphore:
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
1. The score for the model's output, based solely on the rubric (do not assign scores not given by the rubric)
2. Your reasoning for this score

Format your response as JSON:
{{
    "score": 0.85,
    "reasoning": "Your detailed explanation here..."
}}"""

            try:
                client = self.get_client()
                response = await client.chat.completions.create(
                    model=self.judge_model,
                    messages=[{"role": "user", "content": judge_prompt}],
                    max_tokens=8192,
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
    
    async def evaluate_responses_batch(self, evaluation_data: List[Tuple[str, str, str]]) -> List[Tuple[Optional[float], str]]:
        """Evaluate multiple responses concurrently"""
        tasks = []
        for response_text, original_prompt, rubric_prompt in evaluation_data:
            task = self.evaluate_response(response_text, original_prompt, rubric_prompt)
            tasks.append(task)
        
        return await asyncio.gather(*tasks)

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
