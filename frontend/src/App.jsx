import { useEffect, useState } from "react"
import "./App.css"

function App() {
  const [tables, setTables] = useState({})
  const [modelRunning, setModelRunning] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch("/api/tables").then(r => r.json()),
      fetch("/api/model-status").then(r => r.json())
    ])
      .then(([tablesRes, modelRes]) => {
        setTables(tablesRes.tables || {})
        setModelRunning(modelRes.running)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="center">Loading</div>
  }

  return (
    <div className="container">
      <header>
        <h1>System Dashboard</h1>
        <div className={modelRunning ? "status on" : "status off"}>
          Model {modelRunning ? "Running" : "Stopped"}
        </div>
      </header>

      {Object.keys(tables).length === 0 && (
        <p>No tables found</p>
      )}

      {Object.entries(tables).map(([tableName, table]) => (
        <div key={tableName} className="table-card">
          <h2>{tableName}</h2>
          <table>
            <thead>
              <tr>
                {table.columns.map(col => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j}>{String(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}

export default App
