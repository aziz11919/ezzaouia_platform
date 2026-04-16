import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Plus, Send, Mic, MicOff, Paperclip, Trash2,
  Bot, User, Clock, ChevronRight, X, StopCircle,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import Sidebar from '../components/Layout/Sidebar'
import Topbar  from '../components/Layout/Topbar'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import { chatbotAPI } from '../api/chatbot'

const SUGGESTIONS = [
  'Quel est le BOPD moyen des 30 derniers jours ?',
  'Liste des puits avec BSW > 80%',
  'Résumé du dernier rapport de test de puits',
  'Quelle est la tendance de production ce trimestre ?',
]

export default function Chatbot() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const effectiveSessionId = sessionId && sessionId !== 'new' ? sessionId : null

  const [sessions,     setSessions]     = useState([])
  const [messages,     setMessages]     = useState([])
  const [activeSession, setActiveSession] = useState(null)
  const [input,        setInput]        = useState('')
  const [sending,      setSending]      = useState(false)
  const [recording,    setRecording]    = useState(false)
  const [uploadedDocs, setUploadedDocs] = useState([])
  const [loadingSess,  setLoadingSess]  = useState(true)
  const [loadingMsgs,  setLoadingMsgs]  = useState(false)

  const messagesEndRef = useRef(null)
  const fileInputRef   = useRef(null)
  const recognitionRef = useRef(null)
  const sendingRef     = useRef(false)

  // Load sessions
  useEffect(() => {
    chatbotAPI.getSessions()
      .then(r => setSessions(r.data?.sessions || []))
      .catch(console.error)
      .finally(() => setLoadingSess(false))
  }, [])

  // Load messages for current session
  useEffect(() => {
    if (!effectiveSessionId) {
      setMessages([])
      setActiveSession(null)
      return
    }
    setLoadingMsgs(true)
    chatbotAPI.getMessages(effectiveSessionId)
      .then(r => {
        setMessages(r.data?.messages || [])
        setActiveSession({ id: +effectiveSessionId, title: r.data?.title })
      })
      .catch(console.error)
      .finally(() => setLoadingMsgs(false))
  }, [effectiveSessionId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const handleSend = async (text) => {
    const question = (text || input).trim()
    if (!question || sendingRef.current) return
    sendingRef.current = true
    setInput('')
    setSending(true)

    // Optimistic UI
    const userMsg = { id: Date.now(), question, answer: null, pending: true }
    setMessages(prev => [...prev, userMsg])

    try {
      const payload = {
        question,
        session_id: activeSession?.id || null,
        doc_ids: uploadedDocs.map(d => d.doc_id),
      }
      const r = await chatbotAPI.ask(payload)
      const data = r.data

      if (!activeSession && data.session_id) {
        const newSess = { id: data.session_id, title: question.slice(0, 60) }
        setActiveSession(newSess)
        setSessions(prev => [newSess, ...prev])
        navigate(`/chatbot/${data.session_id}`, { replace: true })
      }

      const rawAnswer =
        typeof data?.answer === 'string'
          ? data.answer
          : typeof data?.response === 'string'
            ? data.response
            : typeof data?.reponse === 'string'
              ? data.reponse
              : ''

      const displayAnswer = data?.stopped
        ? 'Generation stopped.'
        : (rawAnswer?.trim() || 'No answer text returned by server.')

      setMessages(prev => prev.map(m =>
        m.id === userMsg.id
          ? { ...m, answer: displayAnswer, duration: data.duration, pending: false, message_id: data.message_id }
          : m
      ))
    } catch (err) {
      setMessages(prev => prev.map(m =>
        m.id === userMsg.id
          ? { ...m, answer: `Erreur: ${err.response?.data?.error || err.message}`, pending: false, error: true }
          : m
      ))
    } finally {
      setSending(false)
      sendingRef.current = false
    }
  }

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files || [])
    for (const file of files) {
      const fd = new FormData()
      fd.append('file', file)
      try {
        const r = await chatbotAPI.upload(fd)
        setUploadedDocs(prev => [...prev, { name: file.name, doc_id: r.data.doc_id }])
      } catch (err) {
        console.error('Upload error', err)
      }
    }
    e.target.value = ''
  }

  const toggleMic = () => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) return
    if (recording) {
      recognitionRef.current?.stop()
      setRecording(false)
      return
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    const rec = new SpeechRecognition()
    rec.lang = 'fr-FR'
    rec.onresult = e => setInput(e.results[0][0].transcript)
    rec.onend = () => setRecording(false)
    recognitionRef.current = rec
    rec.start()
    setRecording(true)
  }

  const deleteSession = async (id) => {
    await chatbotAPI.deleteSession(id)
    setSessions(prev => prev.filter(s => s.id !== id))
    if (activeSession?.id === id) {
      navigate('/chatbot', { replace: true })
    }
  }

  return (
    <div className="flex h-screen bg-maretap-dark overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Topbar title="Chatbot IA" subtitle="Posez des questions sur vos documents de production" />

        <div className="flex-1 flex overflow-hidden">

          {/* ── Sessions panel ── */}
          <aside className="w-56 flex-shrink-0 bg-maretap-dark2 border-r border-red-900/20 flex flex-col">
            <div className="p-3 border-b border-red-900/10">
              <button
                onClick={() => navigate('/chatbot')}
                className="flex items-center gap-2 w-full px-3 py-2 bg-maretap-red hover:bg-maretap-red-light text-white text-xs font-rajdhani font-bold uppercase tracking-wider rounded transition-colors"
              >
                <Plus size={14} /> Nouvelle conversation
              </button>
            </div>

            <div className="flex-1 overflow-y-auto py-2">
              {loadingSess
                ? <div className="flex justify-center p-4"><LoadingSpinner size="sm" /></div>
                : sessions.length === 0
                  ? <p className="text-xs text-gray-600 text-center p-4">Aucune conversation</p>
                  : sessions.map(s => (
                    <div
                      key={s.id}
                      className={`group flex items-center gap-2 px-3 py-2.5 cursor-pointer hover:bg-red-900/10 transition-colors ${activeSession?.id === s.id ? 'bg-red-900/10 border-l-2 border-maretap-red' : 'border-l-2 border-transparent'}`}
                      onClick={() => navigate(`/chatbot/${s.id}`)}
                    >
                      <Bot size={12} className="shrink-0 text-gray-600" />
                      <span className="text-xs text-gray-400 truncate flex-1">{s.title}</span>
                      <button
                        onClick={e => { e.stopPropagation(); deleteSession(s.id) }}
                        className="hidden group-hover:block text-gray-600 hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  ))
              }
            </div>
          </aside>

          {/* ── Chat area ── */}
          <div className="flex-1 flex flex-col overflow-hidden">

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {loadingMsgs
                ? <div className="flex justify-center p-8"><LoadingSpinner text="Chargement de la conversation..." /></div>
                : messages.length === 0
                  ? (
                    <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
                      <div className="w-16 h-16 rounded-full bg-maretap-dark3 border border-red-900/20 flex items-center justify-center">
                        <Bot size={28} className="text-maretap-red opacity-60" />
                      </div>
                      <div>
                        <p className="text-gray-400 font-rajdhani text-lg">Assistant IA MARETAP</p>
                        <p className="text-gray-600 text-sm mt-1">Posez une question sur vos documents de production</p>
                      </div>
                      <div className="grid grid-cols-2 gap-2 max-w-xl">
                        {SUGGESTIONS.map(s => (
                          <button
                            key={s}
                            onClick={() => handleSend(s)}
                            className="text-left text-xs text-gray-500 bg-maretap-dark3 border border-red-900/10 hover:border-red-700/30 hover:text-gray-300 rounded-md px-3 py-2 transition-colors"
                          >
                            <ChevronRight size={12} className="inline mr-1 text-maretap-red" />
                            {s}
                          </button>
                        ))}
                      </div>
                    </div>
                  )
                  : messages.map(msg => (
                    <div key={msg.id}>
                      {/* User message */}
                      <div className="flex justify-end mb-2">
                        <div className="flex items-end gap-2 max-w-2xl">
                          <div className="bg-maretap-red/15 border border-maretap-red/20 rounded-xl rounded-br-sm px-4 py-3 text-sm text-gray-200">
                            {msg.question}
                          </div>
                          <div className="w-7 h-7 rounded-full bg-maretap-red/20 flex items-center justify-center shrink-0">
                            <User size={14} className="text-maretap-red" />
                          </div>
                        </div>
                      </div>

                      {/* Bot answer */}
                      <div className="flex justify-start mb-4">
                        <div className="flex items-start gap-2 max-w-3xl">
                          <div className="w-7 h-7 rounded-full bg-maretap-dark3 border border-red-900/20 flex items-center justify-center shrink-0 mt-0.5">
                            <Bot size={14} className="text-maretap-red" />
                          </div>
                          <div className="bg-maretap-dark3 border border-red-900/10 rounded-xl rounded-bl-sm px-4 py-3 text-sm text-gray-300 prose prose-invert prose-sm max-w-none">
                            {msg.pending
                              ? <span className="flex items-center gap-2">
                                  <span className="w-2 h-2 bg-maretap-red rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                  <span className="w-2 h-2 bg-maretap-red rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                  <span className="w-2 h-2 bg-maretap-red rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                </span>
                              : <ReactMarkdown>{msg.answer || ''}</ReactMarkdown>
                            }
                            {!msg.pending && msg.duration && (
                              <div className="flex items-center gap-1 mt-2 text-xs text-gray-600 border-t border-red-900/10 pt-2">
                                <Clock size={11} />
                                <span>{msg.duration}s</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
              }
              <div ref={messagesEndRef} />
            </div>

            {/* Active docs */}
            {uploadedDocs.length > 0 && (
              <div className="flex items-center gap-2 px-4 py-2 border-t border-red-900/10 flex-wrap">
                {uploadedDocs.map(d => (
                  <span key={d.doc_id} className="flex items-center gap-1.5 text-xs bg-blue-900/20 border border-blue-700/30 text-blue-400 rounded-full px-2.5 py-1">
                    <Paperclip size={10} /> {d.name}
                    <button onClick={() => setUploadedDocs(prev => prev.filter(x => x.doc_id !== d.doc_id))}>
                      <X size={10} className="hover:text-white" />
                    </button>
                  </span>
                ))}
              </div>
            )}

            {/* Input bar */}
            <div className="border-t border-red-900/20 p-4">
              <div className="flex items-end gap-2">
                <div className="flex-1 bg-maretap-dark3 border border-red-900/20 rounded-xl flex items-end gap-2 px-4 py-3 focus-within:border-maretap-red transition-colors">
                  <textarea
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleSend()
                      }
                    }}
                    placeholder="Posez votre question... (Entrée pour envoyer)"
                    rows={1}
                    className="flex-1 bg-transparent text-sm text-white placeholder-gray-600 outline-none resize-none"
                    style={{ maxHeight: '120px', overflowY: 'auto' }}
                  />
                  <div className="flex items-center gap-1 shrink-0">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.docx,.xlsx"
                      multiple
                      className="hidden"
                      onChange={handleFileUpload}
                    />
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="p-1.5 text-gray-600 hover:text-gray-400 transition-colors"
                      title="Joindre un fichier"
                    >
                      <Paperclip size={15} />
                    </button>
                    <button
                      onClick={toggleMic}
                      className={`p-1.5 transition-colors ${recording ? 'text-maretap-red animate-pulse' : 'text-gray-600 hover:text-gray-400'}`}
                      title="Reconnaissance vocale"
                    >
                      {recording ? <MicOff size={15} /> : <Mic size={15} />}
                    </button>
                  </div>
                </div>

                {sending
                  ? (
                    <button
                      onClick={() => chatbotAPI.stopGeneration()}
                      className="p-3 bg-red-900/30 border border-red-700/30 text-red-400 rounded-xl hover:bg-red-900/50 transition-colors"
                      title="Arrêter"
                    >
                      <StopCircle size={20} />
                    </button>
                  )
                  : (
                    <button
                      onClick={() => handleSend()}
                      disabled={!input.trim()}
                      className="p-3 bg-maretap-red hover:bg-maretap-red-light text-white rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <Send size={20} />
                    </button>
                  )
                }
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  )
}
