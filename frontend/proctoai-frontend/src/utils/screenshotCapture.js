/**
 * Screenshot Capture Utility (Sprint 3 – REQ-9)
 *
 * Captures a frame from a <video> element (or react-webcam ref)
 * and returns it as a PNG Blob for direct upload to MinIO via
 * a presigned PUT URL.
 */

import logger from './logger';

/**
 * Capture a single frame from a webcam <video> element.
 *
 * @param {React.RefObject} webcamRef - react-webcam ref (has getCanvas / video)
 * @param {number}          width     - output width  (default 640)
 * @param {number}          height    - output height (default 480)
 * @returns {Promise<Blob|null>}      PNG blob or null on failure
 */
export async function captureScreenshot(webcamRef, width = 640, height = 480) {
  if (!webcamRef?.current) return null;

  try {
    // react-webcam exposes getCanvas() which returns an HTMLCanvasElement
    const canvas = webcamRef.current.getCanvas?.();
    if (canvas) {
      logger.debug('ScreenshotCapture', 'Captured frame via getCanvas()');
      return await canvasToBlob(canvas);
    }

    // Fallback: draw the underlying <video> element onto a new canvas
    const video = webcamRef.current.video ?? webcamRef.current;
    if (!video || video.readyState < 2) return null;

    const offscreen = document.createElement('canvas');
    offscreen.width = width;
    offscreen.height = height;
    const ctx = offscreen.getContext('2d');
    ctx.drawImage(video, 0, 0, width, height);
    logger.debug('ScreenshotCapture', 'Captured frame via video fallback');
    return await canvasToBlob(offscreen);
  } catch (err) {
    logger.error('ScreenshotCapture', 'Failed to capture frame', { error: err.message });
    return null;
  }
}

/**
 * Upload a blob directly to MinIO using a presigned PUT URL.
 *
 * @param {string} presignedUrl - presigned PUT URL from backend
 * @param {Blob}   blob         - screenshot blob
 * @returns {Promise<boolean>}  true if upload succeeded
 */
export async function uploadToPresignedUrl(presignedUrl, blob) {
  try {
    logger.debug('ScreenshotCapture', 'Uploading screenshot to presigned URL');
    const res = await fetch(presignedUrl, {
      method: 'PUT',
      headers: { 'Content-Type': 'image/png' },
      body: blob,
    });
    if (res.ok) {
      logger.info('ScreenshotCapture', 'Screenshot uploaded successfully');
    } else {
      logger.warn('ScreenshotCapture', `Upload returned non-OK status: ${res.status}`);
    }
    return res.ok;
  } catch (err) {
    logger.error('ScreenshotCapture', 'Upload failed', { error: err.message });
    return false;
  }
}

// ── Helpers ──────────────────────────────────────────

function canvasToBlob(canvas) {
  return new Promise((resolve) => {
    canvas.toBlob(
      (blob) => resolve(blob),
      'image/png',
      0.85,
    );
  });
}
