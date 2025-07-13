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