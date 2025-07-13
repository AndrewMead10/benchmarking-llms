from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
import json

from database.database import get_db
from database import crud, models
from benchmark.runner import BenchmarkRunner
from benchmark.evaluator import get_evaluator

router = APIRouter()
templates = Jinja2Templates(directory="templates")
benchmark_runner = BenchmarkRunner()

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    stats = {
        "total_prompts": db.query(models.Prompt).filter(models.Prompt.is_active == True).count(),
        "total_models": db.query(models.Model).filter(models.Model.is_active == True).count(),
        "total_runs": db.query(models.BenchmarkRun).count(),
        "total_cost": db.query(func.sum(models.BenchmarkRun.cost_usd)).scalar() or 0.0
    }
    
    prompts_needing_rerun = crud.get_prompts_needing_rerun(db)
    queue_items = crud.get_queue_items(db)[:10]
    prompts = crud.get_prompts(db)
    models_list = crud.get_models(db)
    
    model_performance = db.query(
        models.Model.name,
        func.avg(models.BenchmarkRun.score).label('avg_score')
    ).join(models.BenchmarkRun).group_by(models.Model.id).all()
    
    chart_data = {
        "labels": [mp.name for mp in model_performance],
        "scores": [float(mp.avg_score) if mp.avg_score else 0 for mp in model_performance]
    }
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "prompts_needing_rerun": prompts_needing_rerun,
        "queue_items": queue_items,
        "prompts": prompts,
        "models": models_list,
        "chart_data": chart_data
    })

@router.get("/prompts", response_class=HTMLResponse)
async def prompts_page(request: Request, db: Session = Depends(get_db)):
    prompts = crud.get_prompts(db)
    model_types = crud.get_model_types(db)
    
    return templates.TemplateResponse("prompts.html", {
        "request": request,
        "prompts": prompts,
        "model_types": model_types
    })

@router.get("/prompts/{prompt_id}", response_class=HTMLResponse)
async def prompt_detail(request: Request, prompt_id: int, db: Session = Depends(get_db)):
    prompt = crud.get_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    current_revision = crud.get_current_prompt_revision(db, prompt_id)
    revisions = crud.get_prompt_revisions(db, prompt_id)
    benchmark_runs = crud.get_benchmark_runs(db, prompt_id=prompt_id)
    
    compatible_models = db.query(models.Model).filter(
        models.Model.model_type_id == prompt.model_type_id,
        models.Model.is_active == True
    ).all()
    
    all_models = crud.get_models(db)
    
    total_runs = len(benchmark_runs)
    total_cost = sum(run.cost_usd for run in benchmark_runs)
    
    return templates.TemplateResponse("prompt_detail.html", {
        "request": request,
        "prompt": prompt,
        "current_revision": current_revision,
        "revisions": revisions,
        "benchmark_runs": benchmark_runs,
        "models": compatible_models,
        "all_models": all_models,
        "total_runs": total_runs,
        "total_cost": total_cost
    })

@router.get("/models", response_class=HTMLResponse)
async def models_page(request: Request, db: Session = Depends(get_db)):
    models_list = crud.get_models(db)
    model_types = crud.get_model_types(db)
    
    return templates.TemplateResponse("models.html", {
        "request": request,
        "models": models_list,
        "model_types": model_types
    })

