/**
 * UploadPage — landing page with PDF upload + page grid + process controls.
 * After upload, shows page thumbnails and lets users process all or individual pages.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import DropZone from '../components/DropZone';
import ProcessingOverlay from '../components/ProcessingOverlay';
import useAppStore from '../store/useAppStore';
import { uploadPdf } from '../services/api';
import { useProcessing } from '../hooks/useProcessing';
import { staticUrl } from '../services/api';

export default function UploadPage() {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const setPdf = useAppStore((s) => s.setPdf);
  const pdfId = useAppStore((s) => s.pdfId);
  const pages = useAppStore((s) => s.pages);
  const processingStatus = useAppStore((s) => s.processingStatus);
  const reset = useAppStore((s) => s.reset);
  const navigate = useNavigate();
  const { startDocumentProcessing, startPageProcessing } = useProcessing();

  // Navigate to results when processing completes
  useEffect(() => {
    if (processingStatus === 'completed') {
      navigate('/results');
    }
  }, [processingStatus, navigate]);

  const handleFile = async (file) => {
    setUploading(true);
    setError('');

    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => Math.min(prev + 8, 90));
    }, 200);

    try {
      const data = await uploadPdf(file);
      clearInterval(progressInterval);
      setUploadProgress(100);

      setPdf(data.pdf_id, data.pages);

      setTimeout(() => {
        setUploading(false);
        setUploadProgress(0);
      }, 500);
    } catch (e) {
      clearInterval(progressInterval);
      setError(e.message);
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleProcessAll = () => {
    startDocumentProcessing();
  };

  const handleProcessPage = (pageNumber) => {
    startPageProcessing(pageNumber);
  };

  const handleNewUpload = () => {
    reset();
  };

  // ── Upload view (no PDF loaded) ──────────────────────────────────
  if (!pdfId) {
    return (
      <div className="upload-page">
        <motion.div
          className="upload-page__card"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        >
          <div className="upload-page__branding">
            <div className="upload-page__logo">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="7" height="7" rx="1" />
                <rect x="14" y="3" width="7" height="7" rx="1" />
                <rect x="3" y="14" width="7" height="7" rx="1" />
                <rect x="14" y="14" width="7" height="7" rx="1" />
              </svg>
            </div>
            <h1 className="upload-page__title">Parking Slot Detector</h1>
            <p className="upload-page__desc">
              Upload a parking layout PDF and let AI automatically detect
              and classify every parking slot on each page.
            </p>
          </div>

          <DropZone onFileSelect={handleFile} disabled={uploading} />

          {uploading && (
            <motion.div
              className="upload-page__progress"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div className="progress-bar progress-bar--upload">
                <motion.div
                  className="progress-bar__fill"
                  animate={{ width: `${uploadProgress}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
              <span className="upload-page__progress-text">
                {uploadProgress < 100 ? 'Uploading & processing PDF…' : 'Done!'}
              </span>
            </motion.div>
          )}

          {error && (
            <motion.p
              className="upload-page__error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              {error}
            </motion.p>
          )}

          <div className="upload-page__setup-link">
            <button
              className="btn btn--ghost"
              onClick={() => navigate('/setup')}
              style={{ marginTop: '16px' }}
            >
              🔧 Setup Reference Images for Classification
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  // ── Pages view (PDF loaded, ready to process) ────────────────────
  return (
    <div className="pages-view">
      {/* Header */}
      <motion.header
        className="pages-header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="pages-header__left">
          <button className="btn btn--ghost" onClick={handleNewUpload}>
            ← New Upload
          </button>
          <h2 className="pages-header__title">
            {pages.length} Page{pages.length !== 1 ? 's' : ''} Loaded
          </h2>
        </div>
        <div className="pages-header__actions">
          <button
            className="btn btn--ghost"
            onClick={() => navigate('/setup')}
          >
            🔧 Setup
          </button>
          <motion.button
            className="btn btn--primary btn--lg"
            onClick={handleProcessAll}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            🚀 Process All Pages
          </motion.button>
        </div>
      </motion.header>

      {/* Page grid */}
      <motion.div
        className="pages-grid"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        {pages.map((page, idx) => (
          <motion.div
            key={page.page_number}
            className="page-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
          >
            <div className="page-card__image">
              <img
                src={staticUrl(page.preview_url)}
                alt={`Page ${page.page_number + 1}`}
                loading="lazy"
              />
              <div className="page-card__badge">
                Page {page.page_number + 1}
              </div>
            </div>
            <div className="page-card__footer">
              <span className="page-card__dims">
                {page.width} × {page.height}
              </span>
              <motion.button
                className="btn btn--ghost page-card__btn"
                onClick={() => handleProcessPage(page.page_number)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                ▶ Process
              </motion.button>
            </div>
          </motion.div>
        ))}
      </motion.div>

      {/* Processing overlay */}
      <ProcessingOverlay />
    </div>
  );
}
