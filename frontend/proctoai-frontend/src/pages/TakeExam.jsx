import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Webcam from 'react-webcam';
import Navbar from '../components/Navbar';
import Toast from '../components/Toast';
import useToast from '../hooks/useToast';
import useAuth from '../hooks/useAuth';
import LoadingSpinner from '../components/LoadingSpinner';
import useWebcam from '../hooks/useWebcam';
import useFaceDetection from '../hooks/useFaceDetection';
import useTabFocusMonitor from '../hooks/useTabFocusMonitor';
import useAudioDetection from '../hooks/useAudioDetection';
import useViolationBuffer from '../hooks/useViolationBuffer';
import { examsAPI, proctoringAPI, reportsAPI } from '../services/api';

// ── Proctoring Warning Banner ─────────────────────────
const WarningBanner = ({ message, type = 'warning', onDismiss }) => {
  const colors = {
    warning: { bg: '#fef3c7', border: '#f59e0b', text: '#92400e', icon: '⚠️' },
    danger: { bg: '#fee2e2', border: '#ef4444', text: '#991b1b', icon: '🚨' },
    info: { bg: '#dbeafe', border: '#3b82f6', text: '#1e40af', icon: 'ℹ️' },
  };
  const c = colors[type] || colors.warning;

  return (
    <div
      style={{
        position: 'fixed',
        top: '5rem',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000,
        background: c.bg,
        border: `2px solid ${c.border}`,
        borderRadius: '12px',
        padding: '0.75rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        boxShadow: '0 10px 25px rgba(0,0,0,0.15)',
        animation: 'slideUp 0.3s ease',
        maxWidth: '600px',
        width: '90vw',
      }}
    >
      <span style={{ fontSize: '1.25rem' }}>{c.icon}</span>
      <span style={{ color: c.text, fontWeight: 600, fontSize: '0.875rem', flex: 1 }}>{message}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          style={{
            background: 'none',
            border: 'none',
            color: c.text,
            fontSize: '1.25rem',
            cursor: 'pointer',
            padding: '0 0.25rem',
          }}
        >
          ×
        </button>
      )}
    </div>
  );
};

// ── Proctoring Status Indicator ───────────────────────
const StatusDot = ({ active, label, color = 'var(--success)' }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.75rem' }}>
    <div
      style={{
        width: 8,
        height: 8,
        borderRadius: '50%',
        background: active ? color : 'var(--border)',
        boxShadow: active ? `0 0 6px ${color}` : 'none',
        transition: 'all 0.3s',
      }}
    />
    <span style={{ color: 'var(--text-muted)' }}>{label}</span>
  </div>
);

// ── Audio Level Meter ─────────────────────────────────
const AudioMeter = ({ db }) => {
  const normalized = Math.max(0, Math.min(100, ((db + 60) / 60) * 100));
  const barColor = normalized > 70 ? 'var(--danger)' : normalized > 40 ? 'var(--warning)' : 'var(--success)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.7rem' }}>
      <span style={{ color: 'var(--text-muted)', minWidth: 24 }}>🎙️</span>
      <div
        style={{
          flex: 1,
          height: 4,
          background: 'var(--border)',
          borderRadius: 2,
          overflow: 'hidden',
          minWidth: 50,
        }}
      >
        <div
          style={{
            width: `${normalized}%`,
            height: '100%',
            background: barColor,
            borderRadius: 2,
            transition: 'width 0.15s',
          }}
        />
      </div>
      <span style={{ color: 'var(--text-muted)', fontFamily: 'monospace', fontSize: '0.65rem', minWidth: 36 }}>
        {db > -Infinity ? `${Math.round(db)}dB` : '--'}
      </span>
    </div>
  );
};

