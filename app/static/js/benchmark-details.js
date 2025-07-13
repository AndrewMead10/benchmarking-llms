/**
 * Shared component for rendering benchmark run details
 */

function renderBenchmarkRunDetails(data) {
    return `
        <div class="row">
            <div class="col-12 mb-3">
                <h6>Model:</h6>
                <p class="mb-2">${data.model_name}</p>
            </div>
            <div class="col-12 mb-3">
                <h6>Prompt:</h6>
                <pre class="bg-light p-3 border rounded">${data.prompt_content}</pre>
            </div>
            <div class="col-12 mb-3">
                <h6>Response:</h6>
                <pre class="bg-light p-3 border rounded">${data.response_text}</pre>
            </div>
            ${data.judge_reasoning ? `
            <div class="col-12 mb-3">
                <h6>Judge Output:</h6>
                <pre class="bg-light p-3 border rounded">${data.judge_reasoning}</pre>
            </div>
            ` : ''}
            <div class="col-12">
                <h6>Metrics:</h6>
                <div class="row">
                    <div class="col-md-6">
                        <ul class="list-unstyled">
                            <li><strong>Score:</strong> ${data.score ? data.score.toFixed(3) : 'N/A'}</li>
                            <li><strong>Input Tokens:</strong> ${data.input_tokens}</li>
                            <li><strong>Output Tokens:</strong> ${data.output_tokens}</li>
                            <li><strong>Total Tokens:</strong> ${data.input_tokens + data.output_tokens}</li>
                        </ul>
                    </div>
                    <div class="col-md-6">
                        <ul class="list-unstyled">
                            <li><strong>Cost:</strong> $${data.cost_usd.toFixed(4)}</li>
                            <li><strong>Runtime:</strong> ${data.run_time_ms}ms</li>
                            <li><strong>Date:</strong> ${new Date(data.created_at).toLocaleString()}</li>
                            ${data.judge_model ? `<li><strong>Judge Model:</strong> ${data.judge_model}</li>` : ''}
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function showBenchmarkRunDetails(runId, modalId = 'detailsModal', contentId = 'detailsContent') {
    fetch(`/api/benchmark-runs/${runId}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById(contentId).innerHTML = renderBenchmarkRunDetails(data);
            const modal = new bootstrap.Modal(document.getElementById(modalId));
            modal.show();
        })
        .catch(error => {
            console.error('Error loading benchmark run details:', error);
            alert('Error loading details. Please try again.');
        });
}

function renderBenchmarkSuiteDetails(suiteData) {
    const suite = suiteData.suite;
    const runs = suiteData.runs;
    
    let tabsHtml = `
        <ul class="nav nav-tabs" id="suiteDetailTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="overview-tab" data-bs-toggle="tab" data-bs-target="#overview" type="button" role="tab">Overview</button>
            </li>
    `;
    
    runs.forEach((run, index) => {
        tabsHtml += `
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="run${run.run_index}-tab" data-bs-toggle="tab" data-bs-target="#run${run.run_index}" type="button" role="tab">Run ${run.run_index}</button>
            </li>
        `;
    });
    
    tabsHtml += '</ul>';
    
    let contentHtml = `
        <div class="tab-content" id="suiteDetailTabsContent">
            <div class="tab-pane fade show active" id="overview" role="tabpanel">
                <div class="mt-3">
                    <h6>Suite Statistics</h6>
                    <div class="row">
                        <div class="col-md-6">
                            <ul class="list-unstyled">
                                <li><strong>Model:</strong> ${suite.model_name}</li>
                                <li><strong>Prompt:</strong> ${suite.prompt_name}</li>
                                <li><strong>Status:</strong> ${suite.status}</li>
                                <li><strong>Run Count:</strong> ${suite.run_count}</li>
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <ul class="list-unstyled">
                                <li><strong>Max Score:</strong> ${suite.max_score ? (suite.max_score * 100).toFixed(1) + '%' : 'N/A'}</li>
                                <li><strong>Avg Score:</strong> ${suite.avg_score ? (suite.avg_score * 100).toFixed(1) + '%' : 'N/A'}</li>
                                <li><strong>Min Score:</strong> ${suite.min_score ? (suite.min_score * 100).toFixed(1) + '%' : 'N/A'}</li>
                                <li><strong>Total Cost:</strong> $${suite.total_cost_usd ? suite.total_cost_usd.toFixed(4) : 'N/A'}</li>
                            </ul>
                        </div>
                    </div>
                    <h6 class="mt-4">Individual Run Scores</h6>
                    <div class="d-flex gap-2 flex-wrap">
    `;
    
    runs.forEach(run => {
        const scorePercent = run.score ? (run.score * 100).toFixed(1) : 'N/A';
        contentHtml += `<span class="badge bg-primary">Run ${run.run_index}: ${scorePercent}%</span>`;
    });
    
    contentHtml += `
                    </div>
                </div>
            </div>
    `;
    
    runs.forEach(run => {
        contentHtml += `
            <div class="tab-pane fade" id="run${run.run_index}" role="tabpanel">
                <div class="mt-3">
                    ${run.judge_reasoning ? `
                    <div class="mb-3">
                        <h6>Judge Output:</h6>
                        <pre class="bg-light p-3 border rounded">${run.judge_reasoning}</pre>
                    </div>
                    ` : ''}
                    <div class="mb-3">
                        <h6>Response:</h6>
                        <pre class="bg-light p-3 border rounded">${run.response_text}</pre>
                    </div>
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Metrics:</h6>
                            <ul class="list-unstyled">
                                <li><strong>Score:</strong> ${run.score ? (run.score * 100).toFixed(1) + '%' : 'N/A'}</li>
                                <li><strong>Input Tokens:</strong> ${run.input_tokens}</li>
                                <li><strong>Output Tokens:</strong> ${run.output_tokens}</li>
                                <li><strong>Total Tokens:</strong> ${run.input_tokens + run.output_tokens}</li>
                                <li><strong>Cost:</strong> $${run.cost_usd.toFixed(4)}</li>
                                <li><strong>Runtime:</strong> ${run.run_time_ms}ms</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    contentHtml += '</div>';
    
    return tabsHtml + contentHtml;
}

function showBenchmarkSuiteDetails(suiteId, modalId = 'detailsModal', contentId = 'detailsContent') {
    fetch(`/api/suite-runs/${suiteId}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById(contentId).innerHTML = renderBenchmarkSuiteDetails(data);
            const modal = new bootstrap.Modal(document.getElementById(modalId));
            modal.show();
        })
        .catch(error => {
            console.error('Error loading benchmark suite details:', error);
            alert('Error loading details. Please try again.');
        });
}