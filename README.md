# LLM Benchmarking Tool

A comprehensive web-based tool for benchmarking and evaluating Large Language Models (LLMs) across different types (text, vision, agent) with automated scoring and detailed analytics.

## Quick Start

### Prerequisites
- Python 3.8+
- Required API keys (see Environment Setup)

### Installation
```bash
# Clone the repository
git clone https://github.com/AndrewMead10/benchmarking-llms
cd benchmarking-llms

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (see Environment Setup below)
# Start the application
cd app
python main.py
```

The application will be available at `http://localhost:7543`

### Environment Setup
Create a `.env` file or set environment variables:

```bash
# Required: Default API key for OpenRouter
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional: Custom API keys for specific models
# CUSTOM_MODEL_API_KEY=your_custom_key_here
```

## Web Interface Guide

### Dashboard (`/`)
**What it shows:** Overview of your benchmarking system
- **Statistics cards:** Total prompts, models, benchmark suites, and costs
- **Performance chart:** Bar chart comparing average scores across models
- **Queue management:** Current running/pending benchmark jobs
- **Quick actions:** Queue new benchmark runs, rerun outdated prompts

**Expected output:** Real-time metrics and ability to queue new benchmarks

### Prompts Page (`/prompts`)
**What it shows:** Management of evaluation prompts
- **Prompt cards:** All created prompts with type and creation date
- **Create new prompts:** Modal form for adding prompts with evaluation rubrics
- **Status indicators:** Shows which prompts need to be rerun

**Expected output:** 
- List of all prompts you've created
- Ability to create new prompts with custom evaluation criteria
- Visual indication of prompts requiring re-evaluation

### Prompt Detail Page (`/prompts/{id}`)
**What it shows:** Detailed view of a specific prompt
- **Current version:** Latest prompt content and evaluation rubric
- **Revision history:** All versions with ability to revert
- **Model rankings:** Performance comparison of all models on this prompt
- **Edit capabilities:** Create new revisions while maintaining history

**Expected output:**
- Complete prompt details and evaluation criteria
- Historical performance data showing which models perform best
- Ability to modify prompts and track changes over time

### Models Page (`/models`)
**What it shows:** Management of LLM models
- **Model cards:** All registered models with type and run counts
- **Add new models:** Form for registering models with custom API endpoints
- **Evaluation triggers:** Quick evaluation buttons for untested models

**Expected output:**
- List of all available models for benchmarking
- Ability to add custom models with specific API configurations
- Quick access to start evaluations

### Model Detail Page (`/models/{id}`)
**What it shows:** Detailed performance analysis for a specific model
- **Configuration:** API settings and model type information
- **Performance stats:** Average scores, costs, and token usage
- **Benchmark results:** Detailed table of all runs with filtering
- **Individual responses:** View actual model outputs and evaluations

**Expected output:**
- Comprehensive model performance metrics
- Detailed breakdown of how the model performs on different prompts
- Access to raw model responses and scoring details

### Results & Analytics Page (`/results`)
**What it shows:** Comprehensive analytics and data export
- **Comparison charts:** Interactive charts comparing models across different metrics
- **Filtering options:** Filter by evaluation type, specific prompts, or date ranges
- **Cost analysis:** Pie chart showing cost distribution across models
- **Token usage:** Bar chart showing average token consumption
- **Detailed results table:** All benchmark suites with export functionality

**Expected output:**
- Visual analytics comparing model performance
- Cost and efficiency analysis
- Exportable data for further analysis
- Filterable views for specific comparisons

## How to Use the Tool

### 1. Set Up Models
1. Go to `/models`
2. Click "Add New Model"
3. Enter the exact model name (e.g., `gpt-4`, `claude-3-opus`)
4. Select model type (text, vision, or agent)
5. Optionally configure custom API endpoint and key

### 2. Create Evaluation Prompts
1. Go to `/prompts`
2. Click "Create New Prompt"
3. Write your prompt content
4. Define evaluation rubric (how responses should be scored)
5. Select appropriate model type

### 3. Run Benchmarks
1. From the dashboard, click "Queue New Run"
2. Select a prompt and one or more models
3. Choose a judge model for evaluation
4. The system will queue and process runs automatically

### 4. Analyze Results
1. View real-time progress on the dashboard
2. Check individual model performance on model detail pages
3. Compare models on specific prompts via prompt detail pages
4. Use the results page for comprehensive analytics

## Key Features

### Automated Evaluation
- **LLM Judge System:** Uses one model to evaluate another's responses
- **Custom Rubrics:** Define specific evaluation criteria for each prompt
- **Multiple Metrics:** Tracks scores, costs, tokens, and runtime

### Version Control
- **Prompt Versioning:** Track changes to prompts over time
- **Revert Capability:** Roll back to previous prompt versions
- **Change Tracking:** Automatic flagging when prompts need re-evaluation

### Queue System
- **Background Processing:** Runs up to 5 concurrent evaluations
- **Status Tracking:** Real-time updates on job progress
- **Automatic Retry:** Handles failures and retries

### Cost Tracking
- **Per-Run Costs:** Detailed cost breakdown for each evaluation
- **Model Comparison:** Compare efficiency across different models
- **Budget Monitoring:** Track total spending over time

## Understanding Output

### Scores
- Displayed as percentages (0-100%)
- Based on LLM judge evaluation using your rubric
- Higher scores indicate better performance according to your criteria

### Status Indicators
- **Completed:** Benchmark finished successfully
- **Running:** Currently being processed
- **Failed:** Encountered an error (will retry automatically)
- **Needs Rerun:** Prompt was modified, existing results may be outdated

### Charts and Analytics
- **Performance Charts:** Compare average scores across models
- **Cost Analysis:** Understand spending patterns
- **Token Usage:** Monitor efficiency and resource consumption

## Troubleshooting

### Common Issues
1. **"Model not found" errors:** Verify the exact model name matches the API provider's specification
2. **API key errors:** Check environment variables and model-specific API key settings
3. **Evaluation failures:** Ensure judge model has access and rubric is clear

### Performance Tips
- Use smaller, faster models as judges for routine evaluations
- Batch multiple models in single runs for efficiency
- Monitor costs when using expensive models repeatedly

The tool automatically creates the SQLite database on first run, so no manual database setup is required.
