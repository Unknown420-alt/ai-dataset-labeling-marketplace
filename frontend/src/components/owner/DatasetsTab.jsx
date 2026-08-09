import { useEffect, useState } from 'react'
import api from '../../api'

export default function DatasetsTab() {
  const [datasets, setDatasets] = useState([])
  const [form, setForm] = useState({ name: '', description: '', file_type: 'csv' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

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
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.id} className="border-t">
                  <td className="px-6 py-2">{d.name}</td>
                  <td className="px-6 py-2 text-gray-600">{d.description || '-'}</td>
                  <td className="px-6 py-2">{d.file_type}</td>
                  <td className="px-6 py-2">{d.total_items}</td>
                  <td className="px-6 py-2 capitalize">{d.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}