@router.get("/models/{model_id}", response_class=HTMLResponse)
async def model_detail(request: Request, model_id: int, db: Session = Depends(get_db)):
    model = crud.get_model(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    benchmark_runs = crud.get_benchmark_runs(db, model_id=model_id)
    
    compatible_prompts = db.query(models.Prompt).filter(
        models.Prompt.model_type_id == model.model_type_id,
        models.Prompt.is_active == True
    ).all()
    
    total_runs = len(benchmark_runs)
    total_cost = sum(run.cost_usd for run in benchmark_runs)
    total_tokens = sum(run.input_tokens + run.output_tokens for run in benchmark_runs)
    average_score = sum(run.score for run in benchmark_runs if run.score) / len([r for r in benchmark_runs if r.score]) if benchmark_runs else None
    
    return templates.TemplateResponse("model_detail.html", {
        "request": request,
        "model": model,
        "benchmark_runs": benchmark_runs,
        "prompts": compatible_prompts,
        "total_runs": total_runs,
        "total_cost": total_cost,
        "total_tokens": total_tokens,
        "average_score": average_score
    })

@router.get("/results", response_class=HTMLResponse)
async def results_page(request: Request, db: Session = Depends(get_db)):
    benchmark_runs = db.query(models.BenchmarkRun).order_by(models.BenchmarkRun.created_at.desc()).limit(100).all()
    model_types = crud.get_model_types(db)
    prompts = crud.get_prompts(db)
    
    model_stats = db.query(
        models.Model.name,
        func.avg(models.BenchmarkRun.score).label('avg_score'),
        func.sum(models.BenchmarkRun.cost_usd).label('total_cost'),
        func.sum(models.BenchmarkRun.input_tokens + models.BenchmarkRun.output_tokens).label('total_tokens')
    ).join(models.BenchmarkRun).group_by(models.Model.id).all()
    
    chart_data = {
        "model_names": [ms.name for ms in model_stats],
        "average_scores": [float(ms.avg_score) if ms.avg_score else 0 for ms in model_stats],
        "total_costs": [float(ms.total_cost) if ms.total_cost else 0 for ms in model_stats],
        "total_tokens": [int(ms.total_tokens) if ms.total_tokens else 0 for ms in model_stats]
    }
    
    return templates.TemplateResponse("results.html", {
        "request": request,
        "benchmark_runs": benchmark_runs,
        "model_types": model_types,
        "prompts": prompts,
        "chart_data": chart_data
    })

@router.post("/api/prompts")
async def create_prompt(
    name: str = Form(...),
    model_type_id: int = Form(...),
    content: str = Form(...),
    rubric_prompt: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    crud.create_prompt(db, name, model_type_id, content, rubric_prompt)
    return RedirectResponse(url="/prompts", status_code=303)

@router.post("/api/prompts/{prompt_id}/revisions")
async def create_prompt_revision(
    prompt_id: int,
    content: str = Form(...),
    rubric_prompt: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    crud.create_prompt_revision(db, prompt_id, content, rubric_prompt)
    return RedirectResponse(url=f"/prompts/{prompt_id}", status_code=303)

@router.post("/api/models")
async def create_model(
    name: str = Form(...),
    model_type_id: int = Form(...),
    api_endpoint: Optional[str] = Form(None),
    api_key_name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    crud.create_model(db, name, model_type_id, api_endpoint, api_key_name)
    return RedirectResponse(url="/models", status_code=303)

@router.post("/api/queue-run")
async def queue_run(
    prompt_id: int = Form(...),
    model_ids: List[int] = Form(...),
    judge_model_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    current_revision = crud.get_current_prompt_revision(db, prompt_id)
    if not current_revision:
        raise HTTPException(status_code=404, detail="No current revision found for prompt")
    
    judge_model_name = None
    judge_base_url = None
    
    if judge_model_id:
        judge_model = crud.get_model(db, judge_model_id)
        if judge_model:
            judge_model_name = judge_model.name
            judge_base_url = judge_model.api_endpoint
    
    for model_id in model_ids:
        crud.add_to_queue(db, model_id, current_revision.id, judge_model_name, judge_base_url)
    
    return RedirectResponse(url="/", status_code=303)

@router.post("/api/rerun-prompt/{prompt_id}")
async def rerun_prompt(prompt_id: int, db: Session = Depends(get_db)):
    current_revision = crud.get_current_prompt_revision(db, prompt_id)
    if not current_revision:
        raise HTTPException(status_code=404, detail="No current revision found")
    
    prompt = crud.get_prompt(db, prompt_id)
    compatible_models = db.query(models.Model).filter(
        models.Model.model_type_id == prompt.model_type_id,
        models.Model.is_active == True
    ).all()
    
    for model in compatible_models:
        crud.add_to_queue(db, model.id, current_revision.id)
    
    return RedirectResponse(url=f"/prompts/{prompt_id}", status_code=303)

@router.post("/api/rerun-prompt-with-judge")
async def rerun_prompt_with_judge(
    prompt_id: int = Form(...),
    judge_model_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    current_revision = crud.get_current_prompt_revision(db, prompt_id)
    if not current_revision:
        raise HTTPException(status_code=404, detail="No current revision found")
    
    prompt = crud.get_prompt(db, prompt_id)
    compatible_models = db.query(models.Model).filter(
        models.Model.model_type_id == prompt.model_type_id,
        models.Model.is_active == True
    ).all()
    
    judge_model_name = None
    judge_base_url = None
    
    if judge_model_id:
        judge_model = crud.get_model(db, judge_model_id)
        if judge_model:
            judge_model_name = judge_model.name
            judge_base_url = judge_model.api_endpoint
    
    for model in compatible_models:
        crud.add_to_queue(db, model.id, current_revision.id, judge_model_name, judge_base_url)
    
    return RedirectResponse(url=f"/prompts/{prompt_id}", status_code=303)

@router.post("/api/evaluate-model/{model_id}")
async def evaluate_model(model_id: int, db: Session = Depends(get_db)):
    model = crud.get_model(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    compatible_prompts = db.query(models.Prompt).filter(
        models.Prompt.model_type_id == model.model_type_id,
        models.Prompt.is_active == True
    ).all()
    
    for prompt in compatible_prompts:
        current_revision = crud.get_current_prompt_revision(db, prompt.id)
        if current_revision:
            crud.add_to_queue(db, model.id, current_revision.id)
    
    return RedirectResponse(url=f"/models/{model_id}", status_code=303)

@router.post("/api/evaluate-model-with-judge")
async def evaluate_model_with_judge(
    model_id: int = Form(...),
    judge_model_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    model = crud.get_model(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    judge_model_name = None
    judge_base_url = None
    
    if judge_model_id:
        judge_model = crud.get_model(db, judge_model_id)
        if judge_model:
            judge_model_name = judge_model.name
            judge_base_url = judge_model.api_endpoint
    
    compatible_prompts = db.query(models.Prompt).filter(
        models.Prompt.model_type_id == model.model_type_id,
        models.Prompt.is_active == True
    ).all()
    
    for prompt in compatible_prompts:
        current_revision = crud.get_current_prompt_revision(db, prompt.id)
        if current_revision:
            crud.add_to_queue(db, model.id, current_revision.id, judge_model_name, judge_base_url)
    
    return RedirectResponse(url="/models", status_code=303)
