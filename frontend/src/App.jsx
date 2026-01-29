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

  // Chat state
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [tone, setTone] = useState("")
  const [trainingData, setTrainingData] = useState("")
  const [chatLoading, setChatLoading] = useState(false)

  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage = { role: "user", content: input }
    setMessages(prev => [...prev, userMessage])
    setInput("")
    setChatLoading(true)

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: input,
          tone: tone,
          training_data: trainingData
        })
      })
      const data = await response.json()
      setMessages(prev => [...prev, { role: "model", content: data.answer }])
    } catch (error) {
      console.error("Chat error:", error)
      setMessages(prev => [...prev, { role: "error", content: "Failed to get response" }])
    } finally {
      setChatLoading(false)
    }
  }

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

      <div className="dashboard-grid">
        <div className="sidebar">
          <section className="config-section">
            <h3>Model Configuration</h3>
            <div className="form-group">
              <label>Tone</label>
              <input
                type="text"
                value={tone}
                onChange={e => setTone(e.target.value)}
                placeholder="e.g. Professional, Pirate, Yoda"
              />
            </div>
            <div className="form-group">
              <label>Training Data (System Instructions)</label>
              <textarea
                value={trainingData}
                onChange={e => setTrainingData(e.target.value)}
                placeholder="You are a helpful assistant..."
                rows={5}
              />
            </div>
          </section>
        </div>

        <div className="main-content">
          <section className="chat-section">
            <h3>Chat with Model</h3>
            <div className="messages-list">
              {messages.map((msg, i) => (
                <div key={i} className={`message ${msg.role}`}>
                  <div className="message-content">{msg.content}</div>
                </div>
              ))}
              {chatLoading && <div className="message model loading">Typing...</div>}
            </div>
            <div className="chat-input-area">
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSend()}
                placeholder="Type your message..."
              />
              <button onClick={handleSend} disabled={chatLoading}>Send</button>
            </div>
          </section>

          <section className="tables-section">
            <h3>Database Tables</h3>
            {Object.keys(tables).length === 0 && (
              <p>No tables found</p>
            )}

            {Object.entries(tables).map(([tableName, table]) => (
              <div key={tableName} className="table-card">
                <h4>{tableName}</h4>
                <div className="table-wrapper">
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
              </div>
            ))}
          </section>
        </div>
      </div>
    </div>
  )
}

export default App
