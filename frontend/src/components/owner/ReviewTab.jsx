import { useEffect, useState } from 'react'
import api from '../../api'
import Button from '../ui/Button'
import Card, { CardHeader } from '../ui/Card'
import Badge from '../ui/Badge'
import Select from '../ui/Select'
import EmptyState from '../ui/EmptyState'
import { LoadingPage } from '../ui/LoadingSpinner'
import Table, { TableHead, TableHeadCell, TableBody, TableRow, TableCell } from '../ui/Table'

const reviewVariant = {
  pending: 'warning',
  accepted: 'success',
  rejected: 'default',
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export default function ReviewTab() {
  const [tasks, setTasks] = useState([])
  const [taskId, setTaskId] = useState('')
  const [subs, setSubs] = useState([])
  const [consensus, setConsensus] = useState(null)
  const [board, setBoard] = useState([])
  const [filter, setFilter] = useState('pending')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(null)

  async function loadTasks() {
    try {
      setLoading(true)
      const res = await api.get('/tasks/')
      setTasks(res.data)
      if (res.data.length && !taskId) setTaskId(String(res.data[0].id))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTasks()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function loadReview(id) {
    if (!id) return
    setError('')
    try {
      const [s, c, b] = await Promise.all([
        api.get(`/tasks/${id}/submissions`),
        api.get(`/tasks/${id}/consensus`),
        api.get(`/tasks/${id}/leaderboard`),
      ])
      setSubs(s.data)
      setConsensus(c.data)
      setBoard(b.data)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    loadReview(taskId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId])

  async function handleReview(subId, decision) {
    setWorking(subId)
    setError('')
    try {
      await api.post(`/submissions/${subId}/review`, { decision })
      await loadReview(taskId)
    } catch (err) {
      setError(err.message)
    } finally {
      setWorking(null)
    }
  }

  async function handleGold(itemId, labelValue) {
    setWorking(`gold-${itemId}`)
    setError('')
    try {
      await api.post(`/data_items/${itemId}/gold`, { gold_label: labelValue })
      await loadReview(taskId)
    } catch (err) {
      setError(err.message)
    } finally {
      setWorking(null)
    }
  }

  async function handleExport(format) {
    setError('')
    try {
      const res = await api.get(`/tasks/${taskId}/export`, {
        params: { format },
        responseType: 'blob',
      })
      downloadBlob(res, `task_${taskId}_labels.${format}`)
    } catch (err) {
      setError(err.message || 'Export failed')
    }
  }

  const visible = subs.filter((s) => filter === 'all' || s.status === filter)
  const labelDist = {}
  consensus?.items.forEach((i) => {
    const key = i.majority_label ? JSON.stringify(i.majority_label) : 'unlabeled'
    labelDist[key] = (labelDist[key] || 0) + 1
  })

  if (loading) return <LoadingPage />

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-sand-900">Review labels</h2>
        <p className="text-sm text-sand-500 mt-0.5">
          Accept good work, reject the rest — accepted labels become the final answer.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-clay-50 text-clay-700 text-sm">
          {error}
        </div>
      )}

      {tasks.length === 0 ? (
        <EmptyState
          title="No tasks to review"
          description="Create a task first — submissions from labelers will land here."
        />
      ) : (
        <>
          {/* Task picker + consensus */}
          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-1">
              <CardHeader title="Task" subtitle="Pick what to review." />
              <div className="mt-3">
                <Select value={taskId} onChange={(e) => setTaskId(e.target.value)}>
                  {tasks.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.title} ({t.status?.replace('_', ' ')})
                    </option>
                  ))}
                </Select>
              </div>
              {consensus && (
                <div className="mt-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-sand-500">Labeled</span>
                    <span className="font-medium text-sand-800">{consensus.labeled_count} / {consensus.total_items}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sand-500">Agreement</span>
                    <span className="font-medium text-sand-800">{Math.round(consensus.overall_agreement * 100)}%</span>
                  </div>
                  <div className="h-1.5 bg-sand-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-moss-500 rounded-full transition-all"
                      style={{ width: `${Math.round(consensus.overall_agreement * 100)}%` }}
                    />
                  </div>
                  <div className="pt-1 flex flex-wrap gap-1.5">
                    {Object.entries(labelDist).map(([k, v]) => (
                      <span key={k} className="px-2 py-0.5 text-xs rounded-md bg-sand-100 text-sand-600">
                        {k} · {v}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div className="mt-4 flex gap-2">
                <Button size="sm" variant="secondary" onClick={() => handleExport('csv')} disabled={!taskId}>
                  Export CSV
                </Button>
                <Button size="sm" variant="secondary" onClick={() => handleExport('json')} disabled={!taskId}>
                  Export JSON
                </Button>
              </div>
              {board.length > 0 && (
                <div className="mt-4 pt-4 border-t border-sand-100">
                  <h4 className="text-sm font-semibold text-sand-800">Leaderboard</h4>
                  <div className="mt-2 space-y-2">
                    {board.map((b, i) => (
                      <div key={b.labeler_id} className="flex items-center gap-2 text-xs">
                        <span className={`w-5 h-5 rounded-md flex items-center justify-center font-semibold
                          ${i === 0 ? 'bg-amber-100 text-amber-700' : 'bg-sand-100 text-sand-500'}`}>
                          {i + 1}
                        </span>
                        <span className="flex-1 truncate text-sand-600">{b.labeler_email}</span>
                        <span className="text-sand-500" title="Gold accuracy">
                          {b.gold_accuracy != null ? `★ ${Math.round(b.gold_accuracy * 100)}%` : '★ —'}
                        </span>
                        <span className="text-sand-500" title="Review acceptance">
                          {b.review_accuracy != null ? `✓ ${Math.round(b.review_accuracy * 100)}%` : '✓ —'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>

            {/* Submissions */}
            <Card padding={false} className="lg:col-span-2">
              <div className="px-5 sm:px-6 pt-5 pb-3 flex flex-wrap items-center justify-between gap-2">
                <CardHeader
                  title="Submissions"
                  subtitle={`${visible.length} shown · ${subs.filter((s) => s.status === 'pending').length} waiting`}
                />
                <div className="inline-flex rounded-lg border border-sand-200 overflow-hidden text-xs font-medium">
                  {['pending', 'accepted', 'rejected', 'all'].map((f) => (
                    <button
                      key={f}
                      onClick={() => setFilter(f)}
                      className={`px-2.5 py-1 capitalize ${filter === f ? 'bg-sand-800 text-white' : 'text-sand-500 hover:bg-sand-50'}`}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>
              {visible.length === 0 ? (
                <div className="px-5 sm:px-6 pb-6">
                  <EmptyState
                    title={filter === 'pending' ? 'Queue is clear' : `No ${filter} submissions`}
                    description={filter === 'pending' ? 'Every submission has been reviewed. Grab a coffee.' : 'Try a different filter.'}
                  />
                </div>
              ) : (
                <div className="hidden sm:block">
                  <Table>
                    <TableHead>
                      <TableHeadCell>Item</TableHeadCell>
                      <TableHeadCell>Labeler</TableHeadCell>
                      <TableHeadCell>Label</TableHeadCell>
                      <TableHeadCell>Status</TableHeadCell>
                      <TableHeadCell>Decision</TableHeadCell>
                    </TableHead>
                    <TableBody>
                      {visible.map((s) => (
                        <TableRow key={s.id}>
                          <TableCell className="max-w-[220px]">
                            <div className="truncate text-sand-700">#{s.row_index} · {s.item_text}</div>
                          </TableCell>
                          <TableCell className="text-sand-500 text-xs">{s.labeler_email}</TableCell>
                          <TableCell className="font-medium">{s.label_value?.label ?? JSON.stringify(s.label_value)}</TableCell>
                          <TableCell>
                            <Badge variant={reviewVariant[s.status] || 'default'} dot>{s.status}</Badge>
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-1.5 items-center">
                              <Button
                                size="sm"
                                disabled={s.status === 'accepted' || working === s.id}
                                loading={working === s.id}
                                onClick={() => handleReview(s.id, 'accepted')}
                              >
                                Accept
                              </Button>
                              <Button
                                size="sm"
                                variant="secondary"
                                disabled={s.status === 'rejected' || working === s.id}
                                onClick={() => handleReview(s.id, 'rejected')}
                              >
                                Reject
                              </Button>
                              <button
                                title={s.is_gold ? 'Gold item — click to clear' : 'Mark as gold check'}
                                disabled={working === `gold-${s.item_id}`}
                                onClick={() => handleGold(s.item_id, s.is_gold ? null : s.label_value)}
                                className={`px-2 py-1 text-sm rounded-lg border transition-all
                                  ${s.is_gold
                                    ? 'bg-amber-100 border-amber-300 text-amber-600'
                                    : 'bg-white border-sand-200 text-sand-300 hover:text-amber-500 hover:border-amber-200'}`}
                              >
                                ★
                              </button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
              {/* Mobile cards */}
              <div className="sm:hidden px-4 pb-4 space-y-3">
                {visible.map((s) => (
                  <Card key={s.id}>
                    <div className="flex items-start justify-between gap-2">
                      <div className="text-sm text-sand-700">#{s.row_index} · {s.item_text}</div>
                      <Badge variant={reviewVariant[s.status] || 'default'} dot>{s.status}</Badge>
                    </div>
                    <div className="mt-1 text-xs text-sand-400">{s.labeler_email}</div>
                    <div className="mt-2 font-medium text-sand-800">{s.label_value?.label ?? JSON.stringify(s.label_value)}</div>
                    <div className="mt-3 flex gap-2 items-center">
                      <Button size="sm" disabled={s.status === 'accepted' || working === s.id} onClick={() => handleReview(s.id, 'accepted')}>
                        Accept
                      </Button>
                      <Button size="sm" variant="secondary" disabled={s.status === 'rejected' || working === s.id} onClick={() => handleReview(s.id, 'rejected')}>
                        Reject
                      </Button>
                      <button
                        title={s.is_gold ? 'Gold item — click to clear' : 'Mark as gold check'}
                        disabled={working === `gold-${s.item_id}`}
                        onClick={() => handleGold(s.item_id, s.is_gold ? null : s.label_value)}
                        className={`px-2 py-1 text-sm rounded-lg border
                          ${s.is_gold ? 'bg-amber-100 border-amber-300 text-amber-600' : 'bg-white border-sand-200 text-sand-300'}`}
                      >
                        ★
                      </button>
                    </div>
                  </Card>
                ))}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
