'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { 
  Send, 
  Bot, 
  User, 
  Folder,
  FileText,
  MessageCircle,
  Trash2,
  Eye,
  MoreVertical
} from 'lucide-react'
import { GlassCard } from '../components/GlassCard'
import { GradientOrbs } from '../components/GradientOrbs'

interface User {
  id: number
  email: string
  username?: string
  first_name?: string
  last_name?: string
}

interface Workspace {
  id: number
  name: string
  description?: string
  owner_id: number
  created_at: string
}

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  sources?: RetrievedDocument[]
}

interface RetrievedDocument {
  s3_key: string
  score: number
  content: string
  workspace_name: string
}

export default function AIChatPage() {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [selectedWorkspace, setSelectedWorkspace] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [retrievedSources, setRetrievedSources] = useState<RetrievedDocument[]>([])
  const [showSources, setShowSources] = useState(false)
  const [selectedDocument, setSelectedDocument] = useState<RetrievedDocument | null>(null)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const router = useRouter()

  useEffect(() => {
    checkAuth()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const checkAuth = async () => {
    try {
      const token = localStorage.getItem('authToken')
      if (!token) {
        router.push('/login')
        return
      }

      const response = await fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
        await loadWorkspaces(userData.id)
      } else {
        localStorage.removeItem('authToken')
        localStorage.removeItem('user')
        router.push('/login')
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      router.push('/login')
    } finally {
      setIsLoading(false)
    }
  }

  const loadWorkspaces = async (userId: number) => {
    try {
      const response = await fetch(`/api/workspaces?owner_id=${userId}`)
      if (response.ok) {
        const workspaceData = await response.json()
        setWorkspaces(workspaceData)
        if (workspaceData.length > 0) {
          setSelectedWorkspace(workspaceData[0].id)
          addSystemMessage(`Connected to workspace: ${workspaceData[0].name}`)
        } else {
          addSystemMessage('No workspaces available. Please create a workspace and upload documents first.')
        }
      }
    } catch (error) {
      console.error('Failed to load workspaces:', error)
      addSystemMessage('Failed to load workspaces. Please refresh the page.')
    }
  }

  const addSystemMessage = (content: string) => {
    const systemMessage: Message = {
      id: Date.now().toString(),
      role: 'system',
      content,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, systemMessage])
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleWorkspaceChange = (workspaceId: number) => {
    setSelectedWorkspace(workspaceId)
    const workspace = workspaces.find(w => w.id === workspaceId)
    addSystemMessage(`Switched to workspace: ${workspace?.name || 'Unknown'}`)
    setRetrievedSources([])
  }

  const sendMessage = async () => {
    if (!inputMessage.trim() || !selectedWorkspace || isTyping) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsTyping(true)

    try {
      // Create conversation history for context
      const conversation = messages
        .filter(msg => msg.role !== 'system')
        .map(msg => ({
          role: msg.role,
          content: msg.content
        }))
      
      conversation.push({ role: 'user', content: userMessage.content })

      const response = await fetch('/api/ai-agent/conversation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: conversation,
          workspace_id: selectedWorkspace
        })
      })

      if (response.ok) {
        const data = await response.json()
        
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.response,
          timestamp: new Date(),
          sources: data.relevant_docs || []
        }

        setMessages(prev => [...prev, assistantMessage])
        setRetrievedSources(data.relevant_docs || [])
      } else {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'I apologize, but I encountered an error while processing your request. Please try again.',
          timestamp: new Date()
        }
        setMessages(prev => [...prev, assistantMessage])
      }
    } catch (error) {
      console.error('Error sending message:', error)
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'I apologize, but I encountered a network error. Please check your connection and try again.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, assistantMessage])
    } finally {
      setIsTyping(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearConversation = () => {
    if (confirm('Are you sure you want to clear the conversation?')) {
      setMessages([])
      setRetrievedSources([])
      if (selectedWorkspace) {
        const workspace = workspaces.find(w => w.id === selectedWorkspace)
        addSystemMessage(`Conversation cleared. Connected to workspace: ${workspace?.name || 'Unknown'}`)
      }
    }
  }

  const formatSourceName = (s3Key: string) => {
    const parts = s3Key.split('/')
    return parts[parts.length - 1]
  }

  if (isLoading) {
    return (
      <div className="relative min-h-screen bg-gray-900">
        <GradientOrbs />
        <div className="flex items-center justify-center min-h-screen">
          <div className="flex items-center space-x-2 text-white">
            <div className="w-8 h-8 border-2 border-white/30 border-t-emerald-500 rounded-full animate-spin"></div>
            <span>Loading...</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="relative min-h-screen bg-gray-900">
      <GradientOrbs />
      
      <div className="container mx-auto px-6 py-8 h-screen flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <Bot className="text-emerald-400" size={32} />
            <div>
              <h1 className="text-2xl font-bold text-white">AI Assistant</h1>
              <p className="text-white/60">Chat with your documents</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Workspace Selector */}
            <div className="flex items-center space-x-2">
              <Folder className="text-white/60" size={18} />
              <select
                value={selectedWorkspace || ''}
                onChange={(e) => handleWorkspaceChange(parseInt(e.target.value))}
                className="bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value="">Select workspace...</option>
                {workspaces.map((workspace) => (
                  <option key={workspace.id} value={workspace.id}>
                    {workspace.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Clear Chat */}
            <button
              onClick={clearConversation}
              className="text-white/60 hover:text-red-400 transition-colors p-2 rounded-lg hover:bg-white/5"
              title="Clear conversation"
            >
              <Trash2 size={18} />
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-0">
          {/* Chat Area */}
          <div className="lg:col-span-3 flex flex-col">
            <GlassCard className="flex-1 flex flex-col min-h-0">
              {/* Messages */}
              <div className="flex-1 p-6 overflow-y-auto space-y-4" style={{ minHeight: 0 }}>
                {messages.map((message) => (
                  <MessageBubble key={message.id} message={message} />
                ))}
                
                {isTyping && (
                  <div className="flex items-start space-x-3">
                    <div className="w-8 h-8 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full flex items-center justify-center">
                      <Bot size={16} className="text-white" />
                    </div>
                    <div className="bg-white/10 rounded-2xl rounded-tl-sm px-4 py-3">
                      <div className="flex items-center space-x-1">
                        <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="p-6 border-t border-white/10">
                <div className="flex items-end space-x-4">
                  <div className="flex-1">
                    <textarea
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder={selectedWorkspace ? "Ask me anything about your documents..." : "Please select a workspace first..."}
                      disabled={!selectedWorkspace || isTyping}
                      className="w-full px-4 py-3 glass-premium rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
                      rows={1}
                      style={{ minHeight: '3rem', maxHeight: '8rem' }}
                    />
                  </div>
                  
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={sendMessage}
                    disabled={!inputMessage.trim() || !selectedWorkspace || isTyping}
                    className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white p-3 rounded-lg shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                  >
                    <Send size={18} />
                  </motion.button>
                </div>
              </div>
            </GlassCard>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-4">
            {/* Conversation Info */}
            <GlassCard className="p-4">
              <h3 className="text-white font-semibold mb-3 flex items-center space-x-2">
                <MessageCircle size={16} />
                <span>Conversation</span>
              </h3>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-white/60">Messages:</span>
                  <span className="text-white">{messages.filter(m => m.role !== 'system').length}</span>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-white/60">Workspace:</span>
                  <span className="text-white text-xs truncate">
                    {selectedWorkspace ? workspaces.find(w => w.id === selectedWorkspace)?.name : 'None'}
                  </span>
                </div>
              </div>
            </GlassCard>

            {/* Retrieved Documents */}
            <GlassCard className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-white font-semibold flex items-center space-x-2">
                  <FileText size={16} />
                  <span>Sources</span>
                </h3>
                <span className="text-white/60 text-xs">
                  {retrievedSources.length} docs
                </span>
              </div>
              
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {retrievedSources.length > 0 ? (
                  retrievedSources.map((doc, index) => (
                    <motion.div
                      key={index}
                      whileHover={{ scale: 1.02 }}
                      onClick={() => setSelectedDocument(doc)}
                      className="bg-white/5 border border-white/10 rounded-lg p-3 cursor-pointer hover:border-emerald-500/30 transition-all"
                    >
                      <div className="text-white text-xs font-medium mb-1 truncate">
                        {formatSourceName(doc.s3_key)}
                      </div>
                      <div className="text-emerald-400 text-xs mb-2">
                        Relevance: {(doc.score * 100).toFixed(1)}%
                      </div>
                      <div className="text-white/60 text-xs line-clamp-2">
                        {doc.content.substring(0, 80)}...
                      </div>
                    </motion.div>
                  ))
                ) : (
                  <p className="text-white/40 text-xs text-center py-4">
                    No documents retrieved yet
                  </p>
                )}
              </div>
            </GlassCard>
          </div>
        </div>

        {/* Document Modal */}
        {selectedDocument && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-gray-800 rounded-lg max-w-2xl w-full max-h-[80vh] flex flex-col"
            >
              <div className="flex items-center justify-between p-4 border-b border-white/10">
                <h3 className="text-white font-semibold">
                  {formatSourceName(selectedDocument.s3_key)}
                </h3>
                <button
                  onClick={() => setSelectedDocument(null)}
                  className="text-white/60 hover:text-white text-xl leading-none"
                >
                  ×
                </button>
              </div>
              
              <div className="p-4 border-b border-white/10">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-white/60">Relevance:</span>
                    <span className="text-emerald-400 ml-2">
                      {(selectedDocument.score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-white/60">Workspace:</span>
                    <span className="text-white ml-2">{selectedDocument.workspace_name}</span>
                  </div>
                </div>
              </div>
              
              <div className="flex-1 p-4 overflow-y-auto">
                <div className="text-white/80 text-sm leading-relaxed whitespace-pre-wrap">
                  {selectedDocument.content}
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  )
}

// Message Bubble Component
function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <div className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 max-w-md text-center">
          <p className="text-white/70 text-sm">{message.content}</p>
          <p className="text-white/40 text-xs mt-1">
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={`flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
        isUser 
          ? 'bg-gradient-to-r from-blue-500 to-purple-500' 
          : 'bg-gradient-to-r from-emerald-500 to-teal-500'
      }`}>
        {isUser ? <User size={16} className="text-white" /> : <Bot size={16} className="text-white" />}
      </div>

      {/* Message Content */}
      <div className={`max-w-[70%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div className={`rounded-2xl px-4 py-3 ${
          isUser 
            ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-tr-sm' 
            : 'bg-white/10 text-white rounded-tl-sm'
        }`}>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>
        
        {/* Timestamp and Sources */}
        <div className={`flex items-center space-x-2 mt-1 text-xs text-white/40 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
          <span>{message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
          {!isUser && message.sources && message.sources.length > 0 && (
            <span className="text-emerald-400">
              • {message.sources.length} source{message.sources.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}