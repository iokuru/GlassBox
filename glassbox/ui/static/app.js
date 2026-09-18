/**
 * GlassBox · CloneForge Spectacular Interactive Frontend Controller
 * - Tab switching
 * - Smooth scroll & scroll-linked parallax regression
 * - Real-time mouse parallax with lerp (0.08 ease factor)
 * - Interactive IntroBlackBox slideshow with word-by-word reveal
 * - Interactive Visual Diff split slider
 * - Web Audio API atmospheric synthesizer
 * - GlassBox Agent runner & live cognition streaming
 */

document.addEventListener('DOMContentLoaded', () => {
  initTabNavigation();
  initMouseParallax();
  initScrollParallax();
  initIntroSlideshow();
  initDiffSlider();
  initAtmosphericAudio();
  initAgentCognitionStudio();
});

/* ==========================================================================
   1. TAB NAVIGATION
   ========================================================================== */
function initTabNavigation() {
  const tabs = document.querySelectorAll('.mode-tab');
  const views = document.querySelectorAll('.tab-view');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      views.forEach(v => v.classList.remove('active'));

      tab.classList.add('active');
      const targetId = tab.getAttribute('data-tab');
      const targetView = document.getElementById(targetId);
      if (targetView) targetView.classList.add('active');

      window.dispatchEvent(new Event('resize'));
    });
  });
}

/* ==========================================================================
   2. REAL-TIME MOUSE PARALLAX WITH LERP (Ease 0.08)
   ========================================================================== */
function initMouseParallax() {
  const landscape = document.getElementById('parallax-bg');
  const eagle = document.getElementById('eagle-bird');
  const fighter = document.getElementById('fighter-jet');
  const drone = document.getElementById('sentinel-drone');

  let mouseX = 0, mouseY = 0;
  let targetX = 0, targetY = 0;
  let currentX = 0, currentY = 0;

  window.addEventListener('mousemove', (e) => {
    const cx = window.innerWidth / 2;
    const cy = window.innerHeight / 2;
    targetX = (e.clientX - cx) / cx;
    targetY = (e.clientY - cy) / cy;
  }, { passive: true });

  function renderLoop() {
    currentX += (targetX - currentX) * 0.08;
    currentY += (targetY - currentY) * 0.08;

    if (landscape) {
      // Invert direction, strength 18px
      landscape.style.transform = `translate3d(${-currentX * 22}px, ${-currentY * 22}px, 0) scale(1.06)`;
    }

    if (eagle) {
      // Follow cursor, strength 12px
      eagle.style.transform = `translate3d(${currentX * 18}px, ${currentY * 18}px, 0)`;
    }

    if (fighter) {
      fighter.style.transform = `translate3d(${-currentX * 14}px, ${-currentY * 10}px, 0)`;
    }

    if (drone) {
      drone.style.transform = `translate3d(${currentX * 12}px, ${currentY * 12}px, 0)`;
    }

    requestAnimationFrame(renderLoop);
  }

  requestAnimationFrame(renderLoop);
}

/* ==========================================================================
   3. SCROLL-LINKED PARALLAX & TYPOGRAPHIC REGRESSION
   ========================================================================== */
function initScrollParallax() {
  const ww3Text = document.getElementById('ww3-text');
  const heroSec = document.getElementById('hero-sec');
  const tankUnit = document.getElementById('tank-unit');

  window.addEventListener('scroll', () => {
    const scrollY = window.scrollY;

    // Formula: scrollY * 0.49 (WW3 parallax) and scale down
    if (ww3Text && heroSec) {
      const heroHeight = heroSec.offsetHeight || 800;
      const progress = Math.min(1, Math.max(0, scrollY / heroHeight));
      const translateY = progress * 40; // 0vh to 40vh
      const scale = 1 - progress * 0.12; // 1 to 0.88
      const opacity = Math.max(0.02, 0.14 - progress * 0.12);

      ww3Text.style.transform = `translate3d(0, ${translateY}vh, 0) scale(${scale})`;
      ww3Text.style.opacity = opacity.toString();
    }

    // Formula: scrollY * -0.07 (Tank parallax)
    if (tankUnit) {
      const tankOffset = (scrollY * 0.08) % 120;
      tankUnit.style.transform = `translate3d(0, ${-tankOffset}px, 0)`;
    }
  }, { passive: true });
}

/* ==========================================================================
   4. INTRO BLACK BOX SLIDESHOW WITH WORD-BY-WORD STAGGER
   ========================================================================== */
