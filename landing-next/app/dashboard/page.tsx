'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { 
  FileText, 
  Upload, 
  MessageSquare,
  BarChart3,
  Folder,
  CheckCircle, 
  Clock,
  AlertCircle
} from 'lucide-react'
import { GlassCard } from '../components/GlassCard'
import { useAuth } from '../components/SecureAuthGuard'

interface Workspace {
  id: number
  name: string
  owner_id: number
  created_at: string
}

interface FileItem {
  id: string
  name: string
  s3_key: string
  workspace_id: number
  status: number
  created_at: string
}

interface DashboardStats {
  total_files: number
  processed_files: number
  processing_files: number
  error_files: number
  total_workspaces: number
}

export default function DashboardPage() {
  const { user, isLoading } = useAuth() // Use the auth context from SecureAuthGuard
  const [stats, setStats] = useState<DashboardStats>({
    total_files: 0,
    processed_files: 0,
    processing_files: 0,
    error_files: 0,
    total_workspaces: 0
  })
  const [recentFiles, setRecentFiles] = useState<FileItem[]>([])
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null)
  const [showFileViewer, setShowFileViewer] = useState(false)
  const router = useRouter()

  useEffect(() => {
    if (user) {
      loadDashboardData(user.id)
    }
  }, [user])

  const loadDashboardData = async (authUserId: number) => {
    try {
      // First, get the ingestion service user ID from the username
      const username = user?.username || `${user?.first_name}_${user?.last_name}`.toLowerCase()
      
      const ingestionUserResponse = await fetch(`/api/users?username=${encodeURIComponent(username)}`)
      let ingestionUserId = authUserId // fallback to auth user ID
      
      if (ingestionUserResponse.ok) {
        const users = await ingestionUserResponse.json()
        if (users && users.length > 0) {
          ingestionUserId = users[0].id
        }
      }

      // Load user stats
      const statsResponse = await fetch(`/api/dashboard/stats?user_id=${ingestionUserId}`)
      if (statsResponse.ok) {
        const statsData = await statsResponse.json()
        setStats(statsData)
      }

      // Load recent files
      const filesResponse = await fetch(`/api/files?user_id=${ingestionUserId}&limit=6`)
      if (filesResponse.ok) {
        const filesData = await filesResponse.json()
        setRecentFiles(filesData)
      }

      // Load workspaces
      const workspacesResponse = await fetch(`/api/workspaces?owner_id=${ingestionUserId}`)
      if (workspacesResponse.ok) {
        const workspacesData = await workspacesResponse.json()
        setWorkspaces(workspacesData)
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    }
  }

  const handleViewFile = (file: FileItem) => {
    setSelectedFile(file)
    setShowFileViewer(true)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex items-center space-x-2 text-white">
          <div className="w-8 h-8 border-2 border-white/30 border-t-emerald-500 rounded-full animate-spin"></div>
          <span>Loading...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 min-h-full bg-gray-900">
      {/* Page Title */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-white/60">Welcome back, {user?.first_name}!</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatsCard
          title="Total Files"
          value={stats.total_files.toString()}
          change={stats.total_files > 0 ? "+12%" : "0%"}
          positive={stats.total_files > 0}
          icon={<FileText size={24} />}
        />
        <StatsCard
          title="Processed Files"
          value={stats.processed_files.toString()}
          change={stats.processed_files > 0 ? "+5%" : "0%"}
          positive={stats.processed_files > 0}
          icon={<CheckCircle size={24} />}
        />
        <StatsCard
          title="Processing"
          value={stats.processing_files.toString()}
          change="0%"
          positive={null}
          icon={<Clock size={24} />}
        />
        <StatsCard
          title="Workspaces"
          value={stats.total_workspaces.toString()}
          change={stats.total_workspaces > 0 ? "+8%" : "0%"}
          positive={stats.total_workspaces > 0}
          icon={<Folder size={24} />}
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <QuickActionCard
          title="Upload Documents"
          description="Add new files to your workspace"
          icon={<Upload size={32} />}
          onClick={() => router.push('/dashboard/files')}
          gradient="from-blue-500 to-cyan-500"
        />
        <QuickActionCard
          title="Chat with AI"
          description="Ask questions about your documents"
          icon={<MessageSquare size={32} />}
          onClick={() => router.push('/dashboard/chat')}
          gradient="from-emerald-500 to-teal-500"
        />
        <QuickActionCard
          title="View Analytics"
          description="Monitor your usage and insights"
          icon={<BarChart3 size={32} />}
          onClick={() => router.push('/dashboard/analytics')}
          gradient="from-purple-500 to-pink-500"
        />
      </div>

      {/* Recent Files */}
      <GlassCard className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-white">Recent Files</h2>
          <Link 
            href="/dashboard/files"
            className="text-emerald-400 hover:text-emerald-300 text-sm font-medium"
          >
            View All
          </Link>
        </div>

        {recentFiles.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recentFiles.map((file) => (
              <FileCard key={file.id} file={file} onViewFile={handleViewFile} />
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <FileText className="mx-auto text-white/40 mb-4" size={48} />
            <p className="text-white/60 text-lg">No files uploaded yet</p>
            <p className="text-white/40 text-sm mt-2">
              Upload your first document to get started
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => router.push('/dashboard/files')}
              className="mt-4 bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-6 py-3 rounded-lg font-medium"
            >
              Upload Files
            </motion.button>
          </div>
        )}
      </GlassCard>

      {/* Workspaces Overview */}
      {workspaces.length > 0 && (
        <GlassCard className="p-6 mt-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-white">Your Workspaces</h2>
            <span className="text-white/60 text-sm">{workspaces.length} workspace{workspaces.length > 1 ? 's' : ''}</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {workspaces.map((workspace) => (
              <WorkspaceCard key={workspace.id} workspace={workspace} />
            ))}
          </div>
        </GlassCard>
      )}

      {/* File Viewer Modal */}
      {showFileViewer && selectedFile && (
        <FileViewer 
          file={selectedFile} 
          onClose={() => {
            setShowFileViewer(false)
            setSelectedFile(null)
          }}
        />
      )}
    </div>
  )
}

// Stats Card Component
function StatsCard({ 
  title, 
  value, 
  change, 
  positive,
  icon 
}: { 
  title: string, 
  value: string, 
  change: string, 
  positive: boolean | null,
  icon?: React.ReactNode
}) {
  return (
    <GlassCard className="p-6">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-white/60 text-sm font-medium">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
          <div className={`text-sm font-medium mt-1 ${
            positive === null ? 'text-white/60' :
            positive ? 'text-green-400' : 'text-red-400'
          }`}>
            {change}
          </div>
        </div>
        {icon && (
          <div className="text-emerald-400/60">
            {icon}
          </div>
        )}
      </div>
    </GlassCard>
  )
}

// Quick Action Card Component
function QuickActionCard({
  title,
  description,
  icon,
  onClick,
  gradient
}: {
  title: string
  description: string
  icon: React.ReactNode
  onClick: () => void
  gradient: string
}) {
  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className="glass-premium p-6 rounded-lg border border-white/10 hover:border-emerald-500/30 transition-all cursor-pointer group"
    >
      <div className={`w-12 h-12 bg-gradient-to-r ${gradient} rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
        <div className="text-white">
          {icon}
        </div>
      </div>
      <h3 className="text-white font-semibold mb-2">{title}</h3>
      <p className="text-white/60 text-sm">{description}</p>
    </motion.div>
  )
}

// File Card Component
function FileCard({ file, onViewFile }: { file: FileItem; onViewFile: (file: FileItem) => void }) {
  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase()
    switch (extension) {
      case 'pdf': return '📄'
      case 'doc':
      case 'docx': return '📝'
      case 'xls':
      case 'xlsx': return '📊'
      case 'txt': return '📄'
      default: return '📄'
    }
  }

  const getStatusColor = (status: number) => {
    switch (status) {
      case 1: return 'text-yellow-400'
      case 2: return 'text-green-400'
      case 3: return 'text-red-400'
      default: return 'text-white/60'
    }
  }

  const getStatusText = (status: number) => {
    switch (status) {
      case 1: return 'Processing'
      case 2: return 'Processed'
      case 3: return 'Error'
      default: return 'Unknown'
    }
  }

  const handleFileClick = () => {
    // Open file viewer instead of navigating
    onViewFile(file)
  }

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      onClick={handleFileClick}
      className="glass-premium p-4 rounded-lg border border-white/10 hover:border-emerald-500/30 transition-all cursor-pointer"
    >
      <div className="flex items-center space-x-3 mb-3">
        <span className="text-2xl">{getFileIcon(file.name)}</span>
        <div className="flex-1 min-w-0">
          <p className="text-white font-medium truncate" title={file.name}>
            {file.name}
          </p>
          <p className="text-white/60 text-sm">
            {new Date(file.created_at).toLocaleDateString()}
          </p>
        </div>
      </div>
      <div className="flex items-center justify-between text-sm">
        <span className={`font-medium ${getStatusColor(file.status)}`}>
          {getStatusText(file.status)}
        </span>
      </div>
    </motion.div>
  )
}

// Workspace Card Component
function WorkspaceCard({ workspace }: { workspace: Workspace }) {
  const router = useRouter()
  
  const handleWorkspaceClick = () => {
    // Navigate to files page and highlight the workspace
    router.push(`/dashboard/files?highlight=workspace_${workspace.id}`)
  }

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      onClick={handleWorkspaceClick}
      className="glass-premium p-4 rounded-lg border border-white/10 hover:border-emerald-500/30 transition-all cursor-pointer"
    >
      <div className="flex items-center space-x-3 mb-3">
        <div className="w-10 h-10 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-lg flex items-center justify-center">
          <Folder className="text-white" size={20} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-white font-medium truncate" title={workspace.name}>
            {workspace.name}
          </p>
          <p className="text-white/60 text-sm">
            Created {new Date(workspace.created_at).toLocaleDateString()}
          </p>
        </div>
      </div>
    </motion.div>
  )
}

// FileViewer component for modal display
function FileViewer({ file, onClose }: { file: any; onClose: () => void }) {
  const [content, setContent] = useState<string>('')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchContent = async () => {
      if (!file.s3_key) {
        setError('File not available (no S3 key)')
        setIsLoading(false)
        return
      }

      try {
        setIsLoading(true)
        const response = await fetch(`/api/file-content?s3_key=${encodeURIComponent(file.s3_key)}`)
        
        if (response.ok) {
          const data = await response.json()
          setContent(data.content || 'No content available')
          setError(null)
        } else {
          setError('Failed to fetch file content')
        }
      } catch (error) {
        console.error('Error fetching file content:', error)
        setError('Error loading file content')
      } finally {
        setIsLoading(false)
      }
    }

    fetchContent()
  }, [file.s3_key])

  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase()
    switch (extension) {
      case 'pdf': return '📄'
      case 'doc':
      case 'docx': return '📝'
      case 'xls':
      case 'xlsx': return '📊'
      case 'txt': return '📄'
      case 'md': return '📝'
      case 'py': return '🐍'
      case 'js':
      case 'ts': return '⚡'
      case 'json': return '📋'
      default: return '📄'
    }
  }

  const getStatusColor = (status: number) => {
    switch (status) {
      case 1: return 'text-yellow-400'
      case 2: return 'text-green-400'
      case 3: return 'text-red-400'
      default: return 'text-white/60'
    }
  }

  const getStatusText = (status: number) => {
    switch (status) {
      case 1: return 'Processing'
      case 2: return 'Processed'
      case 3: return 'Error'
      default: return 'Unknown'
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-white/10 backdrop-blur-lg rounded-xl border border-white/20 max-w-6xl w-full max-h-[90vh] overflow-hidden"
      >
        <div className="flex items-center justify-between p-6 border-b border-white/20">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">{getFileIcon(file.name)}</span>
            <div>
              <h3 className="text-white text-xl font-bold">{file.name}</h3>
              <div className="flex items-center space-x-4 text-sm">
                <span className="text-white/60">
                  {new Date(file.created_at).toLocaleDateString()} • {new Date(file.created_at).toLocaleTimeString()}
                </span>
                <div className={`flex items-center space-x-1 ${getStatusColor(file.status)}`}>
                  <span>{getStatusText(file.status)}</span>
                </div>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white/60 hover:text-white p-2 hover:bg-white/10 rounded-lg transition-colors"
            title="Close"
          >
            ✕
          </button>
        </div>
        
        <div className="p-6 overflow-auto max-h-[calc(90vh-120px)]">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="flex items-center space-x-2 text-white">
                <div className="w-6 h-6 border-2 border-white/30 border-t-emerald-500 rounded-full animate-spin"></div>
                <span>Loading file content...</span>
              </div>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <div className="text-red-400 mb-4">
                <AlertCircle size={48} className="mx-auto mb-2" />
                <p className="text-lg">{error}</p>
              </div>
              <p className="text-white/60 text-sm">
                The file might not be processed yet or there was an error loading the content.
              </p>
            </div>
          ) : (
            <div className="bg-gray-900/50 rounded-lg p-4 border border-white/10">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-white font-medium">File Content</h4>
                <div className="text-white/60 text-xs">
                  {content.length} characters
                </div>
              </div>
              <pre className="whitespace-pre-wrap text-white/90 text-sm leading-relaxed overflow-auto max-h-96 bg-black/20 p-4 rounded border border-white/10">
                {content}
              </pre>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  )
}