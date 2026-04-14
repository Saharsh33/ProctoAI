import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Toast from '../components/Toast';
import useToast from '../hooks/useToast';
import useAuth from '../hooks/useAuth';
import LoadingSpinner from '../components/LoadingSpinner';
import { reportsAPI, examsAPI } from '../services/api';

// ── Trust Score Gauge ─────────────────────────────────
const TrustScoreGauge = ({ score }) => {
  const color = score >= 70 ? '#10b981' : score >= 40 ? '#f59e0b' : '#ef4444';
  const label = score >= 70 ? 'Good' : score >= 40 ? 'Review' : 'Critical';
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div style={{ textAlign: 'center' }}>
      <svg width="140" height="140" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r="54" fill="none" stroke="#e2e8f0" strokeWidth="8" />
        <circle
          cx="60" cy="60" r="54" fill="none"
          stroke={color} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transform: 'rotate(-90deg)', transformOrigin: '60px 60px', transition: 'stroke-dashoffset 1s ease' }}
        />
        <text x="60" y="55" textAnchor="middle" fontSize="28" fontWeight="700" fill={color}>{score}</text>
        <text x="60" y="72" textAnchor="middle" fontSize="10" fill="#94a3b8">/100</text>
      </svg>
      <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', fontWeight: 600, color }}>{label}</div>
    </div>
  );
};

// ── Marks Display Card ────────────────────────────────
const MarksDisplay = ({ obtained, total }) => {
  if (!total || total === 0) return null;
  
  const percentage = Math.round((obtained / total) * 100);
  const color = percentage >= 70 ? '#10b981' : percentage >= 40 ? '#f59e0b' : '#ef4444';
  const label = percentage >= 70 ? 'Excellent' : percentage >= 40 ? 'Average' : 'Below Average';

  return (
    <div style={{ textAlign: 'center' }}>
      <svg width="140" height="140" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r="54" fill="none" stroke="#e2e8f0" strokeWidth="8" />
        <circle
          cx="60" cy="60" r="54" fill="none"
          stroke={color} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={2 * Math.PI * 54}
          strokeDashoffset={2 * Math.PI * 54 - (percentage / 100) * 2 * Math.PI * 54}
          style={{ transform: 'rotate(-90deg)', transformOrigin: '60px 60px', transition: 'stroke-dashoffset 1s ease' }}
        />
        <text x="60" y="55" textAnchor="middle" fontSize="28" fontWeight="700" fill={color}>{percentage}</text>
        <text x="60" y="72" textAnchor="middle" fontSize="10" fill="#94a3b8">%</text>
      </svg>
      <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', fontWeight: 600, color }}>{label}</div>
      <div style={{ marginTop: '0.25rem', fontSize: '0.75rem', color: '#64748b' }}>{obtained}/{total}</div>
    </div>
  );
};

