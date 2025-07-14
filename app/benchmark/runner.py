import openai
import time
import os
import asyncio
import statistics
from typing import Dict, Any, Tuple, List
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database.models import BenchmarkSuite, BenchmarkRun

load_dotenv()

class BenchmarkRunner:
    def __init__(self):
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
    
    def get_client(self, model_config: Dict[str, Any]) -> openai.AsyncOpenAI:
        api_endpoint = model_config.get("api_endpoint")
        api_key_name = model_config.get("api_key_name")
        
        if api_endpoint and api_key_name:
            api_key = os.getenv(api_key_name)
            return openai.AsyncOpenAI(
                api_key=api_key,
                base_url=api_endpoint
            )
        else:
            return openai.AsyncOpenAI(
                api_key=self.openrouter_api_key,
                base_url=self.openrouter_base_url
            )
    
    async def run_benchmark(self, prompt_content: str, model_name: str, model_config: Dict[str, Any]) -> Tuple[str, int, int, float, int]:
        client = self.get_client(model_config)
        
        start_time = time.time()
        
        try:
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt_content}
                ],
                max_tokens=8192,
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
    
    async def run_benchmark_suite(self, db: Session, suite_id: int, prompt_content: str, model_name: str, model_config: Dict[str, Any], run_count: int = 5) -> None:
        """Run a benchmark suite with multiple runs and aggregate results"""
        suite = db.query(BenchmarkSuite).filter(BenchmarkSuite.id == suite_id).first()
        if not suite:
            return
        
        suite.status = "running"
        db.commit()
        
        run_results = []
        
        for run_index in range(1, run_count + 1):
            try:
                response_text, input_tokens, output_tokens, cost_usd, run_time_ms = await self.run_benchmark(
                    prompt_content, model_name, model_config
                )
                
                run_results.append({
                    'response_text': response_text,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'cost_usd': cost_usd,
                    'run_time_ms': run_time_ms,
                    'run_index': run_index
                })
                
            except Exception as e:
                run_results.append({
                    'response_text': f"Error: {str(e)}",
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'cost_usd': 0.0,
                    'run_time_ms': 0,
                    'run_index': run_index
                })
        
        self._save_suite_results(db, suite_id, run_results)

    def _save_suite_results(self, db: Session, suite_id: int, run_results: List[Dict[str, Any]]) -> None:
        """Save individual runs and calculate suite aggregates"""
        suite = db.query(BenchmarkSuite).filter(BenchmarkSuite.id == suite_id).first()
        if not suite:
            return
        
        scores = []
        total_cost = 0.0
        input_tokens_list = []
        output_tokens_list = []
        run_times_list = []
        
        for result in run_results:
            benchmark_run = BenchmarkRun(
                prompt_revision_id=suite.prompt_revision_id,
                model_id=suite.model_id,
                suite_id=suite_id,
                run_index=result['run_index'],
                response_text=result['response_text'],
                input_tokens=result['input_tokens'],
                output_tokens=result['output_tokens'],
                cost_usd=result['cost_usd'],
                run_time_ms=result['run_time_ms']
            )
            db.add(benchmark_run)
            
            total_cost += result['cost_usd']
            input_tokens_list.append(result['input_tokens'])
            output_tokens_list.append(result['output_tokens'])
            run_times_list.append(result['run_time_ms'])
        
        db.commit()
        
        suite.total_cost_usd = total_cost
        suite.avg_input_tokens = statistics.mean(input_tokens_list) if input_tokens_list else 0
        suite.avg_output_tokens = statistics.mean(output_tokens_list) if output_tokens_list else 0
        suite.avg_run_time_ms = statistics.mean(run_times_list) if run_times_list else 0
        suite.status = "completed"
        db.commit()

    def update_suite_scores(self, db: Session, suite_id: int) -> None:
        """Update suite scores after all runs have been scored"""
        runs = db.query(BenchmarkRun).filter(
            BenchmarkRun.suite_id == suite_id,
            BenchmarkRun.score.isnot(None)
        ).all()
        
        if not runs:
            return
        
        scores = [run.score for run in runs]
        
        suite = db.query(BenchmarkSuite).filter(BenchmarkSuite.id == suite_id).first()
        if suite:
            suite.max_score = max(scores)
            suite.avg_score = statistics.mean(scores)
            suite.min_score = min(scores)
            suite.std_dev_score = statistics.stdev(scores) if len(scores) > 1 else 0.0
            db.commit()

    async def run_benchmarks_batch(self, benchmark_data: List[Tuple[str, str, Dict[str, Any]]]) -> List[Tuple[str, int, int, float, int]]:
        """Run multiple benchmarks concurrently, processing up to 5 at a time"""
        semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent requests
        
        async def run_single_benchmark_with_semaphore(prompt_content: str, model_name: str, model_config: Dict[str, Any]):
            async with semaphore:
                return await self.run_benchmark(prompt_content, model_name, model_config)
        
        tasks = []
        for prompt_content, model_name, model_config in benchmark_data:
            task = run_single_benchmark_with_semaphore(prompt_content, model_name, model_config)
            tasks.append(task)
        
        return await asyncio.gather(*tasks)
