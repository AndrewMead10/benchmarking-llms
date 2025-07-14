from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import asyncio
import logging

from database.database import engine, get_db
from database import models, crud
from pages.routes import router as pages_router
from benchmark.runner import BenchmarkRunner
from benchmark.evaluator import get_evaluator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    
    db = next(get_db())
    try:
        if not crud.get_model_types(db):
            crud.create_model_type(db, "text", "Text-based language models")
            crud.create_model_type(db, "vision", "Vision-capable models")
            crud.create_model_type(db, "agent", "Agent-capable models")
            logger.info("Created default model types")
    except Exception as e:
        logger.error(f"Error creating model types: {e}")
    finally:
        db.close()
    
    asyncio.create_task(queue_processor())
    yield

app = FastAPI(
    title="LLM Benchmarking Tool",
    description="A tool for benchmarking and comparing LLM performance",
    version="1.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(pages_router)

benchmark_runner = BenchmarkRunner()

async def queue_processor():
    while True:
        try:
            db = next(get_db())
            try:
                pending_items = crud.get_queue_items(db, "pending")
                # Process up to 5 items concurrently
                batch_items = pending_items[:5]
                if batch_items:
                    tasks = [process_queue_item(item.id, db) for item in batch_items]
                    await asyncio.gather(*tasks, return_exceptions=True)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in queue processor: {e}")
        
        await asyncio.sleep(5)

async def process_queue_item(queue_item_id: int, db: Session):
    try:
        queue_item = db.query(models.RunQueue).filter(models.RunQueue.id == queue_item_id).first()
        if not queue_item or queue_item.status != "pending":
            return
        
        queue_item.status = "running"
        queue_item.started_at = models.func.now()
        db.commit()
        
        model = queue_item.model
        prompt_revision = queue_item.prompt_revision
        judge_model_name = queue_item.judge_model
        judge_base_url = queue_item.judge_base_url
        
        model_config = {
            "api_endpoint": model.api_endpoint,
            "api_key_name": model.api_key_name
        }
        
        # Create benchmark suite instead of single run
        suite = crud.create_benchmark_suite(db, prompt_revision.id, model.id, run_count=5)
        
        # Run the benchmark suite (5 runs)
        await benchmark_runner.run_benchmark_suite(
            db, suite.id, prompt_revision.content, model.name, model_config, run_count=5
        )
        
        # Score all runs in the suite if judge is available
        if judge_model_name and prompt_revision.rubric_prompt:
            await score_suite_runs(db, suite.id, judge_model_name, judge_base_url, prompt_revision)
        else:
            await score_suite_runs_basic(db, suite.id, model.model_type.name)
        
        # Update suite aggregates after scoring
        benchmark_runner.update_suite_scores(db, suite.id)
        
        crud.mark_revision_as_run(db, prompt_revision.id)
        
        queue_item.status = "completed"
        queue_item.completed_at = models.func.now()
        db.commit()
        
        logger.info(f"Completed benchmark suite for model {model.name} on prompt {prompt_revision.prompt.name}")
        
    except Exception as e:
        logger.error(f"Error processing queue item {queue_item_id}: {e}")
        if queue_item:
            queue_item.status = "failed"
            queue_item.completed_at = models.func.now()
            db.commit()

async def score_suite_runs(db: Session, suite_id: int, judge_model_name: str, judge_base_url: str, prompt_revision):
    """Score all runs in a suite using LLM judge"""
    runs = crud.get_suite_runs(db, suite_id)
    
    if not runs:
        return
    
    try:
        from benchmark.evaluator import LLMJudgeEvaluator
        judge = LLMJudgeEvaluator(judge_model_name, judge_base_url)
        
        evaluation_data = [
            (run.response_text, prompt_revision.content, prompt_revision.rubric_prompt)
            for run in runs
        ]
        
        results = await judge.evaluate_responses_batch(evaluation_data)
        
        for run, (score, judge_reasoning) in zip(runs, results):
            run.score = score if score is not None else 0.0
            run.judge_model = judge_model_name
            run.judge_base_url = judge_base_url
            run.judge_reasoning = judge_reasoning
            
    except Exception as e:
        logger.error(f"Error scoring suite {suite_id}: {e}")
        for run in runs:
            run.score = 0.0
    
    db.commit()

async def score_suite_runs_basic(db: Session, suite_id: int, model_type_name: str):
    """Score all runs in a suite using basic evaluator"""
    runs = crud.get_suite_runs(db, suite_id)
    evaluator = get_evaluator(model_type_name)
    
    for run in runs:
        try:
            score = evaluator.evaluate_response(run.response_text)
            run.score = score
        except Exception as e:
            logger.error(f"Error scoring run {run.id}: {e}")
            run.score = 0.0
    
    db.commit()

@app.get("/api/benchmark-runs/{run_id}")
async def get_benchmark_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(models.BenchmarkRun).filter(models.BenchmarkRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Benchmark run not found")
    
    return {
        "id": run.id,
        "prompt_content": run.prompt_revision.content,
        "response_text": run.response_text,
        "score": run.score,
        "input_tokens": run.input_tokens,
        "output_tokens": run.output_tokens,
        "cost_usd": run.cost_usd,
        "run_time_ms": run.run_time_ms,
        "created_at": run.created_at.isoformat(),
        "model_name": run.model.name,
        "judge_model": run.judge_model,
        "judge_base_url": run.judge_base_url,
        "judge_reasoning": run.judge_reasoning
    }

@app.get("/api/suite-runs/{suite_id}")
async def get_suite_runs(suite_id: int, db: Session = Depends(get_db)):
    suite = crud.get_benchmark_suite(db, suite_id)
    if not suite:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Benchmark suite not found")
    
    runs = crud.get_suite_runs(db, suite_id)
    
    return {
        "suite": {
            "id": suite.id,
            "status": suite.status,
            "run_count": suite.run_count,
            "max_score": suite.max_score,
            "avg_score": suite.avg_score,
            "min_score": suite.min_score,
            "total_cost_usd": suite.total_cost_usd,
            "prompt_name": suite.prompt_revision.prompt.name,
            "model_name": suite.model.name,
            "created_at": suite.created_at.isoformat(),
            "completed_at": suite.completed_at.isoformat() if suite.completed_at else None
        },
        "runs": [
            {
                "id": run.id,
                "run_index": run.run_index,
                "response_text": run.response_text,
                "score": run.score,
                "judge_reasoning": run.judge_reasoning,
                "input_tokens": run.input_tokens,
                "output_tokens": run.output_tokens,
                "cost_usd": run.cost_usd,
                "run_time_ms": run.run_time_ms,
                "created_at": run.created_at.isoformat()
            }
            for run in runs
        ]
    }

@app.get("/api/chart-data")
async def get_chart_data(
    eval_type: int = None,
    prompt_id: int = None,
    days: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(
        models.Model.name,
        models.func.avg(models.BenchmarkSuite.avg_score).label('avg_score'),
        models.func.sum(models.BenchmarkSuite.total_cost_usd).label('total_cost'),
        models.func.avg(models.BenchmarkSuite.avg_input_tokens + models.BenchmarkSuite.avg_output_tokens).label('avg_tokens')
    ).join(models.BenchmarkSuite).join(models.PromptRevision).join(models.Prompt)
    
    if eval_type:
        query = query.filter(models.Prompt.model_type_id == eval_type)
    if prompt_id:
        query = query.filter(models.Prompt.id == prompt_id)
    if days:
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        query = query.filter(models.BenchmarkSuite.created_at >= cutoff_date)
    
    query = query.filter(models.BenchmarkSuite.status == "completed")
    results = query.group_by(models.Model.id).all()
    
    return {
        "model_names": [r.name for r in results],
        "average_scores": [float(r.avg_score) if r.avg_score else 0 for r in results],
        "total_costs": [float(r.total_cost) if r.total_cost else 0 for r in results],
        "avg_tokens": [float(r.avg_tokens) if r.avg_tokens else 0 for r in results]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True, host="0.0.0.0", port=8000)
