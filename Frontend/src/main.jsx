import React from 'react';
import ReactDOM from 'react-dom/client';
import ApproachBApp from './approach_b_ui/App';

// React 18 root rendering
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <ApproachBApp />
  </React.StrictMode>
);
