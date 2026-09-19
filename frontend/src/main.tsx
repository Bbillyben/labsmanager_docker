import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './app/App'
import './styles/global.css'

// Apply the local display preference before the first React paint.
try {
  const saved = localStorage.getItem('labsmanager-theme')
  const dark = saved ? saved === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches
  document.documentElement.classList.toggle('dark', dark)
} catch { /* Browser storage may be unavailable. */ }

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