const SLIDES_DATA = [
  {
    tag: "01 // SYSTEM DOCTRINE",
    heading: "The war for capital efficiency has begun.",
    body: "Traditional liquidity models bleed equity through slippage, toxic order flow, and opaque routing. Structured protocol decouples state from settlement.",
    stat: "$482M",
    statLabel: "Synthesized Liquidity"
  },
  {
    tag: "02 // KINETIC ROUTING",
    heading: "Deterministic execution without latency penalty.",
    body: "Every swap executes across zero-slippage virtual invariant pools, verified cryptographically before memory-pool broadcast.",
    stat: "1.4ms",
    statLabel: "Finality Drift"
  },
  {
    tag: "03 // SOVEREIGN BALANCE",
    heading: "Autonomous algorithmic asset stabilization.",
    body: "Self-healing collateral ratios adjust within block zero, insulating reserves against systemic cascade failures.",
    stat: "99.98%",
    statLabel: "Invariant Stability"
  }
];

let currentSlideIdx = 0;

function initIntroSlideshow() {
  const dots = document.querySelectorAll('.slide-dot');
  dots.forEach(dot => {
    dot.addEventListener('click', (e) => {
      const idx = parseInt(e.target.getAttribute('data-index'), 10);
      switchSlide(idx);
    });
  });

  // Auto-advance slideshow every 7 seconds
  setInterval(() => {
    const nextIdx = (currentSlideIdx + 1) % SLIDES_DATA.length;
    switchSlide(nextIdx);
  }, 7000);
}

function switchSlide(idx) {
  currentSlideIdx = idx;
  const slide = SLIDES_DATA[idx];
  if (!slide) return;

  // Update dots
  document.querySelectorAll('.slide-dot').forEach((d, i) => {
    d.classList.toggle('active', i === idx);
  });

  // Update tag & stat
  const tagEl = document.getElementById('slide-tag');
  const statEl = document.getElementById('slide-stat');
  const statLabelEl = document.getElementById('slide-stat-label');
  const bodyEl = document.getElementById('slide-body');
  const headingEl = document.getElementById('slide-heading');

  if (tagEl) tagEl.textContent = slide.tag;
  if (statEl) statEl.textContent = slide.stat;
  if (statLabelEl) statLabelEl.textContent = slide.statLabel;

  // Word-by-word heading reveal
  if (headingEl) {
    headingEl.innerHTML = '';
    const words = slide.heading.split(' ');
    words.forEach((w, i) => {
      const span = document.createElement('span');
      span.className = 'word';
      span.textContent = w + ' ';
      span.style.animationDelay = `${i * 0.035}s`;
      headingEl.appendChild(span);
    });
  }

  // Fade body in
  if (bodyEl) {
    bodyEl.style.animation = 'none';
    bodyEl.offsetHeight; // trigger reflow
    bodyEl.textContent = slide.body;
    bodyEl.style.animation = 'fadeIn 0.6s 0.25s var(--ease-standard) forwards';
  }
}

/* ==========================================================================
   5. INTERACTIVE SPLIT-SCREEN VISUAL DIFF SLIDER
   ========================================================================== */
function initDiffSlider() {
  const sliderBox = document.getElementById('diff-slider-box');
  const clonePane = document.getElementById('diff-clone-pane');
  const handle = document.getElementById('slider-handle');

  if (!sliderBox || !clonePane || !handle) return;

  let isDragging = false;

  function updateSlider(clientX) {
    const rect = sliderBox.getBoundingClientRect();
    let x = clientX - rect.left;
    x = Math.max(0, Math.min(x, rect.width));
    const percent = (x / rect.width) * 100;

    clonePane.style.clipPath = `polygon(${percent}% 0, 100% 0, 100% 100%, ${percent}% 100%)`;
    handle.style.left = `${percent}%`;
  }

  sliderBox.addEventListener('mousedown', (e) => {
    isDragging = true;
    updateSlider(e.clientX);
  });

  window.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    updateSlider(e.clientX);
  });

  window.addEventListener('mouseup', () => {
    isDragging = false;
  });

  // Touch support
  sliderBox.addEventListener('touchmove', (e) => {
    if (e.touches.length > 0) {
      updateSlider(e.touches[0].clientX);
    }
  }, { passive: true });
}

/* ==========================================================================
   6. WEB AUDIO ATMOSPHERIC SYNTHESIZER (No external assets required)
   ========================================================================== */
let audioCtx = null;
let isAudioActive = false;
let osc1 = null, osc2 = null, masterGain = null;