const TakeExam = () => {
  const { examId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toasts, addToast, removeToast } = useToast();
  const [exam, setExam] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);
  const [examLocked, setExamLocked] = useState(false);
  const [proctoringReady, setProctoringReady] = useState(false);
  const [violationLog, setViolationLog] = useState([]);
  const [showSubmitConfirm, setShowSubmitConfirm] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const timerRef = useRef(null);
  const timerStartedRef = useRef(false);
  const violationDebounceRef = useRef({});
  const answersRef = useRef({});
  const autoSubmitRef = useRef(null);
  const isSubmittingRef = useRef(false);

  // ── Hook 1: WebRTC Media Capture ────────────────────
  const {
    webcamRef,
    stream,
    permissionStatus,
    errorMessage: mediaError,
    currentFrame,
    requestMedia,
    stopMedia,
  } = useWebcam({ fps: 2, enabled: proctoringReady });

  // ── Sprint 3: Batch violation buffer + evidence capture ──
  const { enqueue: bufferEnqueue, flush: flushBuffer } = useViolationBuffer({
    webcamRef,
    flushInterval: 2000,
    captureEvidence: true,
  });

  // ── Violation logger (sends to backend via batch buffer) ──
  const logViolation = useCallback(
    async (violation) => {
      // Debounce same type within 2s
      const now = Date.now();
      if (
        violationDebounceRef.current[violation.type] &&
        now - violationDebounceRef.current[violation.type] < 2000
      ) {
        return;
      }
      violationDebounceRef.current[violation.type] = now;

      // Add to local log
      setViolationLog((prev) => [...prev.slice(-49), { ...violation, id: now }]);

      // Enqueue to batch buffer (captures screenshot + uploads evidence)
      bufferEnqueue({
        email: user?.email || '',
        test_id: examId,
        violation_type: violation.type,
        message: violation.message,
        severity: violation.type === 'multiple_faces' ? 'critical' : 'warning',
        metadata_json: JSON.stringify(violation),
        uid: user?.userId || '',
      });
    },
    [examId, user, bufferEnqueue]
  );

  // ── Hook 2: Face Detection AI ───────────────────────
  const {
    faceDetected,
    faceCount,
    absentSince,
    violation: faceViolation,
    processFrame,
  } = useFaceDetection({
    absenceThresholdMs: 7000,
    onViolation: logViolation,
    enabled: proctoringReady && permissionStatus === 'granted',
  });

  // ── Hook 3: Tab-Switch & Focus Monitor ──────────────
  const {
    isTabVisible,
    isFocused,
    warningVisible: tabWarningVisible,
    tabSwitchCount,
    dismissWarning: dismissTabWarning,
  } = useTabFocusMonitor({
    onViolation: logViolation,
    enabled: proctoringReady && !submitting && !submitted,
  });

  // ── Hook 4: Audio Pattern Detection ─────────────────
  const {
    currentDb,
    isNoisy,
    violation: audioViolation,
  } = useAudioDetection({
    stream,
    noiseThresholdDb: -35,
    spikeThresholdDb: -20,
    onViolation: logViolation,
    enabled: proctoringReady && permissionStatus === 'granted',
  });

  // ── Feed frames to face detection ───────────────────
  useEffect(() => {
    if (currentFrame) {
      processFrame(currentFrame); // async – fire and forget (back-pressure handled inside hook)
    }
  }, [currentFrame, processFrame]);

  // ── Init proctoring on mount ────────────────────────
  useEffect(() => {
    const initProctoring = async () => {
      const mediaStream = await requestMedia();
      if (mediaStream) {
        setProctoringReady(true);
        // Request fullscreen mode for proctored exam
        try {
          await document.documentElement.requestFullscreen();
          setIsFullscreen(true);
        } catch (err) {
          console.warn('[Fullscreen] Could not enter fullscreen:', err);
        }
      }
    };
    initProctoring();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Fullscreen exit detection ───────────────────────
  useEffect(() => {
    if (!proctoringReady) return;

    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
      if (!document.fullscreenElement && !isSubmittingRef.current) {
        // Student exited fullscreen – log violation and re-request
        logViolation({
          type: 'tab_switch',
          message: 'Fullscreen exited during exam',
          timestamp: Date.now(),
        });
        // Re-request fullscreen after a short delay (browsers require user gesture
        // for fullscreen, so we show an overlay that blocks the exam until they click)
      }
    };

    // Intercept Escape key to prevent fullscreen exit
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' || e.key === 'F11') {
        e.preventDefault();
        e.stopPropagation();
      }
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('keydown', handleKeyDown, true);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('keydown', handleKeyDown, true);
    };
  }, [proctoringReady, logViolation]);

  // ── Cleanup on unmount ──────────────────────────────
  useEffect(() => {
    return () => {
      stopMedia();
      if (timerRef.current) clearInterval(timerRef.current);
      // Exit fullscreen on unmount
      if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => {});
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Exam data loading ───────────────────────────────
  useEffect(() => {
    loadExamData();
  }, [examId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (exam && proctoringReady && !timerStartedRef.current && !submitted) {
      timerStartedRef.current = true;
      const durationInSeconds = exam.duration * 60;
      setTimeLeft(durationInSeconds);
      startTimer(durationInSeconds);
    }
  }, [exam, proctoringReady]); // eslint-disable-line react-hooks/exhaustive-deps

  const startTimer = (initialTime) => {
    let remaining = initialTime;
    timerRef.current = setInterval(() => {
      remaining -= 1;
      setTimeLeft(remaining);
      if (remaining <= 0) {
        clearInterval(timerRef.current);
        // Call through ref to always use the latest closure
        if (autoSubmitRef.current) autoSubmitRef.current();
      }
    }, 1000);
  };

  const loadExamData = async () => {
    try {
      setLoading(true);

      // Check if student already submitted this exam before loading
      try {
        const submittedIds = await examsAPI.mySubmissions();
        if (submittedIds.includes(examId)) {
          addToast('You have already submitted this exam.', 'error');
          navigate('/student/exams');
          return;
        }
      } catch {
        // If the check fails, continue loading – backend will still block re-submit
      }

      const [examData, questionsData] = await Promise.all([
        examsAPI.get(examId),
        examsAPI.getQuestions(examId),
      ]);
      setExam(examData);
      setQuestions(questionsData);

      // Initialize answers object
      const initialAnswers = {};
      questionsData.forEach((q) => {
        initialAnswers[q.qid] = '';
      });
      setAnswers(initialAnswers);
      answersRef.current = initialAnswers;
    } catch (err) {
      addToast(err.message || 'Failed to load exam', 'error');
      navigate('/student/exams');
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerChange = (qid, answer) => {
    setAnswers((prev) => {
      const next = { ...prev, [qid]: answer };
      answersRef.current = next;
      return next;
    });
  };

  const handleAutoSubmit = useCallback(async () => {
    setExamLocked(true);
    addToast('Time is up! Submitting your exam...', 'info');
    await submitExam();
  }, []);

  // Keep ref in sync so the setInterval closure always calls the latest version
  useEffect(() => {
    autoSubmitRef.current = handleAutoSubmit;
  }, [handleAutoSubmit]);

  const handleSubmit = async () => {
    if (submitted) return;
    setShowSubmitConfirm(true);
  };

  const confirmSubmit = async () => {
    setShowSubmitConfirm(false);
    await submitExam();
  };

  const submitExam = async () => {
    if (submitted || isSubmittingRef.current) return; // Prevent double submission
    isSubmittingRef.current = true;
    setSubmitting(true);
    setSubmitted(true);
    try {
      // Clear timer & stop proctoring
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      stopMedia();

      // Exit fullscreen before navigation
      if (document.fullscreenElement) {
        try { await document.exitFullscreen(); } catch (e) { /* ignore */ }
      }

      // Flush any remaining violations in the batch buffer
      await flushBuffer();

      // Prepare answers for submission – use ref for the freshest state
      const latestAnswers = answersRef.current;
      const answersList = Object.entries(latestAnswers).map(([qid, answer]) => ({
        qid,
        answer: answer || 'Not Answered',
      }));

      await examsAPI.submit(examId, {
        examId,
        answers: answersList,
      });

      // Force-flush backend violation buffer so all violations are in DB before report
      try {
        await proctoringAPI.flushBuffer();
      } catch (flushErr) {
        console.warn('[Flush] Backend buffer flush failed:', flushErr.message);
      }

      // Generate proctoring report (Sprint 4 – fire-and-forget, don't block navigation)
      try {
        await reportsAPI.generate({
          test_id: examId,
          email: user?.email || '',
          uid: user?.userId || '',
        });
      } catch (reportErr) {
        console.warn('[Report] Auto-generation failed:', reportErr.message);
      }

      addToast('Exam submitted successfully!', 'success');
      setTimeout(() => {
        navigate('/student/exams');
      }, 2000);
    } catch (err) {
      // If backend says already submitted (409), treat as success – don't allow retry
      if (err.message && err.message.toLowerCase().includes('already submitted')) {
        addToast('Exam was already submitted.', 'info');
        setTimeout(() => {
          navigate('/student/exams');
        }, 2000);
        return;
      }
      addToast(err.message || 'Failed to submit exam', 'error');
      setSubmitting(false);
      setSubmitted(false);
      isSubmittingRef.current = false;
    }
  };

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getTimeColor = () => {
    const percentage = (timeLeft / (exam?.duration * 60)) * 100;
    if (percentage > 50) return 'var(--success)';
    if (percentage > 20) return 'var(--warning)';
    return 'var(--danger)';
  };

  if (loading) {
    return (
      <div>
        <Navbar />
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
          <LoadingSpinner />
        </div>
        <Toast toasts={toasts} onRemove={removeToast} />
      </div>
    );
  }

  /* ── Permission Gate: Block exam until camera & mic are granted ── */
  if (permissionStatus !== 'granted') {
    return (
      <div>
        <Navbar />
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '80vh',
            padding: '2rem',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              background: 'white',
              borderRadius: 'var(--radius-md)',
              border: '2px solid var(--danger)',
              padding: '3rem 2rem',
              maxWidth: 480,
              width: '100%',
              boxShadow: 'var(--shadow-md)',
            }}
          >
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📷</div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.75rem' }}>
              Camera &amp; Microphone Required
            </h2>
            <p style={{ color: 'var(--text-light)', marginBottom: '1.5rem', lineHeight: 1.6 }}>
              This is a proctored exam. You must allow camera and microphone access to proceed.
              Please grant permissions and try again.
            </p>
            {mediaError && (
              <p style={{ color: 'var(--danger)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
                {mediaError}
              </p>
            )}
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
              <button
                className="btn btn-primary"
                onClick={async () => {
                  const s = await requestMedia();
                  if (s) setProctoringReady(true);
                }}
              >
                Grant Permissions
              </button>
              <button
                className="btn btn-ghost"
                onClick={() => navigate('/student/exams')}
              >
                Go Back
              </button>
            </div>
          </div>
        </div>
        <Toast toasts={toasts} onRemove={removeToast} />
      </div>
    );
  }

  return (
    <div>
      <Navbar />

      {/* ── Sprint 5: Exam lock overlay (auto-submit) ── */}
      {examLocked && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            background: 'rgba(0, 0, 0, 0.7)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
          }}
        >
          <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>⏱️</div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            Time&apos;s Up!
          </h2>
          <p style={{ fontSize: '1rem', opacity: 0.85, marginBottom: '1.5rem' }}>
            Your exam is being submitted automatically…
          </p>
          <LoadingSpinner />
        </div>
      )}

      {/* ── Fullscreen enforcement overlay ── */}
      {proctoringReady && !isFullscreen && !submitted && !examLocked && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9998,
            background: 'rgba(0, 0, 0, 0.85)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
          }}
        >
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🖥️</div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            Fullscreen Required
          </h2>
          <p style={{ fontSize: '1rem', opacity: 0.85, marginBottom: '1.5rem', textAlign: 'center', maxWidth: 400 }}>
            You exited fullscreen mode. This violation has been logged. Click below to continue your exam.
          </p>
          <button
            className="btn btn-primary"
            style={{ fontSize: '1rem', padding: '0.75rem 2rem' }}
            onClick={async () => {
              try {
                await document.documentElement.requestFullscreen();
              } catch (err) {
                console.warn('[Fullscreen] Re-request failed:', err);
              }
            }}
          >
            Re-enter Fullscreen
          </button>
        </div>
      )}

      {/* ── Custom Submit Confirmation Modal (avoids window.confirm blur) ── */}
      {showSubmitConfirm && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9998,
            background: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div
            style={{
              background: 'white',
              borderRadius: 'var(--radius-md)',
              padding: '2rem',
              maxWidth: 420,
              width: '90%',
              boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>📝</div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>
              Submit Exam?
            </h3>
            <p style={{ color: 'var(--text-light)', marginBottom: '0.5rem', lineHeight: 1.5 }}>
              Are you sure you want to submit your exam? You cannot change your answers after submission.
            </p>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-light)', marginBottom: '1.5rem' }}>
              Answered: {Object.values(answers).filter((a) => a).length} / {questions.length}
            </p>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
              <button
                className="btn btn-ghost"
                onClick={() => setShowSubmitConfirm(false)}
                style={{ minWidth: 100 }}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={confirmSubmit}
                style={{ minWidth: 100 }}
              >
                Yes, Submit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab-switch warning banner ──────────────── */}
      {tabWarningVisible && (
        <WarningBanner
          message={`Tab switch detected! This violation has been logged. (Total: ${tabSwitchCount})`}
          type="danger"
          onDismiss={dismissTabWarning}
        />
      )}

      {/* ── Face absence warning banner ────────────── */}
      {faceViolation && (
        <WarningBanner message={faceViolation.message} type="danger" />
      )}

      {/* Audio violations are logged silently – no popup banner */}

      {/* ── Permission denied banner ───────────────── */}
      {permissionStatus === 'denied' && (
        <WarningBanner
          message={mediaError || 'Camera & mic access denied. Proctoring is required to take this exam.'}
          type="danger"
        />
      )}

      <div style={{ display: 'flex', maxWidth: '1200px', margin: '0 auto', padding: '2rem 1rem', gap: '1.5rem' }}>
        {/* ── Main exam area ──────────────────────── */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Timer & Header */}
          <div style={{ position: 'sticky', top: '4rem', zIndex: 10, background: 'var(--bg)', padding: '1rem 0', marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', background: 'white', borderRadius: 'var(--radius-md)', border: '2px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
              <div>
                <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                  {exam?.title}
                </h1>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-light)' }}>
                  {questions.length} Questions
                </p>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-light)', marginBottom: '0.25rem' }}>
                  Time Remaining
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 700, color: getTimeColor(), fontFamily: 'monospace' }}>
                  {formatTime(timeLeft)}
                </div>
              </div>
            </div>
          </div>

          {/* Questions */}
          <div style={{ display: 'grid', gap: '1.5rem', marginBottom: '2rem' }}>
            {questions.map((question, index) => (
              <div key={question.questions_uid} className="card card-no-hover">
                <div className="card-body">
                  <div style={{ marginBottom: '1rem' }}>
                    <span style={{ fontWeight: 700, fontSize: '1.125rem', color: 'var(--primary)' }}>
                      Question {index + 1}
                    </span>
                    <span style={{ marginLeft: '0.5rem', fontSize: '0.875rem', color: 'var(--text-light)' }}>
                      ({question.marks} {question.marks === 1 ? 'mark' : 'marks'})
                    </span>
                  </div>
                  <div style={{ marginBottom: '1.25rem', fontSize: '1rem', lineHeight: 1.6 }}>
                    {question.q}
                  </div>
                  <div style={{ display: 'grid', gap: '0.75rem' }}>
                    {['A', 'B', 'C', 'D'].map((option) => (
                      <label
                        key={option}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          padding: '0.875rem',
                          border: `2px solid ${answers[question.qid] === option ? 'var(--primary)' : 'var(--border)'}`,
                          borderRadius: 'var(--radius-sm)',
                          background: answers[question.qid] === option ? '#ede9fe' : 'white',
                          cursor: 'pointer',
                          transition: 'all 0.2s',
                        }}
                      >
                        <input
                          type="radio"
                          name={`question-${question.qid}`}
                          value={option}
                          checked={answers[question.qid] === option}
                          onChange={(e) => handleAnswerChange(question.qid, e.target.value)}
                          style={{ marginRight: '0.75rem', cursor: 'pointer' }}
                        />
                        <span style={{ fontWeight: 600, marginRight: '0.5rem' }}>{option}.</span>
                        <span>{question[option.toLowerCase()]}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Submit Button */}
          <div style={{ position: 'sticky', bottom: 0, padding: '1.5rem 0', background: 'var(--bg)' }}>
            <div style={{ padding: '1.5rem', background: 'white', borderRadius: 'var(--radius-md)', border: '2px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '0.875rem', color: 'var(--text-light)', marginBottom: '0.25rem' }}>
                    Answered: {Object.values(answers).filter((a) => a).length} / {questions.length}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-light)' }}>
                    Make sure you've answered all questions before submitting
                  </div>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={handleSubmit}
                  disabled={submitting || examLocked || submitted}
                  style={{ minWidth: 140 }}
                >
                  {submitting ? <LoadingSpinner /> : submitted ? 'Submitted ✓' : 'Submit Exam'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* ── Proctoring Sidebar Panel ────────────── */}
        <div style={{ width: 280, flexShrink: 0, position: 'sticky', top: '5rem', alignSelf: 'flex-start' }}>
          <div
            className="card card-no-hover"
            style={{
              overflow: 'hidden',
              border: permissionStatus !== 'granted' ? '2px solid var(--danger)' : '2px solid var(--border)',
            }}
          >
            {/* Webcam feed */}
            <div style={{ position: 'relative', background: '#1e293b', aspectRatio: '4/3' }}>
              {permissionStatus === 'granted' ? (
                <Webcam
                  ref={webcamRef}
                  audio={false}
                  width="100%"
                  height="100%"
                  videoConstraints={{ facingMode: 'user', width: 640, height: 480 }}
                  style={{ display: 'block', objectFit: 'cover', width: '100%', height: '100%' }}
                  mirrored
                />
              ) : (
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '100%',
                    minHeight: 140,
                    color: '#94a3b8',
                    padding: '1rem',
                    textAlign: 'center',
                  }}
                >
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M23 7l-7 5 7 5V7z" />
                    <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                  </svg>
                  <span style={{ fontSize: '0.75rem', marginTop: '0.5rem' }}>
                    {permissionStatus === 'pending' ? 'Requesting camera...' : 'Camera access denied'}
                  </span>
                </div>
              )}

              {/* Face detection overlay */}
              {permissionStatus === 'granted' && (
                <div
                  style={{
                    position: 'absolute',
                    top: 6,
                    right: 6,
                    background: faceDetected ? 'rgba(16,185,129,0.85)' : 'rgba(239,68,68,0.85)',
                    color: '#fff',
                    fontSize: '0.625rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: 4,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#fff' }} />
                  {faceDetected
                    ? faceCount > 1
                      ? `${faceCount} Faces!`
                      : '1 Face'
                    : 'No Face'}
                </div>
              )}
            </div>

            {/* Proctoring status panel */}
            <div style={{ padding: '0.75rem' }}>
              <div style={{ fontSize: '0.8125rem', fontWeight: 700, marginBottom: '0.5rem', color: 'var(--text)' }}>
                🛡️ Proctoring Status
              </div>

              <div style={{ display: 'grid', gap: '0.375rem' }}>
                <StatusDot
                  active={permissionStatus === 'granted'}
                  label="Camera & Mic"
                  color={permissionStatus === 'granted' ? 'var(--success)' : 'var(--danger)'}
                />
                <StatusDot
                  active={faceDetected}
                  label={faceDetected ? `Face detected (${faceCount})` : 'No face detected'}
                  color={faceDetected ? (faceCount > 1 ? 'var(--danger)' : 'var(--success)') : 'var(--danger)'}
                />
                <StatusDot
                  active={isTabVisible && isFocused}
                  label={isTabVisible && isFocused ? 'Tab focused' : 'Tab not focused!'}
                  color={isTabVisible && isFocused ? 'var(--success)' : 'var(--danger)'}
                />
                <StatusDot
                  active={!isNoisy}
                  label={isNoisy ? 'Noise detected!' : 'Audio normal'}
                  color={isNoisy ? 'var(--warning)' : 'var(--success)'}
                />
              </div>

              {/* Audio level meter */}
              <div style={{ marginTop: '0.5rem' }}>
                <AudioMeter db={currentDb} />
              </div>

              {/* Violation counter */}
              {violationLog.length > 0 && (
                <div
                  style={{
                    marginTop: '0.75rem',
                    padding: '0.5rem',
                    background: '#fef2f2',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid #fecaca',
                  }}
                >
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--danger)', marginBottom: '0.25rem' }}>
                    ⚠️ {violationLog.length} Violation{violationLog.length !== 1 ? 's' : ''} Logged
                  </div>
                  <div style={{ fontSize: '0.65rem', color: '#991b1b' }}>
                    {tabSwitchCount > 0 && <div>• Tab switches: {tabSwitchCount}</div>}
                    {violationLog.filter((v) => v.type === 'face_absent').length > 0 && (
                      <div>• Face absent: {violationLog.filter((v) => v.type === 'face_absent').length}</div>
                    )}
                    {violationLog.filter((v) => v.type === 'multiple_faces').length > 0 && (
                      <div>• Multiple faces: {violationLog.filter((v) => v.type === 'multiple_faces').length}</div>
                    )}
                    {violationLog.filter((v) => v.type === 'audio_violation').length > 0 && (
                      <div>• Audio violations: {violationLog.filter((v) => v.type === 'audio_violation').length}</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <Toast toasts={toasts} onRemove={removeToast} />
    </div>
  );
};

export default TakeExam;
