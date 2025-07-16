# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an LLM benchmarking tool built with FastAPI that allows evaluation of language models across different types (text, vision, agent). The application features a web interface for managing prompts, models, and viewing benchmark results with scoring capabilities.

## Key Architecture Components

### Database Layer (`app/database/`)
- **SQLAlchemy ORM** with SQLite backend
- **Models** (`models.py`): Core entities include ModelType, Prompt, PromptRevision, Model, BenchmarkRun, RunQueue
- **CRUD operations** (`crud.py`): Database interaction layer
- **Database connection** (`database.py`): Session management and engine setup

### Benchmarking System (`app/benchmark/`)
- **BenchmarkRunner** (`runner.py`): Executes LLM API calls, supports OpenRouter and custom endpoints
- **Evaluators** (`evaluator.py`): Scoring system with LLMJudgeEvaluator for custom rubrics and basic evaluators for text/vision/agent types
- **Queue Processing**: Asynchronous background task system for running benchmarks

### Web Interface (`app/pages/`)
- **FastAPI routes** (`routes.py`): REST API and HTML endpoints
- **Jinja2 templates** (`templates/`): Dashboard, prompts, models, results pages
- **Static assets** (`static/`): JavaScript and CSS files

### Core Features
- **Prompt Management**: Create, edit, version, and revert prompts with rubric support
- **Model Management**: Register models with different types and API configurations  
- **Queue System**: Background processing of benchmark runs with concurrent execution
- **Scoring**: Automatic evaluation using LLM judges or built-in evaluators
- **Cost Tracking**: Token usage and cost calculation per model/prompt
- **Results Visualization**: Charts and detailed breakdowns of model performance

## Development Commands

### Running the Application
```bash
# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Operations
```bash
# Database tables are automatically created on startup via SQLAlchemy
# No separate migration commands needed - handled in app startup (main.py:19)
```

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Required environment variables:
# OPENROUTER_API_KEY - for default LLM API access
# Custom API keys can be configured per model
```

### Docker Deployment

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### SystemD Service (Arch Linux)

```bash
# Copy service file to systemd directory
sudo cp benchmarking-llms.service /etc/systemd/system/

# Enable and start service
sudo systemctl enable benchmarking-llms.service
sudo systemctl start benchmarking-llms.service

# Check status
sudo systemctl status benchmarking-llms.service

# View logs
sudo journalctl -u benchmarking-llms.service -f
```

## Key Design Patterns

### Prompt Versioning
- Each prompt has multiple revisions with version numbers
- `is_current` flag indicates active revision  
- `needs_rerun` tracks when benchmarks should be re-executed
- Version history allows reverting to previous prompt versions

### Queue-Based Execution
- Background queue processor runs continuously (5-second intervals)
- Processes up to 5 concurrent benchmark runs
- Queue items track status: pending → running → completed/failed
- Automatic retry handling for failed runs

### Model Type System
- Three evaluation types: text, vision, agent
- Models are categorized by type to determine compatible prompts
- Evaluation strategies differ per type (currently only text fully implemented)

### Judge Integration
- Optional LLM judge models for custom evaluation rubrics
- Falls back to built-in evaluators when no judge specified
- Judge responses parsed as JSON with score and reasoning

## File Structure Notes

- `app/main.py` - FastAPI application entry point with lifespan management
- `app/database/models.py` - SQLAlchemy model definitions with relationships
- `app/benchmark/runner.py` - Core benchmarking execution logic
- `app/benchmark/evaluator.py` - Scoring and evaluation implementations
- `app/pages/routes.py` - Web routes and API endpoints
- `templates/` - Jinja2 HTML templates for web interface
- `static/` - Client-side assets (JavaScript charts, CSS)