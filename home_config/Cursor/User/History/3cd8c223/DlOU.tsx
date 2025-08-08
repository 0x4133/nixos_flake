import React, { useEffect } from 'react';
import { Flow } from './components/Flow';
import { MinimalTest } from './components/MinimalTest';
import { useAppStore } from './store';

function App() {
  const { theme, setTheme, currentProject, createProject } = useAppStore();

  useEffect(() => {
    // Apply theme to document
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  useEffect(() => {
    // Create default project if none exists
    if (!currentProject) {
      createProject('My API Workflow');
    }
  }, [currentProject, createProject]);

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  return (
    <div className={`h-screen ${theme === 'dark' ? 'dark' : ''}`}>
      {/* Theme Toggle */}
      <div className="fixed top-4 right-4 z-50">
        <button
          onClick={toggleTheme}
          className="btn btn-circle btn-sm"
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
          {theme === 'light' ? '🌙' : '☀️'}
        </button>
      </div>

      {/* Main Content */}
      <Flow />
    </div>
  );
}

export default App;
