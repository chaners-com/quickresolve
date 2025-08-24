'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { 
  Upload, 
  Search, 
  Filter, 
  Grid, 
  List, 
  Plus,
  Folder,
  FileText,
  BarChart3,
  Trash2,
  Download,
  Eye,
  AlertCircle,
  CheckCircle,
  Clock
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
  workspace?: Workspace
}

export default function FileManagementPage() {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [files, setFiles] = useState<FileItem[]>([])
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [selectedWorkspace, setSelectedWorkspace] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [selectedFilter, setSelectedFilter] = useState('all')
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({})
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  
  const router = useRouter()

  useEffect(() => {
    checkAuth()
  }, [])

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
        await loadFiles(userData.id)
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
        }
      }
    } catch (error) {
      console.error('Failed to load workspaces:', error)
    }
  }

  const loadFiles = async (userId: number, workspaceId?: number) => {
    try {
      let url = `/api/files?user_id=${userId}`
      if (workspaceId) {
        url += `&workspace_id=${workspaceId}`
      }
      
      const response = await fetch(url)
      if (response.ok) {
        const fileData = await response.json()
        setFiles(fileData)
      }
    } catch (error) {
      console.error('Failed to load files:', error)
    }
  }

  const handleWorkspaceChange = (workspaceId: number) => {
    setSelectedWorkspace(workspaceId)
    if (user) {
      loadFiles(user.id, workspaceId)
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || !selectedWorkspace || !user) return

    setIsUploading(true)
    const uploadPromises = Array.from(files).map(async (file) => {
      const formData = new FormData()
      formData.append('file', file)

      try {
        const response = await fetch(`/api/upload?workspace_id=${selectedWorkspace}`, {
          method: 'POST',
          body: formData,
        })

        if (response.ok) {
          const result = await response.json()
          setMessage({ type: 'success', text: `${file.name} uploaded successfully!` })
          
          // Poll for processing status
          pollFileStatus(result.file_id, file.name)
        } else {
          throw new Error(`Upload failed for ${file.name}`)
        }
      } catch (error) {
        console.error(`Upload error for ${file.name}:`, error)
        setMessage({ type: 'error', text: `Failed to upload ${file.name}` })
      }
    })

    await Promise.all(uploadPromises)
    setIsUploading(false)
    
    // Refresh file list
    loadFiles(user.id, selectedWorkspace)
    
    // Clear the input
    event.target.value = ''
  }

  const pollFileStatus = async (fileId: string, fileName: string) => {
    const poll = async () => {
      try {
        const response = await fetch(`/api/files/${fileId}/status`)
        if (response.ok) {
          const statusData = await response.json()
          
          if (statusData.status === 2) { // Completed
            setUploadProgress(prev => ({ ...prev, [fileId]: 100 }))
            loadFiles(user!.id, selectedWorkspace!)
            return
          } else if (statusData.status === 3) { // Error
            setMessage({ type: 'error', text: `Processing failed for ${fileName}` })
            return
          }
          
          // Still processing, continue polling
          setTimeout(poll, 2000)
        }
      } catch (error) {
        console.error('Status polling error:', error)
      }
    }
    
    poll()
  }

  const getStatusIcon = (status: number) => {
    switch (status) {
      case 1: return <Clock className="text-yellow-400" size={16} />
      case 2: return <CheckCircle className="text-green-400" size={16} />
      case 3: return <AlertCircle className="text-red-400" size={16} />
      default: return <Clock className="text-gray-400" size={16} />
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

  const filteredFiles = files.filter(file => {
    if (searchQuery && !file.name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false
    }
    if (selectedFilter !== 'all') {
      if (selectedFilter === 'processing' && file.status !== 1) return false
      if (selectedFilter === 'processed' && file.status !== 2) return false
      if (selectedFilter === 'error' && file.status !== 3) return false
    }
    return true
  })

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
      
      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">File Management</h1>
            <p className="text-white/60 mt-1">Upload, organize, and manage your documents</p>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* File Upload */}
            <div className="relative">
              <input
                type="file"
                id="fileUpload"
                multiple
                onChange={handleFileUpload}
                className="hidden"
                disabled={!selectedWorkspace || isUploading}
              />
              <motion.label
                htmlFor="fileUpload"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={`bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-6 py-3 rounded-lg font-medium flex items-center space-x-2 shadow-lg cursor-pointer ${
                  !selectedWorkspace || isUploading ? 'opacity-50 cursor-not-allowed' : ''
                }`}
              >
                <Upload size={18} />
                <span>{isUploading ? 'Uploading...' : 'Upload Files'}</span>
              </motion.label>
            </div>
          </div>
        </div>

        {/* Message Display */}
        {message && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`mb-6 p-4 rounded-lg ${
              message.type === 'success' 
                ? 'bg-green-500/20 border border-green-500/30 text-green-400'
                : 'bg-red-500/20 border border-red-500/30 text-red-400'
            }`}
          >
            {message.text}
          </motion.div>
        )}

        {/* Workspace Selection */}
        <div className="mb-6">
          <GlassCard className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <Folder className="text-emerald-400" size={20} />
                <div>
                  <label className="block text-white/80 text-sm font-medium mb-1">
                    Current Workspace
                  </label>
                  <select
                    value={selectedWorkspace || ''}
                    onChange={(e) => handleWorkspaceChange(parseInt(e.target.value))}
                    className="bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="">Select a workspace</option>
                    {workspaces.map((workspace) => (
                      <option key={workspace.id} value={workspace.id}>
                        {workspace.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              
              <div className="flex items-center space-x-2 text-white/60 text-sm">
                <span>{filteredFiles.length} files</span>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Controls */}
        <div className="mb-6">
          <GlassCard className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40" size={16} />
                  <input
                    type="text"
                    placeholder="Search files..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10 pr-4 py-2 w-64 glass-premium rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                {/* Filter */}
                <select
                  value={selectedFilter}
                  onChange={(e) => setSelectedFilter(e.target.value)}
                  className="px-3 py-2 glass-premium rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="all">All Files</option>
                  <option value="processing">Processing</option>
                  <option value="processed">Processed</option>
                  <option value="error">Error</option>
                </select>
              </div>

              {/* View Toggle */}
              <div className="flex bg-white/10 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-2 rounded ${viewMode === 'grid' ? 'bg-emerald-500 text-white' : 'text-white/60 hover:text-white'} transition-colors`}
                >
                  <Grid size={16} />
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={`p-2 rounded ${viewMode === 'list' ? 'bg-emerald-500 text-white' : 'text-white/60 hover:text-white'} transition-colors`}
                >
                  <List size={16} />
                </button>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Files Display */}
        <GlassCard className="p-6">
          {selectedWorkspace ? (
            <>
              {filteredFiles.length > 0 ? (
                <>
                  {viewMode === 'grid' ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {filteredFiles.map((file) => (
                        <FileCard key={file.id} file={file} />
                      ))}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {filteredFiles.map((file) => (
                        <FileRow key={file.id} file={file} />
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-12">
                  <FileText className="mx-auto text-white/40 mb-4" size={48} />
                  <p className="text-white/60 text-lg">No files found</p>
                  <p className="text-white/40 text-sm mt-2">
                    {searchQuery || selectedFilter !== 'all' 
                      ? 'Try adjusting your search or filter criteria'
                      : 'Upload some files to get started'
                    }
                  </p>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <Folder className="mx-auto text-white/40 mb-4" size={48} />
              <p className="text-white/60 text-lg">Select a workspace</p>
              <p className="text-white/40 text-sm mt-2">
                Choose a workspace to view and manage your files
              </p>
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  )
}

// File Card Component
function FileCard({ file }: { file: FileItem }) {
  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase()
    switch (extension) {
      case 'pdf':
        return '📄'
      case 'doc':
      case 'docx':
        return '📝'
      case 'xls':
      case 'xlsx':
        return '📊'
      case 'txt':
        return '📄'
      case 'md':
        return '📝'
      default:
        return '📄'
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

  const getStatusIcon = (status: number) => {
    switch (status) {
      case 1: return <Clock size={16} />
      case 2: return <CheckCircle size={16} />
      case 3: return <AlertCircle size={16} />
      default: return <Clock size={16} />
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
      
      <div className="flex items-center justify-between">
        <div className={`flex items-center space-x-1 text-sm ${getStatusColor(file.status)}`}>
          {getStatusIcon(file.status)}
          <span>{getStatusText(file.status)}</span>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            className="text-white/60 hover:text-white transition-colors p-1 rounded"
            title="View file"
          >
            <Eye size={14} />
          </button>
          <button
            className="text-white/60 hover:text-red-400 transition-colors p-1 rounded"
            title="Delete file"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </motion.div>
  )
}

// File Row Component
function FileRow({ file }: { file: FileItem }) {
  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase()
    switch (extension) {
      case 'pdf':
        return '📄'
      case 'doc':
      case 'docx':
        return '📝'
      case 'xls':
      case 'xlsx':
        return '📊'
      case 'txt':
        return '📄'
      case 'md':
        return '📝'
      default:
        return '📄'
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

  const getStatusIcon = (status: number) => {
    switch (status) {
      case 1: return <Clock size={16} />
      case 2: return <CheckCircle size={16} />
      case 3: return <AlertCircle size={16} />
      default: return <Clock size={16} />
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
      whileHover={{ scale: 1.01 }}
      className="glass-premium p-4 rounded-lg border border-white/10 hover:border-emerald-500/30 transition-all cursor-pointer"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3 flex-1 min-w-0">
          <span className="text-xl">{getFileIcon(file.name)}</span>
          <div className="flex-1 min-w-0">
            <p className="text-white font-medium truncate" title={file.name}>
              {file.name}
            </p>
            <p className="text-white/60 text-sm">
              Created {new Date(file.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className={`flex items-center space-x-1 text-sm ${getStatusColor(file.status)}`}>
            {getStatusIcon(file.status)}
            <span>{getStatusText(file.status)}</span>
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              className="text-white/60 hover:text-white transition-colors p-1 rounded"
              title="View file"
            >
              <Eye size={16} />
            </button>
            <button
              className="text-white/60 hover:text-red-400 transition-colors p-1 rounded"
              title="Delete file"
            >
              <Trash2 size={16} />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  )
}