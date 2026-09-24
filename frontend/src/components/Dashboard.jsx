import { useState } from 'react'
import DatasetsTab from './owner/DatasetsTab'
import TasksTab from './owner/TasksTab'
import ReviewTab from './owner/ReviewTab'
import AnalyticsTab from './owner/AnalyticsTab'
import LabelingTab from './labeler/LabelingTab'
import Avatar from './ui/Avatar'
import Badge from './ui/Badge'
import Button from './ui/Button'

const tabs = {
  owner: [
    { id: 'datasets', label: 'Datasets', icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
      </svg>
    )},
    { id: 'tasks', label: 'Tasks', icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    )},
    { id: 'review', label: 'Review', icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    )},
    { id: 'analytics', label: 'Analytics', icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 3v18h18M7 15l4-6 4 3 4-7" />
      </svg>
    )},
  ],
  labeler: [
    { id: 'labeling', label: 'Labeling', icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
      </svg>
    )},
  ],
}

export default function Dashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState(tabs[user.role]?.[0]?.id || 'datasets')
  const roleTabs = tabs[user.role] || []

  return (
    <div className="min-h-screen bg-sand-50">
      {/* Header */}
      <header className="bg-white border-b border-sand-200 sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-16">
            {/* Brand */}
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-clay-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-clay-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <span className="text-lg font-semibold text-sand-900 hidden sm:block">Label Studio</span>
            </div>

            {/* User info */}
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-2">
                <Avatar name={user.full_name} size="sm" />
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-sand-800 leading-tight">{user.full_name}</span>
                  <Badge variant={user.role === 'owner' ? 'info' : 'success'} className="mt-0.5">
                    {user.role === 'owner' ? 'Owner' : 'Labeler'}
                  </Badge>
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={onLogout}>
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                <span className="hidden sm:inline">Logout</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile role badge */}
      <div className="sm:hidden bg-white border-b border-sand-100 px-4 py-2">
        <div className="flex items-center gap-2">
          <Avatar name={user.full_name} size="sm" />
          <span className="text-sm font-medium text-sand-800">{user.full_name}</span>
          <Badge variant={user.role === 'owner' ? 'info' : 'success'} className="ml-auto">
            {user.role === 'owner' ? 'Owner' : 'Labeler'}
          </Badge>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-sand-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <nav className="flex gap-1 -mb-px overflow-x-auto" aria-label="Tabs">
            {roleTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
                  ${activeTab === tab.id
                    ? 'border-clay-500 text-clay-600'
                    : 'border-transparent text-sand-500 hover:text-sand-700 hover:border-sand-300'
                  }`}
                aria-current={activeTab === tab.id ? 'page' : undefined}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
        <div className="fade-in">
          {activeTab === 'datasets' && <DatasetsTab />}
          {activeTab === 'tasks' && <TasksTab />}
          {activeTab === 'review' && <ReviewTab />}
          {activeTab === 'analytics' && <AnalyticsTab />}
          {activeTab === 'labeling' && <LabelingTab />}
        </div>
      </main>
    </div>
  )
}
