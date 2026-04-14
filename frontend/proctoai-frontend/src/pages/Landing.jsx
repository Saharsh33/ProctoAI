import { Link, Navigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import useAuth from '../hooks/useAuth';

const ShieldSvg = () => (
  <svg viewBox="0 0 200 220" fill="none" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
    <defs>
      <linearGradient id="shieldGrad" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor="#4f46e5" />
        <stop offset="100%" stopColor="#06b6d4" />
      </linearGradient>
    </defs>
    <path d="M100 10 L180 45 L180 110 C180 158 144 196 100 210 C56 196 20 158 20 110 L20 45 Z"
      fill="url(#shieldGrad)" opacity="0.15" />
    <path d="M100 22 L168 53 L168 110 C168 151 137 184 100 197 C63 184 32 151 32 110 L32 53 Z"
      fill="url(#shieldGrad)" opacity="0.25" />
    <path d="M100 36 L156 62 L156 110 C156 144 130 172 100 183 C70 172 44 144 44 110 L44 62 Z"
      fill="url(#shieldGrad)" />
    <circle cx="100" cy="105" r="28" fill="white" opacity="0.9" />
    <circle cx="100" cy="105" r="16" fill="url(#shieldGrad)" />
    <path d="M92 105 L98 111 L110 99" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const Landing = () => {
  const { user, loading } = useAuth();

  // Redirect authenticated users straight to dashboard
  if (!loading && user) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="landing">
      <Navbar />

      {/* Hero */}
      <section className="hero">
        <div className="hero-content">
          <div className="hero-text">
            <div className="hero-eyebrow">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              Online Exam Proctoring Platform
            </div>
            <h1 className="hero-title">
              Online<br />
              <span>Exam Proctoring</span><br />
              Made Simple
            </h1>
            <p className="hero-subtitle">
              ProctoAI helps you run monitored online exams with clear logs and
              simple tools for admins and students.
            </p>
            <div className="hero-actions">
              <Link to="/signup" className="btn btn-primary btn-lg">
                Get Started
              </Link>
              <Link to="/signin" className="btn btn-outline btn-lg">
                Sign In
              </Link>
            </div>
          </div>
          <div className="hero-graphic">
            <ShieldSvg />
          </div>
        </div>
      </section>

      {/* Contact & Footer */}
      <footer className="footer">
        <div className="footer-contact">
          <span>Contact us: <a href="mailto:support@proctoai.com">support@proctoai.com</a></span>
        </div>
        <p>© {new Date().getFullYear()} <span>ProctoAI</span>. All rights reserved. Online exam proctoring.</p>
      </footer>
    </div>
  );
};

export default Landing;

