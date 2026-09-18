const PRESETS = {
  fibonacci: `Debug and fix the following recursive Fibonacci function that is failing:
\`\`\`python
def fib(n):
    return fib(n - 1) + fib(n - 2)
print(fib(5))
\`\`\``,

  rate_limit: `Search documentation to resolve Python RecursionError with base cases, and test the resulting fix in the sandbox.
\`\`\`python
def fib(n):
    return fib(n - 1) + fib(n - 2)
print(fib(5))
\`\`\``,

  stagnation: `The agent is stuck in an exploratory search loop for an undefined symbol. Break the cycle and implement a standalone factorial solution.
\`\`\`python
def factorial(n):
    return 1 if n <= 1 else n * factorial(n - 1)
print(factorial(5))
\`\`\``,

  timeout: `Execute and debug a blocking while-loop snippet that exceeds subprocess timeout limits.
\`\`\`python
# Infinite loop bug
i = 0
while i < 10:
    pass # missing increment
print(i)
\`\`\``,
};

const elScenario = document.getElementById("scenario-select");
const elTask = document.getElementById("task-prompt");
const elBtnRun = document.getElementById("btn-run");
const elBtnCompare = document.getElementById("btn-compare");
const elBtnReset = document.getElementById("btn-reset");
const elTraceStream = document.getElementById("trace-stream");
const elLiveIndicator = document.getElementById("live-indicator");

const elStatus = document.getElementById("metric-status");
const elSteps = document.getElementById("metric-steps");
const elFailures = document.getElementById("metric-failures");
const elRecoveries = document.getElementById("metric-recoveries");
const elDuration = document.getElementById("metric-duration");

const elComparisonView = document.getElementById("comparison-view");
const elCompGB = document.getElementById("comp-gb-body");
const elCompLC = document.getElementById("comp-lc-body");
const elBtnCloseComp = document.getElementById("btn-close-comparison");

// Set initial scenario
elTask.value = PRESETS.fibonacci;

elScenario.addEventListener("change", (e) => {
  const val = e.target.value;
  elTask.value = PRESETS[val] || "";
});

elBtnReset.addEventListener("click", () => {
  elTraceStream.innerHTML = `
    <div class="empty-state">
      <p>Select a scenario and click <strong>Run GlassBox</strong> to inspect the agent's cognition as it breaks and self-heals.</p>
    </div>
  `;
  elStatus.textContent = "IDLE";
  elStatus.className = "metric-value status-idle";
  elSteps.textContent = "0";
  elFailures.textContent = "0";
  elRecoveries.textContent = "0";
  elDuration.textContent = "0 ms";
  elComparisonView.classList.add("hidden");
});

elBtnCloseComp.addEventListener("click", () => {
  elComparisonView.classList.add("hidden");
});

elBtnRun.addEventListener("click", async () => {
  const task = elTask.value.trim();
  if (!task) return;

  const scenario = elScenario.value;
  let faultType = null;
  if (scenario === "rate_limit") faultType = "rate_limit";
  if (scenario === "timeout") faultType = "timeout";

  elBtnRun.disabled = true;
  elLiveIndicator.classList.remove("hidden");
  elStatus.textContent = "RUNNING";
  elStatus.className = "metric-value status-running";
  elTraceStream.innerHTML = "";

  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task, fault_type: faultType }),
    });

    const data = await res.json();
    renderTrace(data);
  } catch (err) {
    elTraceStream.innerHTML = `<div class="trace-item trace-observation-err"><strong>Error:</strong> ${err.message}</div>`;
    elStatus.textContent = "ERROR";
    elStatus.className = "metric-value status-failed";
  } finally {
    elBtnRun.disabled = false;
    elLiveIndicator.classList.add("hidden");
  }
});

