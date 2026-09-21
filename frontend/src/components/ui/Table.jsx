export default function Table({ children, className = '' }) {
  return (
    <div className={`overflow-x-auto -mx-5 sm:-mx-6 ${className}`}>
      <div className="inline-block min-w-full align-middle px-5 sm:px-6">
        <table className="min-w-full divide-y divide-sand-200">
          {children}
        </table>
      </div>
    </div>
  )
}

export function TableHead({ children }) {
  return (
    <thead className="bg-sand-50">
      <tr>
        {children}
      </tr>
    </thead>
  )
}

export function TableHeadCell({ children, className = '' }) {
  return (
    <th
      scope="col"
      className={`px-4 py-3 text-left text-xs font-medium text-sand-500 uppercase tracking-wider
        first:pl-5 sm:first:pl-6 last:pr-5 sm:last:pr-6 ${className}`}
    >
      {children}
    </th>
  )
}

export function TableBody({ children, emptyMessage = 'No items yet.' }) {
  return (
    <tbody className="divide-y divide-sand-100 bg-white">
      {children}
    </tbody>
  )
}

export function TableRow({ children, className = '' }) {
  return (
    <tr className={`hover:bg-sand-50 transition-colors ${className}`}>
      {children}
    </tr>
  )
}

export function TableCell({ children, className = '' }) {
  return (
    <td className={`px-4 py-3 text-sm text-sand-800 first:pl-5 sm:first:pl-6 last:pr-5 sm:last:pr-6 ${className}`}>
      {children}
    </td>
  )
}
