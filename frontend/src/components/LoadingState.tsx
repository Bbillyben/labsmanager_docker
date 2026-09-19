type LoadingStateProps = { message?: string }

export function LoadingState({ message = 'Chargement…' }: LoadingStateProps) {
  return <div className="loading-state" role="status"><div><div className="loading-indicator" aria-hidden="true" /><p>{message}</p></div></div>
}
