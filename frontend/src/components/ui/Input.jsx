import { forwardRef } from 'react'

const Input = forwardRef(function Input(
  { label, error, hint, className = '', ...props },
  ref
) {
  return (
    <div className="space-y-1">
      {label && (
        <label className="block text-sm font-medium text-sand-700">
          {label}
        </label>
      )}
      <input
        ref={ref}
        className={`w-full px-3 py-2 text-sm rounded-lg border transition-colors
          ${error
            ? 'border-red-300 focus:ring-2 focus:ring-red-200 focus:border-red-400'
            : 'border-sand-200 focus:ring-2 focus:ring-sky-100 focus:border-sky-400 hover:border-sand-300'
          }
          placeholder:text-sand-400
          ${className}`}
        {...props}
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
      {hint && !error && <p className="text-xs text-sand-500">{hint}</p>}
    </div>
  )
})

export default Input
