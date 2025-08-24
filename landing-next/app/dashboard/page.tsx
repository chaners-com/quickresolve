'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { 
  UserCircle, 
  FileText, 
  Settings, 
  LogOut, 
  Upload, 
  Search,
  Bell,
  Home,
  Folder,
  BarChart3,
  Plus,
  Filter,
  Grid,
  List,
  MessageSquare,
  User as UserIcon
} from 'lucide-react'
import { GlassCard } from '../components/GlassCard'
import { GradientOrbs } from '../components/GradientOrbs'

interface User {
  id: number
  email: string
  username?: string
  first_name?: string
  last_name?: string
  is_active: boolean
  created_at: string
}

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
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [stats, setStats] = useState<DashboardStats>({
    total_files: 0,
    processed_files: 0,
    processing_files: 0,
    error_files: 0,
    total_workspaces: 0
  })
  const [recentFiles, setRecentFiles] = useState<FileItem[]>([])
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [selectedFilter, setSelectedFilter] = useState('all')
  const [currentPage, setCurrentPage] = useState('dashboard')
  const router = useRouter()

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    try {
      const token = localStorage.getItem('authToken')
      const userData = localStorage.getItem('user')

      if (!token || !userData) {
        router.push('/login')
        return
      }

      // Verify token with backend
      const response = await fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        const user = await response.json()
        setUser(user)
        await loadDashboardData(user.id)
      } else {
        // Token is invalid, redirect to login
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

  const loadDashboardData = async (userId: number) => {
    try {
      // Load user stats
      const statsResponse = await fetch(`/api/dashboard/stats?user_id=${userId}`)
      if (statsResponse.ok) {
        const statsData = await statsResponse.json()
        setStats(statsData)
      }

      // Load recent files
      const filesResponse = await fetch(`/api/files?user_id=${userId}&limit=6`)
      if (filesResponse.ok) {
        const filesData = await filesResponse.json()
        setRecentFiles(filesData)
      }

      // Load workspaces
      const workspacesResponse = await fetch(`/api/workspaces?owner_id=${userId}`)
      if (workspacesResponse.ok) {
        const workspacesData = await workspacesResponse.json()
        setWorkspaces(workspacesData)
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('authToken')
    localStorage.removeItem('user')
    router.push('/login')
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    // For now, redirect to file management page
    router.push('/dashboard/files')
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
      
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-64 glass-premium border-r border-white/10 z-50">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center px-6 py-4">
            <Link href="/" className="text-2xl font-bold gradient-text">
              QuickResolve
            </Link>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 space-y-2">
            <NavItem 
              icon={<Home size={20} />} 
              label="Dashboard" 
              active={currentPage === 'dashboard'}
              onClick={() => setCurrentPage('dashboard')}
            />
            <NavItem 
              icon={<Folder size={20} />} 
              label="Files" 
              onClick={() => router.push('/dashboard/files')}
            />
            <NavItem 
              icon={<MessageSquare size={20} />} 
              label="AI Chat" 
              onClick={() => router.push('/dashboard/chat')}
            />
            <NavItem 
              icon={<BarChart3 size={20} />} 
              label="Analytics" 
              onClick={() => router.push('/dashboard/analytics')}
            />
            <NavItem 
              icon={<UserIcon size={20} />} 
              label="Profile" 
              onClick={() => router.push('/dashboard/profile')}
            />
            <NavItem 
              icon={<Settings size={20} />} 
              label="Settings" 
              onClick={() => router.push('/dashboard/settings')}
            />
          </nav>

          {/* User Profile */}
          <div className="p-4 border-t border-white/10">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full flex items-center justify-center">
                <span className="text-white font-semibold text-sm">
                  {user?.first_name?.[0]}{user?.last_name?.[0]}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium truncate">
                  {user?.first_name} {user?.last_name}
                </p>
                <p className="text-white/60 text-xs truncate">
                  {user?.email}
                </p>
              </div>
              <button
                onClick={handleLogout}
                className="text-white/60 hover:text-white transition-colors"
                title="Logout"
              >
                <LogOut size={18} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="ml-64">
        {/* Header */}
        <header className="bg-white/5 border-b border-white/10 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white">
                Welcome back, {user?.first_name}!
              </h1>
              <p className="text-white/60 mt-1">
                Manage your files and interact with your documents
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <button className="relative text-white/60 hover:text-white transition-colors">
                <Bell size={20} />
                <span className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-500 rounded-full"></span>
              </button>
              
              {/* File Upload */}
              <div className="relative">
                <input
                  type="file"
                  id="headerFileUpload"
                  multiple
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <motion.label
                  htmlFor="headerFileUpload"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-4 py-2 rounded-lg font-medium flex items-center space-x-2 shadow-lg cursor-pointer"
                >
                  <Upload size={18} />
                  <span>Upload Files</span>
                </motion.label>
              </div>
            </div>
          </div>
        </header>

        {/* Dashboard Content */}
        <main className="p-6">
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
                  <FileCard key={file.id} file={file} />
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
        </main>
      </div>
    </div>
  )
}

// Navigation Item Component
function NavItem({ 
  icon, 
  label, 
  active = false, 
  onClick 
}: { 
  icon: React.ReactNode, 
  label: string, 
  active?: boolean, 
  onClick?: () => void 
}) {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      onClick={onClick}
      className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
        active 
          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
          : 'text-white/70 hover:text-white hover:bg-white/5'
      }`}
    >
      {icon}
      <span className="font-medium">{label}</span>
    </motion.button>
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
function FileCard({ file }: { file: FileItem }) {
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

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
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
  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
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

// Import additional icons
import { CheckCircle, Clock } from 'lucide-react'