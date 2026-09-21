export default function Card({ children, className = '', padding = true, ...props }) {
  return (
    <div
      className={`bg-white rounded-xl border border-sand-200 shadow-sm
        ${padding ? 'p-5 sm:p-6' : ''}
        ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action, className = '' }) {
  return (
    <div className={`flex items-start justify-between gap-4 ${className}`}>
      <div className="min-w-0">
        <h3 className="text-lg font-semibold text-sand-900">{title}</h3>
        {subtitle && <p className="mt-0.5 text-sm text-sand-500">{subtitle}</p>}
      </div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  )
}
