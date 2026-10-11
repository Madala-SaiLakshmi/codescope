import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AnalysisGraph from './pages/AnalysisGraph'
import ImpactCompare from './pages/ImpactCompare'
import ImpactReportView from './pages/ImpactReportView'
import Repositories from './pages/Repositories'
import RepositoryDetail from './pages/RepositoryDetail'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Repositories />} />
        <Route path="/repositories/:id" element={<RepositoryDetail />} />
        <Route path="/repositories/:id/compare" element={<ImpactCompare />} />
        <Route path="/analyses/:id" element={<AnalysisGraph />} />
        <Route path="/impact/:id" element={<ImpactReportView />} />
        <Route path="*" element={<p className="p-8 text-slate-300">Page not found</p>} />
      </Routes>
    </BrowserRouter>
  )
}
