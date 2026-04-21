/**
 * ResultPage — displays per-page detection results with overlay images,
 * slot counts, type summaries, and dynamic type colors.
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import useAppStore from '../store/useAppStore';
import { staticUrl, getReferenceStatus } from '../services/api';

export default function ResultPage() {
  const results = useAppStore((s) => s.results);
  const reset = useAppStore((s) => s.reset);
  const navigate = useNavigate();
  const [typeColors, setTypeColors] = useState({});
  const [expandedPage, setExpandedPage] = useState(null);

  useEffect(() => {
    if (!results) { navigate('/'); return; }
    // Load dynamic type colors
    getReferenceStatus()
      .then((data) => {
        const colors = {};
        for (const t of (data.types || [])) {
          colors[t.type_id] = t.color_hex;
          colors[t.name] = t.color_hex;
        }
        colors['DETECTED'] = '#666666';
        colors['UNKNOWN'] = '#555555';
        setTypeColors(colors);
      })
      .catch(() => {});
  }, [results, navigate]);

  if (!results) return null;

  const pageResults = results.pages || [];

  // Aggregate totals across all pages
  const totals = {};
  let totalSlots = 0;
  pageResults.forEach((pr) => {
    totalSlots += pr.total_slots;
    Object.entries(pr.summary || {}).forEach(([k, v]) => {
      totals[k] = (totals[k] || 0) + v;
    });
  });

  const getColor = (typeKey) => typeColors[typeKey] || '#888888';

  return (
    <div className="result-page">
      {/* Header */}
      <motion.header
        className="result-header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="result-header__title">Detection Results</h1>
        <div className="result-header__actions">
          <button className="btn btn--primary" onClick={() => { reset(); navigate('/'); }}>
            🔄 New Upload
          </button>
        </div>
      </motion.header>

      {/* Summary cards */}
      <motion.div
        className="result-summary"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        <div className="result-summary__card result-summary__card--total">
          <span className="result-summary__number">{totalSlots}</span>
          <span className="result-summary__label">Total Slots</span>
        </div>
        {Object.entries(totals).map(([type, count]) => (
          <div
            key={type}
            className="result-summary__card"
            style={{ borderLeftColor: getColor(type) }}
          >
            <span className="result-summary__number">{count}</span>
            <span className="result-summary__label">{type}</span>
          </div>
        ))}
        <div className="result-summary__card">
          <span className="result-summary__number">{pageResults.length}</span>
          <span className="result-summary__label">Pages Processed</span>
        </div>
      </motion.div>

      {/* Legend */}
      {Object.keys(totals).length > 0 && (
        <motion.div
          className="result-legend"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <span className="result-legend__title">Legend:</span>
          {Object.keys(totals).map((type) => (
            <span key={type} className="result-legend__item">
              <span
                className="result-legend__dot"
                style={{ backgroundColor: getColor(type) }}
              />
              {type}
            </span>
          ))}
        </motion.div>
      )}

      {/* Per-page results */}
      <div className="result-grid">
        {pageResults.map((pr, idx) => (
          <motion.div
            key={pr.page_number}
            className="result-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.08 }}
          >
            <div className="result-card__header">
              <h3>Page {pr.page_number + 1}</h3>
              <span className="result-card__count">{pr.total_slots} slots</span>
            </div>

            {pr.result_image_url && (
              <div
                className="result-card__image"
                onClick={() => setExpandedPage(expandedPage === pr.page_number ? null : pr.page_number)}
                style={{ cursor: 'pointer' }}
              >
                <img
                  src={staticUrl(pr.result_image_url)}
                  alt={`Result for page ${pr.page_number + 1}`}
                  loading="lazy"
                />
              </div>
            )}

            <div className="result-card__summary">
              {Object.entries(pr.summary || {}).map(([type, count]) => (
                <span
                  key={type}
                  className="result-badge"
                  style={{ backgroundColor: getColor(type) }}
                >
                  {type}: {count}
                </span>
              ))}
              {Object.keys(pr.summary || {}).length === 0 && (
                <span className="result-badge result-badge--empty">
                  {pr.total_slots > 0 ? 'Detected (unclassified)' : 'No slots found'}
                </span>
              )}
            </div>

            {pr.slots && pr.slots.length > 0 && (
              <div className="result-card__table-wrapper">
                <table className="result-card__table">
                  <thead>
                    <tr>
                      <th>Slot ID</th>
                      <th>Type</th>
                      <th>Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pr.slots.slice(0, 20).map((slot) => (
                      <tr key={slot.slot_id}>
                        <td className="result-card__slot-id">{slot.slot_id}</td>
                        <td>
                          <span
                            className="result-badge result-badge--sm"
                            style={{ backgroundColor: getColor(slot.parking_type) }}
                          >
                            {slot.parking_type}
                          </span>
                        </td>
                        <td>{(slot.confidence * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                    {pr.slots.length > 20 && (
                      <tr>
                        <td colSpan={3} className="result-card__more">
                          +{pr.slots.length - 20} more slots
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Expanded image modal */}
      {expandedPage !== null && (() => {
        const pr = pageResults.find((p) => p.page_number === expandedPage);
        if (!pr || !pr.result_image_url) return null;
        return (
          <motion.div
            className="result-modal"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            onClick={() => setExpandedPage(null)}
          >
            <motion.div
              className="result-modal__content"
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="result-modal__header">
                <h3>Page {pr.page_number + 1} — {pr.total_slots} slots detected</h3>
                <button
                  className="result-modal__close"
                  onClick={() => setExpandedPage(null)}
                >
                  ✕
                </button>
              </div>
              <img
                src={staticUrl(pr.result_image_url)}
                alt={`Full result for page ${pr.page_number + 1}`}
              />
            </motion.div>
          </motion.div>
        );
      })()}
    </div>
  );
}
