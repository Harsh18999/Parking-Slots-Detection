/**
 * SetupPage — drag & drop any number of reference images.
 * Each uploaded image becomes a unique classification type
 * with an auto-generated ID and random color.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  uploadReferencesBatch,
  deleteReference,
  buildEmbeddings,
  getReferenceStatus,
} from '../services/api';

export default function SetupPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [types, setTypes] = useState([]);
  const [isDbReady, setIsDbReady] = useState(false);
  const [dbTypes, setDbTypes] = useState([]);

  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [building, setBuilding] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  // ── Load status ────────────────────────────────────────────────
  const loadStatus = useCallback(async () => {
    try {
      const data = await getReferenceStatus();
      setTypes(data.types || []);
      setIsDbReady(data.embedding_db_initialized);
      setDbTypes(data.embedding_db_types || []);
    } catch (e) {
      console.error('Status load error:', e);
    }
  }, []);

  useEffect(() => { loadStatus(); }, [loadStatus]);

  // ── Upload handlers ────────────────────────────────────────────
  const handleFiles = async (files) => {
    const imageFiles = Array.from(files).filter((f) =>
      /\.(png|jpe?g)$/i.test(f.name)
    );
    if (imageFiles.length === 0) {
      setError('No valid image files (PNG/JPG only).');
      return;
    }

    setUploading(true);
    setError('');
    setMessage('');

    try {
      const result = await uploadReferencesBatch(imageFiles);
      setMessage(`✅ ${result.total} reference image(s) uploaded.`);
      await loadStatus();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (!uploading) handleFiles(e.dataTransfer.files);
  };

  // ── Delete handler ─────────────────────────────────────────────
  const handleDelete = async (typeId) => {
    try {
      await deleteReference(typeId);
      setMessage('Deleted.');
      await loadStatus();
    } catch (e) {
      setError(e.message);
    }
  };

  // ── Build embeddings ───────────────────────────────────────────
  const handleBuild = async () => {
    setBuilding(true);
    setError('');
    setMessage('');
    try {
      const result = await buildEmbeddings();
      if (result.initialized) {
        setMessage(`✅ Embedding DB built! Types: ${result.types.join(', ')}`);
      } else {
        setError('Build failed. Check SageMaker endpoint availability.');
      }
      await loadStatus();
    } catch (e) {
      setError(`Build failed: ${e.message}`);
    } finally {
      setBuilding(false);
    }
  };

  return (
    <div className="setup-page">
      <motion.div
        className="setup-card"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Header */}
        <div className="setup-header">
          <h1>🧠 Model Setup</h1>
          <p className="setup-desc">
            Drop reference images below — each image becomes a classification type
            with a unique ID and random color. Then build the embedding database.
          </p>
        </div>

        {/* Status bar */}
        <div className="setup-status">
          <div className={`status-dot ${isDbReady ? 'status-dot--ok' : 'status-dot--warn'}`} />
          <span>
            Embedding DB: {isDbReady
              ? `Ready (${dbTypes.length} types)`
              : types.length > 0
                ? 'Not built yet — click Build below'
                : 'No images uploaded'}
          </span>
        </div>

        {/* ── Drop Zone ───────────────────────────────────────────── */}
        <div
          className={`setup-dropzone ${isDragging ? 'setup-dropzone--active' : ''} ${uploading ? 'setup-dropzone--disabled' : ''}`}
          onDragOver={(e) => { e.preventDefault(); if (!uploading) setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
          onClick={() => !uploading && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".png,.jpg,.jpeg"
            multiple
            style={{ display: 'none' }}
            onChange={(e) => { handleFiles(e.target.files); e.target.value = ''; }}
          />

          <div className="setup-dropzone__icon">
            {uploading ? '⏳' : isDragging ? '📥' : '🖼️'}
          </div>
          <p className="setup-dropzone__title">
            {uploading
              ? 'Uploading…'
              : isDragging
                ? 'Drop images here'
                : 'Drop reference images or click to browse'}
          </p>
          <p className="setup-dropzone__hint">
            PNG / JPG • Multiple files supported • Each becomes a type
          </p>
        </div>

        {/* ── Uploaded types list ──────────────────────────────────── */}
        {types.length > 0 && (
          <div className="setup-types-list">
            <div className="setup-types-header">
              <h3>Reference Types ({types.length})</h3>
            </div>
            <div className="setup-types-grid">
              <AnimatePresence>
                {types.map((t) => (
                  <motion.div
                    key={t.type_id}
                    className="setup-type-chip"
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    layout
                  >
                    <div
                      className="setup-type-chip__color"
                      style={{ backgroundColor: t.color_hex }}
                    />
                    <div className="setup-type-chip__info">
                      <span className="setup-type-chip__name">{t.name}</span>
                      <span className="setup-type-chip__id">{t.type_id}</span>
                    </div>
                    <span className={`setup-type-chip__badge ${t.has_embedding ? 'setup-type-chip__badge--ok' : ''}`}>
                      {t.has_embedding ? '✓' : '○'}
                    </span>
                    <button
                      className="setup-type-chip__delete"
                      onClick={(e) => { e.stopPropagation(); handleDelete(t.type_id); }}
                      title="Remove"
                    >
                      ✕
                    </button>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        )}

        {/* ── Build button ─────────────────────────────────────────── */}
        <div className="setup-build">
          <motion.button
            className="btn btn--primary btn--lg"
            onClick={handleBuild}
            disabled={types.length === 0 || building}
            whileHover={types.length > 0 && !building ? { scale: 1.02 } : {}}
            whileTap={types.length > 0 && !building ? { scale: 0.98 } : {}}
          >
            {building ? '⏳ Building Embeddings…' : '🧠 Build Embedding Database'}
          </motion.button>
          {types.length === 0 && (
            <p className="setup-hint">Upload at least one reference image to get started.</p>
          )}
        </div>

        {/* Messages */}
        {message && <p className="setup-success">{message}</p>}
        {error && <p className="setup-error">{error}</p>}

        {/* Navigation */}
        <div className="setup-nav">
          <button className="btn btn--ghost" onClick={() => navigate('/')}>
            ← Back
          </button>
          {isDbReady && (
            <motion.button
              className="btn btn--primary"
              onClick={() => navigate('/')}
              whileHover={{ scale: 1.03 }}
            >
              ✅ Ready — Go to Upload
            </motion.button>
          )}
        </div>
      </motion.div>
    </div>
  );
}
