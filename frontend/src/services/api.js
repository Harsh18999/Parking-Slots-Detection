/**
 * API service — all HTTP calls to the FastAPI backend.
 */

const BASE_URL = 'http://localhost:8000';

/**
 * Upload a PDF file. Returns { pdf_id, total_pages, pages }.
 */
export async function uploadPdf(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${BASE_URL}/upload-pdf`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Upload failed');
  }

  return res.json();
}

/**
 * Process all pages of a PDF. Returns { task_id }.
 */
export async function processDocument(pdfId) {
  const res = await fetch(`${BASE_URL}/process-document`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pdf_id: pdfId }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Processing failed' }));
    throw new Error(err.detail || 'Processing failed');
  }

  return res.json();
}

/**
 * Process a single page of a PDF. Returns { task_id }.
 */
export async function processPage(pdfId, pageNumber) {
  const res = await fetch(`${BASE_URL}/process-page`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pdf_id: pdfId, page_number: pageNumber }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Processing failed' }));
    throw new Error(err.detail || 'Processing failed');
  }

  return res.json();
}

/**
 * Poll processing progress.
 */
export async function getProgress(taskId) {
  const res = await fetch(`${BASE_URL}/progress/${taskId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Progress check failed' }));
    throw new Error(err.detail || 'Progress check failed');
  }
  return res.json();
}

/**
 * Get the final result for a completed task.
 */
export async function getResult(taskId) {
  const res = await fetch(`${BASE_URL}/result/${taskId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Result fetch failed' }));
    throw new Error(err.detail || 'Result fetch failed');
  }
  return res.json();
}

/**
 * Build the full URL for a static image served by the backend.
 */
export function staticUrl(path) {
  if (!path) return '';
  // Data URLs (base64 images) are used directly — no backend prefix needed
  if (path.startsWith('data:')) return path;
  return `${BASE_URL}${path}`;
}

// ── Reference Image Management ─────────────────────────────────────────────

/**
 * Upload multiple reference images in one batch.
 */
export async function uploadReferencesBatch(files) {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }

  const res = await fetch(`${BASE_URL}/upload-references-batch`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Upload failed');
  }

  return res.json();
}

/**
 * Upload a single reference image with an optional label.
 */
export async function uploadReferenceImage(file, label) {
  const formData = new FormData();
  formData.append('file', file);
  if (label) formData.append('label', label);

  const res = await fetch(`${BASE_URL}/upload-reference`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Upload failed');
  }

  return res.json();
}

/**
 * Delete a reference type.
 */
export async function deleteReference(typeId) {
  const res = await fetch(`${BASE_URL}/reference/${typeId}`, { method: 'DELETE' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Delete failed' }));
    throw new Error(err.detail || 'Delete failed');
  }
  return res.json();
}

/**
 * Build embedding database from all uploaded reference images.
 */
export async function buildEmbeddings() {
  const res = await fetch(`${BASE_URL}/build-embeddings`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Build failed' }));
    throw new Error(err.detail || 'Build failed');
  }
  return res.json();
}

/**
 * Get reference image & embedding DB status.
 */
export async function getReferenceStatus() {
  const res = await fetch(`${BASE_URL}/reference-status`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Status check failed' }));
    throw new Error(err.detail || 'Status check failed');
  }
  return res.json();
}

/**
 * Health check.
 */
export async function getHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}
