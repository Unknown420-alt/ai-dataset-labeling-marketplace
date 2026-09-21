export default function EmptyState({ icon, title, description, action, className = '' }) {
  return (
    <div className={`flex flex-col items-center justify-center py-12 px-6 text-center ${className}`}>
      {icon && (
        <div className="w-12 h-12 rounded-full bg-sand-100 flex items-center justify-center mb-4">
          {icon}
        </div>
      )}
      <h3 className="text-base font-medium text-sand-800 mb-1">{title}</h3>
      {description && (
        <p className="text-sm text-sand-500 max-w-sm mb-4">{description}</p>
      )}
      {action}
    </div>
  )
}