function initAtmosphericAudio() {
  const audioBtn = document.getElementById('btn-audio-toggle');
  if (!audioBtn) return;

  audioBtn.addEventListener('click', () => {
    if (!audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      audioCtx = new AudioContext();
    }

    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }

    if (!isAudioActive) {
      startAmbientSynth();
      audioBtn.classList.add('active');
      audioBtn.querySelector('.audio-text').textContent = 'ATMOSPHERE: ACTIVE';
      isAudioActive = true;
    } else {
      stopAmbientSynth();
      audioBtn.classList.remove('active');
      audioBtn.querySelector('.audio-text').textContent = 'ATMOSPHERE: OFF';
      isAudioActive = false;
    }
  });

  // Subtle tactical click sound on hover over Diamond Buttons
  document.querySelectorAll('.diamond-button').forEach(btn => {
    btn.addEventListener('mouseenter', () => {
      if (isAudioActive && audioCtx) {
        playTacticalTick();
      }
    });
  });
}

function startAmbientSynth() {
  if (!audioCtx) return;

  masterGain = audioCtx.createGain();
  masterGain.gain.setValueAtTime(0.08, audioCtx.currentTime);
  masterGain.connect(audioCtx.destination);

  // Sub drone (55Hz - A1)
  osc1 = audioCtx.createOscillator();
  osc1.type = 'sine';
  osc1.frequency.setValueAtTime(55, audioCtx.currentTime);
  osc1.connect(masterGain);
  osc1.start();

  // Shimmer harmonic (110Hz - A2 with gentle detune)
  osc2 = audioCtx.createOscillator();
  osc2.type = 'triangle';
  osc2.frequency.setValueAtTime(110.5, audioCtx.currentTime);

  const filter = audioCtx.createBiquadFilter();
  filter.type = 'lowpass';
  filter.frequency.setValueAtTime(320, audioCtx.currentTime);

  osc2.connect(filter);
  filter.connect(masterGain);
  osc2.start();
}

function stopAmbientSynth() {
  if (masterGain && audioCtx) {
    masterGain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.5);
    setTimeout(() => {
      if (osc1) { osc1.stop(); osc1.disconnect(); }
      if (osc2) { osc2.stop(); osc2.disconnect(); }
    }, 550);
  }
}

function playTacticalTick() {
  if (!audioCtx) return;
  const tickOsc = audioCtx.createOscillator();
  const tickGain = audioCtx.createGain();

  tickOsc.type = 'sine';
  tickOsc.frequency.setValueAtTime(1800, audioCtx.currentTime);
  tickOsc.frequency.exponentialRampToValueAtTime(400, audioCtx.currentTime + 0.04);

  tickGain.gain.setValueAtTime(0.04, audioCtx.currentTime);
  tickGain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.04);

  tickOsc.connect(tickGain);
  tickGain.connect(audioCtx.destination);

  tickOsc.start();
  tickOsc.stop(audioCtx.currentTime + 0.045);
}

/* ==========================================================================
   7. GLASSBOX AGENT COGNITION STUDIO (From original engine)
   ========================================================================== */
const SCENARIOS = {
  fibonacci: {
    task: `def fibonacci(n):
    # Buggy recursive fibonacci causing RecursionError
    return fibonacci(n - 1) + fibonacci(n - 2)

print(fibonacci(10))`,
    fault: null,
  },
  rate_limit: {
    task: `Search web documentation for 'Python recursion limit sys.setrecursionlimit' and patch the failing calculation script.`,
    fault: 'rate_limit',
  },
  stagnation: {
    task: `Investigate why memory allocator fails under repetitive circular buffer increments.`,
    fault: null,
  },
  timeout: {
    task: `import time
while True:
    time.sleep(0.5)`,
    fault: 'timeout',
  }
};

