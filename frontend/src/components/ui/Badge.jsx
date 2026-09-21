const variants = {
  default: 'bg-sand-100 text-sand-700',
  success: 'bg-moss-100 text-moss-700',
  warning: 'bg-amber-100 text-amber-700',
  danger: 'bg-clay-100 text-clay-700',
  info: 'bg-sky-100 text-sky-700',
}

const dotColors = {
  default: 'bg-sand-400',
  success: 'bg-moss-500',
  warning: 'bg-amber-500',
  danger: 'bg-clay-500',
  info: 'bg-sky-500',
}

export default function Badge({ variant = 'default', dot = false, children, className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium
        ${variants[variant]} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]}`} />}
      {children}
    </span>
  )
}
