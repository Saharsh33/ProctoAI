/**
 * ProctoAI Frontend Logger
 *
 * Provides structured, levelled logging for the frontend.
 * Log levels: DEBUG < INFO < WARN < ERROR
 *
 * Usage:
 *   import logger from '../utils/logger';
 *   logger.info('AuthContext', 'User logged in', { userId: '123' });
 *   logger.error('API', 'Request failed', { url, status });
 *
 * Configuration:
 *   Set LOG_LEVEL in .env: VITE_LOG_LEVEL=DEBUG (default: INFO in dev, WARN in prod)
 */

const LEVELS = { DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3 };

function getConfiguredLevel() {
  const envLevel = import.meta.env.VITE_LOG_LEVEL?.toUpperCase();
  if (envLevel && LEVELS[envLevel] !== undefined) return LEVELS[envLevel];
  return import.meta.env.DEV ? LEVELS.INFO : LEVELS.WARN;
}

const currentLevel = getConfiguredLevel();

function formatTimestamp() {
  return new Date().toISOString();
}

function formatMessage(level, module, message, data) {
  const ts = formatTimestamp();
  const prefix = `[${ts}] [${level}] [${module}]`;
  if (data !== undefined && data !== null) {
    return { prefix, message, data };
  }
  return { prefix, message };
}

const logger = {
  debug(module, message, data) {
    if (currentLevel <= LEVELS.DEBUG) {
      const { prefix, ...rest } = formatMessage('DEBUG', module, message, data);
      console.debug(`${prefix} ${rest.message}`, rest.data !== undefined ? rest.data : '');
    }
  },

  info(module, message, data) {
    if (currentLevel <= LEVELS.INFO) {
      const { prefix, ...rest } = formatMessage('INFO', module, message, data);
      console.info(`${prefix} ${rest.message}`, rest.data !== undefined ? rest.data : '');
    }
  },

  warn(module, message, data) {
    if (currentLevel <= LEVELS.WARN) {
      const { prefix, ...rest } = formatMessage('WARN', module, message, data);
      console.warn(`${prefix} ${rest.message}`, rest.data !== undefined ? rest.data : '');
    }
  },

  error(module, message, data) {
    if (currentLevel <= LEVELS.ERROR) {
      const { prefix, ...rest } = formatMessage('ERROR', module, message, data);
      console.error(`${prefix} ${rest.message}`, rest.data !== undefined ? rest.data : '');
    }
  },
};

export default logger;
