from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from . import models
from typing import List, Optional

def get_model_types(db: Session):
    return db.query(models.ModelType).all()

def create_model_type(db: Session, name: str, description: str):
    db_model_type = models.ModelType(name=name, description=description)
    db.add(db_model_type)
    db.commit()
    db.refresh(db_model_type)
    return db_model_type

def get_prompts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Prompt).filter(models.Prompt.is_active == True).offset(skip).limit(limit).all()

def get_prompt(db: Session, prompt_id: int):
    return db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()

def create_prompt(db: Session, name: str, model_type_id: int, content: str, rubric_prompt: str = None):
    db_prompt = models.Prompt(name=name, model_type_id=model_type_id)
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    
    db_revision = models.PromptRevision(
        prompt_id=db_prompt.id,
        content=content,
        rubric_prompt=rubric_prompt,
        version_number=1,
        is_current=True,
        needs_rerun=True
    )
    db.add(db_revision)
    db.commit()
    db.refresh(db_revision)
    
    return db_prompt

def create_prompt_revision(db: Session, prompt_id: int, content: str, rubric_prompt: str = None):
    current_revision = db.query(models.PromptRevision).filter(
        and_(models.PromptRevision.prompt_id == prompt_id, models.PromptRevision.is_current == True)
    ).first()
    
    if current_revision:
        current_revision.is_current = False
        new_version = current_revision.version_number + 1
    else:
        new_version = 1
    
    db_revision = models.PromptRevision(
        prompt_id=prompt_id,
        content=content,
        rubric_prompt=rubric_prompt,
        version_number=new_version,
        is_current=True,
        needs_rerun=True
    )
    db.add(db_revision)
    db.commit()
    db.refresh(db_revision)
    
    return db_revision

def get_prompt_revisions(db: Session, prompt_id: int):
    return db.query(models.PromptRevision).filter(
        models.PromptRevision.prompt_id == prompt_id
    ).order_by(desc(models.PromptRevision.version_number)).all()

def get_current_prompt_revision(db: Session, prompt_id: int):
    return db.query(models.PromptRevision).filter(
        and_(models.PromptRevision.prompt_id == prompt_id, models.PromptRevision.is_current == True)
    ).first()

def get_models(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Model).filter(models.Model.is_active == True).offset(skip).limit(limit).all()

def get_model(db: Session, model_id: int):
    return db.query(models.Model).filter(models.Model.id == model_id).first()

def create_model(db: Session, name: str, model_type_id: int, api_endpoint: str = None, api_key_name: str = None):
    db_model = models.Model(
        name=name,
        model_type_id=model_type_id,
        api_endpoint=api_endpoint,
        api_key_name=api_key_name
    )
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model

def get_benchmark_runs(db: Session, prompt_id: int = None, model_id: int = None):
    query = db.query(models.BenchmarkRun)
    if prompt_id:
        query = query.join(models.PromptRevision).filter(models.PromptRevision.prompt_id == prompt_id)
    if model_id:
        query = query.filter(models.BenchmarkRun.model_id == model_id)
    return query.order_by(desc(models.BenchmarkRun.created_at)).all()

