export default function ErrorMessage({ message, onClose }) {
  if (!message) return null
  return (
    <div className="alert alert-danger" role="alert">
      <span style={{ flex: 1 }}>{message}</span>
      {onClose && (
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: '1rem' }}
        >
          ×
        </button>
      )}
    </div>
  )
}

export function SuccessMessage({ message, onClose }) {
  if (!message) return null
  return (
    <div className="alert alert-success" role="alert">
      <span style={{ flex: 1 }}>{message}</span>
      {onClose && (
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: '1rem' }}
        >
          ×
        </button>
      )}
    </div>
  )
}
