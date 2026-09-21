import { useEffect, useState } from 'react'
import api from '../../api'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Card, { CardHeader } from '../ui/Card'
import Badge from '../ui/Badge'
import EmptyState from '../ui/EmptyState'
import { LoadingPage } from '../ui/LoadingSpinner'
import Table, { TableHead, TableHeadCell, TableBody, TableRow, TableCell } from '../ui/Table'

const statusVariant = {
  pending: 'warning',
  active: 'success',
  completed: 'default',
  closed: 'default',
}

function formatDate(d) {
  if (!d) return '—'
  const dt = new Date(d)
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function TasksTab() {
  const [tasks, setTasks] = useState([])
  const [datasets, setDatasets] = useState([])
  const [form, setForm] = useState({ dataset_id: '', max_labelers: 3 })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)

  async function load() {
    try {
      setLoading(true)
      const [tasksRes, datasetsRes] = await Promise.all([
        api.get('/tasks/'),
        api.get('/datasets/'),
      ])
      setTasks(tasksRes.data)
      setDatasets(datasetsRes.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function handleCreate(e) {
    e.preventDefault()
    setCreating(true)
    setError('')
    try {
      await api.post('/tasks/', {
        dataset_id: parseInt(form.dataset_id, 10),
        max_labelers: parseInt(form.max_labelers, 10),
      })
      setForm({ dataset_id: '', max_labelers: 3 })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  const totalAssigned = tasks.reduce((s, t) => s + (t.assigned_labelers || 0), 0)
  const totalCompleted = tasks.reduce((s, t) => s + (t.completed_labelers || 0), 0)

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card>
          <div className="text-sm text-sand-500">Total tasks</div>
          <div className="text-2xl font-semibold text-sand-900 mt-1">{tasks.length}</div>
        </Card>
        <Card>
          <div className="text-sm text-sand-500">Active</div>
          <div className="text-2xl font-semibold text-moss-600 mt-1">
            {tasks.filter((t) => t.status === 'active').length}
          </div>
        </Card>
        <Card>
          <div className="text-sm text-sand-500">Assigned</div>
          <div className="text-2xl font-semibold text-sky-600 mt-1">{totalAssigned}</div>
        </Card>
        <Card>
          <div className="text-sm text-sand-500">Completed</div>
          <div className="text-2xl font-semibold text-sand-600 mt-1">{totalCompleted}</div>
        </Card>
      </div>

      {/* Create form */}
      <Card>
        <CardHeader title="Create a labeling task" subtitle="Assign a dataset to labelers for annotation." />
        <form onSubmit={handleCreate} className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Select
            required
            value={form.dataset_id}
            onChange={(e) => setForm({ ...form, dataset_id: e.target.value })}
          >
            <option value="">Select dataset</option>
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.total_items} items)
              </option>
            ))}
          </Select>
          <Input
            type="number"
            min={1}
            max={100}
            label="Max labelers"
            value={form.max_labelers}
            onChange={(e) => setForm({ ...form, max_labelers: e.target.value })}
          />
          <div className="flex items-end">
            <Button type="submit" loading={creating} className="w-full">
              Create task
            </Button>
          </div>
        </form>
        {error && (
          <div className="mt-3 flex items-center gap-2 p-3 rounded-lg bg-clay-50 text-clay-700 text-sm">
            <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            {error}
          </div>
        )}
      </Card>

      {/* Tasks list */}
      <Card padding={false}>
        <div className="px-5 sm:px-6 pt-5 pb-3">
          <CardHeader
            title="All tasks"
            subtitle={`${tasks.length} task${tasks.length !== 1 ? 's' : ''} across all datasets`}
          />
        </div>

        {loading ? (
          <div className="px-5 sm:px-6 pb-6">
            <LoadingPage />
          </div>
        ) : tasks.length === 0 ? (
          <EmptyState
            title="No tasks yet"
            description="Create a labeling task above to start getting your data labeled."
            icon={
              <svg className="w-6 h-6 text-sand-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
            }
          />
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden sm:block">
              <Table>
                <TableHead>
                  <TableHeadCell>Dataset</TableHeadCell>
                  <TableHeadCell className="hidden md:table-cell">Created</TableHeadCell>
                  <TableHeadCell>Assigned</TableHeadCell>
                  <TableHeadCell>Progress</TableHeadCell>
                  <TableHeadCell>Status</TableHeadCell>
                </TableHead>
                <TableBody>
                  {tasks.map((t) => {
                    const progress = t.max_labelers ? Math.round((t.completed_labelers / t.max_labelers) * 100) : 0
                    return (
                      <TableRow key={t.id}>
                        <TableCell className="font-medium">{t.dataset_name}</TableCell>
                        <TableCell className="hidden md:table-cell text-sand-500">{formatDate(t.created_at)}</TableCell>
                        <TableCell>
                          <span className="text-sand-600">
                            {t.assigned_labelers || 0}
                            <span className="text-sand-300"> / </span>
                            {t.max_labelers}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className="w-20 h-1.5 bg-sand-100 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-moss-500 rounded-full transition-all"
                                style={{ width: `${Math.min(progress, 100)}%` }}
                              />
                            </div>
                            <span className="text-xs text-sand-500">{progress}%</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={statusVariant[t.status] || 'default'} dot>
                            {t.status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>

            {/* Mobile card list */}
            <div className="sm:hidden px-4 pb-4 space-y-3">
              {tasks.map((t) => {
                const progress = t.max_labelers ? Math.round((t.completed_labelers / t.max_labelers) * 100) : 0
                return (
                  <Card key={t.id}>
                    <div className="flex items-start justify-between">
                      <div className="font-medium text-sand-800">{t.dataset_name}</div>
                      <Badge variant={statusVariant[t.status] || 'default'} dot>
                        {t.status}
                      </Badge>
                    </div>
                    <div className="mt-2 text-xs text-sand-400">{formatDate(t.created_at)}</div>
                    <div className="mt-3">
                      <div className="flex items-center justify-between text-xs text-sand-500 mb-1">
                        <span>{t.assigned_labelers || 0} of {t.max_labelers} labelers assigned</span>
                        <span>{progress}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-sand-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-moss-500 rounded-full transition-all"
                          style={{ width: `${Math.min(progress, 100)}%` }}
                        />
                      </div>
                    </div>
                  </Card>
                )
              })}
            </div>
          </>
        )}
      </Card>
    </div>
  )
}
