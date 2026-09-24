import { useEffect, useRef, useState } from 'react'
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

function ErrorBox({ message }) {
  if (!message) return null
  return (
    <div className="flex items-center gap-2 p-3 rounded-lg bg-clay-50 text-clay-700 text-sm">
      <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      {message}
    </div>
  )
}

function ItemCard({ item, index, schema, options, selected, submitting, onLabel, onSubmit, kbd, multi }) {
  const isActive = (key) => (Array.isArray(selected) ? selected.includes(key) : selected === key)
  const canSubmit = Array.isArray(selected) ? selected.length > 0 : !!selected
  return (
    <Card>
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-sand-100 flex items-center justify-center text-xs font-medium text-sand-500">
          {index + 1}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sand-800 leading-relaxed text-[15px]">
            {item.content_json?.text || JSON.stringify(item.content_json)}
          </p>

          {item.ai_suggestion?.label && (
            <div className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-moss-50 text-moss-700 text-xs">
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
                        AI suggests: <span className="font-medium">{item.ai_suggestion.label}</span>
                        {item.ai_confidence > 0 && (
                          <span>({Math.round(item.ai_confidence * 100)}%)</span>
                        )}
            </div>
          )}

          {item.final_label ? (
            <div className="mt-3 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-moss-50 text-moss-600 text-sm font-medium">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
                        {item.final_label.labels ? item.final_label.labels.join(' + ') : item.final_label.label}
            </div>
          ) : (
            <div className="mt-3 flex flex-wrap gap-2 items-center">
              {options.map((key, oi) => (
                <button
                  key={key}
                  onClick={() => onLabel(item.id, key)}
                            className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-all
                              ${isActive(key)
                                ? 'bg-clay-600 text-white border-clay-600 shadow-sm'
                                : 'bg-white text-sand-700 border-sand-200 hover:border-sand-300 hover:bg-sand-50'
                              }`}
                          >
                            {schema[key] || key}
                            {kbd && oi < 9 && (
                              <kbd className={`ml-1.5 px-1 rounded text-[11px] font-mono ${isActive(key) ? 'bg-white/20' : 'bg-sand-100 text-sand-400'}`}>
                                {oi + 1}
                              </kbd>
                            )}
                          </button>
                        ))}
                        <Button
                          size="sm"
                          onClick={() => onSubmit(item.id)}
                          disabled={!canSubmit || submitting === item.id}
                          loading={submitting === item.id}
                        >
                          Submit ⏎
                        </Button>
                        {multi && (
                          <span className="text-xs text-sand-400">tick all that apply</span>
                        )}
            </div>
          )}
        </div>
      </div>
    </Card>
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
  const [mode, setMode] = useState('focus') // focus | all
  const [focusIdx, setFocusIdx] = useState(0)
  const [showGuide, setShowGuide] = useState(false)
  const [goldMsg, setGoldMsg] = useState(null) // {ok: bool} | null
  const [mine, setMine] = useState(null)

  const live = useRef({})
  live.current = { items, labels, focusIdx, submitting, view, mode, activeTask }

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
    api.get('/analytics/mine').then((res) => setMine(res.data)).catch(() => {})
  }, [])

  async function handleOpen(task) {
    setActiveTask(task)
    setView('labeling')
    setError('')
    setLabels({})
    setFocusIdx(0)
    try {
      await api.post(`/tasks/${task.id}/claim`).catch(() => {})
      const res = await api.get(`/tasks/${task.id}/items`)
      setItems(res.data)
    } catch (err) {
      setError(err.message)
    }
  }

  function handleLabel(itemId, value) {
    if (activeTask?.is_multilabel) {
      setLabels((prev) => {
        const cur = Array.isArray(prev[itemId]) ? prev[itemId] : []
        return {
          ...prev,
          [itemId]: cur.includes(value) ? cur.filter((v) => v !== value) : [...cur, value],
        }
      })
    } else {
      setLabels((prev) => ({ ...prev, [itemId]: value }))
    }
  }

  async function handleSubmit(itemId) {
    const s = live.current
    const multi = !!s.activeTask?.is_multilabel
    const sel = s.labels[itemId]
    const empty = multi ? !(Array.isArray(sel) && sel.length) : !sel
    if (empty || s.submitting) return
    setError('')
    setGoldMsg(null)
    setSubmitting(itemId)
    try {
      const payload = multi ? { labels: sel } : { label: sel }
      const res = await api.post(`/data_items/${itemId}/submission`, { label_value: payload })
      const goldFlag = res?.data?.gold_correct
      if (goldFlag === true) setGoldMsg({ ok: true })
      else if (goldFlag === false) setGoldMsg({ ok: false })
      const next = s.items.map((i) =>
        i.id === itemId ? { ...i, final_label: payload } : i
      )
      setItems(next)
      setLabels((prev) => ({ ...prev, [itemId]: undefined }))
      // Auto-advance: stay on the same position, which is now the next pending item.
      const pending = next.filter((i) => !i.final_label)
      setFocusIdx((fi) => Math.min(fi, Math.max(pending.length - 1, 0)))
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(null)
    }
  }

  // Keyboard shortcuts: 1-9 pick a label, Enter submits, arrows move.
  useEffect(() => {
    function onKey(e) {
      const s = live.current
      if (s.view !== 'labeling' || !s.activeTask || s.mode !== 'focus') return
      if (/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName || '')) return
      const schema = s.activeTask.label_schema || {}
      const options = Object.keys(schema)
      const pending = s.items.filter((i) => !i.final_label)
      const item = pending[Math.min(s.focusIdx, Math.max(pending.length - 1, 0))]
      if (!item) return
      if (e.key >= '1' && e.key <= '9') {
        const opt = options[parseInt(e.key, 10) - 1]
        if (opt) {
          e.preventDefault()
          if (s.activeTask?.is_multilabel) {
            const cur = Array.isArray(s.labels[item.id]) ? s.labels[item.id] : []
            const next = cur.includes(opt) ? cur.filter((v) => v !== opt) : [...cur, opt]
            setLabels((prev) => ({ ...prev, [item.id]: next }))
          } else {
            setLabels((prev) => ({ ...prev, [item.id]: opt }))
          }
        }
      } else if (e.key === 'Enter') {
        e.preventDefault()
        handleSubmit(item.id)
      } else if (e.key === 'ArrowRight') {
        e.preventDefault()
        setFocusIdx((fi) => Math.min(fi + 1, pending.length - 1))
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        setFocusIdx((fi) => Math.max(fi - 1, 0))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  async function handleBack() {
    setView('list')
    setActiveTask(null)
    setItems([])
    setLabels({})
    setFocusIdx(0)
    await loadTasks()
  }

  const completedItems = items.filter((i) => i.final_label).length
  const totalItems = items.length

  if (view === 'labeling' && activeTask) {
    const schema = activeTask.label_schema || {}
    const options = Object.keys(schema)
    const multi = !!activeTask.is_multilabel
    const pending = items.filter((i) => !i.final_label)
    const focusItem = pending[Math.min(focusIdx, Math.max(pending.length - 1, 0))] || null

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
              {activeTask.title || activeTask.dataset_name}
            </h2>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <button
                onClick={() => setShowGuide((v) => !v)}
                className="text-sm text-sky-600 hover:text-sky-700 font-medium"
              >
                {showGuide ? 'Hide guidelines' : 'Read guidelines'}
              </button>
              <span className="text-sand-300">·</span>
              <div className="inline-flex rounded-lg border border-sand-200 overflow-hidden text-xs font-medium">
                <button
                  onClick={() => setMode('focus')}
                  className={`px-2.5 py-1 ${mode === 'focus' ? 'bg-sand-800 text-white' : 'text-sand-500 hover:bg-sand-50'}`}
                >
                  Focus
                </button>
                <button
                  onClick={() => setMode('all')}
                  className={`px-2.5 py-1 ${mode === 'all' ? 'bg-sand-800 text-white' : 'text-sand-500 hover:bg-sand-50'}`}
                >
                  All
                </button>
              </div>
            </div>
          </div>
          <Badge variant="success">
            {completedItems} of {totalItems} labeled
          </Badge>
        </div>

        {/* Guidelines */}
        {showGuide && (
          <Card className="border-sky-200 bg-sky-50/50">
            <h3 className="text-sm font-semibold text-sand-800">How to label this task</h3>
            <p className="mt-1 text-sm text-sand-600 leading-relaxed">{activeTask.instructions || 'No instructions provided.'}</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {options.map((k) => (
                <span key={k} className="px-2 py-0.5 text-xs rounded-md bg-white border border-sand-200 text-sand-600">
                  {k}{schema[k] && schema[k] !== k ? ` → ${schema[k]}` : ''}
                </span>
              ))}
            </div>
            <p className="mt-2 text-xs text-sand-400">Shortcuts: press 1–{Math.min(options.length, 9)} to pick a label, Enter to submit, ← → to move.</p>
          </Card>
        )}

        <ErrorBox message={error} />

        {goldMsg && (
          <div className={`flex items-center gap-2 p-3 rounded-lg text-sm
            ${goldMsg.ok ? 'bg-moss-50 text-moss-700' : 'bg-amber-50 text-amber-700'}`}>
            {goldMsg.ok
              ? 'Spot on — that matches the expected answer.'
              : 'Hmm, that differs from the expected answer. No stress — keep going.'}
          </div>
        )}

        {/* Progress */}
        <div className="hidden sm:block">
          <ProgressBadge items={items} />
        </div>

        {items.length === 0 ? (
          <EmptyState
            title="No items to label"
            description="This task doesn't have any data items yet — the owner needs to upload a CSV first."
            icon={
              <svg className="w-6 h-6 text-sand-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            }
          />
        ) : mode === 'focus' ? (
          <div className="space-y-4">
            {focusItem ? (
              <>
                <ItemCard
                  item={focusItem}
                  index={items.indexOf(focusItem)}
                  schema={schema}
                  options={options}
                  selected={labels[focusItem.id]}
                  submitting={submitting}
                  onLabel={handleLabel}
                  onSubmit={handleSubmit}
                  multi={multi}
                  kbd
                />
                <div className="flex items-center justify-between">
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={focusIdx <= 0}
                    onClick={() => setFocusIdx((fi) => Math.max(fi - 1, 0))}
                  >
                    ← Prev
                  </Button>
                  <span className="text-xs text-sand-400">
                    {pending.length ? `${Math.min(focusIdx + 1, pending.length)} of ${pending.length} left` : 'All done — nice work!'}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={focusIdx >= pending.length - 1}
                    onClick={() => setFocusIdx((fi) => Math.min(fi + 1, pending.length - 1))}
                  >
                    Next →
                  </Button>
                </div>
              </>
            ) : (
              <EmptyState
                title="All done — nice work!"
                description="Every item in this task has a label. Head back to find your next task."
                icon={
                  <svg className="w-6 h-6 text-moss-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                }
              />
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {items.map((item, idx) => (
              <ItemCard
                key={item.id}
                item={item}
                index={idx}
                schema={schema}
                options={options}
                selected={labels[item.id]}
                submitting={submitting}
                onLabel={handleLabel}
                onSubmit={handleSubmit}
              />
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

      {mine && mine.submitted > 0 && (
        <Card>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm">
            <span className="font-medium text-sand-800">My progress</span>
            <span className="text-sand-500">{mine.submitted} submitted</span>
            <span className="text-sand-500">
              {mine.review_accuracy != null ? `✓ ${Math.round(mine.review_accuracy * 100)}% accepted` : 'awaiting review'}
            </span>
            <span className="text-sand-500">
              {mine.gold_accuracy != null ? `★ ${Math.round(mine.gold_accuracy * 100)}% on checks` : 'no checks yet'}
            </span>
            <span className="text-sand-500">{mine.tasks_claimed} tasks claimed</span>
          </div>
        </Card>
      )}

      <ErrorBox message={error} />

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
                  {t.title || t.dataset_name}
                </div>
                <Badge variant={statusVariant[t.status] || 'default'} dot>
                  {t.status?.replace('_', ' ')}
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
