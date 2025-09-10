import React, { useCallback, useMemo, useState } from 'react'

type Evidence = {
  file_type: 'csv' | 'xlsx' | 'pdf' | 'image'
  source_hint: string
  raw_text?: string | null
}

type EmployeeRecord = {
  name: string
  role?: string | null
  email?: string | null
  phone?: string | null
  wage?: number | null
  min_hours?: number | null
  max_hours?: number | null
  evidence?: Evidence | null
  confidence: number
}

type ShiftRecord = {
  employee_name?: string | null
  role?: string | null
  date?: string | null
  start_time?: string | null
  end_time?: string | null
  unpaid_break_min?: number | null
  status?: string | null
  location?: string | null
  evidence?: Evidence | null
  confidence: number
}

type ExtractionPreview = {
  file_type: string
  employees: EmployeeRecord[]
  shifts: ShiftRecord[]
  needs_review_fields: string[]
}

type UploadPreviewResponse = {
  upload_id: number
  preview: ExtractionPreview
}

const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000/api'

export function App() {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [resp, setResp] = useState<UploadPreviewResponse | null>(null)
  const [confirming, setConfirming] = useState(false)

  const onDrop = useCallback(async (file: File) => {
    setError(null)
    setResp(null)
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch(`${API_BASE}/uploads/timesheet`, { method: 'POST', body: fd })
      if (!res.ok) {
        const msg = await res.text()
        throw new Error(msg || `Upload failed (${res.status})`)
      }
      const data = (await res.json()) as UploadPreviewResponse
      setResp(data)
    } catch (e: any) {
      setError(e.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }, [])

  return (
    <div style={{
      fontFamily: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial',
      color: '#0f172a',
      minHeight: '100vh',
      background: 'linear-gradient(180deg, #f8fafc 0%, #ffffff 60%)'
    }}>
      <div style={{ maxWidth: 1000, margin: '0 auto', padding: '40px 24px' }}>
        <header style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <div style={{ width: 36, height: 36, borderRadius: 8, background: '#0ea5e9', display: 'grid', placeItems: 'center', color: 'white', fontWeight: 700 }}>A</div>
          <h1 style={{ margin: 0, fontSize: 22 }}>Amazi — AI-native Scheduling</h1>
        </header>

        <section style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 12, padding: 24 }}>
          <Chat onDrop={onDrop} uploading={uploading} error={error} />
        </section>

        {resp && (
          <section style={{ marginTop: 24, display: 'grid', gap: 16 }}>
            <EditablePreview response={resp} onConfirm={async (payload) => {
              setConfirming(true)
              try {
                const res = await fetch(`${API_BASE}/uploads/${resp.upload_id}/confirm`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(payload)
                })
                if (!res.ok) throw new Error(await res.text())
                alert('Saved!')
              } catch (e: any) {
                alert(e.message || 'Failed to confirm')
              } finally {
                setConfirming(false)
              }
            }} confirming={confirming} />
          </section>
        )}
      </div>
    </div>
  )
}

function Chat({ onDrop, uploading, error }: { onDrop: (file: File) => void, uploading: boolean, error: string | null }) {
  const [hover, setHover] = useState(false)

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) onDrop(e.target.files[0])
  }

  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); setHover(true) }
  const onDragLeave = () => setHover(false)
  const onDropEvent = (e: React.DragEvent) => {
    e.preventDefault(); setHover(false)
    const file = e.dataTransfer.files?.[0]
    if (file) onDrop(file)
  }

  return (
    <div>
      <div style={{ marginBottom: 16, lineHeight: 1.5 }}>
        <div><b>Assistant</b>: Hi! Upload your past timesheet (CSV, XLSX, PDF, or image up to 5 MB). I’ll extract employees and shifts. If I’m unsure, I’ll ask you to confirm.</div>
      </div>
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDropEvent}
        style={{
          padding: 24,
          border: `2px dashed ${hover ? '#0ea5e9' : '#cbd5e1'}`,
          borderRadius: 12,
          background: hover ? '#f0f9ff' : '#f8fafc',
          display: 'grid',
          gap: 12,
          justifyItems: 'center',
          textAlign: 'center'
        }}
      >
        <div style={{ fontWeight: 600 }}>Drag & drop your timesheet here</div>
        <div style={{ color: '#475569', fontSize: 14 }}>or</div>
        <label style={{
          background: '#0ea5e9', color: 'white', fontWeight: 600, padding: '10px 14px', borderRadius: 8, cursor: 'pointer'
        }}>
          Select file
          <input type="file" accept=".csv,.xlsx,.xls,.pdf,.png,.jpg,.jpeg,.heic" style={{ display: 'none' }} onChange={handleInput} />
        </label>
        {uploading && <div style={{ color: '#0ea5e9' }}>Uploading and analyzing...</div>}
        {error && <div style={{ color: '#b91c1c' }}>{error}</div>}
      </div>
    </div>
  )
}

