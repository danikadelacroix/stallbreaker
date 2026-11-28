import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { Landing } from './Landing.tsx'

// Two pages: the landing page at / and the demo at /demo (spec 115).
const onDemo = window.location.pathname.replace(/\/+$/, '') === '/demo'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {onDemo ? <App /> : <Landing />}
  </StrictMode>,
)
