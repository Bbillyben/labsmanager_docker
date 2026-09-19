import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '../auth/AuthProvider'
import { AppRouter } from '../router/AppRouter'

export function App() {
  return <BrowserRouter basename="/app"><AuthProvider><AppRouter /></AuthProvider></BrowserRouter>
}