function EditablePreview({ response, onConfirm, confirming }: { response: UploadPreviewResponse, onConfirm: (payload: { employees: any[]; shifts: any[] }) => void, confirming: boolean }) {
  const [employees, setEmployees] = useState<EmployeeRecord[]>(response.preview.employees)
  const [shifts, setShifts] = useState<ShiftRecord[]>(response.preview.shifts)

  const addEmployee = () => setEmployees(prev => [...prev, { name: '', confidence: 1 } as any])
  const addShift = () => setShifts(prev => [...prev, { confidence: 1 } as any])

  const toPayload = () => ({
    employees: employees.filter(e => e.name?.trim()).map(e => ({ name: e.name, role: e.role || null, email: e.email || null, phone: e.phone || null, wage: e.wage || null, min_hours: e.min_hours || null, max_hours: e.max_hours || null })),
    shifts: shifts.filter(s => s.employee_name && s.date && s.start_time && s.end_time).map(s => ({ employee_name: s.employee_name!, role: s.role || null, date: s.date!, start_time: s.start_time!, end_time: s.end_time!, unpaid_break_min: s.unpaid_break_min || null, status: s.status || null, location: s.location || null }))
  })

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <h2 style={{ margin: '8px 0 0 0', fontSize: 18 }}>Review & edit</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 16 }}>
        <Card title={`Employees (${employees.length})`}>
          <div style={{ display: 'grid', gap: 8 }}>
            {employees.map((e, i) => (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 8 }}>
                <input value={e.name || ''} onChange={ev => setEmployees(arr => arr.map((x, idx) => idx === i ? { ...x, name: ev.target.value } : x))} placeholder="Name" />
                <input value={e.role || ''} onChange={ev => setEmployees(arr => arr.map((x, idx) => idx === i ? { ...x, role: ev.target.value } : x))} placeholder="Role" />
                <button onClick={() => setEmployees(arr => arr.filter((_, idx) => idx !== i))} style={{ background: 'transparent', color: '#dc2626' }}>Remove</button>
              </div>
            ))}
            <button onClick={addEmployee} style={{ background: '#f1f5f9', border: '1px dashed #cbd5e1', borderRadius: 8, padding: 8 }}>+ Add employee</button>
          </div>
        </Card>
        <Card title={`Shifts (${shifts.length})`}>
          <div style={{ display: 'grid', gap: 8 }}>
            {shifts.map((s, i) => (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', gap: 8 }}>
                <input value={s.employee_name || ''} onChange={ev => setShifts(arr => arr.map((x, idx) => idx === i ? { ...x, employee_name: ev.target.value } : x))} placeholder="Employee" />
                <input value={s.date || ''} onChange={ev => setShifts(arr => arr.map((x, idx) => idx === i ? { ...x, date: ev.target.value } : x))} placeholder="YYYY-MM-DD" />
                <input value={s.start_time || ''} onChange={ev => setShifts(arr => arr.map((x, idx) => idx === i ? { ...x, start_time: ev.target.value } : x))} placeholder="HH:MM" />
                <input value={s.end_time || ''} onChange={ev => setShifts(arr => arr.map((x, idx) => idx === i ? { ...x, end_time: ev.target.value } : x))} placeholder="HH:MM" />
                <button onClick={() => setShifts(arr => arr.filter((_, idx) => idx !== i))} style={{ background: 'transparent', color: '#dc2626' }}>Remove</button>
              </div>
            ))}
            <button onClick={addShift} style={{ background: '#f1f5f9', border: '1px dashed #cbd5e1', borderRadius: 8, padding: 8 }}>+ Add shift</button>
          </div>
        </Card>
      </div>
      <div style={{ display: 'flex', gap: 12 }}>
        <button disabled={confirming} onClick={() => onConfirm(toPayload())} style={{ background: '#16a34a', color: 'white', padding: '10px 14px', borderRadius: 8, fontWeight: 700 }}>{confirming ? 'Saving...' : 'Confirm & save'}</button>
      </div>
    </div>
  )
}

function Card({ title, children }: { title: string, children: React.ReactNode }) {
  return (
    <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 12, padding: 16 }}>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>{title}</div>
      {children}
    </div>
  )
}

function Row({ left, right, sub, confidence }: { left: string, right: string, sub?: string | undefined, confidence?: number }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8, alignItems: 'center', padding: '8px 0', borderBottom: '1px dashed #e2e8f0' }}>
      <div>
        <div style={{ fontWeight: 600 }}>{left}</div>
        <div style={{ color: '#64748b', fontSize: 12 }}>{sub || ' '}</div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ color: '#0f172a' }}>{right}</span>
        {typeof confidence === 'number' && (
          <span style={{ fontSize: 12, color: confidence >= 0.8 ? '#16a34a' : confidence >= 0.5 ? '#f59e0b' : '#dc2626' }}>
            {Math.round(confidence * 100)}%
          </span>
        )}
      </div>
    </div>
  )
}

