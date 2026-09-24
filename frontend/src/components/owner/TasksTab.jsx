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
  draft: 'default',
  open: 'success',
  in_progress: 'warning',
  completed: 'default',
}

const DEFAULT_SCHEMA = '{\n  "cat": "cat",\n  "dog": "dog"\n}'

function formatDate(d) {
  if (!d) return '—'
  const dt = new Date(d)
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function TasksTab({ onTaskCreated }) {
  const [tasks, setTasks] = useState([])
  const [datasets, setDatasets] = useState([])
  const [form, setForm] = useState({
    dataset_id: '',
    title: '',
    instructions: '',
    label_schema: DEFAULT_SCHEMA,
    num_labelers: 1,
    is_multilabel: false,
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [importTask, setImportTask] = useState('')
  const [importFormat, setImportFormat] = useState('csv')
  const [importText, setImportText] = useState('')
  const [importMsg, setImportMsg] = useState('')
  const [importing, setImporting] = useState(false)

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

  const datasetName = (id) => datasets.find((d) => d.id === id)?.name || `#${id}`

  async function handleCreate(e) {
    e.preventDefault()
    setCreating(true)
    setError('')
    try {
      let schema
      try {
        schema = JSON.parse(form.label_schema)
      } catch {
        throw new Error('Label schema must be valid JSON, e.g. {"cat": "cat", "dog": "dog"}')
      }
      if (!form.title.trim()) throw new Error('Give the task a title so labelers know what it is.')
      if (!form.instructions.trim()) throw new Error('Write instructions — labelers see these as guidelines.')
      const res = await api.post('/tasks/', {
        dataset_id: parseInt(form.dataset_id, 10),
        title: form.title.trim(),
        instructions: form.instructions.trim(),
        label_schema: schema,
        num_labelers: parseInt(form.num_labelers, 10) || 1,
        is_multilabel: !!form.is_multilabel,
      })
      setForm({ dataset_id: '', title: '', instructions: '', label_schema: DEFAULT_SCHEMA, num_labelers: 1, is_multilabel: false })
      await load()
      onTaskCreated?.(res.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  const countBy = (s) => tasks.filter((t) => t.status === s).length

  async function handleImport(e) {
    e.preventDefault()
    if (!importTask) {
      setImportMsg('Pick a task first.')
      return
    }
    setImporting(true)
    setImportMsg('')
    try {
      let file = e.target?.elements?.namedItem?.('importFile')?.files?.[0]
      if (!file && importText.trim()) {
        file = new File([importText.trim()], `pasted.${importFormat}`, { type: 'text/plain' })
      }
      if (!file) throw new Error('Choose a file or paste rows below.')
      const data = new FormData()
      data.append('file', file)
      const res = await api.post(`/tasks/${importTask}/items/upload`, data, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setImportMsg(`Imported ${res.data.uploaded} items — they're ready for labelers now.`)
      setImportText('')
      if (e.target?.elements?.namedItem?.('importFile')) {
        e.target.elements.namedItem('importFile').value = ''
      }
      await load()
    } catch (err) {
      setImportMsg(err.message)
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card>
          <div className="text-sm text-sand-500">Total tasks</div>
          <div className="text-2xl font-semibold text-sand-900 mt-1">{tasks.length}</div>
        </Card>
        <Card>
          <div className="text-sm text-sand-500">Open</div>
          <div className="text-2xl font-semibold text-moss-600 mt-1">{countBy('open')}</div>
        </Card>
        <Card>
          <div className="text-sm text-sand-500">In progress</div>
          <div className="text-2xl font-semibold text-sky-600 mt-1">{countBy('in_progress')}</div>
        </Card>
        <Card>
          <div className="text-sm text-sand-500">Completed</div>
          <div className="text-2xl font-semibold text-sand-600 mt-1">{countBy('completed')}</div>
        </Card>
      </div>

      {/* Create form */}
      <Card>
        <CardHeader title="Create a labeling task" subtitle="Pick a dataset, tell labelers exactly what to do, and define the allowed labels." />
        <form onSubmit={handleCreate} className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
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
            required
            label="Task title"
            placeholder="e.g. Label 30 pet sentences"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
          <div className="sm:col-span-2">
            <Input
              required
              label="Instructions for labelers"
              placeholder="e.g. Read each sentence and say cat or dog"
              value={form.instructions}
              onChange={(e) => setForm({ ...form, instructions: e.target.value })}
              hint="Shown to labelers as annotation guidelines."
            />
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium text-sand-700">Label schema (JSON)</label>
            <textarea
              rows={4}
              value={form.label_schema}
              onChange={(e) => setForm({ ...form, label_schema: e.target.value })}
              spellCheck={false}
              className="w-full px-3 py-2 text-sm font-mono rounded-lg border border-sand-200
                focus:ring-2 focus:ring-sky-100 focus:border-sky-400 hover:border-sand-300
                placeholder:text-sand-400"
              placeholder='{"cat": "cat", "dog": "dog"}'
            />
            <p className="text-xs text-sand-500">Keys become the buttons labelers press.</p>
          </div>
          <div className="flex flex-col gap-3">
            <Input
              type="number"
              min={1}
              max={100}
              label="Labelers per item"
              value={form.num_labelers}
              onChange={(e) => setForm({ ...form, num_labelers: e.target.value })}
              hint="How many independent labels each item needs for consensus."
            />
            <div className="flex items-end flex-1">
              <Button type="submit" loading={creating} className="w-full">
                Create task
              </Button>
            </div>
            <label className="sm:col-span-2 flex items-center gap-2 text-sm text-sand-700 cursor-pointer">
              <input
                type="checkbox"
                checked={!!form.is_multilabel}
                onChange={(e) => setForm({ ...form, is_multilabel: e.target.checked })}
                className="w-4 h-4 rounded accent-orange-600"
              />
              Allow multiple labels per item
              <span className="text-xs text-sand-400">(labelers tick all that apply; training stays single-label)</span>
            </label>
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

      {/* Bulk import */}
      <Card>
        <CardHeader title="Bulk import items" subtitle="Drop a CSV, JSON, or JSONL file — or paste rows — straight into a task. Up to 10,000 rows, 10 MB." />
        <form onSubmit={handleImport} className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Select value={importTask} onChange={(e) => setImportTask(e.target.value)}>
            <option value="">Select task</option>
            {tasks.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title} ({t.status?.replace('_', ' ')})
              </option>
            ))}
          </Select>
          <div className="flex gap-2">
            <div className="flex-1">
              <Select value={importFormat} onChange={(e) => setImportFormat(e.target.value)}>
                <option value="csv">CSV — text,label per line</option>
                <option value="json">JSON — [{"{"}text, label{"}"}]</option>
                <option value="jsonl">JSONL — one object per line</option>
              </Select>
            </div>
            <label className="flex-1 cursor-pointer inline-flex items-center justify-center px-3.5 py-2 text-sm font-medium rounded-lg bg-sand-100 text-sand-800 hover:bg-sand-200 border border-sand-200 transition-all">
              Choose file
              <input type="file" name="importFile" accept=".csv,.json,.jsonl" className="hidden" />
            </label>
          </div>
          <div className="sm:col-span-2 space-y-1">
            <label className="block text-sm font-medium text-sand-700">Or paste rows</label>
            <textarea
              rows={4}
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              spellCheck={false}
              className="w-full px-3 py-2 text-sm font-mono rounded-lg border border-sand-200
                focus:ring-2 focus:ring-sky-100 focus:border-sky-400 hover:border-sand-300
                placeholder:text-sand-400"
              placeholder={'"the cat naps",cat\n"dog runs fast",dog'}
            />
          </div>
          <div className="sm:col-span-2">
            <Button type="submit" loading={importing} className="w-full sm:w-auto">
              Import items
            </Button>
            {importMsg && <p className="mt-2 text-sm text-sand-600">{importMsg}</p>}
          </div>
        </form>
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
            description="Create a labeling task above — labelers will see it the moment it's open."
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
                  <TableHeadCell>Task</TableHeadCell>
                  <TableHeadCell>Dataset</TableHeadCell>
                  <TableHeadCell className="hidden md:table-cell">Created</TableHeadCell>
                  <TableHeadCell>Labelers</TableHeadCell>
                  <TableHeadCell>Status</TableHeadCell>
                </TableHead>
                <TableBody>
                  {tasks.map((t) => (
                    <TableRow key={t.id}>
                      <TableCell className="font-medium">
                        {t.title}
                        {t.is_multilabel && (
                          <span className="ml-2 px-1.5 py-0.5 text-[11px] rounded-md bg-sky-100 text-sky-700 font-medium">multi</span>
                        )}
                        <div className="text-xs font-normal text-sand-400 truncate max-w-[240px]">{t.instructions}</div>
                      </TableCell>
                      <TableCell>{datasetName(t.dataset_id)}</TableCell>
                      <TableCell className="hidden md:table-cell text-sand-500">{formatDate(t.created_at)}</TableCell>
                      <TableCell>
                        <span className="text-sand-600">{t.num_labelers} per item</span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusVariant[t.status] || 'default'} dot>
                          {t.status?.replace('_', ' ')}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Mobile card list */}
            <div className="sm:hidden px-4 pb-4 space-y-3">
              {tasks.map((t) => (
                <Card key={t.id}>
                  <div className="flex items-start justify-between">
                    <div className="font-medium text-sand-800">{t.title}</div>
                    <Badge variant={statusVariant[t.status] || 'default'} dot>
                      {t.status?.replace('_', ' ')}
                    </Badge>
                  </div>
                  <div className="mt-1 text-xs text-sand-500">{datasetName(t.dataset_id)} · {formatDate(t.created_at)}</div>
                  <div className="mt-2 text-xs text-sand-400 line-clamp-2">{t.instructions}</div>
                  <div className="mt-3 text-xs text-sand-500">{t.num_labelers} labeler{t.num_labelers !== 1 ? 's' : ''} per item</div>
                </Card>
              ))}
            </div>
          </>
        )}
      </Card>
    </div>
  )
}
