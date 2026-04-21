/**
 * Zustand store — single source of truth for the entire app.
 * Manages: PDF data, processing state, and results.
 * (Annotations removed — detection is automatic.)
 */
import { create } from 'zustand';

const useAppStore = create((set, get) => ({
  // ── PDF State ────────────────────────────────────────────────────
  pdfId: null,
  pages: [],
  currentPage: 0,

  setPdf: (pdfId, pages) => set({ pdfId, pages, currentPage: 0, results: null }),
  setCurrentPage: (page) => set({ currentPage: page }),

  // ── Processing State ─────────────────────────────────────────────
  taskId: null,
  progress: 0,
  processingStatus: 'idle', // idle | pending | processing | completed | failed
  processingMessage: '',

  setProcessing: (taskId) =>
    set({ taskId, progress: 0, processingStatus: 'pending', processingMessage: 'Starting…' }),

  updateProgress: (progress, message, status) =>
    set({ progress, processingMessage: message, processingStatus: status }),

  // ── Results ──────────────────────────────────────────────────────
  results: null,
  setResults: (results) => set({ results, processingStatus: 'completed', progress: 100 }),

  // ── Reset ────────────────────────────────────────────────────────
  reset: () =>
    set({
      pdfId: null,
      pages: [],
      currentPage: 0,
      taskId: null,
      progress: 0,
      processingStatus: 'idle',
      processingMessage: '',
      results: null,
    }),
}));

export default useAppStore;
