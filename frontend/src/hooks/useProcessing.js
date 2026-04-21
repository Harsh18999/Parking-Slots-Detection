/**
 * useProcessing — custom hook managing the submit → poll → result lifecycle.
 * Supports document-level (all pages) and single-page processing.
 */
import { useCallback, useRef } from 'react';
import useAppStore from '../store/useAppStore';
import { processDocument, processPage, getProgress } from '../services/api';

export function useProcessing() {
  const pdfId = useAppStore((s) => s.pdfId);
  const setProcessing = useAppStore((s) => s.setProcessing);
  const updateProgress = useAppStore((s) => s.updateProgress);
  const setResults = useAppStore((s) => s.setResults);
  const processingStatus = useAppStore((s) => s.processingStatus);

  const pollRef = useRef(null);

  const _startPolling = useCallback(
    (taskId) => {
      pollRef.current = setInterval(async () => {
        try {
          const prog = await getProgress(taskId);
          updateProgress(prog.progress, prog.message, prog.status);

          if (prog.status === 'completed') {
            clearInterval(pollRef.current);
            pollRef.current = null;
            setResults(prog.result);
          } else if (prog.status === 'failed') {
            clearInterval(pollRef.current);
            pollRef.current = null;
            updateProgress(prog.progress, prog.message, 'failed');
          }
        } catch (e) {
          console.error('Progress poll error:', e);
        }
      }, 1000);
    },
    [updateProgress, setResults]
  );

  /**
   * Process all pages of the PDF.
   */
  const startDocumentProcessing = useCallback(async () => {
    try {
      const { task_id } = await processDocument(pdfId);
      setProcessing(task_id);
      _startPolling(task_id);
    } catch (e) {
      updateProgress(0, e.message, 'failed');
    }
  }, [pdfId, setProcessing, updateProgress, _startPolling]);

  /**
   * Process a single page of the PDF.
   */
  const startPageProcessing = useCallback(
    async (pageNumber) => {
      try {
        const { task_id } = await processPage(pdfId, pageNumber);
        setProcessing(task_id);
        _startPolling(task_id);
      } catch (e) {
        updateProgress(0, e.message, 'failed');
      }
    },
    [pdfId, setProcessing, updateProgress, _startPolling]
  );

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  return {
    startDocumentProcessing,
    startPageProcessing,
    stopPolling,
    processingStatus,
  };
}
