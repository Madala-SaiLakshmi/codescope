import { BrowserRouter, Route, Routes } from 'react-router-dom'
import RequireAuth from './components/RequireAuth'
import AnalysisGraph from './pages/AnalysisGraph'
import ImpactCompare from './pages/ImpactCompare'
import ImpactReportView from './pages/ImpactReportView'
import Login from './pages/Login'
import Repositories from './pages/Repositories'
import RepositoryDetail from './pages/RepositoryDetail'

const guard = (el: React.ReactNode) => <RequireAuth>{el}</RequireAuth>

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login mode="login" />} />
        <Route path="/register" element={<Login mode="register" />} />
        <Route path="/" element={guard(<Repositories />)} />
        <Route path="/repositories/:id" element={guard(<RepositoryDetail />)} />
        <Route path="/repositories/:id/compare" element={guard(<ImpactCompare />)} />
        <Route path="/analyses/:id" element={guard(<AnalysisGraph />)} />
        <Route path="/impact/:id" element={guard(<ImpactReportView />)} />
        <Route path="*" element={<p className="p-8 text-slate-300">Page not found</p>} />
      </Routes>
    </BrowserRouter>
  )
}