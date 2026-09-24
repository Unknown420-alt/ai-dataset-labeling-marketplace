import { useState } from 'react'
import Login from './components/Login'
import Signup from './components/Signup'
import VerifyEmail from './components/VerifyEmail'
import Dashboard from './components/Dashboard'

function readUser() {
  const raw = localStorage.getItem('user')
  try {
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export default function App() {
  const [user, setUser] = useState(readUser)
  const [screen, setScreen] = useState('login')
  const [pending, setPending] = useState(null) // {email, devCode} after signup

  function handleAuth(accessToken, userData, opts = {}) {
    if (opts.requiresVerification) {
      setPending({ email: opts.email, devCode: opts.devCode });
      return
    }
    localStorage.setItem('token', accessToken)
    localStorage.setItem('user', JSON.stringify(userData))
    setUser(userData)
    setPending(null)
  }

  function handleLogout() {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
    setPending(null)
    setScreen('login')
  }

  if (pending && !user) {
    return (
      <VerifyEmail
        email={pending.email}
        devCode={pending.devCode}
        onVerified={handleAuth}
        onBack={() => { setPending(null); setScreen('login') }}
      />
    )
  }

  if (!user) {
    return screen === 'signup' ? (
      <Signup onAuth={handleAuth} goToLogin={() => setScreen('login')} />
    ) : (
      <Login onAuth={handleAuth} goToSignup={() => setScreen('signup')} />
    )
  }

  if (!user.email_verified) {
    return (
      <VerifyEmail
        email={user.email}
        onVerified={handleAuth}
        onBack={handleLogout}
      />
    )
  }

  return <Dashboard user={user} onLogout={handleLogout} />
}