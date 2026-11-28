import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { Landing } from './Landing.tsx'
import { RolePicker } from './roles/RolePicker.tsx'
import { TechnicianView } from './roles/TechnicianView.tsx'
import { PartsView } from './roles/PartsView.tsx'

// The landing page at /, the role picker at /demo, and one view per role under it (specs 115, 116).
const path = window.location.pathname.replace(/\/+$/, '')
const page = path === '/demo' ? <RolePicker />
  : path === '/demo/manager' ? <App />
  : path === '/demo/technician' ? <TechnicianView />
  : path === '/demo/parts' ? <PartsView />
  : <Landing />

createRoot(document.getElementById('root')!).render(<StrictMode>{page}</StrictMode>)
