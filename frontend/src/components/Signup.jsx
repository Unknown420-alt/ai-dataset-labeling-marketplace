import { useEffect, useState } from 'react'
import api from '../api'
import Button from './ui/Button'
import Input from './ui/Input'
import Select from './ui/Select'
import Card from './ui/Card'

function checkLocal(password, rules) {
  const has = (re) => re.test(password)
  const results = {}
  for (const r of rules) {
    if (r.key === 'length') results.length = password.length >= 8
    else if (r.key === 'upper') results.upper = has(/[A-Z]/)
    else if (r.key === 'lower') results.lower = has(/[a-z]/)
    else if (r.key === 'digit') results.digit = has(/[0-9]/)
    else if (r.key === 'special') results.special = has(/[^A-Za-z0-9]/)
  }
  return results
}

export default function Signup({ onAuth, goToLogin }) {
  const [form, setForm] = useState({ email: '', full_name: '', password: '', role: 'labeler' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [rules, setRules] = useState([])

  useEffect(() => {
    api.get('/auth/password-rules').then((res) => setRules(res.data)).catch(() => {})
  }, [])

  const passed = checkLocal(form.password, rules)
  const allOk = rules.length > 0 && rules.every((r) => passed[r.key])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.post('/auth/signup', form)
      if (res.data.requires_verification) {
        onAuth(null, null, {
          requiresVerification: true,
          email: form.email,
          devCode: res.data.dev_code,
        })
      } else {
        onAuth(res.data.access_token, res.data.user)
      }
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
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-moss-100 mb-4">
            <svg className="w-7 h-7 text-moss-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          </div>
          <h1 className="text-2xl font-semibold text-sand-900">Create your account</h1>
          <p className="text-sm text-sand-500 mt-1">
            Join as a dataset owner or labeler to get started.
          </p>
        </div>

        <Card>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Full name"
              required
              placeholder="Jane Doe"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            />
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
              placeholder="Make it a strong one"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
            {rules.length > 0 && form.password && (
              <ul className="space-y-1 rounded-lg bg-sand-50 border border-sand-100 px-3 py-2">
                {rules.map((r) => {
                  const ok = !!passed[r.key]
                  return (
                    <li key={r.key} className={`flex items-center gap-2 text-xs ${ok ? 'text-moss-600' : 'text-sand-400'}`}>
                      <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold
                        ${ok ? 'bg-moss-500 text-white' : 'bg-sand-200 text-sand-400'}`}>
                        {ok ? '✓' : '·'}
                      </span>
                      {r.label}
                    </li>
                  )
                })}
              </ul>
            )}
            <Select
              label="I want to"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
            >
              <option value="labeler">Label data — earn by completing tasks</option>
              <option value="owner">Own datasets — create and manage labeling tasks</option>
            </Select>

            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-clay-50 text-clay-700 text-sm">
                <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                {error}
              </div>
            )}

            <Button type="submit" loading={loading} disabled={form.password.length > 0 && !allOk} className="w-full">
              Create account
            </Button>
          </form>

          <div className="mt-5 pt-4 border-t border-sand-100 text-center">
            <p className="text-sm text-sand-500">
              Already have an account?{' '}
              <button
                onClick={goToLogin}
                className="font-medium text-clay-600 hover:text-clay-700"
              >
                Sign in
              </button>
            </p>
          </div>
        </Card>
      </div>
    </div>
  )
}
