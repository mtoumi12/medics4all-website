// ============================================================================
// Medics4ALL Core Scribe — frontend logic
// ----------------------------------------------------------------------------
// Single-page app:
//   1. Create a Visit
//   2. Record audio (MediaRecorder)
//   3. Upload the audio (multipart POST)
//   4. Poll /status until pipeline is READY
//   5. Render + edit the SOAP note (debounced PATCH)
//   6. Sign + export
// ============================================================================

const API = '/api/v1';
const POLL_MS = 1500;
const DEBOUNCE_MS = 800;

const state = {
  visitId: null,
  recorder: null,
  chunks: [],
  recording: false,
  startedAt: 0,
  timerHandle: null,
  pollHandle: null,
  noteCache: null,
  saveHandle: null,
  saving: false,
};

// ------------------------- helpers -----------------------------------------
const $ = (id) => document.getElementById(id);

function toast(msg, kind = 'info') {
  const el = $('toast');
  el.textContent = msg;
  el.classList.remove('hidden', 'bg-slate-900', 'bg-emerald-600', 'bg-red-600');
  if (kind === 'success') el.classList.add('bg-emerald-600');
  else if (kind === 'error') el.classList.add('bg-red-600');
  else el.classList.add('bg-slate-900');
  clearTimeout(toast._h);
  toast._h = setTimeout(() => el.classList.add('hidden'), 2800);
}

