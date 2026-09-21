import { useEffect, useState } from 'react'
import api from '../../api'

export default function DatasetsTab() {
  const [datasets, setDatasets] = useState([])
  const [form, setForm] = useState({ name: '', description: '', file_type: 'csv' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')

  async function load() {
    const res = await api.get('/datasets/')
    setDatasets(res.data)
  }

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [])

  async function handleCreate(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await api.post('/datasets/', form)
      setForm({ name: '', description: '', file_type: 'csv' })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
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

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-3">Create a dataset</h2>
        <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <input
            placeholder="Name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="border rounded px-3 py-2"
          />
          <input
            placeholder="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="border rounded px-3 py-2"
          />
          <div className="flex gap-2">
            <select
              value={form.file_type}
              onChange={(e) => setForm({ ...form, file_type: e.target.value })}
              className="border rounded px-3 py-2"
            >
              <option value="csv">CSV</option>
              <option value="json">JSON</option>
            </select>
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 text-white rounded px-4 py-2 hover:bg-blue-700 disabled:opacity-50"
            >
              Create
            </button>
          </div>
        </form>
        {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <h2 className="text-lg font-semibold px-6 pt-5 pb-3">My datasets</h2>
        {datasets.length === 0 ? (
          <p className="px-6 pb-5 text-gray-500">No datasets yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left">
              <tr>
                <th className="px-6 py-2">Name</th>
                <th className="px-6 py-2">Description</th>
                <th className="px-6 py-2">Type</th>
                <th className="px-6 py-2">Items</th>
                <th className="px-6 py-2">Status</th>
                <th className="px-6 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.id} className="border-t">
                  <td className="px-6 py-2">
                    {editingId === d.id ? (
                      <div className="flex gap-1">
                        <input
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleRename(d.id)
                            if (e.key === 'Escape') setEditingId(null)
                          }}
                          className="border rounded px-2 py-1 text-sm w-full"
                          autoFocus
                        />
                        <button
                          onClick={() => handleRename(d.id)}
                          className="text-green-600 hover:text-green-800 text-xs font-medium"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="text-gray-500 hover:text-gray-700 text-xs"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      d.name
                    )}
                  </td>
                  <td className="px-6 py-2 text-gray-600">{d.description || '-'}</td>
                  <td className="px-6 py-2">{d.file_type}</td>
                  <td className="px-6 py-2">{d.total_items}</td>
                  <td className="px-6 py-2 capitalize">{d.status}</td>
                  <td className="px-6 py-2">
                    <div className="flex gap-2">
                      <button
                        onClick={() => startEdit(d)}
                        disabled={editingId === d.id}
                        className="text-blue-600 hover:text-blue-800 text-xs font-medium disabled:opacity-40"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(d.id, d.name)}
                        className="text-red-600 hover:text-red-800 text-xs font-medium"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