// ── Violation Breakdown Card ──────────────────────────
const BreakdownTable = ({ breakdown }) => {
  if (!breakdown || breakdown.length === 0) {
    return (
      <div style={{ padding: '1.5rem', textAlign: 'center', color: '#10b981', fontSize: '0.95rem' }}>
        ✅ No violations recorded – excellent conduct.
      </div>
    );
  }

  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
      <thead>
        <tr style={{ background: '#4f46e5', color: 'white' }}>
          <th style={{ padding: '0.75rem 1rem', textAlign: 'left' }}>Violation Type</th>
          <th style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>Count</th>
          <th style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>Weight</th>
          <th style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>Penalty</th>
        </tr>
      </thead>
      <tbody>
        {breakdown.map((item, i) => (
          <tr key={item.type} style={{ background: i % 2 === 0 ? '#f8fafc' : 'white' }}>
            <td style={{ padding: '0.625rem 1rem' }}>{item.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</td>
            <td style={{ padding: '0.625rem 1rem', textAlign: 'center' }}>{item.count}</td>
            <td style={{ padding: '0.625rem 1rem', textAlign: 'center' }}>{item.weight}</td>
            <td style={{ padding: '0.625rem 1rem', textAlign: 'center', color: '#ef4444', fontWeight: 600 }}>−{item.subtotal}</td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr style={{ borderTop: '2px solid #cbd5e1', fontWeight: 700 }}>
          <td colSpan={3} style={{ padding: '0.625rem 1rem', textAlign: 'right' }}>Total Penalty</td>
          <td style={{ padding: '0.625rem 1rem', textAlign: 'center', color: '#ef4444' }}>
            −{breakdown.reduce((sum, b) => sum + b.subtotal, 0)}
          </td>
        </tr>
      </tfoot>
    </table>
  );
};

const ExamReports = () => {
  const { user } = useAuth();
  const { toasts, addToast, removeToast } = useToast();
  const [searchParams] = useSearchParams();

  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [filterExam, setFilterExam] = useState(searchParams.get('test_id') || '');
  const [filterEmail, setFilterEmail] = useState(searchParams.get('email') || '');

  const loadReports = useCallback(async () => {
    try {
      setLoading(true);
      const data = await reportsAPI.list(filterExam, filterEmail);
      setReports(data);
    } catch (err) {
      addToast(err.message || 'Failed to load reports', 'error');
    } finally {
      setLoading(false);
    }
  }, [filterExam, filterEmail, addToast]);

  const loadExams = useCallback(async () => {
    try {
      const data = await examsAPI.list(0, 200);
      setExams(data);
    } catch {
      // non-critical
    }
  }, []);

  useEffect(() => { loadReports(); }, [loadReports]);
  useEffect(() => { loadExams(); }, [loadExams]);

  const handleGenerate = async (testId, email, uid) => {
    setGenerating(true);
    try {
      const report = await reportsAPI.generate({ test_id: testId, email, uid });
      addToast('Report generated successfully!', 'success');
      setSelectedReport(report);
      loadReports();
    } catch (err) {
      addToast(err.message || 'Failed to generate report', 'error');
    } finally {
      setGenerating(false);
    }
  };

  const handleDownloadPdf = async (reportId) => {
    try {
      const blob = await reportsAPI.downloadPdf(reportId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `proctoring_report_${reportId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      addToast('PDF downloaded', 'success');
    } catch (err) {
      addToast(err.message || 'PDF download failed', 'error');
    }
  };

  const handleViewReport = async (reportId) => {
    try {
      const report = await reportsAPI.get(reportId);
      setSelectedReport(report);
    } catch (err) {
      addToast(err.message || 'Failed to load report', 'error');
    }
  };

  const parseBreakdown = (json) => {
    try { return JSON.parse(json); }
    catch { return []; }
  };

  return (
    <div>
      <Navbar />
      <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '2rem 1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>📊 Exam Reports</h1>
            <p style={{ color: 'var(--text-light)', fontSize: '0.875rem' }}>
              AI-generated proctoring reports with trust scores and violation analysis
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="card card-no-hover" style={{ marginBottom: '1.5rem' }}>
          <div className="card-body" style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 200 }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-light)', display: 'block', marginBottom: '0.25rem' }}>
                Filter by Exam
              </label>
              <select
                className="input"
                value={filterExam}
                onChange={(e) => setFilterExam(e.target.value)}
                style={{ width: '100%' }}
              >
                <option value="">All Exams</option>
                {exams.map((ex) => (
                  <option key={ex.examId} value={ex.examId}>{ex.title}</option>
                ))}
              </select>
            </div>
            <div style={{ flex: 1, minWidth: 200 }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-light)', display: 'block', marginBottom: '0.25rem' }}>
                Filter by Email
              </label>
              <input
                className="input"
                placeholder="student@example.com"
                value={filterEmail}
                onChange={(e) => setFilterEmail(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>
            <button className="btn btn-secondary" onClick={loadReports} style={{ height: 40 }}>
              🔍 Search
            </button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: selectedReport ? '1fr 1fr' : '1fr', gap: '1.5rem' }}>
          {/* Report List */}
          <div>
            {loading ? (
              <div style={{ textAlign: 'center', padding: '3rem' }}><LoadingSpinner /></div>
            ) : reports.length === 0 ? (
              <div className="card card-no-hover" style={{ textAlign: 'center', padding: '3rem' }}>
                <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📋</div>
                <p style={{ color: 'var(--text-light)' }}>No reports found. Generate one after an exam is completed.</p>
              </div>
            ) : (
              <div style={{ display: 'grid', gap: '0.75rem' }}>
                {reports.map((r) => {
                  const scoreColor = r.trust_score >= 70 ? '#10b981' : r.trust_score >= 40 ? '#f59e0b' : '#ef4444';
                  const marksPercentage = r.total_marks > 0 ? Math.round((r.obtained_marks / r.total_marks) * 100) : 0;
                  const marksColor = marksPercentage >= 70 ? '#10b981' : marksPercentage >= 40 ? '#f59e0b' : '#ef4444';
                  
                  return (
                    <div
                      key={r.report_id}
                      className="card"
                      onClick={() => handleViewReport(r.report_id)}
                      style={{
                        cursor: 'pointer',
                        border: selectedReport?.report_id === r.report_id ? '2px solid var(--primary)' : undefined,
                      }}
                    >
                      <div className="card-body" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '0.25rem' }}>
                            {r.email}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-light)' }}>
                            Exam: {exams.find(e => e.examId === r.test_id)?.title || r.test_id}
                          </div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.125rem' }}>
                            {new Date(r.generated_at).toLocaleString()} · {r.total_violations} violation{r.total_violations !== 1 ? 's' : ''}
                          </div>
                          {r.total_marks > 0 && (
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-light)', marginTop: '0.25rem' }}>
                              📊 Marks: <span style={{ fontWeight: 600, color: marksColor }}>{r.obtained_marks}/{r.total_marks}</span>
                            </div>
                          )}
                        </div>
                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                          {r.total_marks > 0 && (
                            <div style={{
                              fontSize: '1.125rem', fontWeight: 700, color: marksColor,
                              minWidth: 45, textAlign: 'center', padding: '0.5rem',
                              background: `${marksColor}15`, borderRadius: '0.375rem',
                            }}>
                              {marksPercentage}%
                            </div>
                          )}
                          <div style={{
                            fontSize: '1.5rem', fontWeight: 700, color: scoreColor,
                            minWidth: 50, textAlign: 'center',
                          }}>
                            {r.trust_score}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Report Detail */}
          {selectedReport && (
            <div style={{ position: 'sticky', top: '5rem', alignSelf: 'flex-start' }}>
              <div className="card card-no-hover">
                <div className="card-body">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                    <div>
                      <h2 style={{ fontSize: '1.125rem', fontWeight: 700, marginBottom: '0.25rem' }}>Report Detail</h2>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-light)' }}>{selectedReport.email}</div>
                    </div>
                    <button
                      style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text-light)' }}
                      onClick={() => setSelectedReport(null)}
                    >×</button>
                  </div>

                  <TrustScoreGauge score={selectedReport.trust_score} />

                  {(selectedReport.total_marks > 0 || selectedReport.obtained_marks >= 0) && (
                    <div style={{ margin: '1.25rem 0' }}>
                      <h3 style={{ fontSize: '0.875rem', fontWeight: 700, marginBottom: '0.5rem' }}>Exam Performance</h3>
                      <div style={{ display: 'flex', justifyContent: 'center' }}>
                        <MarksDisplay obtained={selectedReport.obtained_marks} total={selectedReport.total_marks} />
                      </div>
                    </div>
                  )}

                  <div style={{ margin: '1.25rem 0' }}>
                    <h3 style={{ fontSize: '0.875rem', fontWeight: 700, marginBottom: '0.5rem' }}>Violation Breakdown</h3>
                    <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
                      <BreakdownTable breakdown={parseBreakdown(selectedReport.violation_breakdown_json)} />
                    </div>
                  </div>

                  {selectedReport.summary && (
                    <div style={{ marginBottom: '1.25rem' }}>
                      <h3 style={{ fontSize: '0.875rem', fontWeight: 700, marginBottom: '0.5rem' }}>Summary</h3>
                      <p style={{ fontSize: '0.825rem', lineHeight: 1.6, color: 'var(--text-light)' }}>{selectedReport.summary}</p>
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: '0.75rem' }}>
                    {selectedReport.pdf_path && (
                      <button
                        className="btn btn-primary"
                        onClick={() => handleDownloadPdf(selectedReport.report_id)}
                        style={{ flex: 1 }}
                      >
                        📥 Download PDF
                      </button>
                    )}
                    <button
                      className="btn btn-secondary"
                      onClick={() => handleGenerate(selectedReport.test_id, selectedReport.email, selectedReport.uid)}
                      disabled={generating}
                      style={{ flex: 1 }}
                    >
                      {generating ? <LoadingSpinner /> : '🔄 Regenerate'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      <Toast toasts={toasts} onRemove={removeToast} />
    </div>
  );
};

export default ExamReports;
