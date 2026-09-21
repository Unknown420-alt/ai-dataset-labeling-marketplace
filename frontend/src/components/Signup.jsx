import { useState } from 'react'
import api from '../api'
import Button from './ui/Button'
import Input from './ui/Input'
import Select from './ui/Select'
import Card from './ui/Card'

export default function Signup({ onAuth, goToLogin }) {
  const [form, setForm] = useState({ email: '', full_name: '', password: '', role: 'labeler' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.post('/auth/signup', form)
      onAuth(res.data.access_token, res.data.user)
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
              placeholder="At least 6 characters"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
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

            <Button type="submit" loading={loading} className="w-full">
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
