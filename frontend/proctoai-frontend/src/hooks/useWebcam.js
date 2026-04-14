import { useRef, useState, useCallback, useEffect } from 'react';
import logger from '../utils/logger';

/**
 * useWebcam – WebRTC Media Capture hook (Sprint 2 – REQ-7)
 *
 * Responsibilities:
 *  • Request webcam + mic via getUserMedia()
 *  • Expose a <video> ref that can be attached to react-webcam or a raw <video>
 *  • Extract canvas frames at a configurable FPS (default 2) for AI processing
 *  • Provide graceful permission-denial handling with clear status
 */

const FRAME_FPS = 2; // Canvas frame extraction rate

export default function useWebcam({ fps = FRAME_FPS, enabled = true } = {}) {
  const webcamRef = useRef(null);
  const canvasRef = useRef(document.createElement('canvas'));
  const frameIntervalRef = useRef(null);

  const [stream, setStream] = useState(null);
  const [permissionStatus, setPermissionStatus] = useState('pending'); // pending | granted | denied | error
  const [errorMessage, setErrorMessage] = useState('');
  const [currentFrame, setCurrentFrame] = useState(null); // latest ImageData for AI

  // ── Request media stream ────────────────────────────
  const requestMedia = useCallback(async () => {
    try {
      setPermissionStatus('pending');
      setErrorMessage('');
      logger.info('Webcam', 'Requesting media stream (camera + mic)');

      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
        audio: true,
      });

      setStream(mediaStream);
      setPermissionStatus('granted');
      logger.info('Webcam', 'Media stream granted', {
        videoTracks: mediaStream.getVideoTracks().length,
        audioTracks: mediaStream.getAudioTracks().length,
      });

      // Attach stream to webcamRef if it's a raw <video> element
      if (webcamRef.current && webcamRef.current.tagName === 'VIDEO') {
        webcamRef.current.srcObject = mediaStream;
      }

      return mediaStream;
    } catch (err) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setPermissionStatus('denied');
        setErrorMessage('Camera & microphone access was denied. Please allow access in your browser settings to continue the proctored exam.');
        logger.warn('Webcam', 'Media permission denied by user');
      } else if (err.name === 'NotFoundError') {
        setPermissionStatus('error');
        setErrorMessage('No camera or microphone found. Please connect a webcam and microphone.');
        logger.error('Webcam', 'No media devices found');
      } else {
        setPermissionStatus('error');
        setErrorMessage(`Media error: ${err.message}`);
        logger.error('Webcam', 'Media request failed', { error: err.message, name: err.name });
      }
      return null;
    }
  }, []);

  // ── Stop all tracks ─────────────────────────────────
  const stopMedia = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      setStream(null);
      logger.info('Webcam', 'Media stream stopped');
    }
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
  }, [stream]);

  // ── Canvas frame extraction at `fps` ────────────────
  const captureFrame = useCallback(() => {
    const video =
      webcamRef.current?.video ?? // react-webcam exposes .video
      webcamRef.current;         // raw <video>

    if (!video || video.readyState < 2) return null; // HAVE_CURRENT_DATA

    const canvas = canvasRef.current;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    return imageData;
  }, []);

  // Start / stop frame extraction loop
  useEffect(() => {
    if (!enabled || permissionStatus !== 'granted') return;

    const interval = 1000 / fps;
    logger.info('Webcam', `Starting frame extraction: fps=${fps}, interval=${interval}ms`);
    frameIntervalRef.current = setInterval(() => {
      const frame = captureFrame();
      if (frame) setCurrentFrame(frame);
    }, interval);

    return () => {
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
        frameIntervalRef.current = null;
        logger.info('Webcam', 'Frame extraction stopped');
      }
    };
  }, [enabled, permissionStatus, fps, captureFrame]);

  // Cleanup on unmount
  useEffect(() => {
    return () => stopMedia();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    webcamRef,
    stream,
    permissionStatus,
    errorMessage,
    currentFrame,
    requestMedia,
    stopMedia,
    captureFrame,
  };
}
