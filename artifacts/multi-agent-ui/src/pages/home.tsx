import { useState, useRef } from 'react'

type StepResult = {
  id: string
  tool: string
  status: string
  result: string
  attempt: number
  elapsed_seconds: number
  confidence: number
}

type PlanStep = {
  id: string
  description: string
  tool: string
  dependencies: string[]
}

type Phase = 'idle' | 'planning' | 'running' | 'done' | 'error'

const TOOL_COLORS: Record<string, string> = {
  summarize: 'bg-blue-100 text-blue-800',
  linkedin_post: 'bg-purple-100 text-purple-800',
  email_draft: 'bg-green-100 text-green-800',
  web_search: 'bg-orange-100 text-orange-800',
  document_qa: 'bg-pink-100 text-pink-800',
}

const STATUS_ICON: Record<string, string> = {
  success: '✅',
  failed: '❌',
  pending: '⏳',
}

export default function Home() {
  const [task, setTask] = useState('Summarize article, create LinkedIn post, draft email')
  const [phase, setPhase] = useState<Phase>('idle')
  const [plan, setPlan] = useState<PlanStep[]>([])
  const [steps, setSteps] = useState<StepResult[]>([])
  const [error, setError] = useState('')
  const esRef = useRef<EventSource | null>(null)

  const runAgents = () => {
    if (!task.trim() || phase === 'running' || phase === 'planning') return

    setPlan([])
    setSteps([])
    setError('')
    setPhase('planning')

    if (esRef.current) {
      esRef.current.close()
    }

    const base = import.meta.env.BASE_URL.replace(/\/$/, '')
    const url = `${base}/api/run-task/stream?task=${encodeURIComponent(task)}`
    const es = new EventSource(url)
    esRef.current = es

    es.addEventListener('plan', (e) => {
      const data = JSON.parse(e.data)
      setPlan(data.steps ?? [])
      setPhase('running')
    })

    es.addEventListener('step', (e) => {
      const data: StepResult = JSON.parse(e.data)
      setSteps((prev) => [...prev, data])
    })

    es.addEventListener('done', () => {
      setPhase('done')
      es.close()
    })

    es.onerror = () => {
      setError('Connection to backend lost. Make sure the backend API server is running and your OPENAI_API_KEY is configured.')
      setPhase('error')
      es.close()
    }
  }

  const reset = () => {
    esRef.current?.close()
    setPlan([])
    setSteps([])
    setError('')
    setPhase('idle')
  }

  return (
    <main className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-3xl mx-auto space-y-8">

        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
            Multi-Agent AI Task Automation
          </h1>
          <p className="mt-2 text-gray-500 text-sm">
            Describe a complex task — the planner breaks it into steps, worker agents execute each one in real time.
          </p>
        </div>

        {/* Input */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 space-y-4">
          <label className="block text-sm font-medium text-gray-700">Your task</label>
          <textarea
            value={task}
            onChange={(e) => setTask(e.target.value)}
            rows={3}
            placeholder="e.g. Search for the latest AI news, summarize it, then draft a LinkedIn post"
            className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
          />
          <div className="flex gap-3">
            <button
              onClick={runAgents}
              disabled={phase === 'running' || phase === 'planning'}
              className="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white font-semibold py-2.5 px-6 rounded-xl transition-colors text-sm"
            >
              {phase === 'planning' ? 'Planning…' : phase === 'running' ? 'Running agents…' : 'Run Agents'}
            </button>
            {(phase === 'done' || phase === 'error') && (
              <button
                onClick={reset}
                className="px-5 py-2.5 rounded-xl border border-gray-300 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              >
                Reset
              </button>
            )}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Plan */}
        {plan.length > 0 && (
          <div className="space-y-2">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400">
              Execution plan
            </h2>
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm divide-y divide-gray-100">
              {plan.map((step, i) => (
                <div key={step.id} className="flex items-start gap-3 px-5 py-3">
                  <span className="mt-0.5 text-xs font-bold text-gray-400 w-6 shrink-0">
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm text-gray-700">{step.description}</span>
                  </div>
                  <span className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${TOOL_COLORS[step.tool] ?? 'bg-gray-100 text-gray-700'}`}>
                    {step.tool}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Steps streaming */}
        {steps.length > 0 && (
          <div className="space-y-2">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400">
              Agent outputs
            </h2>
            <div className="space-y-3">
              {steps.map((step) => (
                <div
                  key={`${step.id}-${step.attempt}`}
                  className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-3"
                >
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                        {step.id}
                      </span>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${TOOL_COLORS[step.tool] ?? 'bg-gray-100 text-gray-700'}`}>
                        {step.tool}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-gray-400">
                      <span>{STATUS_ICON[step.status] ?? '❓'} {step.status}</span>
                      <span>{step.elapsed_seconds}s</span>
                      <span>attempt {step.attempt}</span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap border-t border-gray-100 pt-3">
                    {step.result}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Running indicator */}
        {phase === 'running' && (
          <div className="flex items-center gap-2 text-sm text-indigo-600">
            <span className="inline-block w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
            Waiting for next agent step…
          </div>
        )}

        {/* Done */}
        {phase === 'done' && (
          <div className="text-center text-sm text-gray-400 py-4">
            All steps completed.
          </div>
        )}
      </div>
    </main>
  )
}
