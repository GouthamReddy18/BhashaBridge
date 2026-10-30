import React, { useState, useEffect, useCallback } from 'react';
import { fetchResearchReadiness } from './api';
import { Header } from './components/Header';
import { Hero } from './components/Hero';
import { LanguageLab } from './components/LanguageLab';
import { PipelineExplorer } from './components/PipelineExplorer';
import { ResearchObservatory } from './components/ResearchObservatory';
import { MethodologySection } from './components/MethodologySection';
import { Footer } from './components/Footer';

export function App() {
  const [readiness, setReadiness] = useState(null);
  const [readinessLoading, setReadinessLoading] = useState(false);
  const [readinessError, setReadinessError] = useState('');
  const [toastMessage, setToastMessage] = useState('');

  const loadReadiness = useCallback(async () => {
    setReadinessLoading(true);
    setReadinessError('');
    try {
      const data = await fetchResearchReadiness();
      setReadiness(data);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setReadinessError('Readiness diagnostics unavailable. Backend may be offline.');
      }
    } finally {
      setReadinessLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReadiness();
  }, [loadReadiness]);

  const showNotification = useCallback((msg) => {
    setToastMessage(msg);
    const timer = setTimeout(() => setToastMessage(''), 3000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="observatory-app">
      {/* Accessibility Skip Link */}
      <a href="#lab" className="skip-link">
        Skip to Interactive Lab
      </a>

      {/* Persistent Sticky Header */}
      <Header readiness={readiness} />

      {/* Main Observatory Content */}
      <main id="main-content">
        <Hero readiness={readiness} />

        <LanguageLab onNotify={showNotification} />

        <PipelineExplorer />

        <ResearchObservatory
          readiness={readiness}
          onRefresh={loadReadiness}
          loading={readinessLoading}
        />

        <MethodologySection />
      </main>

      {/* Observatory Footer */}
      <Footer />

      {/* Global Toast Notification */}
      {toastMessage && (
        <div className="observatory-toast" role="status" aria-live="polite">
          <span className="toast-pip" />
          <span className="toast-text">{toastMessage}</span>
        </div>
      )}
    </div>
  );
}

export default App;
