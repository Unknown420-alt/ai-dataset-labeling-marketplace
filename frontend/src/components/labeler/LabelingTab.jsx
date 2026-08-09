import { useEffect, useState } from 'react'
import api from '../../api'

export default function LabelingTab() {
  const [tasks, setTasks] = useState([])
  const [items, setItems] = useState([])
  const [activeTask, setActiveTask] = useState(null)
  const [labels, setLabels] = useState({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function loadTasks() {
    const res = await api.get('/tasks/')
    setTasks(res.data)
  }

  useEffect(() => {
    loadTasks().catch((err) => setError(err.message))
  }, [])

  async function handleOpen(task) {
    setActiveTask(task)
    setError('')
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
    try {
      await api.post(`/data_items/${itemId}/submission`, { label_value: { label } })
      setItems((prev) =>
        prev.map((i) => (i.id === itemId ? { ...i, final_label: { label } } : i))
      )
      setLabels((prev) => ({ ...prev, [itemId]: undefined }))
      setLoading(false)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleBack() {
    setActiveTask(null)
    setItems([])
    setLabels({})
    await loadTasks()
  }

  if (activeTask) {
    const schema = activeTask.label_schema || {}
    const options = Object.keys(schema)
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <button onClick={handleBack} className="text-blue-600 text-sm hover:underline mb-1">
              &larr; Back to tasks
            </button>
            <h2 className="text-lg font-semibold">{activeTask.title}</h2>
            <p className="text-sm text-gray-500">{activeTask.instructions}</p>
          </div>
          <span className="text-sm bg-gray-100 rounded-full px-2 py-0.5">
            {items.length} items
          </span>
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}

        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.id} className="bg-white rounded-lg shadow p-4">
              <p className="mb-3">{item.content_json?.text}</p>
              {item.ai_suggestion?.label && (
                <p className="text-xs text-gray-500 mb-3">
                  AI suggests: <span className="font-medium">{item.ai_suggestion.label}</span>
                </p>
              )}
              {item.final_label ? (
                <p className="text-sm text-green-700">
                  Labeled: {item.final_label.label}
                </p>
              ) : (
                <div className="flex flex-wrap gap-2 items-center">
                  {options.map((key) => (
                    <button
                      key={key}
                      onClick={() => handleLabel(item.id, key)}
                      className={`border rounded px-3 py-1 text-sm ${
                        labels[item.id] === key
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'bg-white hover:bg-gray-50'
                      }`}
                    >
                      {schema[key] || key}
                    </button>
                  ))}
                  <button
                    onClick={() => handleSubmit(item.id)}
                    disabled={!labels[item.id] || loading}
                    className="bg-green-600 text-white rounded px-3 py-1 text-sm hover:bg-green-700 disabled:opacity-40"
                  >
                    Submit
                  </button>
                </div>
              )}
            </li>
          ))}
          {items.length === 0 && (
            <p className="text-gray-500">No items in this task yet.</p>
          )}
        </ul>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <h2 className="text-lg font-semibold px-6 pt-5 pb-3">Available tasks</h2>
        {tasks.length === 0 ? (
          <p className="px-6 pb-5 text-gray-500">No tasks published yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left">
              <tr>
                <th className="px-6 py-2">Title</th>
                <th className="px-6 py-2">Instructions</th>
                <th className="px-6 py-2">Status</th>
                <th className="px-6 py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id} className="border-t">
                  <td className="px-6 py-2">{t.title}</td>
                  <td className="px-6 py-2 text-gray-600 max-w-xs truncate">
                    {t.instructions}
                  </td>
                  <td className="px-6 py-2 capitalize">{t.status}</td>
                  <td className="px-6 py-2">
                    {t.status === 'draft' ? (
                      <span className="text-gray-400 text-xs">not open yet</span>
                    ) : (
                      <button
                        onClick={() => handleOpen(t)}
                        className="text-blue-600 hover:underline text-sm"
                      >
                        Start labeling
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <p className="text-xs text-gray-400">
        Claiming is automatic - just open a task to start labeling its items.
      </p>
    </div>
  )
}