async function apiJson(method, path, body) {
  const r = await fetch(`${API}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    let msg = r.statusText;
    try {
      const d = await r.json();
      msg = d.detail || msg;
    } catch (_) {}
    throw new Error(`${r.status}: ${msg}`);
  }
  if (r.status === 204) return null;
  return r.json();
}

function fmtTime(ms) {
  const total = Math.floor(ms / 1000);
  const m = String(Math.floor(total / 60)).padStart(2, '0');
  const s = String(total % 60).padStart(2, '0');
  return `${m}:${s}`;
}

function setStepState(step, cls) {
  document.querySelectorAll('.pipeline-step').forEach((el) => {
    if (el.dataset.step === step) {
      el.classList.remove('active', 'done', 'error');
      el.classList.add(cls);
    }
  });
}

function resetPipelineUI() {
  document.querySelectorAll('.pipeline-step').forEach((el) =>
    el.classList.remove('active', 'done', 'error'),
  );
  $('visit-meta').classList.add('hidden');
  $('visit-meta').textContent = '';
}

const STEP_ORDER = ['UPLOADING', 'TRANSCRIBING', 'SUMMARIZING', 'READY'];
function reflectPipelineStatus(status, errorMsg) {
  const upper = (status || '').toUpperCase();
  if (upper === 'ERROR') {
    document.querySelectorAll('.pipeline-step').forEach((el) => {
      if (!el.classList.contains('done')) el.classList.add('error');
    });
    $('visit-meta').classList.remove('hidden');
    $('visit-meta').textContent = `Pipeline error: ${errorMsg || 'unknown'}`;
    $('transcript-pre').textContent = `Pipeline error: ${errorMsg || 'unknown'}`;
    return;
  }
  const idx = STEP_ORDER.indexOf(upper);
  if (idx === -1) return;
  STEP_ORDER.forEach((s, i) => {
    if (i < idx) setStepState(s, 'done');
    else if (i === idx) setStepState(s, upper === 'READY' ? 'done' : 'active');
  });

  // Update transcript section to reflect current pipeline status
  updateTranscriptStatus(upper);
}

function updateTranscriptStatus(status) {
  const statusMessages = {
    'UPLOADING': 'Audio uploaded — processing will begin shortly...',
    'TRANSCRIBING': 'Converting audio to text — this may take a minute...',
    'SUMMARIZING': 'Generating SOAP note from transcript — almost done...',
    'READY': null // Will be handled by loadVisitAndNote()
  };

  const recordStateMessages = {
    'UPLOADING': 'Processing audio upload...',
    'TRANSCRIBING': 'Transcribing audio to text...',
    'SUMMARIZING': 'Generating SOAP note...',
    'READY': null // Will be handled by loadVisitAndNote()
  };

  const message = statusMessages[status];
  const recordMessage = recordStateMessages[status];
  
  if (message) {
    $('transcript-pre').textContent = message;
  }
  if (recordMessage) {
    $('record-state').textContent = recordMessage;
  }
}

// ------------------------- health check ------------------------------------
async function healthCheck() {
  try {
    const h = await apiJson('GET', '/health');
    $('health-pill').classList.remove('hidden');

    let label;
    if (h.mock_pipeline) {
      label = 'Demo mode';
      $('mock-banner').classList.remove('hidden');
    } else if (h.asr_provider === 'local' && h.llm_provider === 'ollama') {
      label = `Local · ${h.asr_model} + ${h.llm_model}`;
    } else if (h.asr_provider === 'openai' && h.llm_provider === 'openai') {
      label = `Cloud · ${h.llm_model}`;
    } else {
      label = `Hybrid · ${h.asr_provider}/${h.llm_provider}`;
    }
    $('health-text').textContent = label;
  } catch (e) {
    $('health-pill').classList.remove('hidden');
    $('health-pill').classList.replace('bg-emerald-600/20', 'bg-red-600/20');
    $('health-text').textContent = 'Backend offline';
  }
}

// ------------------------- Step 1: create visit ----------------------------
$('visit-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = {
    clinician_name: fd.get('clinician_name') || 'Dr. Demo',
    patient_label: fd.get('patient_label') || 'Patient',
    chief_complaint: fd.get('chief_complaint') || null,
  };
  try {
    const v = await apiJson('POST', '/visits', body);
    state.visitId = v.id;
    resetPipelineUI();
    $('recorder-card').classList.remove('opacity-50', 'pointer-events-none');
    $('record-state').textContent = 'Click to start recording';
    $('record-timer').textContent = '00:00';
    $('note-card').classList.add('opacity-50', 'pointer-events-none');
    $('transcript-pre').textContent = 'Visit ready — start recording to begin.';
    toast(`Visit ${v.id.slice(0, 8)} created`, 'success');
  } catch (err) {
    toast(`Could not create visit: ${err.message}`, 'error');
  }
});

// ------------------------- Step 2: recording -------------------------------
$('record-btn').addEventListener('click', async () => {
  if (!state.visitId) {
    toast('Create a visit first', 'error');
    return;
  }
  if (!state.recording) await startRecording();
  else await stopRecording();
});

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm';
    state.recorder = new MediaRecorder(stream, { mimeType: mime });
    state.chunks = [];
    state.recorder.ondataavailable = (ev) => {
      if (ev.data.size) state.chunks.push(ev.data);
    };
    state.recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(state.chunks, { type: mime });
      await uploadAudio(blob);
    };
    state.recorder.start(1000);
    state.recording = true;
    state.startedAt = Date.now();
    $('record-btn').classList.add('recording');
    $('record-state').textContent = 'Recording — click again to stop';
    $('record-icon').innerHTML = '<rect x="6" y="6" width="12" height="12" rx="1.5" />';
    state.timerHandle = setInterval(() => {
      $('record-timer').textContent = fmtTime(Date.now() - state.startedAt);
    }, 250);
  } catch (err) {
    toast(`Mic access denied: ${err.message}`, 'error');
  }
}

async function stopRecording() {
  if (!state.recorder) return;
  state.recorder.stop();
  state.recording = false;
  clearInterval(state.timerHandle);
  $('record-btn').classList.remove('recording');
  $('record-icon').innerHTML =
    '<path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2Z" />';
  $('record-state').textContent = 'Uploading…';
}

// ------------------------- Step 3: upload + poll ---------------------------
async function uploadAudio(blob) {
  if (!state.visitId) return;
  const fd = new FormData();
  fd.append('audio', blob, `visit-${state.visitId}.webm`);

  $('upload-wrap').classList.remove('hidden');
  $('upload-bar').style.width = '0%';
  $('upload-pct').textContent = '0%';

  await new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API}/visits/${state.visitId}/audio`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        $('upload-bar').style.width = pct + '%';
        $('upload-pct').textContent = pct + '%';
      }
    };
    xhr.onload = () => (xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new Error(xhr.statusText)));
    xhr.onerror = () => reject(new Error('Upload failed'));
    xhr.send(fd);
  }).catch((err) => {
    toast(`Upload failed: ${err.message}`, 'error');
  });

  $('upload-label').textContent = 'Upload complete — pipeline running…';
  $('transcript-pre').textContent = 'Audio uploaded — processing will begin shortly...';
  $('record-state').textContent = 'Processing audio upload...';
  startPolling();
}

