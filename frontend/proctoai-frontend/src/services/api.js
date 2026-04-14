import logger from '../utils/logger';

// Use VITE_API_BASE_URL from environment variables, fallback to localhost for development
const BASE_URL = import.meta.env.VITE_API_BASE_URL;

const getHeaders = (auth = false) => {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const token = localStorage.getItem('token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};

const handleResponse = async (res) => {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'An error occurred' }));
    logger.error('API', `Request failed: ${res.status} ${res.url}`, { detail: err.detail });
    throw new Error(err.detail || 'Request failed');
  }
  logger.debug('API', `Response OK: ${res.status} ${res.url}`);
  return res.json();
};

export const authAPI = {
  
  login: (email, password) => {
    logger.info('API', `POST /auth/login — email=${email}`);
    return fetch(`${BASE_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ email, password }),
    }).then(handleResponse);
  },

  signup: (data) => {
    logger.info('API', `POST /auth/signup — email=${data.email}, role=${data.role}`);
    return fetch(`${BASE_URL}/api/v1/auth/signup`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },

  me: () => {
    logger.debug('API', 'GET /auth/me');
    return fetch(`${BASE_URL}/api/v1/auth/me`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },
};

export const usersAPI = {
  list: (skip = 0, limit = 100) => {
    logger.info('API', `GET /users — skip=${skip}, limit=${limit}`);
    return fetch(`${BASE_URL}/api/v1/users/?skip=${skip}&limit=${limit}`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },

  get: (id) => {
    logger.info('API', `GET /users/${id}`);
    return fetch(`${BASE_URL}/api/v1/users/${id}`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },

  create: (data) => {
    logger.info('API', `POST /users — email=${data.email}`);
    return fetch(`${BASE_URL}/api/v1/users/`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },

  update: (id, data) => {
    logger.info('API', `PATCH /users/${id}`);
    return fetch(`${BASE_URL}/api/v1/users/${id}`, {
      method: 'PATCH',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },
};

export const examsAPI = {
  create: (data) => {
    logger.info('API', `POST /exam/create — title=${data.title}`);
    return fetch(`${BASE_URL}/api/v1/exam/create`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },

  list: (skip = 0, limit = 100) => {
    logger.info('API', `GET /exam/list — skip=${skip}, limit=${limit}`);
    return fetch(`${BASE_URL}/api/v1/exam/list?skip=${skip}&limit=${limit}`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },

  mySubmissions: () => {
    logger.info('API', 'GET /exam/my-submissions');
    return fetch(`${BASE_URL}/api/v1/exam/my-submissions`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },

  get: (examId) => {
    logger.info('API', `GET /exam/${examId}`);
    return fetch(`${BASE_URL}/api/v1/exam/${examId}`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },

  update: (examId, data) => {
    logger.info('API', `PUT /exam/${examId}`);
    return fetch(`${BASE_URL}/api/v1/exam/${examId}`, {
      method: 'PUT',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },

  delete: (examId) => {
    logger.info('API', `DELETE /exam/${examId}`);
    return fetch(`${BASE_URL}/api/v1/exam/${examId}`, {
      method: 'DELETE',
      headers: getHeaders(true),
    });
  },

  getQuestions: (examId, skip = 0, limit = 100) => {
    logger.debug('API', `GET /exam/${examId}/questions — skip=${skip}, limit=${limit}`);
    return fetch(`${BASE_URL}/api/v1/exam/${examId}/questions?skip=${skip}&limit=${limit}`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },

  addQuestion: (examId, data) => {
    logger.info('API', `POST /exam/${examId}/questions`);
    return fetch(`${BASE_URL}/api/v1/exam/${examId}/questions`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },

  updateQuestion: (examId, questionId, data) => {
    logger.info('API', `PUT /exam/${examId}/questions/${questionId}`);
    return fetch(`${BASE_URL}/api/v1/exam/${examId}/questions/${questionId}`, {
      method: 'PUT',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },

  deleteQuestion: (examId, questionId) => {
    logger.info('API', `DELETE /exam/${examId}/questions/${questionId}`);
    return fetch(`${BASE_URL}/api/v1/exam/${examId}/questions/${questionId}`, {
      method: 'DELETE',
      headers: getHeaders(true),
    });
  },

  submit: (examId, data) => {
    logger.info('API', `POST /exam/${examId}/submit — answers=${data.answers?.length || 0}`);
    return fetch(`${BASE_URL}/api/v1/exam/${examId}/submit`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },
};

// ── Proctoring APIs (Sprint 2) ──────────────────────
export const proctoringAPI = {
  getLogs: (email = '', testId = '') => {
    logger.debug('API', `GET /proctoring/logs — email=${email}, testId=${testId}`);
    const params = new URLSearchParams();
    if (email) params.set('email', email);
    if (testId) params.set('test_id', testId);
    return fetch(`${BASE_URL}/api/v1/proctoring/logs?${params}`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },

  createLog: (data) => {
    logger.info('API', `POST /proctoring/logs — email=${data.email}`);
    return fetch(`${BASE_URL}/api/v1/proctoring/logs`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },

  logViolation: (data) => {
    logger.info('API', `POST /proctoring/log_violation — type=${data.violation_type}, email=${data.email}`);
    return fetch(`${BASE_URL}/api/v1/proctoring/log_violation`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },

  // ── Sprint 3 additions ──────────────────────────

  /** Send a batch of violations to the async buffer endpoint. */
  logViolationBatch: (data) => {
    logger.info('API', `POST /proctoring/log_violations_batch — count=${data.violations?.length || 0}`);
    return fetch(`${BASE_URL}/api/v1/proctoring/log_violations_batch`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },

  /** List violations with optional filters. */
  listViolations: (email = '', testId = '', violationType = '') => {
    logger.debug('API', `GET /proctoring/violations — email=${email}, testId=${testId}, type=${violationType}`);
    const params = new URLSearchParams();
    if (email) params.set('email', email);
    if (testId) params.set('test_id', testId);
    if (violationType) params.set('violation_type', violationType);
    return fetch(`${BASE_URL}/api/v1/proctoring/violations?${params}`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },

  /** Get a presigned PUT URL for uploading evidence to MinIO. */
  getEvidenceUploadUrl: (data) => {
    logger.debug('API', `POST /proctoring/evidence/upload-url — type=${data.violation_type}`);
    return fetch(`${BASE_URL}/api/v1/proctoring/evidence/upload-url`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },

  /** Force-flush pending violations from the backend buffer to DB. */
  flushBuffer: () => {
    logger.info('API', 'POST /proctoring/flush');
    return fetch(`${BASE_URL}/api/v1/proctoring/flush`, {
      method: 'POST',
      headers: getHeaders(true),
    }).then(handleResponse);
  },
};

// ── Window Events APIs (Sprint 2) ───────────────────
export const windowEventsAPI = {
  list: (email = '', testId = '') => {
    logger.debug('API', `GET /window-events — email=${email}, testId=${testId}`);
    const params = new URLSearchParams();
    if (email) params.set('email', email);
    if (testId) params.set('test_id', testId);
    return fetch(`${BASE_URL}/api/v1/window-events/?${params}`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },

  create: (data) => {
    logger.info('API', `POST /window-events — email=${data.email}`);
    return fetch(`${BASE_URL}/api/v1/window-events/`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },
};

// ── Reports APIs (Sprint 4) ─────────────────────────
export const reportsAPI = {
  /** Compute trust score without generating a full report. */
  getTrustScore: (data) => {
    logger.info('API', `POST /reports/trust-score — test_id=${data.test_id}, email=${data.email}`);
    return fetch(`${BASE_URL}/api/v1/reports/trust-score`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },

  /** Generate a full proctoring report (trust + PDF). */
  generate: (data) => {
    logger.info('API', `POST /reports/generate — test_id=${data.test_id}, email=${data.email}`);
    return fetch(`${BASE_URL}/api/v1/reports/generate`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },

  /** List reports with optional filters. */
  list: (testId = '', email = '') => {
    logger.debug('API', `GET /reports — testId=${testId}, email=${email}`);
    const params = new URLSearchParams();
    if (testId) params.set('test_id', testId);
    if (email) params.set('email', email);
    return fetch(`${BASE_URL}/api/v1/reports/?${params}`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },

  /** Get a single report by ID. */
  get: (reportId) => {
    logger.info('API', `GET /reports/${reportId}`);
    return fetch(`${BASE_URL}/api/v1/reports/${reportId}`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },

  /** Download report PDF (returns blob). */
  downloadPdf: (reportId) => {
    logger.info('API', `GET /reports/${reportId}/pdf`);
    return fetch(`${BASE_URL}/api/v1/reports/${reportId}/pdf`, {
      headers: getHeaders(true),
    }).then((res) => {
      if (!res.ok) {
        logger.error('API', `PDF download failed: ${res.status}`, { reportId });
        throw new Error('PDF download failed');
      }
      logger.info('API', `PDF downloaded: report_id=${reportId}`);
      return res.blob();
    });
  },
};

// ── Admin APIs (Sprint 5) ───────────────────────────
export const adminAPI = {
  /** List violations with actions (admin-only, enriched view). */
  listViolations: (email = '', testId = '', violationType = '', severity = '') => {
    logger.info('API', `GET /admin/violations — email=${email}, testId=${testId}`);
    const params = new URLSearchParams();
    if (email) params.set('email', email);
    if (testId) params.set('test_id', testId);
    if (violationType) params.set('violation_type', violationType);
    if (severity) params.set('severity', severity);
    return fetch(`${BASE_URL}/api/v1/admin/violations?${params}`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },

  /** Get total violation count for dashboard stats. */
  countViolations: (email = '', testId = '') => {
    logger.debug('API', `GET /admin/violations/count — email=${email}, testId=${testId}`);
    const params = new URLSearchParams();
    if (email) params.set('email', email);
    if (testId) params.set('test_id', testId);
    return fetch(`${BASE_URL}/api/v1/admin/violations/count?${params}`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },

  /** Perform an admin action (warn / invalidate / ban) on a violation. */
  performAction: (data) => {
    logger.info('API', `POST /admin/actions — violation_id=${data.violation_id}, action=${data.action_type}`);
    return fetch(`${BASE_URL}/api/v1/admin/actions`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    }).then(handleResponse);
  },

  /** List admin action audit log. */
  listActions: (violationId = '') => {
    logger.debug('API', `GET /admin/actions — violationId=${violationId}`);
    const params = new URLSearchParams();
    if (violationId) params.set('violation_id', violationId);
    return fetch(`${BASE_URL}/api/v1/admin/actions?${params}`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },

  /** Get per-exam student summary (violations + trust scores). */
  examStudents: (testId = '') => {
    logger.info('API', `GET /admin/exam-students — testId=${testId}`);
    const params = new URLSearchParams();
    if (testId) params.set('test_id', testId);
    return fetch(`${BASE_URL}/api/v1/admin/exam-students?${params}`, {
      headers: getHeaders(true),
    }).then(handleResponse);
  },
};

export default {
  authAPI,
  usersAPI,
  examsAPI,
  proctoringAPI,
  windowEventsAPI,
  reportsAPI,
  adminAPI,
};
