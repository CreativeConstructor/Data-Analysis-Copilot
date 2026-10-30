import { useEffect, useState } from 'react'
import { api } from './api'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, BarChart, Bar } from 'recharts'

function App() {
  const [datasets, setDatasets] = useState([])
  const [datasetId, setDatasetId] = useState('')
  const [file, setFile] = useState(null)
  const [conversationId, setConversationId] = useState('')
  const [turns, setTurns] = useState([])
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function loadDatasets() {
    try {
      const rows = await api('/datasets/')
      setDatasets(rows)
      if (!datasetId && rows.length) setDatasetId(rows[0].id)
    } catch (err) { setError(err.message) }
  }

  useEffect(() => { loadDatasets() }, [])

  useEffect(() => {
    if (!datasetId) return
    setTurns([]); setConversationId(''); setError('')
  }, [datasetId])

  async function upload(event) {
    event.preventDefault()
    if (!file) return
    setBusy(true); setError(''); setNotice('')
    try {
      const body = new FormData(); body.append('file', file)
      const result = await api('/datasets/', { method: 'POST', body })
      await loadDatasets(); setDatasetId(result.id); setFile(null)
      setNotice(`${result.original_filename} uploaded and profiled.`)
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  async function ask(event) {
    event.preventDefault()
    if (!datasetId || !question.trim()) return
    setBusy(true); setError(''); setNotice('')
    try {
      const result = await api('/analysis/', { method: 'POST', body: JSON.stringify({ dataset_id: datasetId, question: question.trim(), ...(conversationId ? { conversation_id: conversationId } : {}) }) })
      setConversationId(result.conversation_id); setTurns(previous => [...previous, result]); setQuestion('')
    } catch (err) {
      if (err.data?.id) {
        setConversationId(err.data.conversation_id)
        setTurns(previous => [...previous, err.data])
        setQuestion('')
      }
      setError(err.message)
    } finally { setBusy(false) }
  }

  async function signOut() {
    try { await api('/logout/', { method: 'POST' }); window.location.href = 'http://127.0.0.1:8000/accounts/login/' }
    catch (err) { setError(err.message) }
  }

  async function loadHistory(id) {
    try {
      const history = await api(`/conversations/${id}/`)
      setConversationId(history.id); setDatasetId(history.dataset_id); setTurns(history.turns)
    } catch (err) { setError(err.message) }
  }

  const selected = datasets.find(item => item.id === datasetId)
  return <div className="app-shell">
    <header className="topbar"><a className="brand" href="#"><span className="brand-mark">D</span>DataPilot</a><div className="top-actions"><span className="connected"><i /> Django session</span><button className="signout" onClick={signOut}>Sign out</button></div></header>
    <main className="workspace">
      <section className="intro"><div><p className="eyebrow">YOUR DATA WORKSPACE</p><h1>Ask better questions<br/><em>of your data.</em></h1><p className="subhead">Upload a dataset, describe what you want to learn, and explore the results.</p></div><div className="intro-art" aria-hidden="true"><div className="art-grid"/><div className="art-card"><div className="art-label">MONTHLY REVENUE</div><div className="art-value">$48,290 <span>↗ 12.8%</span></div><svg viewBox="0 0 260 74" preserveAspectRatio="none"><path d="M0 60 C25 48 30 58 52 43 S88 52 110 32 S140 42 160 22 S192 37 210 16 S240 22 260 4" fill="none" stroke="#0b8a72" strokeWidth="3"/><path d="M0 60 C25 48 30 58 52 43 S88 52 110 32 S140 42 160 22 S192 37 210 16 S240 22 260 4 L260 74 L0 74Z" fill="url(#fade)" opacity=".16"/><defs><linearGradient id="fade" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#0b8a72"/><stop offset="1" stopColor="white"/></linearGradient></defs></svg></div></div></section>

      <section className="workspace-grid">
        <aside className="sidebar">
          <div className="panel-heading"><span className="step">01</span><div><h2>Your datasets</h2><p>Upload CSV or Excel</p></div></div>
          <form className="upload-box" onSubmit={upload}><label className="dropzone"><span className="upload-icon">↑</span><strong>{file ? file.name : 'Choose a file'}</strong><small>CSV or XLSX · up to 10 MB</small><input type="file" accept=".csv,.xlsx" onChange={event => setFile(event.target.files?.[0] || null)} /></label><button className="button button-dark" disabled={busy || !file}>{busy ? 'Working…' : 'Upload dataset'}</button></form>
          <div className="dataset-list"><div className="list-label">YOUR FILES <span>{datasets.length}</span></div>{datasets.map(item => <button key={item.id} className={`dataset-item ${datasetId === item.id ? 'active' : ''}`} onClick={() => setDatasetId(item.id)}><span className="file-icon">▤</span><span className="dataset-name"><strong>{item.original_filename}</strong><small>{item.row_count.toLocaleString()} rows · {item.column_count} columns</small></span><span className="chevron">›</span></button>)}{!datasets.length && <p className="empty-small">Your uploaded datasets will appear here.</p>}</div>
          {conversationId && <button className="history-link" onClick={() => loadHistory(conversationId)}>↻ Reload conversation history</button>}
        </aside>

        <section className="analysis-panel"><div className="panel-heading"><span className="step">02</span><div><h2>Analysis studio</h2><p>{selected ? `Working with ${selected.original_filename}` : 'Select or upload a dataset to begin'}</p></div></div>
          {!turns.length && <div className="welcome-state"><div className="spark">✳</div><h3>What would you like to discover?</h3><p>Ask a question in plain language. DataPilot will analyze your data and show the result.</p><div className="suggestions">{['Compare values by category','Find the strongest trend','Summarize the key metrics'].map(item => <button key={item} onClick={() => setQuestion(item)}>{item} <span>↗</span></button>)}</div></div>}
          <div className="turn-list">{turns.map((turn, index) => <article className="turn" key={turn.id || index}><div className="question-bubble"><span>YOU ASKED</span><p>{turn.question}</p></div>{turn.status === 'succeeded' ? <div className="answer"><div className="answer-title"><span className="success-dot">✓</span> Analysis complete</div><p className="insight">{turn.insight}</p>{turn.chart && <div className="chart-wrap"><div className="chart-title">{turn.chart.y} by {turn.chart.x}</div><ResponsiveContainer width="100%" height={250}>{turn.chart.type === 'line' ? <LineChart data={turn.chart.data} margin={{ top: 12, right: 18, left: 0, bottom: 4 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e9eeeb"/><XAxis dataKey={turn.chart.x} tick={{fontSize:11,fill:'#72807c'}}/><YAxis tick={{fontSize:11,fill:'#72807c'}}/><Tooltip/><Line type="monotone" dataKey={turn.chart.y} stroke="#078875" strokeWidth={3} dot={{r:3}}/></LineChart> : <BarChart data={turn.chart.data} margin={{ top: 12, right: 18, left: 0, bottom: 4 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e9eeeb"/><XAxis dataKey={turn.chart.x} tick={{fontSize:11,fill:'#72807c'}}/><YAxis tick={{fontSize:11,fill:'#72807c'}}/><Tooltip/><Bar dataKey={turn.chart.y} fill="#078875" radius={[5,5,0,0]}/></BarChart>}</ResponsiveContainer></div>}
            {turn.table && <div className="table-wrap"><table><thead><tr>{turn.table.columns.map(column => <th key={column}>{column}</th>)}</tr></thead><tbody>{turn.table.rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell == null ? '—' : String(cell)}</td>)}</tr>)}</tbody></table>{turn.table.truncated && <small className="truncated">Showing the first 50 rows of the result.</small>}</div>}
            <details className="details"><summary>Generated code <span>View code</span></summary><pre>{turn.code}</pre></details><details className="details"><summary>Attempt history <span>{turn.attempts?.length || 0} attempts</span></summary><ol className="attempts">{turn.attempts?.map(attempt => <li key={attempt.attempt}><b>Attempt {attempt.attempt} · {attempt.status}</b>{attempt.error && <p>{attempt.error}</p>}<pre>{attempt.code}</pre></li>)}</ol></details></div> : <div className="answer error-answer"><b>Analysis could not complete</b><p>{turn.error}</p></div>}</article>)}</div>
          <form className="question-form" onSubmit={ask}><label htmlFor="question">ASK A QUESTION</label><div className="question-entry"><textarea id="question" rows="2" value={question} onChange={event => setQuestion(event.target.value)} placeholder={datasetId ? 'e.g. Which region had the highest sales?' : 'Choose a dataset to start'} disabled={!datasetId || busy} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); ask(event) } }} /><button className="send-button" disabled={busy || !datasetId || !question.trim()} aria-label="Run analysis">{busy ? '…' : '↑'}</button></div><small>Enter to analyze · Shift + Enter for a new line</small></form>
        </section>
      </section>
      {(error || notice) && <div className={`toast ${error ? 'toast-error' : ''}`} role="status">{error || notice}<button onClick={() => { setError(''); setNotice('') }}>×</button></div>}
      <footer>DataPilot <span>·</span> AI-assisted analysis with privacy-conscious schema context</footer>
    </main>
  </div>
}

export default App
