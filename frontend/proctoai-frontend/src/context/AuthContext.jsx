import { createContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';
import logger from '../utils/logger';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(() => !!localStorage.getItem('token'));

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      logger.debug('AuthContext', 'No token found, skipping auto-login');
      return;
    }
    logger.info('AuthContext', 'Token found, attempting auto-login');
    authAPI
      .me()
      .then((u) => {
        setUser(u);
        logger.info('AuthContext', 'Auto-login successful', { userId: u.user_id, role: u.role });
      })
      .catch((err) => {
        logger.warn('AuthContext', 'Auto-login failed, clearing token', { error: err.message });
        localStorage.removeItem('token');
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    logger.info('AuthContext', `Logging in: email=${email}`);
    const data = await authAPI.login(email, password);
    localStorage.setItem('token', data.access_token);
    const me = await authAPI.me();
    setUser(me);
    logger.info('AuthContext', 'Login successful', { userId: me.user_id, role: me.role });
    return me;
  };

  const signup = async (userData) => {
    logger.info('AuthContext', `Signing up: email=${userData.email}, role=${userData.role}`);
    const result = await authAPI.signup(userData);
    logger.info('AuthContext', 'Signup successful', { userId: result.user_id });
    return result;
  };

  const logout = () => {
    logger.info('AuthContext', 'User logging out', { userId: user?.user_id });
    localStorage.removeItem('token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
