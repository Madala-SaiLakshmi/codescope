import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Repositories from './pages/Repositories'
import RepositoryDetail from './pages/RepositoryDetail'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Repositories />} />
        <Route path="/repositories/:id" element={<RepositoryDetail />} />
        <Route path="*" element={<p className="p-8 text-slate-300">Page not found</p>} />
      </Routes>
    </BrowserRouter>
  )
}
