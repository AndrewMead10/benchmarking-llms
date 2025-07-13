from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class ModelType(Base):
    __tablename__ = "model_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    
    models = relationship("Model", back_populates="model_type")
    prompts = relationship("Prompt", back_populates="model_type")

class Prompt(Base):
    __tablename__ = "prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    model_type_id = Column(Integer, ForeignKey("model_types.id"))
    rubric = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    
    model_type = relationship("ModelType", back_populates="prompts")
    revisions = relationship("PromptRevision", back_populates="prompt")

class PromptRevision(Base):
    __tablename__ = "prompt_revisions"
    
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"))
    content = Column(Text)
    version_number = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(String, default="user")
    is_current = Column(Boolean, default=True)
    needs_rerun = Column(Boolean, default=True)
    
    prompt = relationship("Prompt", back_populates="revisions")
    benchmark_runs = relationship("BenchmarkRun", back_populates="prompt_revision")
    queue_items = relationship("RunQueue", back_populates="prompt_revision")

class Model(Base):
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    model_type_id = Column(Integer, ForeignKey("model_types.id"))
    api_endpoint = Column(String, nullable=True)
    api_key_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    
    model_type = relationship("ModelType", back_populates="models")
    benchmark_runs = relationship("BenchmarkRun", back_populates="model")
    queue_items = relationship("RunQueue", back_populates="model")

class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    prompt_revision_id = Column(Integer, ForeignKey("prompt_revisions.id"))
    model_id = Column(Integer, ForeignKey("models.id"))
    judge_model_id = Column(Integer, ForeignKey("models.id"), nullable=True)
    response_text = Column(Text)
    score = Column(Float, nullable=True)
    judge_reasoning = Column(Text, nullable=True)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    judge_tokens = Column(Integer, default=0)
    cost_usd = Column(Float)
    judge_cost_usd = Column(Float, default=0.0)
    run_time_ms = Column(Integer)
    judge_time_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    run_metadata = Column(JSON, nullable=True)
    
    prompt_revision = relationship("PromptRevision", back_populates="benchmark_runs")
    model = relationship("Model", back_populates="benchmark_runs", foreign_keys=[model_id])
    judge_model = relationship("Model", foreign_keys=[judge_model_id])

class RunQueue(Base):
    __tablename__ = "run_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("models.id"))
    prompt_revision_id = Column(Integer, ForeignKey("prompt_revisions.id"))
    judge_model_id = Column(Integer, ForeignKey("models.id"), nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    model = relationship("Model", back_populates="queue_items", foreign_keys=[model_id])
    prompt_revision = relationship("PromptRevision", back_populates="queue_items")
    judge_model = relationship("Model", foreign_keys=[judge_model_id])