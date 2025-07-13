from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import asyncio
import logging

from .database.database import engine, get_db
from .database import models, crud
from .pages.routes import router as pages_router
from .benchmark.runner import BenchmarkRunner
from .benchmark.evaluator import get_evaluator

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
                for item in pending_items[:1]:
                    await process_queue_item(item.id, db)
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
        judge_model = queue_item.judge_model
        
        model_config = {
            "api_endpoint": model.api_endpoint,
            "api_key_name": model.api_key_name
        }
        
        response_text, input_tokens, output_tokens, cost_usd, run_time_ms = benchmark_runner.run_benchmark(
            prompt_revision.content,
            model.name,
            model_config
        )
        
        evaluator = get_evaluator(model.model_type.name)()
        
        judge_reasoning = None
        judge_tokens = 0
        judge_cost_usd = 0.0
        judge_time_ms = 0
        
        if judge_model and prompt_revision.prompt.rubric:
            judge_config = {
                "api_endpoint": judge_model.api_endpoint,
                "api_key_name": judge_model.api_key_name
            }
            score, judge_reasoning, judge_tokens, judge_cost_usd, judge_time_ms = evaluator.evaluate_response(
                response_text,
                prompt_revision.content,
                prompt_revision.prompt.rubric,
                judge_model.name,
                judge_config
            )
        else:
            score, judge_reasoning, judge_tokens, judge_cost_usd, judge_time_ms = evaluator.evaluate_response(response_text)
        
        crud.create_benchmark_run(
            db,
            prompt_revision.id,
            model.id,
            response_text,
            input_tokens,
            output_tokens,
            cost_usd,
            run_time_ms,
            score,
            None,  # run_metadata
            judge_model.id if judge_model else None,
            judge_reasoning,
            judge_tokens,
            judge_cost_usd,
            judge_time_ms
        )
        
        crud.mark_revision_as_run(db, prompt_revision.id)
        
        queue_item.status = "completed"
        queue_item.completed_at = models.func.now()
        db.commit()
        
        logger.info(f"Completed benchmark run for model {model.name} on prompt {prompt_revision.prompt.name}")
        
    except Exception as e:
        logger.error(f"Error processing queue item {queue_item_id}: {e}")
        if queue_item:
            queue_item.status = "failed"
            queue_item.completed_at = models.func.now()
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
        "model_name": run.model.name
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
        models.func.avg(models.BenchmarkRun.score).label('avg_score'),
        models.func.sum(models.BenchmarkRun.cost_usd).label('total_cost'),
        models.func.sum(models.BenchmarkRun.input_tokens + models.BenchmarkRun.output_tokens).label('total_tokens')
    ).join(models.BenchmarkRun).join(models.PromptRevision).join(models.Prompt)
    
    if eval_type:
        query = query.filter(models.Prompt.model_type_id == eval_type)
    if prompt_id:
        query = query.filter(models.Prompt.id == prompt_id)
    if days:
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        query = query.filter(models.BenchmarkRun.created_at >= cutoff_date)
    
    results = query.group_by(models.Model.id).all()
    
    return {
        "model_names": [r.name for r in results],
        "average_scores": [float(r.avg_score) if r.avg_score else 0 for r in results],
        "total_costs": [float(r.total_cost) if r.total_cost else 0 for r in results],
        "total_tokens": [int(r.total_tokens) if r.total_tokens else 0 for r in results]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)