/**
 * useViolationBuffer – client-side batch buffer (Sprint 3).
 *
 * Accumulates violations in memory and flushes them to the backend
 * batch endpoint every `flushInterval` ms.  Also handles evidence
 * upload (screenshot → presigned URL → MinIO → object_url attached
 * to the violation record).
 */

import { useRef, useCallback, useEffect } from 'react';
import { proctoringAPI } from '../services/api';
import { captureScreenshot, uploadToPresignedUrl } from '../utils/screenshotCapture';
import logger from '../utils/logger';

const DEFAULT_FLUSH_INTERVAL = 2000; // 2 s – matches backend buffer

/**
 * @param {Object}  opts
 * @param {React.RefObject} opts.webcamRef   – react-webcam ref for screenshots
 * @param {number}  [opts.flushInterval=2000]
 * @param {boolean} [opts.captureEvidence=true]
 */
export default function useViolationBuffer({
  webcamRef,
  flushInterval = DEFAULT_FLUSH_INTERVAL,
  captureEvidence = true,
} = {}) {
  const bufferRef = useRef([]);
  const timerRef = useRef(null);

  // ── Flush buffer to backend ──────────────────────
  const flush = useCallback(async () => {
    if (bufferRef.current.length === 0) return;

    const batch = [...bufferRef.current];
    bufferRef.current = [];

    logger.info('ViolationBuffer', `Flushing ${batch.length} violations to backend`);
    try {
      await proctoringAPI.logViolationBatch({ violations: batch });
      logger.info('ViolationBuffer', `Flush successful: ${batch.length} violations sent`);
    } catch (err) {
      logger.error('ViolationBuffer', 'Batch flush failed, re-queuing', { error: err.message, count: batch.length });
      // Put them back at the front so they retry on next flush
      bufferRef.current = [...batch, ...bufferRef.current];
    }
  }, []);

  // ── Start / stop flush timer ─────────────────────
  useEffect(() => {
    logger.info('ViolationBuffer', `Starting flush timer: interval=${flushInterval}ms`);
    timerRef.current = setInterval(flush, flushInterval);
    return () => {
      logger.info('ViolationBuffer', 'Stopping flush timer, performing final flush');
      clearInterval(timerRef.current);
      // Final flush on unmount
      flush();
    };
  }, [flush, flushInterval]);

  // ── Enqueue a violation (with optional evidence capture) ──
  const enqueue = useCallback(
    async (violationData) => {
      let evidence_url = null;

      logger.debug('ViolationBuffer', `Enqueuing violation: type=${violationData.violation_type}`, {
        email: violationData.email,
        test_id: violationData.test_id,
      });

      if (captureEvidence && webcamRef) {
        try {
          const blob = await captureScreenshot(webcamRef);
          if (blob) {
            logger.debug('ViolationBuffer', 'Screenshot captured, requesting upload URL');
            const result = await proctoringAPI.getEvidenceUploadUrl({
              test_id: violationData.test_id,
              email: violationData.email,
              violation_type: violationData.violation_type,
              timestamp_ms: Date.now(),
            });
            const ok = await uploadToPresignedUrl(result.upload_url, blob);
            if (ok) {
              evidence_url = result.object_url;
              logger.info('ViolationBuffer', 'Evidence uploaded successfully', { object_url: evidence_url });
            } else {
              logger.warn('ViolationBuffer', 'Evidence upload returned non-OK status');
            }
          }
        } catch (err) {
          logger.warn('ViolationBuffer', 'Evidence capture/upload failed', { error: err.message });
        }
      }

      bufferRef.current.push({
        ...violationData,
        evidence_url,
      });
      logger.debug('ViolationBuffer', `Violation enqueued, buffer size: ${bufferRef.current.length}`);
    },
    [webcamRef, captureEvidence],
  );

  return { enqueue, flush, pendingCount: () => bufferRef.current.length };
}
