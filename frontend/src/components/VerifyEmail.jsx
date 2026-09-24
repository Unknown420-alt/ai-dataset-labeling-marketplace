import { useState } from 'react'
import api from '../api'
import Button from './ui/Button'
import Input from './ui/Input'
import Card from './ui/Card'

export default function VerifyEmail({ email, devCode, onVerified, onBack }) {
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [resending, setResending] = useState(false)
  const [sentMsg, setSentMsg] = useState('')
  const [hintCode, setHintCode] = useState(devCode || '')

  async function handleVerify(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.post('/auth/otp/verify', { email, code: code.trim() })
      if (res.data?.access_token) {
        onVerified(res.data.access_token, res.data.user)
      } else {
        setError('Verified! Please sign in with your new account.')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleResend() {
    setError('')
    setSentMsg('')
    setResending(true)
    try {
      const res = await api.post('/auth/otp/request', { email, purpose: 'verify' })
      if (res.data?.dev_code) setHintCode(res.data.dev_code)
      setSentMsg('A fresh code is on its way — check your inbox.')
    } catch (err) {
      setError(err.message)
    } finally {
      setResending(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-sand-50 px-4">
      <div className="w-full max-w-md fade-in">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-sky-100 mb-4">
            <svg className="w-7 h-7 text-sky-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h1 className="text-2xl font-semibold text-sand-900">Check your inbox</h1>
          <p className="text-sm text-sand-500 mt-1">
            We sent a 6-digit code to <span className="font-medium text-sand-700">{email}</span>.
            It expires in 10 minutes.
          </p>
        </div>

        <Card>
          <form onSubmit={handleVerify} className="space-y-4">
            <Input
              label="Verification code"
              required
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="123456"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              hint="6 digits, numbers only."
            />

            {hintCode && (
              <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                Dev mode (no mail server): your code is <span className="font-mono font-semibold">{hintCode}</span>
              </p>
            )}

            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-clay-50 text-clay-700 text-sm">
                {error}
              </div>
            )}
            {sentMsg && (
              <p className="text-sm text-moss-600">{sentMsg}</p>
            )}

            <Button type="submit" loading={loading} disabled={code.length !== 6} className="w-full">
              Verify email
            </Button>
          </form>

          <div className="mt-5 pt-4 border-t border-sand-100 text-center space-y-2">
            <p className="text-sm text-sand-500">
              Nothing arrived?{' '}
              <button
                onClick={handleResend}
                disabled={resending}
                className="font-medium text-clay-600 hover:text-clay-700 disabled:opacity-50"
              >
                {resending ? 'Sending…' : 'Send it again'}
              </button>
            </p>
            {onBack && (
              <p className="text-sm">
                <button onClick={onBack} className="text-sand-400 hover:text-sand-600">
                  ← Back to sign in
                </button>
              </p>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
