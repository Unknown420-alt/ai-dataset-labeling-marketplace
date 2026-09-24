import { useEffect, useState } from 'react'
import api from '../../api'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Card, { CardHeader } from '../ui/Card'
import Badge from '../ui/Badge'
import EmptyState from '../ui/EmptyState'
import LoadingSpinner, { LoadingPage } from '../ui/LoadingSpinner'
import Table, { TableHead, TableHeadCell, TableBody, TableRow, TableCell } from '../ui/Table'

const statusVariant = {
  ready: 'success',
  draft: 'warning',
  processing: 'info',
}

export default function DatasetsTab() {
  const [datasets, setDatasets] = useState([])
  const [form, setForm] = useState({ name: '', description: '', file_type: 'csv' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')

  const [selectedDatasetId, setSelectedDatasetId] = useState('')
  const [training, setTraining] = useState(false)
  const [trainResult, setTrainResult] = useState(null)
  const [predictText, setPredictText] = useState('')
  const [predicting, setPredicting] = useState(false)
  const [predictResult, setPredictResult] = useState(null)
  const [suggesting, setSuggesting] = useState(false)
  const [suggestMsg, setSuggestMsg] = useState('')

  async function load() {
    try {
      setLoading(true)
      const res = await api.get('/datasets/')
      setDatasets(res.data)
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
      await api.post('/datasets/', form)
      setForm({ name: '', description: '', file_type: 'csv' })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  async function handleRename(id) {
    if (!editName.trim()) return
    setError('')
    try {
      await api.patch(`/datasets/${id}`, { name: editName.trim() })
      setEditingId(null)
      setEditName('')
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
  }

  async function handleDelete(id, name) {
    if (!window.confirm(`Delete dataset "${name}"? This cannot be undone.`)) return
    setError('')
    try {
      await api.delete(`/datasets/${id}`)
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
  }

  function startEdit(d) {
    setEditingId(d.id)
    setEditName(d.name)
  }

  async function handleTrain() {
    if (!selectedDatasetId) return
    setTraining(true)
    setTrainResult(null)
    setPredictResult(null)
    setError('')
    try {
      const res = await api.post(`/datasets/${selectedDatasetId}/train`)
      setTrainResult(res.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setTraining(false)
    }
  }

  async function handlePredict() {
    if (!selectedDatasetId || !predictText.trim()) return
    setPredicting(true)
    setPredictResult(null)
    setError('')
    try {
      const res = await api.post(`/datasets/${selectedDatasetId}/predict`, {
        text: predictText.trim(),
      })
      setPredictResult(res.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setPredicting(false)
    }
  }

  async function handleSuggest() {
    if (!selectedDatasetId) return
    setSuggesting(true)
    setSuggestMsg('')
    setError('')
    try {
      const res = await api.post(`/datasets/${selectedDatasetId}/suggest`)
      setSuggestMsg(`AI suggestions written for ${res.data.suggested} unlabeled items — labelers will see them right away.`)
    } catch (err) {
      setError(err.message)
    } finally {
      setSuggesting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Create form */}
      <Card>
        <CardHeader title="Create a dataset" subtitle="Add a new dataset to organize your labeling work." />
        <form onSubmit={handleCreate} className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <Input
            placeholder="Dataset name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <Input
            placeholder="Description (optional)"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <Select
            value={form.file_type}
            onChange={(e) => setForm({ ...form, file_type: e.target.value })}
          >
            <option value="csv">CSV</option>
            <option value="json">JSON</option>
          </Select>
          <Button type="submit" loading={creating}>
            Create dataset
          </Button>
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

      {/* Datasets list */}
      <Card padding={false}>
        <div className="px-5 sm:px-6 pt-5 pb-3">
          <CardHeader title="My datasets" subtitle={`${datasets.length} dataset${datasets.length !== 1 ? 's' : ''}`} />
        </div>

        {loading ? (
          <div className="px-5 sm:px-6 pb-6">
            <LoadingPage />
          </div>
        ) : datasets.length === 0 ? (
          <EmptyState
            title="No datasets yet"
            description="Create your first dataset above to start organizing your labeling work."
            icon={
              <svg className="w-6 h-6 text-sand-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            }
          />
        ) : (
          <Table>
            <TableHead>
              <TableHeadCell>Name</TableHeadCell>
              <TableHeadCell className="hidden sm:table-cell">Description</TableHeadCell>
              <TableHeadCell className="hidden md:table-cell">Type</TableHeadCell>
              <TableHeadCell>Items</TableHeadCell>
              <TableHeadCell>Status</TableHeadCell>
              <TableHeadCell>Actions</TableHeadCell>
            </TableHead>
            <TableBody>
              {datasets.map((d) => (
                <TableRow key={d.id}>
                  <TableCell className="font-medium">
                    {editingId === d.id ? (
                      <div className="flex items-center gap-1.5">
                        <input
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleRename(d.id)
                            if (e.key === 'Escape') setEditingId(null)
                          }}
                          className="w-full min-w-0 px-2 py-1 text-sm rounded border border-sand-200 focus:ring-2 focus:ring-sky-100 focus:border-sky-400"
                          autoFocus
                        />
                        <button
                          onClick={() => handleRename(d.id)}
                          className="text-moss-600 hover:text-moss-700 text-xs font-medium whitespace-nowrap"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="text-sand-400 hover:text-sand-600 text-xs whitespace-nowrap"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      d.name
                    )}
                  </TableCell>
                  <TableCell className="hidden sm:table-cell text-sand-500 max-w-[200px] truncate">
                    {d.description || <span className="text-sand-300">—</span>}
                  </TableCell>
                  <TableCell className="hidden md:table-cell">
                    <Badge variant="default">{d.file_type?.toUpperCase()}</Badge>
                  </TableCell>
                  <TableCell>{d.total_items}</TableCell>
                  <TableCell>
                    <Badge variant={statusVariant[d.status] || 'default'} dot>
                      {d.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => startEdit(d)}
                        disabled={editingId === d.id}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(d.id, d.name)}
                        className="text-red-500 hover:text-red-600 hover:bg-red-50"
                      >
                        Delete
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {datasets.length > 0 && (
        <Card>
          <CardHeader
            title="Train & predict"
            subtitle="Train a TF-IDF + Naive Bayes classifier on labeled data, then predict new text."
          />
          <div className="mt-4 space-y-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <Select
                value={selectedDatasetId}
                onChange={(e) => {
                  setSelectedDatasetId(e.target.value)
                  setTrainResult(null)
                  setPredictResult(null)
                }}
                className="sm:w-64"
              >
                <option value="">Select a dataset</option>
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.total_items} items)
                  </option>
                ))}
              </Select>
              <Button
                variant="success"
                loading={training}
                disabled={!selectedDatasetId}
                onClick={handleTrain}
              >
                Train model
              </Button>
            </div>

            {trainResult && (
              <div className="flex flex-wrap gap-3 items-center">
                <Badge variant="success" dot>
                  Accuracy: {(trainResult.accuracy * 100).toFixed(1)}%
                </Badge>
                {trainResult.evaluation && (
                  <span className="text-xs text-sand-400 self-center">({trainResult.evaluation})</span>
                )}
                <Badge variant="info">
                  Labeled: {trainResult.labeled_count}
                </Badge>
                <Badge variant="default">
                  Total: {trainResult.total_items}
                </Badge>
                <Button
                  size="sm"
                  variant="secondary"
                  loading={suggesting}
                  onClick={handleSuggest}
                >
                  Generate AI suggestions
                </Button>
              </div>
            )}
            {suggestMsg && (
              <p className="text-sm text-moss-600">{suggestMsg}</p>
            )}

            {trainResult && (
              <div className="border-t border-sand-100 pt-4">
                <p className="text-sm text-sand-600 mb-2">Try a prediction</p>
                <div className="flex gap-2">
                  <input
                    value={predictText}
                    onChange={(e) => setPredictText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handlePredict()
                    }}
                    placeholder="Enter text to classify…"
                    className="flex-1 min-w-0 px-3 py-2 text-sm rounded-lg border border-sand-200 focus:ring-2 focus:ring-sky-100 focus:border-sky-400"
                  />
                  <Button
                    variant="primary"
                    loading={predicting}
                    disabled={!predictText.trim()}
                    onClick={handlePredict}
                  >
                    Predict
                  </Button>
                </div>
                {predictResult && (
                  <div className="mt-2 flex items-center gap-2 text-sm">
                    <span className="text-sand-500">Result:</span>
                    <Badge variant="success">
                      {predictResult.labels ? predictResult.labels.join(' + ') : predictResult.label}
                    </Badge>
                    <span className="text-sand-400">
                      ({(predictResult.confidence * 100).toFixed(1)}% confidence)
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}
