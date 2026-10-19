import React from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';
function App(){return <main><h1>BhashaBridge 2.0</h1><p>Phase 1 prototype scaffold</p><p role="status">Translation and NLP modules are not implemented yet.</p><label htmlFor="sentence">Code-mixed sentence</label><textarea id="sentence" placeholder="nenu college ki vellanu" disabled/><button disabled>Analyze (coming in a later phase)</button></main>}
createRoot(document.getElementById('root')).render(<App/>);