function renderTrace(trace) {
  elStatus.textContent = trace.status.toUpperCase();
  elStatus.className = `metric-value status-${trace.status.toLowerCase()}`;
  elSteps.textContent = trace.steps.length;
  elFailures.textContent = trace.total_failures_encountered;
  elRecoveries.textContent = trace.total_recoveries_applied;
  elDuration.textContent = `${trace.total_duration_ms.toFixed(1)} ms`;

  elTraceStream.innerHTML = "";

  trace.steps.forEach((step) => {
    const stepEl = document.createElement("div");
    stepEl.className = "step-container";

    let html = `
      <div class="step-header">
        <span>Cognitive Step ${step.step_number}</span>
        <span>${step.duration_ms.toFixed(1)} ms</span>
      </div>
      <div class="step-body">
    `;

    // Thought
    if (step.thought) {
      html += `
        <div class="trace-item trace-thought">
          <span class="trace-label">Internal Reasoning (Thought)</span>
          <div>${escapeHtml(step.thought.content)}</div>
        </div>
      `;
    }

    // Action
    if (step.action) {
      html += `
        <div class="trace-item trace-action">
          <span class="trace-label">Proposed Action: ${step.action.tool}</span>
          <pre>${escapeHtml(JSON.stringify(step.action.params, null, 2))}</pre>
        </div>
      `;
    }

    // Failure Detected (Mind Breaking)
    if (step.failure) {
      html += `
        <div class="trace-item trace-mind-break">
          <span class="trace-label">Mind Breaking: Failure Detected [${step.failure.failure_type.toUpperCase()}]</span>
          <div style="font-weight:600; margin-bottom:4px;">Diagnostic: ${escapeHtml(step.failure.description)}</div>
          <div style="font-size:11px; opacity:0.85;">Signature: ${escapeHtml(step.failure.error_signature || "N/A")}</div>
        </div>
      `;
    }

    // Self-Heal Recovery
    if (step.recovery) {
      html += `
        <div class="trace-item trace-self-heal">
          <span class="trace-label">Cognition Self-Heal: Recovery Applied [${step.recovery.strategy.toUpperCase()}]</span>
          <div>${escapeHtml(step.recovery.reason)}</div>
        </div>
      `;
    }

    // Observation
    if (step.observation) {
      const isErr = step.observation.is_error;
      const obsClass = isErr ? "trace-observation-err" : "trace-observation-ok";
      const obsTitle = isErr ? "Observation (Failed / Interrupted)" : "Observation (Success)";
      html += `
        <div class="trace-item ${obsClass}">
          <span class="trace-label">${obsTitle}</span>
          <pre>${escapeHtml(step.observation.content)}</pre>
        </div>
      `;
    }

    html += `</div>`;
    stepEl.innerHTML = html;
    elTraceStream.appendChild(stepEl);
  });

  elTraceStream.scrollTop = elTraceStream.scrollHeight;
}

elBtnCompare.addEventListener("click", async () => {
  const task = elTask.value.trim();
  const scenario = elScenario.value;
  let faultType = null;
  if (scenario === "rate_limit") faultType = "rate_limit";

  elComparisonView.classList.remove("hidden");
  elCompGB.innerHTML = "<p>Running GlassBox...</p>";
  elCompLC.innerHTML = "<p>Running standard ReAct (LangChain baseline)...</p>";

  try {
    const res = await fetch("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task, fault_type: faultType }),
    });

    const data = await res.json();
    const gb = data.glassbox;
    const lc = data.standard_react;

    elCompGB.innerHTML = `
      <p><strong>Status:</strong> <span style="color:var(--green)">${gb.status.toUpperCase()}</span></p>
      <p><strong>Cognitive Steps:</strong> ${gb.steps}</p>
      <p><strong>Failures Classified:</strong> ${gb.failures_detected}</p>
      <p><strong>Self-Healing Recoveries:</strong> ${gb.recoveries_applied}</p>
      <p><strong>Duration:</strong> ${gb.duration_ms.toFixed(1)} ms</p>
      <p style="margin-top:8px; font-size:11px; color:var(--cyan)">
        GlassBox classified the failure into its taxonomy, applied an autonomous strategy redirect, and converged on a verified solution.
      </p>
    `;

    const lcColor = lc.succeeded ? "var(--green)" : "var(--red)";
    elCompLC.innerHTML = `
      <p><strong>Status:</strong> <span style="color:${lcColor}">${lc.succeeded ? "SUCCEEDED" : "FAILED / STALLED"}</span></p>
      <p><strong>Iterations:</strong> ${lc.steps}</p>
      <p><strong>Failures Classified:</strong> ${lc.failures_detected} <em style="color:var(--text-muted)">(Zero taxonomy)</em></p>
      <p><strong>Opaque Errors Hidden:</strong> ${lc.opaque_failures_hidden}</p>
      <p><strong>Terminal Error:</strong> <span style="font-family:monospace; font-size:11px;">${escapeHtml(lc.terminal_error || "None")}</span></p>
      <p style="margin-top:8px; font-size:11px; color:var(--yellow)">
        Standard ReAct black-boxed the failure, failed to adapt arguments or tools, and crashed or ran out of budget.
      </p>
    `;
  } catch (err) {
    elCompGB.innerHTML = `<p class="text-danger">Error: ${err.message}</p>`;
  }
});

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
