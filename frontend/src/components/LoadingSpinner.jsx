export default function LoadingSpinner({ text = 'Загрузка...' }) {
  return (
    <div className="spinner-wrap">
      <div className="spinner" />
      <span>{text}</span>
    </div>
  )
}