function startPolling() {
  clearInterval(state.pollHandle);
  state.pollHandle = setInterval(async () => {
    try {
      const s = await apiJson('GET', `/visits/${state.visitId}/status`);
      reflectPipelineStatus(s.status, s.error_message);
      if (s.status === 'ready') {
        clearInterval(state.pollHandle);
        $('upload-wrap').classList.add('hidden');
        await loadVisitAndNote();
      } else if (s.status === 'error') {
        clearInterval(state.pollHandle);
        $('record-state').textContent = `Processing failed: ${s.error_message}`;
        toast(`Pipeline error: ${s.error_message}`, 'error');
      }
    } catch (e) {
      console.error(e);
    }
  }, POLL_MS);
}

// ------------------------- Step 4: render note -----------------------------
async function loadVisitAndNote() {
  const visit = await apiJson('GET', `/visits/${state.visitId}`);
  $('transcript-pre').textContent = visit.transcript || '(no transcript)';

  const note = await apiJson('GET', `/visits/${state.visitId}/note`);
  state.noteCache = note;

  $('cc-field').value = note.chief_complaint || '';
  $('icd-field').value = note.icd10_codes || '';
  $('s-field').value = note.subjective || '';
  $('o-field').value = note.objective || '';
  $('a-field').value = note.assessment || '';
  $('p-field').value = note.plan || '';
  $('meds-field').value = note.medications || '';

  $('note-status').textContent = note.status;
  $('note-card').classList.remove('opacity-50', 'pointer-events-none');
  $('record-state').textContent = 'Processing complete — note ready for review';
  toast('SOAP note ready for review', 'success');
}

// ------------------------- Step 5: edit (debounced PATCH) ------------------
['cc-field', 's-field', 'o-field', 'a-field', 'p-field'].forEach((id) => {
  $(id).addEventListener('input', () => {
    clearTimeout(state.saveHandle);
    $('save-state').textContent = 'Editing…';
    state.saveHandle = setTimeout(saveNote, DEBOUNCE_MS);
  });
});

async function saveNote() {
  if (!state.visitId || state.saving) return;
  state.saving = true;
  $('save-state').textContent = 'Saving…';
  try {
    const updated = await apiJson('PATCH', `/visits/${state.visitId}/note`, {
      chief_complaint: $('cc-field').value,
      subjective: $('s-field').value,
      objective: $('o-field').value,
      assessment: $('a-field').value,
      plan: $('p-field').value,
    });
    state.noteCache = updated;
    $('note-status').textContent = updated.status;
    $('save-state').textContent = `Saved · ${new Date().toLocaleTimeString()}`;
  } catch (err) {
    $('save-state').textContent = `Save failed: ${err.message}`;
  } finally {
    state.saving = false;
  }
}

// ------------------------- Step 6: sign + export ---------------------------
$('sign-btn').addEventListener('click', async () => {
  const signer = prompt('Sign note as:', state.noteCache?.signed_by || 'Dr. Demo');
  if (!signer) return;
  try {
    const updated = await apiJson('POST', `/visits/${state.visitId}/note/sign`, {
      signed_by: signer,
    });
    state.noteCache = updated;
    $('note-status').textContent = updated.status;
    $('sign-btn').disabled = true;
    toast('Note signed', 'success');
  } catch (err) {
    toast(`Sign failed: ${err.message}`, 'error');
  }
});

$('export-btn').addEventListener('click', () => {
  if (!state.visitId) return;
  window.open(`${API}/visits/${state.visitId}/note/export.txt`, '_blank');
});

// ------------------------- bootstrap ---------------------------------------
healthCheck();
