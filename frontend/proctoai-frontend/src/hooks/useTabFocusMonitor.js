import { useState, useEffect, useRef, useCallback } from 'react';
import logger from '../utils/logger';

/**
 * useTabFocusMonitor – Browser Tab-Switch & Focus Monitor (Sprint 2 – REQ-8)
 *
 * Responsibilities:
 *  • Listen to `visibilitychange` and `blur`/`focus` events
 *  • Detect tab switches / focus loss instantly
 *  • Log violations within 500ms via callback
 *  • Non-intrusive warning banner support (via state)
 *  • Periodic check every 2 seconds as a safety-net
 */

const CHECK_INTERVAL_MS = 2000;  // Safety-net check interval
const LOG_DEBOUNCE_MS = 500;     // Violation must be logged within 500ms

export default function useTabFocusMonitor({ onViolation, enabled = true } = {}) {
  const [isTabVisible, setIsTabVisible] = useState(true);
  const [isFocused, setIsFocused] = useState(true);
  const [warningVisible, setWarningVisible] = useState(false);
  const [tabSwitchCount, setTabSwitchCount] = useState(0);
  const [lastViolationTime, setLastViolationTime] = useState(null);

  const warningTimeoutRef = useRef(null);
  const lastFireTimeRef = useRef(0);
  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  const onViolationRef = useRef(onViolation);
  onViolationRef.current = onViolation;

  // ── Fire violation (deduplicated – only once per 1s window) ──
  const fireViolation = useCallback((reason) => {
    if (!enabledRef.current) return;

    // Deduplicate: both visibilitychange + blur fire for one tab switch.
    // Only count once within a 1-second window.
    const now = Date.now();
    if (now - lastFireTimeRef.current < 1000) return;
    lastFireTimeRef.current = now;

    setTabSwitchCount((c) => c + 1);
    setLastViolationTime(now);

    logger.warn('TabFocusMonitor', `Tab/focus violation: ${reason}`);

    // Show warning banner
    setWarningVisible(true);
    if (warningTimeoutRef.current) clearTimeout(warningTimeoutRef.current);
    warningTimeoutRef.current = setTimeout(() => setWarningVisible(false), 5000);

    // Callback within 500ms window
    if (onViolationRef.current) {
      onViolationRef.current({
        type: 'tab_switch',
        reason,
        timestamp: now,
        message: `Tab/focus violation: ${reason}`,
      });
    }
  }, []);

  // ── Visibility change listener ──────────────────────
  useEffect(() => {
    if (!enabled) return;

    logger.info('TabFocusMonitor', 'Enabling tab/focus monitoring');

    const handleVisibilityChange = () => {
      const visible = document.visibilityState === 'visible';
      setIsTabVisible(visible);
      if (!visible) {
        fireViolation('Tab became hidden (visibilitychange)');
      } else {
        logger.debug('TabFocusMonitor', 'Tab became visible again');
      }
    };

    const handleBlur = () => {
      setIsFocused(false);
      fireViolation('Window lost focus (blur)');
    };

    const handleFocus = () => {
      setIsFocused(true);
      logger.debug('TabFocusMonitor', 'Window regained focus');
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('blur', handleBlur);
    window.addEventListener('focus', handleFocus);

    return () => {
      logger.info('TabFocusMonitor', 'Disabling tab/focus monitoring');
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('blur', handleBlur);
      window.removeEventListener('focus', handleFocus);
    };
  }, [enabled, fireViolation]);

  // ── Safety-net periodic check every 2s ──────────────
  useEffect(() => {
    if (!enabled) return;

    const interval = setInterval(() => {
      if (document.visibilityState !== 'visible' || !document.hasFocus()) {
        // Already handled by event listeners, but log if still hidden
        if (document.visibilityState !== 'visible') {
          setIsTabVisible(false);
        }
        if (!document.hasFocus()) {
          setIsFocused(false);
        }
      }
    }, CHECK_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [enabled]);

  // Cleanup warning timeout
  useEffect(() => {
    return () => {
      if (warningTimeoutRef.current) clearTimeout(warningTimeoutRef.current);
    };
  }, []);

  const dismissWarning = useCallback(() => {
    setWarningVisible(false);
    if (warningTimeoutRef.current) clearTimeout(warningTimeoutRef.current);
    logger.debug('TabFocusMonitor', 'Warning dismissed by user');
  }, []);

  return {
    isTabVisible,
    isFocused,
    warningVisible,
    tabSwitchCount,
    lastViolationTime,
    dismissWarning,
  };
}
