/**
 * DropZone — drag-and-drop PDF upload with animated visual feedback.
 */
import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function DropZone({ onFileSelect, disabled }) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  const MAX_SIZE_MB = 50;

  const validateFile = useCallback((file) => {
    if (!file) return 'No file selected';
    if (!file.name.toLowerCase().endsWith('.pdf')) return 'Only PDF files are accepted';
    if (file.size > MAX_SIZE_MB * 1024 * 1024) return `File exceeds ${MAX_SIZE_MB} MB limit`;
    return null;
  }, []);

  const handleFile = useCallback(
    (file) => {
      const err = validateFile(file);
      if (err) {
        setError(err);
        return;
      }
      setError('');
      onFileSelect(file);
    },
    [onFileSelect, validateFile]
  );

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      setIsDragging(false);
      if (disabled) return;
      const file = e.dataTransfer?.files?.[0];
      handleFile(file);
    },
    [disabled, handleFile]
  );

  return (
    <motion.div
      className={`dropzone ${isDragging ? 'dropzone--active' : ''} ${disabled ? 'dropzone--disabled' : ''}`}
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
      whileHover={!disabled ? { scale: 1.01 } : {}}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        style={{ display: 'none' }}
        onChange={(e) => handleFile(e.target.files?.[0])}
      />

      <div className="dropzone__icon">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="12" y1="18" x2="12" y2="12" />
          <polyline points="9 15 12 12 15 15" />
        </svg>
      </div>

      <h3 className="dropzone__title">
        {isDragging ? 'Drop your PDF here' : 'Upload PDF'}
      </h3>
      <p className="dropzone__subtitle">
        Drag & drop or click to browse • Max {MAX_SIZE_MB} MB
      </p>

      <AnimatePresence>
        {error && (
          <motion.p
            className="dropzone__error"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            {error}
          </motion.p>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
