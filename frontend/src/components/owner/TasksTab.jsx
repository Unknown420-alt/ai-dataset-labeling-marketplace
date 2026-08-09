import { useEffect, useState } from 'react'
import api from '../../api'

export default function TasksTab() {
  const [tasks, setTasks] = useState([])
  const [datasets, setDatasets] = useState([])
  const [form, setForm] = useState({
    dataset_id: '',
    title: '',
    instructions: '',
    label_schema: '{"cat": "cat", "dog": "dog"}',
    num_labelers: 3,
  })
  const [upload, setUpload] = useState({ taskId: '' })
  const [error, setError] = useState('')
  const [uploadMsg, setUploadMsg] = useState('')
  const [loading, setLoading] = useState(false)

  async function load() {
    const [tasksRes, datasetsRes] = await Promise.all([
      api.get('/tasks/'),
      api.get('/datasets/'),
    ])
    setTasks(tasksRes.data)
    setDatasets(datasetsRes.data)
  }

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [])

  function set(field) {
    return (e) => setForm({ ...form, [field]: e.target.value })
  }

  async function handleCreate(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      let schema = {}
      try {
        schema = JSON.parse(form.label_schema)
      } catch {
        throw new Error('label_schema must be valid JSON, e.g. {"cat": "cat"}')
      }
      await api.post('/tasks/', {
        ...form,
        label_schema: schema,
      })
      setForm((f) => ({ ...f, title: '', instructions: '' }))
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleUpload(e) {
    e.preventDefault()
    setUploadMsg('')
    setError('')
    const file = e.target.file.files[0]
    if (!upload.taskId) {
      setError('Pick a task first')
      return
    }
    const body = new FormData()
    body.append('file', file)
    try {
      const res = await api.post(`/tasks/${upload.taskId}/items/upload`, body)
      setUploadMsg(`${res.data.uploaded} items uploaded`)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-3">Create a labeling task</h2>
        <form onSubmit={handleCreate} className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <select required value={form.dataset_id} onChange={set('dataset_id')} className="border rounded px-3 py-2">
              <option value="">Select dataset</option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
            <input
              placeholder="Task title"
              required
              value={form.title}
              onChange={set('title')}
              className="border rounded px-3 py-2"
            />
          </div>
          <input
            placeholder="Instructions for labelers (e.g. 'is this a cat or a dog?')"
            value={form.instructions}
            onChange={set('instructions')}
            className="w-full border rounded px-3 py-2"
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              placeholder='label_schema JSON, e.g. {"cat": "cat"}'
              value={form.label_schema}
              onChange={set('label_schema')}
              className="border rounded px-3 py-2"
            />
            <input
              type="number"
              min="1"
              value={form.num_labelers}
              onChange={set('num_labelers')}
              className="border rounded px-3 py-2"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 text-white rounded px-4 py-2 hover:bg-blue-700 disabled:opacity-50"
          >
            Create task
          </button>
        </form>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-3">Upload items to a task</h2>
        <form onSubmit={handleUpload} className="flex flex-wrap gap-3 items-end">
          <select
            value={upload.taskId}
            onChange={(e) => setUpload({ taskId: e.target.value })}
            className="border rounded px-3 py-2"
          >
            <option value="">Select task</option>
            {tasks.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title}
              </option>
            ))}
          </select>
          <input
            name="file"
            type="file"
            accept=".csv,.json"
            required
            className="border rounded px-3 py-2"
          />
          <button
            type="submit"
            className="bg-green-600 text-white rounded px-4 py-2 hover:bg-green-700"
          >
            Upload
          </button>
        </form>
        {uploadMsg && <p className="text-sm text-green-600 mt-2">{uploadMsg}</p>}
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <h2 className="text-lg font-semibold px-6 pt-5 pb-3">My tasks</h2>
        {tasks.length === 0 ? (
          <p className="px-6 pb-5 text-gray-500">No tasks yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left">
              <tr>
                <th className="px-6 py-2">Title</th>
                <th className="px-6 py-2">Dataset</th>
                <th className="px-6 py-2">Status</th>
                <th className="px-6 py-2">Labelers needed</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id} className="border-t">
                  <td className="px-6 py-2">{t.title}</td>
                  <td className="px-6 py-2">Dataset #{t.dataset_id}</td>
                  <td className="px-6 py-2 capitalize">{t.status}</td>
                  <td className="px-6 py-2">{t.num_labelers}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}