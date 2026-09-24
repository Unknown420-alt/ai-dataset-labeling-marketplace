import { useState } from 'react'
import api from '../api'
import Button from './ui/Button'
import Input from './ui/Input'
import Card from './ui/Card'

export default function Login({ onAuth, goToSignup }) {
  const [mode, setMode] = useState('password') // password | code
  const [form, setForm] = useState({ email: '', password: '' })
  const [code, setCode] = useState('')
  const [codeSent, setCodeSent] = useState(false)
  const [devHint, setDevHint] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [needsVerify, setNeedsVerify] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setNeedsVerify('')
    setLoading(true)
    try {
      const res = await api.post('/auth/login', form)
      onAuth(res.data.access_token, res.data.user)
    } catch (err) {
      setError(err.message)
      if (/verify your email/i.test(err.message)) setNeedsVerify(form.email)
    } finally {
      setLoading(false)
    }
  }

  async function handleSendCode(e) {
    e?.preventDefault()
    setError('')
    setDevHint('')
    setLoading(true)
    try {
      const res = await api.post('/auth/otp/request', { email: form.email, purpose: 'login' })
      if (res.data?.dev_code) setDevHint(res.data.dev_code)
      setCodeSent(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleCodeLogin(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.post('/auth/otp/login', { email: form.email, code: code.trim() })
      onAuth(res.data.access_token, res.data.user)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleResendVerify() {
    setError('')
    setLoading(true)
    try {
      const res = await api.post('/auth/otp/request', { email: needsVerify, purpose: 'verify' })
      if (res.data?.dev_code) setDevHint(res.data.dev_code)
      setError('')
      setNeedsVerify('')
      setMode('code')
      setForm((f) => ({ ...f, email: needsVerify }))
      setCodeSent(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-sand-50 px-4">
      <div className="w-full max-w-md fade-in">
        {/* Logo / Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-clay-100 mb-4">
            <svg className="w-7 h-7 text-clay-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <h1 className="text-2xl font-semibold text-sand-900">Welcome back</h1>
          <p className="text-sm text-sand-500 mt-1">
            Sign in to manage datasets or earn by labeling.
          </p>
        </div>

        <Card>
          <div className="grid grid-cols-2 gap-1 p-1 mb-4 rounded-lg bg-sand-100 text-sm font-medium">
            {['password', 'code'].map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => { setMode(m); setError(''); setCodeSent(false) }}
                className={`py-1.5 rounded-md transition-colors
                  ${mode === m ? 'bg-white text-sand-900 shadow-sm' : 'text-sand-500 hover:text-sand-700'}`}
              >
                {m === 'password' ? 'Password' : 'Email code'}
              </button>
            ))}
          </div>

          {mode === 'password' ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Email"
              type="email"
              required
              placeholder="you@example.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
            <Input
              label="Password"
              type="password"
              required
              placeholder="Your password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />

            {error && (
              <div className="p-3 rounded-lg bg-clay-50 text-clay-700 text-sm">
                {error}
                {needsVerify && (
                  <button
                    type="button"
                    onClick={handleResendVerify}
                    className="ml-1 font-medium underline"
                  >
                    Send me the code again
                  </button>
                )}
              </div>
            )}

            <Button type="submit" loading={loading} className="w-full">
              Sign in
            </Button>
          </form>
          ) : (
          <form onSubmit={codeSent ? handleCodeLogin : handleSendCode} className="space-y-4">
            <Input
              label="Email"
              type="email"
              required
              placeholder="you@example.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
            {codeSent && (
              <Input
                label="6-digit code"
                required
                inputMode="numeric"
                placeholder="123456"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              />
            )}
            {devHint && (
              <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                Dev mode (no mail server): your code is <span className="font-mono font-semibold">{devHint}</span>
              </p>
            )}
            {error && (
              <div className="p-3 rounded-lg bg-clay-50 text-clay-700 text-sm">{error}</div>
            )}
            <Button type="submit" loading={loading} disabled={codeSent && code.length !== 6} className="w-full">
              {codeSent ? 'Sign in with code' : 'Send me a code'}
            </Button>
            {codeSent && (
              <p className="text-center text-sm">
                <button type="button" onClick={handleSendCode} className="text-sand-400 hover:text-sand-600">
                  Send a fresh code
                </button>
              </p>
            )}
          </form>
          )}

          <div className="mt-5 pt-4 border-t border-sand-100 text-center">
            <p className="text-sm text-sand-500">
              No account yet?{' '}
              <button
                onClick={goToSignup}
                className="font-medium text-clay-600 hover:text-clay-700"
              >
                Create one
              </button>
            </p>
          </div>
        </Card>
      </div>
    </div>
  )
}
