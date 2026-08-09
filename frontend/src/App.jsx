import { useState } from 'react'
import Login from './components/Login'
import Signup from './components/Signup'
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

  function handleAuth(accessToken, userData) {
    localStorage.setItem('token', accessToken)
    localStorage.setItem('user', JSON.stringify(userData))
    setUser(userData)
  }

  function handleLogout() {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
    setScreen('login')
  }

  if (!user) {
    return screen === 'signup' ? (
      <Signup onAuth={handleAuth} goToLogin={() => setScreen('login')} />
    ) : (
      <Login onAuth={handleAuth} goToSignup={() => setScreen('signup')} />
    )
  }

  return <Dashboard user={user} onLogout={handleLogout} />
}