def create_benchmark_run(db: Session, prompt_revision_id: int, model_id: int, response_text: str, 
                        input_tokens: int, output_tokens: int, cost_usd: float, run_time_ms: int, 
                        score: float = None, run_metadata: dict = None, judge_model: str = None,
                        judge_base_url: str = None, judge_reasoning: str = None):
    db_run = models.BenchmarkRun(
        prompt_revision_id=prompt_revision_id,
        model_id=model_id,
        judge_model=judge_model,
        judge_base_url=judge_base_url,
        response_text=response_text,
        score=score,
        judge_reasoning=judge_reasoning,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        run_time_ms=run_time_ms,
        run_metadata=run_metadata
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    return db_run

def get_prompts_needing_rerun(db: Session):
    return db.query(models.PromptRevision).filter(
        and_(models.PromptRevision.needs_rerun == True, models.PromptRevision.is_current == True)
    ).all()

def mark_revision_as_run(db: Session, revision_id: int):
    revision = db.query(models.PromptRevision).filter(models.PromptRevision.id == revision_id).first()
    if revision:
        revision.needs_rerun = False
        db.commit()
    return revision

def add_to_queue(db: Session, model_id: int, prompt_revision_id: int, judge_model: str = None, judge_base_url: str = None):
    existing = db.query(models.RunQueue).filter(
        and_(
            models.RunQueue.model_id == model_id,
            models.RunQueue.prompt_revision_id == prompt_revision_id,
            models.RunQueue.status == "pending"
        )
    ).first()
    
    if not existing:
        queue_item = models.RunQueue(
            model_id=model_id, 
            prompt_revision_id=prompt_revision_id,
            judge_model=judge_model,
            judge_base_url=judge_base_url
        )
        db.add(queue_item)
        db.commit()
        db.refresh(queue_item)
        return queue_item
    return existing

def add_to_queue_batch(db: Session, queue_items: List[dict]):
    """Batch add multiple items to queue efficiently"""
    new_items = []
    
    for item in queue_items:
        model_id = item['model_id']
        prompt_revision_id = item['prompt_revision_id']
        judge_model = item.get('judge_model')
        judge_base_url = item.get('judge_base_url')
        
        # Check if item already exists
        existing = db.query(models.RunQueue).filter(
            and_(
                models.RunQueue.model_id == model_id,
                models.RunQueue.prompt_revision_id == prompt_revision_id,
                models.RunQueue.status == "pending"
            )
        ).first()
        
        if not existing:
            queue_item = models.RunQueue(
                model_id=model_id,
                prompt_revision_id=prompt_revision_id,
                judge_model=judge_model,
                judge_base_url=judge_base_url
            )
            new_items.append(queue_item)
    
    if new_items:
        db.add_all(new_items)
        db.commit()
        for item in new_items:
            db.refresh(item)
    
    return new_items

def get_queue_items(db: Session, status: str = None):
    query = db.query(models.RunQueue)
    if status:
        query = query.filter(models.RunQueue.status == status)
    return query.order_by(models.RunQueue.created_at).all()

def create_benchmark_suite(db: Session, prompt_revision_id: int, model_id: int, run_count: int = 5):
    db_suite = models.BenchmarkSuite(
        prompt_revision_id=prompt_revision_id,
        model_id=model_id,
        run_count=run_count,
        status="pending"
    )
    db.add(db_suite)
    db.commit()
    db.refresh(db_suite)
    return db_suite

def get_benchmark_suites(db: Session, prompt_id: int = None, model_id: int = None):
    query = db.query(models.BenchmarkSuite)
    if prompt_id:
        query = query.join(models.PromptRevision).filter(models.PromptRevision.prompt_id == prompt_id)
    if model_id:
        query = query.filter(models.BenchmarkSuite.model_id == model_id)
    return query.order_by(desc(models.BenchmarkSuite.created_at)).all()

def get_benchmark_suite(db: Session, suite_id: int):
    return db.query(models.BenchmarkSuite).filter(models.BenchmarkSuite.id == suite_id).first()

def get_suite_runs(db: Session, suite_id: int):
    return db.query(models.BenchmarkRun).filter(
        models.BenchmarkRun.suite_id == suite_id
    ).order_by(models.BenchmarkRun.run_index).all()

def get_suites_for_results_display(db: Session):
    """Get all completed suites with their related data for results display"""
    return db.query(models.BenchmarkSuite).filter(
        models.BenchmarkSuite.status == "completed"
    ).join(models.PromptRevision).join(models.Model).order_by(
        desc(models.BenchmarkSuite.completed_at)
    ).all()

def get_suites_by_prompt(db: Session, prompt_id: int):
    """Get all completed suites for a specific prompt, ordered by avg_score desc"""
    return db.query(models.BenchmarkSuite).join(models.PromptRevision).filter(
        and_(
            models.PromptRevision.prompt_id == prompt_id,
            models.BenchmarkSuite.status == "completed",
            models.BenchmarkSuite.avg_score.isnot(None)
        )
    ).order_by(desc(models.BenchmarkSuite.avg_score)).all()
