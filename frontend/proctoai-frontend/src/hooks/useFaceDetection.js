import { useRef, useState, useCallback, useEffect } from 'react';
import { FaceDetector, FilesetResolver } from '@mediapipe/tasks-vision';
import logger from '../utils/logger';

/**
 * useFaceDetection – Accurate Face Detection via MediaPipe BlazeFace (Sprint 2 – REQ-4/5)
 *
 * Uses Google MediaPipe's FaceDetector (BlazeFace short-range model) running
 * in-browser via WebAssembly for real-time, accurate face detection.
 *
 * Responsibilities:
 *  • Detect faces in a video frame using a proper neural-network model
 *  • Count faces accurately (no false positives from hands/skin)
 *  • Configurable absence threshold (5–10s)
 *  • Fire violation callback when face is absent too long or multiple faces detected
 */

const DEFAULT_ABSENCE_THRESHOLD_MS = 7000; // 7 seconds default
const MIN_DETECTION_CONFIDENCE = 0.5;

// ── Singleton MediaPipe FaceDetector instance ─────────
let detectorPromise = null;

async function getDetector() {
  if (!detectorPromise) {
    detectorPromise = (async () => {
      try {
        logger.info('FaceDetection', 'Initializing MediaPipe FaceDetector...');
        const vision = await FilesetResolver.forVisionTasks(
          'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
        );
        const detector = await FaceDetector.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath:
              'https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite',
            delegate: 'GPU',
          },
          runningMode: 'IMAGE',
          minDetectionConfidence: MIN_DETECTION_CONFIDENCE,
        });
        logger.info('FaceDetection', 'MediaPipe FaceDetector initialized successfully');
        return detector;
      } catch (err) {
        logger.error('FaceDetection', 'Failed to initialize MediaPipe detector', { error: err.message });
        detectorPromise = null; // allow retry
        return null;
      }
    })();
  }
  return detectorPromise;
}

// ── Public detection helpers (work with ImageData) ────
function imageDataToCanvas(imageData) {
  const canvas = document.createElement('canvas');
  canvas.width = imageData.width;
  canvas.height = imageData.height;
  const ctx = canvas.getContext('2d');
  ctx.putImageData(imageData, 0, 0);
  return canvas;
}

export async function detectFaces(imageData) {
  const detector = await getDetector();
  if (!detector) return [];
  const canvas = imageDataToCanvas(imageData);
  try {
    const result = detector.detect(canvas);
    return result.detections || [];
  } catch (err) {
    logger.warn('FaceDetection', 'Detection error', { error: err.message });
    return [];
  }
}

export async function detectFace(imageData) {
  const faces = await detectFaces(imageData);
  return faces.length > 0;
}

export async function detectMultipleFaces(imageData) {
  const faces = await detectFaces(imageData);
  return faces.length;
}

// ── React hook ────────────────────────────────────────
export default function useFaceDetection({
  absenceThresholdMs = DEFAULT_ABSENCE_THRESHOLD_MS,
  onViolation,
  enabled = true,
} = {}) {
  const [faceDetected, setFaceDetected] = useState(false);
  const [faceCount, setFaceCount] = useState(0);
  const [absentSince, setAbsentSince] = useState(null);
  const [violation, setViolation] = useState(null);

  const absentSinceRef = useRef(null);
  const violationFiredRef = useRef(false);
  const consecutiveMissRef = useRef(0);
  const processingRef = useRef(false);
  const detectorReadyRef = useRef(false);
  const MISS_THRESHOLD = 3; // require 3 consecutive misses before counting as absent

  // Pre-load the detector when the hook is first enabled
  useEffect(() => {
    if (enabled && !detectorReadyRef.current) {
      logger.info('FaceDetection', 'Pre-loading face detector');
      getDetector().then((d) => {
        if (d) {
          detectorReadyRef.current = true;
          logger.info('FaceDetection', 'Face detector ready');
        }
      });
    }
  }, [enabled]);

  const processFrame = useCallback(
    async (imageData) => {
      if (!enabled || !imageData) return;
      // Skip if a previous detection is still in progress
      if (processingRef.current) return;
      processingRef.current = true;

      try {
        const faces = await detectFaces(imageData);
        const count = faces.length;
        const detected = count > 0;

        setFaceDetected(detected);
        setFaceCount(count);

        // ── Multiple faces violation ──────────────────
        if (count > 1 && onViolation) {
          logger.warn('FaceDetection', `Multiple faces detected: count=${count}`);
          onViolation({
            type: 'multiple_faces',
            message: `Multiple faces detected (${count})`,
            count,
            timestamp: Date.now(),
          });
        }

        // ── Absence tracking (with consecutive miss buffer) ──
        if (!detected) {
          consecutiveMissRef.current += 1;
          // Only start absence timer after MISS_THRESHOLD consecutive frames with no face
          if (consecutiveMissRef.current >= MISS_THRESHOLD) {
            if (absentSinceRef.current === null) {
              absentSinceRef.current = Date.now();
              setAbsentSince(Date.now());
              logger.info('FaceDetection', 'Face absence started');
            } else {
              const elapsed = Date.now() - absentSinceRef.current;
              if (elapsed >= absenceThresholdMs && !violationFiredRef.current) {
                violationFiredRef.current = true;
                const v = {
                  type: 'face_absent',
                  message: `No face detected for ${Math.round(elapsed / 1000)}s`,
                  duration: elapsed,
                  timestamp: Date.now(),
                };
                setViolation(v);
                logger.warn('FaceDetection', `Face absent violation: ${Math.round(elapsed / 1000)}s`);
                if (onViolation) onViolation(v);
              }
            }
          }
        } else {
          // Face returned – reset absence tracking
          if (consecutiveMissRef.current >= MISS_THRESHOLD) {
            logger.info('FaceDetection', 'Face returned after absence');
          }
          consecutiveMissRef.current = 0;
          absentSinceRef.current = null;
          violationFiredRef.current = false;
          setAbsentSince(null);
          setViolation(null);
        }
      } catch (err) {
        logger.warn('FaceDetection', 'Frame processing error', { error: err.message });
      } finally {
        processingRef.current = false;
      }
    },
    [enabled, absenceThresholdMs, onViolation]
  );

  return {
    faceDetected,
    faceCount,
    absentSince,
    violation,
    processFrame,
  };
}