function initAgentCognitionStudio() {
  const scenarioSelect = document.getElementById('scenario-select');
  const taskPrompt = document.getElementById('task-prompt');
  const btnRun = document.getElementById('btn-run');
  const btnCompare = document.getElementById('btn-compare');
  const btnReset = document.getElementById('btn-reset');
  const traceStream = document.getElementById('trace-stream');
  const liveIndicator = document.getElementById('live-indicator');

  if (!scenarioSelect || !taskPrompt || !btnRun) return;

  function loadScenario(key) {
    const sc = SCENARIOS[key];
    if (sc) {
      taskPrompt.value = sc.task;
    }
  }

  scenarioSelect.addEventListener('change', (e) => loadScenario(e.target.value));
  loadScenario('fibonacci');

  btnReset.addEventListener('click', () => {
    loadScenario(scenarioSelect.value);
    traceStream.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⌘</div>
        <p>Select a scenario or launch a task to observe GlassBox's internal thoughts, actions, mind breaks, and self-healing loops.</p>
      </div>`;
  });

  btnRun.addEventListener('click', async () => {
    btnRun.disabled = true;
    btnRun.textContent = 'Running Cognition...';
    liveIndicator.classList.remove('hidden');
    traceStream.innerHTML = '';

    const currentKey = scenarioSelect.value;
    const fault = SCENARIOS[currentKey]?.fault || null;

    try {
      const res = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: taskPrompt.value, fault_type: fault })
      });

      const trace = await res.json();
      renderTraceStream(trace, traceStream);
    } catch (err) {
      traceStream.innerHTML = `<div class="trace-step-card failure"><div class="step-body">Server Error: ${err.message}</div></div>`;
    } finally {
      btnRun.disabled = false;
      btnRun.textContent = 'Run GlassBox Agent';
      liveIndicator.classList.add('hidden');
    }
  });

  if (btnCompare) {
    btnCompare.addEventListener('click', async () => {
      btnCompare.disabled = true;
      btnCompare.textContent = 'Benchmarking...';
      try {
        const res = await fetch('/api/compare', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ task: taskPrompt.value, fault_type: 'rate_limit' })
        });
        const comp = await res.json();
        renderComparisonResults(comp, traceStream);
      } catch (err) {
        traceStream.innerHTML = `<div class="trace-step-card failure"><div class="step-body">Comparison Error: ${err.message}</div></div>`;
      } finally {
        btnCompare.disabled = false;
        btnCompare.textContent = 'Compare vs LangChain Baseline';
      }
    });
  }
}

function renderTraceStream(trace, container) {
  container.innerHTML = '';
  const steps = trace.steps || [];

  if (steps.length === 0) {
    container.innerHTML = '<div class="empty-state"><p>No steps generated.</p></div>';
    return;
  }

  steps.forEach((step, idx) => {
    const card = document.createElement('div');
    const isFail = !!step.failure;
    const isRec = !!step.recovery;
    card.className = `trace-step-card ${isFail ? 'failure' : isRec ? 'recovery' : 'thought'}`;

    let html = `<div class="step-meta"><span>Step ${idx + 1} // ${step.action ? step.action.tool_name : 'REASONING'}</span><span>${(step.duration_ms || 120).toFixed(0)} ms</span></div>`;

    if (step.thought) {
      html += `<div class="step-body" style="color:#a5b4fc;margin-bottom:8px"><strong>Thought:</strong> ${escapeHtml(step.thought.content)}</div>`;
    }

    if (step.action) {
      html += `<div class="step-body" style="color:#fbbf24;margin-bottom:8px"><strong>Action:</strong> ${step.action.tool_name}(${JSON.stringify(step.action.tool_input)})</div>`;
    }

    if (step.observation) {
      html += `<div class="step-body" style="color:#94a3b8;margin-bottom:8px"><strong>Observation:</strong> ${escapeHtml(step.observation.content.slice(0, 300))}</div>`;
    }

    if (step.failure) {
      html += `<div class="step-body" style="color:#f87171;font-weight:600;margin-bottom:8px"><strong>Mind Break [${step.failure.failure_type}]:</strong> ${escapeHtml(step.failure.error_message)}</div>`;
    }

    if (step.recovery) {
      html += `<div class="step-body" style="color:#34d399;font-weight:600"><strong>Self-Heal Recovery [${step.recovery.strategy_applied}]:</strong> ${step.recovery.mutation_details || 'Policy successfully resolved break'}</div>`;
    }

    card.innerHTML = html;
    container.appendChild(card);
  });
}

function renderComparisonResults(comp, container) {
  container.innerHTML = `
    <div class="trace-step-card recovery" style="border-left-width: 4px">
      <div class="step-meta">BENCHMARK COMPARISON</div>
      <div class="step-body" style="font-size:13px;line-height:1.7">
        <strong>GlassBox Result:</strong> Status=${comp.glassbox_trace.status}, Steps=${comp.glassbox_trace.steps.length}, Recoveries=${comp.glassbox_trace.recoveries_count || 1}<br>
        <strong>LangChain Baseline:</strong> Status=${comp.baseline_trace.status}, Steps=${comp.baseline_trace.steps.length}, Failures=${comp.baseline_trace.failures_count || 1}<br>
        <div style="margin-top:8px;padding:8px;background:rgba(0,0,0,0.3);border-radius:4px;color:#38bdf8">
          ${escapeHtml(comp.verdict)}
        </div>
      </div>
    </div>
  `;
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
