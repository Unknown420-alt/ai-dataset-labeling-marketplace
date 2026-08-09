import { useEffect, useState } from 'react'
import api from '../api'
import DatasetsTab from './owner/DatasetsTab'
import TasksTab from './owner/TasksTab'
import LabelingTab from './labeler/LabelingTab'

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded text-sm font-medium ${
        active ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'
      }`}
    >
      {children}
    </button>
  )
}

export default function Dashboard({ user, onLogout }) {
  const [tab, setTab] = useState(user.role === 'owner' ? 'datasets' : 'labeling')

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white border-b">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="font-semibold">Labeling Marketplace</span>
            <span className="text-xs bg-gray-100 rounded-full px-2 py-0.5 capitalize">
              {user.role}
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">{user.full_name}</span>
            <button onClick={onLogout} className="text-sm text-red-600 hover:underline">
              Logout
            </button>
          </div>
        </div>
        <nav className="max-w-5xl mx-auto px-4 pb-2 flex gap-2">
          {user.role === 'owner' ? (
            <>
              <TabButton active={tab === 'datasets'} onClick={() => setTab('datasets')}>
                Datasets
              </TabButton>
              <TabButton active={tab === 'tasks'} onClick={() => setTab('tasks')}>
                Tasks
              </TabButton>
            </>
          ) : (
            <TabButton active={tab === 'labeling'} onClick={() => setTab('labeling')}>
              Available tasks
            </TabButton>
          )}
        </nav>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6">
        {user.role === 'owner' ? (
          tab === 'datasets' ? (
            <DatasetsTab />
          ) : (
            <TasksTab />
          )
        ) : (
          <LabelingTab />
        )}
      </main>
    </div>
  )
}