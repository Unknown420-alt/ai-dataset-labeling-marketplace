import { useEffect, useState } from 'react'
import api from '../../api'
import Card, { CardHeader } from '../ui/Card'
import Badge from '../ui/Badge'
import EmptyState from '../ui/EmptyState'
import { LoadingPage } from '../ui/LoadingSpinner'

function shortDate(iso) {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' })
}

export default function AnalyticsTab() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/analytics/overview')
      .then((res) => setData(res.data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingPage />
  if (error) {
    return (
      <div className="p-3 rounded-lg bg-clay-50 text-clay-700 text-sm">{error}</div>
    )
  }
  if (!data || data.tasks === 0) {
    return (
      <EmptyState
        title="Nothing to measure yet"
        description="Create a dataset and a task — your throughput, progress, and agreement will show up here."
      />
    )
  }

  const maxDay = Math.max(1, ...data.daily_submissions.map((d) => d.count))
  const stats = [
    { label: 'Datasets', value: data.datasets },
    { label: 'Tasks', value: data.tasks },
    { label: 'Items labeled', value: `${data.labeled} / ${data.items}` },
    { label: 'Submissions', value: data.submissions },
    { label: 'Agreement', value: `${Math.round(data.overall_agreement * 100)}%` },
    { label: 'Gold coverage', value: `${Math.round((data.gold_coverage || 0) * 100)}%` },
    { label: 'Gold accuracy', value: data.gold_accuracy != null ? `${Math.round(data.gold_accuracy * 100)}%` : '—' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-sand-900">Analytics</h2>
        <p className="text-sm text-sand-500 mt-0.5">
          How fast labels come in, where each task stands, and how much labelers agree.
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {stats.map((s) => (
          <Card key={s.label}>
            <div className="text-sm text-sand-500">{s.label}</div>
            <div className="text-2xl font-semibold text-sand-900 mt-1">{s.value}</div>
          </Card>
        ))}
      </div>

      {/* Throughput */}
      <Card>
        <CardHeader title="Labels per day" subtitle="Submissions across all your tasks, last 14 days." />
        <div className="mt-4 flex items-end gap-1.5 h-32">
          {data.daily_submissions.map((d) => (
            <div key={d.date} className="flex-1 flex flex-col items-center gap-1 min-w-0" title={`${d.date}: ${d.count}`}>
              <div className="w-full flex items-end flex-1">
                <div
                  className={`w-full rounded-t-md transition-all ${d.count ? 'bg-clay-500' : 'bg-sand-100'}`}
                  style={{ height: `${Math.max(d.count ? 8 : 4, (d.count / maxDay) * 100)}%` }}
                />
              </div>
              <span className="text-[10px] text-sand-400">{shortDate(d.date)}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Per-task progress */}
      <Card padding={false}>
        <div className="px-5 sm:px-6 pt-5 pb-3">
          <CardHeader title="Tasks" subtitle="Progress and agreement per task." />
        </div>
        <div className="px-5 sm:px-6 pb-5 space-y-4">
          {data.per_task.map((t) => {
            const pct = t.total ? Math.round((t.labeled / t.total) * 100) : 0
            return (
              <div key={t.task_id}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-sand-800 truncate">{t.title}</span>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Badge variant="default" dot>{t.status?.replace('_', ' ')}</Badge>
                    <span className="text-xs text-sand-500">{t.labeled}/{t.total} · {Math.round(t.agreement * 100)}% agree{t.gold_items ? ` · ★ ${t.gold_items}` : ''}</span>
                  </div>
                </div>
                <div className="mt-1.5 h-1.5 bg-sand-100 rounded-full overflow-hidden">
                  <div className="h-full bg-moss-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
                </div>
              </div>
            )
          })}
        </div>
      </Card>

      {/* Label distribution */}
      {Object.keys(data.label_distribution || {}).length > 0 && (
        <Card>
          <CardHeader title="Label mix" subtitle="What the final labels look like across everything." />
          <div className="mt-3 flex flex-wrap gap-1.5">
            {Object.entries(data.label_distribution).map(([k, v]) => (
              <span key={k} className="px-2.5 py-1 text-xs rounded-lg bg-sand-100 text-sand-700">
                {k} · {v}
              </span>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
