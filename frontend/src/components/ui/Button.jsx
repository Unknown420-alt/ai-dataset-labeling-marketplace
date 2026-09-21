import { forwardRef } from 'react'

const variants = {
  primary: 'bg-clay-500 text-white hover:bg-clay-600 active:bg-clay-700 shadow-sm',
  secondary: 'bg-sand-100 text-sand-800 hover:bg-sand-200 active:bg-sand-300 border border-sand-200',
  ghost: 'text-sand-600 hover:bg-sand-100 active:bg-sand-200',
  danger: 'bg-red-500 text-white hover:bg-red-600 active:bg-red-700 shadow-sm',
  success: 'bg-moss-500 text-white hover:bg-moss-600 active:bg-moss-700 shadow-sm',
}

const sizes = {
  sm: 'px-2.5 py-1 text-xs gap-1',
  md: 'px-3.5 py-2 text-sm gap-1.5',
  lg: 'px-5 py-2.5 text-base gap-2',
}

const Button = forwardRef(function Button(
  { variant = 'primary', size = 'md', className = '', children, disabled, loading, ...props },
  ref
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center font-medium rounded-lg transition-all duration-150
        ${variants[variant]} ${sizes[size]}
        disabled:opacity-50 disabled:cursor-not-allowed
        focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400
        ${className}`}
      {...props}
    >
      {loading && (
        <svg className="spinner h-4 w-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {children}
    </button>
  )
})

export default Button
