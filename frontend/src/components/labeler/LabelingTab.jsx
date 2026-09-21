import { useEffect, useState } from 'react'
import api from '../../api'
import Button from '../ui/Button'
import Card, { CardHeader } from '../ui/Card'
import Badge from '../ui/Badge'
import EmptyState from '../ui/EmptyState'
import { LoadingPage } from '../ui/LoadingSpinner'

const statusVariant = {
  pending: 'warning',
  active: 'success',
  completed: 'default',
  draft: 'default',
}

function ProgressBadge({ items }) {
  const done = items.filter((i) => i.final_label).length
  const total = items.length
  const pct = total ? Math.round((done / total) * 100) : 0
  return (
    <div className="flex items-center gap-2 min-w-0">
      <div className="flex-1 h-1.5 bg-sand-100 rounded-full overflow-hidden min-w-[60px]">
        <div
          className="h-full bg-moss-500 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-sand-500 whitespace-nowrap">{done}/{total}</span>
    </div>
  )
}

export default function LabelingTab() {
  const [tasks, setTasks] = useState([])
  const [activeTask, setActiveTask] = useState(null)
  const [items, setItems] = useState([])
  const [labels, setLabels] = useState({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(null)
  const [view, setView] = useState('list') // list | labeling

  async function loadTasks() {
    try {
      setLoading(true)
      const res = await api.get('/tasks/')
      setTasks(res.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTasks()
  }, [])

  async function handleOpen(task) {
    setActiveTask(task)
    setView('labeling')
    setError('')
    setLabels({})
    try {
      await api.post(`/tasks/${task.id}/claim`).catch(() => {})
      const res = await api.get(`/tasks/${task.id}/items`)
      setItems(res.data)
    } catch (err) {
      setError(err.message)
    }
  }

  function handleLabel(itemId, value) {
    setLabels((prev) => ({ ...prev, [itemId]: value }))
  }

  async function handleSubmit(itemId) {
    const label = labels[itemId]
    if (!label) return
    setError('')
    setSubmitting(itemId)
    try {
      await api.post(`/data_items/${itemId}/submission`, { label_value: { label } })
      setItems((prev) =>
        prev.map((i) => (i.id === itemId ? { ...i, final_label: { label } } : i))
      )
      setLabels((prev) => ({ ...prev, [itemId]: undefined }))
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(null)
    }
  }

  async function handleBack() {
    setView('list')
    setActiveTask(null)
    setItems([])
    setLabels({})
    await loadTasks()
  }

  const completedItems = items.filter((i) => i.final_label).length
  const totalItems = items.length

  if (view === 'labeling' && activeTask) {
    const schema = activeTask.label_schema || {}
    const options = Object.keys(schema)

    return (
      <div className="space-y-5">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <button
              onClick={handleBack}
              className="inline-flex items-center gap-1 text-sm text-clay-600 hover:text-clay-700 font-medium mb-1"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
              Back to tasks
            </button>
            <h2 className="text-xl font-semibold text-sand-900">
              {activeTask.dataset_name || activeTask.title}
            </h2>
            {activeTask.instructions && (
              <p className="text-sm text-sand-500 mt-0.5">{activeTask.instructions}</p>
            )}
          </div>
          <Badge variant="success">
            {completedItems} of {totalItems} labeled
          </Badge>
        </div>

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

        {/* Progress */}
        <div className="hidden sm:block">
          <ProgressBadge items={items} />
        </div>

        {/* Items */}
        {items.length === 0 ? (
          <EmptyState
            title="No items to label"
            description="This task doesn't have any data items yet."
            icon={
              <svg className="w-6 h-6 text-sand-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            }
          />
        ) : (
          <div className="space-y-4">
            {items.map((item, idx) => (
              <Card key={item.id}>
                {/* Item content */}
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-sand-100 flex items-center justify-center text-xs font-medium text-sand-500">
                    {idx + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sand-800 leading-relaxed">
                      {item.content_json?.text || JSON.stringify(item.content_json)}
                    </p>

                    {/* AI suggestion */}
                    {item.ai_suggestion?.label && (
                      <div className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-moss-50 text-moss-700 text-xs">
                        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        AI suggests: <span className="font-medium">{item.ai_suggestion.label}</span>
                      </div>
                    )}

                    {/* Already labeled */}
                    {item.final_label ? (
                      <div className="mt-3 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-moss-50 text-moss-600 text-sm font-medium">
                        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                        {item.final_label.label}
                      </div>
                    ) : (
                      /* Label buttons */
                      <div className="mt-3 flex flex-wrap gap-2 items-center">
                        {options.map((key) => (
                          <button
                            key={key}
                            onClick={() => handleLabel(item.id, key)}
                            className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-all
                              ${labels[item.id] === key
                                ? 'bg-clay-600 text-white border-clay-600 shadow-sm'
                                : 'bg-white text-sand-700 border-sand-200 hover:border-sand-300 hover:bg-sand-50'
                              }`}
                          >
                            {schema[key] || key}
                          </button>
                        ))}
                        <Button
                          size="sm"
                          onClick={() => handleSubmit(item.id)}
                          disabled={!labels[item.id] || submitting === item.id}
                          loading={submitting === item.id}
                        >
                          Submit
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    )
  }

  // Task list view
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold text-sand-900">Available tasks</h2>
        <p className="text-sm text-sand-500 mt-0.5">
          Claiming is automatic — open a task to start labeling.
        </p>
      </div>

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

      {loading ? (
        <LoadingPage />
      ) : tasks.length === 0 ? (
        <EmptyState
          title="No tasks available"
          description="Check back later — new labeling tasks are published by dataset owners."
          icon={
            <svg className="w-6 h-6 text-sand-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tasks.map((t) => (
            <Card key={t.id} className="flex flex-col">
              <div className="flex items-start justify-between mb-2">
                <div className="font-medium text-sand-800 truncate">
                  {t.dataset_name || t.title}
                </div>
                <Badge variant={statusVariant[t.status] || 'default'} dot>
                  {t.status}
                </Badge>
              </div>
              {t.instructions && (
                <p className="text-sm text-sand-500 line-clamp-2 mb-4 flex-1">
                  {t.instructions}
                </p>
              )}
              <div className="mt-auto">
                {t.status === 'draft' || t.status === 'pending' ? (
                  <span className="text-xs text-sand-400">Not yet available</span>
                ) : (
                  <Button onClick={() => handleOpen(t)} className="w-full">
                    Start labeling
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
