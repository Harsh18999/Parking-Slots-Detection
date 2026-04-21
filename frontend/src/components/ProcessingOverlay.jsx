/**
 * ProcessingOverlay — fullscreen modal with animated progress bar,
 * status message, and glassmorphism backdrop.
 */
import { motion, AnimatePresence } from 'framer-motion';
import useAppStore from '../store/useAppStore';

export default function ProcessingOverlay() {
  const status = useAppStore((s) => s.processingStatus);
  const progress = useAppStore((s) => s.progress);
  const message = useAppStore((s) => s.processingMessage);

  const isActive = status === 'pending' || status === 'processing';
  const isFailed = status === 'failed';

  return (
    <AnimatePresence>
      {(isActive || isFailed) && (
        <motion.div
          className="processing-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="processing-card"
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={{ type: 'spring', damping: 20 }}
          >
            {/* Spinning icon or error icon */}
            <div className="processing-card__spinner">
              {isFailed ? (
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="15" y1="9" x2="9" y2="15" />
                  <line x1="9" y1="9" x2="15" y2="15" />
                </svg>
              ) : (
                <svg width="48" height="48" viewBox="0 0 50 50">
                  <circle
                    cx="25"
                    cy="25"
                    r="20"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    strokeDasharray="90 60"
                    strokeLinecap="round"
                  >
                    <animateTransform
                      attributeName="transform"
                      type="rotate"
                      from="0 25 25"
                      to="360 25 25"
                      dur="1s"
                      repeatCount="indefinite"
                    />
                  </circle>
                </svg>
              )}
            </div>

            <h3 className="processing-card__title">
              {isFailed ? 'Processing Failed' : 'Detecting Parking Slots…'}
            </h3>

            {/* Progress bar */}
            {!isFailed && (
              <div className="progress-bar">
                <motion.div
                  className="progress-bar__fill"
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.round(progress)}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
            )}

            <div className="processing-card__stats">
              <span className="processing-card__pct">
                {isFailed ? '✕' : `${Math.round(progress)}%`}
              </span>
              <span className="processing-card__msg">{message}</span>
            </div>

            {isFailed && (
              <button
                className="btn btn--ghost"
                style={{ marginTop: '16px' }}
                onClick={() => useAppStore.getState().updateProgress(0, '', 'idle')}
              >
                Dismiss
              </button>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
