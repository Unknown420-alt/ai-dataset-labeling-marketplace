function getInitials(name) {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0][0].toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

const colors = [
  'bg-clay-200 text-clay-700',
  'bg-moss-200 text-moss-700',
  'bg-sky-200 text-sky-700',
  'bg-sand-300 text-sand-800',
  'bg-amber-200 text-amber-700',
]

function getColor(name) {
  if (!name) return colors[0]
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

const sizes = {
  sm: 'w-7 h-7 text-xs',
  md: 'w-9 h-9 text-sm',
  lg: 'w-12 h-12 text-base',
}

export default function Avatar({ name, size = 'md', className = '' }) {
  return (
    <div
      className={`inline-flex items-center justify-center rounded-full font-medium
        ${getColor(name)} ${sizes[size]} ${className}`}
      title={name}
    >
      {getInitials(name)}
    </div>
  )
}
