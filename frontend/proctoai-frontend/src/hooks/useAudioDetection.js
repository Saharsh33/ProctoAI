import { useState, useEffect, useRef, useCallback } from 'react';
import logger from '../utils/logger';

/**
 * useAudioDetection – Audio Pattern Detection (Sprint 2 – REQ-6)
 *
 * Responsibilities:
 *  • Create AudioContext + AnalyserNode from the media stream
 *  • Monitor audio levels (RMS dB)
 *  • Detect noise above configurable threshold
 *  • Classify suspicious audio patterns (sustained speech, sudden spikes)
 *  • Fire violation callback when suspicious audio detected
 */

const DEFAULT_NOISE_THRESHOLD_DB = -35;   // dB – anything above is "noisy"
const DEFAULT_SPIKE_THRESHOLD_DB = -20;   // dB – sudden loud spike
const ANALYSIS_INTERVAL_MS = 250;          // Check audio every 250ms
const SUSTAINED_NOISE_DURATION_MS = 3000;  // 3s of continuous noise = suspicious

export default function useAudioDetection({
  stream,
  noiseThresholdDb = DEFAULT_NOISE_THRESHOLD_DB,
  spikeThresholdDb = DEFAULT_SPIKE_THRESHOLD_DB,
  onViolation,
  enabled = true,
} = {}) {
  const [currentDb, setCurrentDb] = useState(-Infinity);
  const [isNoisy, setIsNoisy] = useState(false);
  const [violation, setViolation] = useState(null);

  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const sourceRef = useRef(null);
  const intervalRef = useRef(null);
  const noisySinceRef = useRef(null);
  const onViolationRef = useRef(onViolation);
  onViolationRef.current = onViolation;

  // ── Setup AudioContext & AnalyserNode ───────────────
  const setupAudio = useCallback((mediaStream) => {
    try {
      logger.info('AudioDetection', 'Setting up AudioContext and AnalyserNode');
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.8;

      const source = audioCtx.createMediaStreamSource(mediaStream);
      source.connect(analyser);
      // Do NOT connect to destination (we don't want to hear playback)

      audioContextRef.current = audioCtx;
      analyserRef.current = analyser;
      sourceRef.current = source;

      logger.info('AudioDetection', 'AudioContext setup complete');
      return true;
    } catch (err) {
      logger.warn('AudioDetection', 'Failed to setup AudioContext', { error: err.message });
      return false;
    }
  }, []);

  // ── Compute RMS dB from analyser ────────────────────
  const getRmsDb = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return -Infinity;

    const dataArray = new Float32Array(analyser.fftSize);
    analyser.getFloatTimeDomainData(dataArray);

    let sumSquares = 0;
    for (let i = 0; i < dataArray.length; i++) {
      sumSquares += dataArray[i] * dataArray[i];
    }
    const rms = Math.sqrt(sumSquares / dataArray.length);
    const db = 20 * Math.log10(rms + 1e-10);
    return db;
  }, []);

  // ── Classify audio pattern ──────────────────────────
  const classifyAudio = useCallback(
    (db) => {
      // 1. Sudden spike check
      if (db > spikeThresholdDb) {
        return { suspicious: true, reason: 'loud_spike', message: `Loud audio spike detected (${db.toFixed(1)} dB)` };
      }

      // 2. Sustained noise (e.g. someone talking)
      if (db > noiseThresholdDb) {
        if (noisySinceRef.current === null) {
          noisySinceRef.current = Date.now();
        }
        const elapsed = Date.now() - noisySinceRef.current;
        if (elapsed >= SUSTAINED_NOISE_DURATION_MS) {
          return {
            suspicious: true,
            reason: 'sustained_noise',
            message: `Sustained noise detected for ${Math.round(elapsed / 1000)}s (${db.toFixed(1)} dB)`,
          };
        }
      } else {
        noisySinceRef.current = null;
      }

      return { suspicious: false };
    },
    [noiseThresholdDb, spikeThresholdDb]
  );

  // ── Start / stop analysis loop ──────────────────────
  useEffect(() => {
    if (!enabled || !stream) return;

    const audioTracks = stream.getAudioTracks();
    if (audioTracks.length === 0) {
      logger.warn('AudioDetection', 'No audio tracks found in stream');
      return;
    }

    logger.info('AudioDetection', 'Starting audio analysis loop');
    const ok = setupAudio(stream);
    if (!ok) return;

    intervalRef.current = setInterval(() => {
      const db = getRmsDb();
      setCurrentDb(db);
      setIsNoisy(db > noiseThresholdDb);

      const result = classifyAudio(db);
      if (result.suspicious) {
        const v = {
          type: 'audio_violation',
          reason: result.reason,
          message: result.message,
          db: Math.round(db),
          timestamp: Date.now(),
        };
        setViolation(v);
        logger.warn('AudioDetection', `Audio violation: ${result.reason}`, { db: Math.round(db) });
        if (onViolationRef.current) {
          onViolationRef.current(v);
        }
        // Reset sustained noise counter after firing
        if (result.reason === 'sustained_noise') {
          noisySinceRef.current = Date.now();
        }
      }
    }, ANALYSIS_INTERVAL_MS);

    return () => {
      logger.info('AudioDetection', 'Stopping audio analysis loop');
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close().catch(() => {});
      }
      audioContextRef.current = null;
      analyserRef.current = null;
      sourceRef.current = null;
      noisySinceRef.current = null;
    };
  }, [enabled, stream, setupAudio, getRmsDb, classifyAudio, noiseThresholdDb]);

  return {
    currentDb,
    isNoisy,
    violation,
  };
}
