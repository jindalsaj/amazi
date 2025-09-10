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
          <div style={{ width: 36, height: 36, borderRadius: 8, background: '#0ea5e9', display: 'grid', placeItems: 'center', color: 'white', fontWeight: 700 }}>A</n></div>
          <h1 style={{ margin: 0, fontSize: 22 }}>Amazi — AI-native Scheduling</h1>
        </header>

        <section style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 12, padding: 24 }}>
          <Chat onDrop={onDrop} uploading={uploading} error={error} />
        </section>

        {resp && (
          <section style={{ marginTop: 24, display: 'grid', gap: 16 }}>
            <Preview response={resp} />
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

function Preview({ response }: { response: UploadPreviewResponse }) {
  const { preview } = response
  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <h2 style={{ margin: '8px 0 0 0', fontSize: 18 }}>Extraction preview</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 16 }}>
        <Card title={`Employees (${preview.employees.length})`}>
          <div style={{ display: 'grid', gap: 8 }}>
            {preview.employees.length === 0 && <div style={{ color: '#64748b' }}>No employees detected yet.</div>}
            {preview.employees.map((e, idx) => (
              <Row key={idx} left={e.name} right={e.role || '—'} sub={e.evidence?.source_hint} confidence={e.confidence} />
            ))}
          </div>
        </Card>
        <Card title={`Shifts (${preview.shifts.length})`}>
          <div style={{ display: 'grid', gap: 6, maxHeight: 360, overflow: 'auto' }}>
            {preview.shifts.length === 0 && <div style={{ color: '#64748b' }}>No shifts parsed. If this is a PDF or image, I may need manual confirmation.</div>}
            {preview.shifts.map((s, idx) => (
              <Row key={idx}
                   left={`${s.date || '??'}  ${s.start_time || '??'}–${s.end_time || '??'}`}
                   right={s.employee_name || s.role || '—'}
                   sub={s.evidence?.source_hint}
                   confidence={s.confidence} />
            ))}
          </div>
        </Card>
      </div>
      {preview.needs_review_fields.length > 0 && (
        <Card title="Needs review">
          <ul style={{ margin: 0, paddingLeft: 16 }}>
            {preview.needs_review_fields.map((f, i) => <li key={i} style={{ color: '#b45309' }}>{f}</li>)}
          </ul>
        </Card>
      )}
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

