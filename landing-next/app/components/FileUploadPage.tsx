'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { 
  Upload, 
  Search, 
  Filter, 
  Grid, 
  List, 
  Folder,
  FileText,
  CheckCircle,
  Clock,
  AlertCircle,
  Eye,
  Trash2
} from 'lucide-react'
import { GlassCard } from '../components/GlassCard'
import { GradientOrbs } from '../components/GradientOrbs'
import { User } from '../../types/auth'

interface Workspace {
  id: number
  name: string
  owner_id: number
}

interface FileItem {
  id: string
  name: string
  s3_key: string
  workspace_id: number
  status: number
  created_at: string
}

interface SearchResult {
  payload: {
    s3_key: string
  }
  score: number
}

export default function FileUploadPage() {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [uploadUsername, setUploadUsername] = useState('')
  const [uploadWorkspace, setUploadWorkspace] = useState('')
  const [searchUsername, setSearchUsername] = useState('')
  const [searchWorkspace, setSearchWorkspace] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [workspaceMessage, setWorkspaceMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [currentWorkspaceId, setCurrentWorkspaceId] = useState<number | null>(null)
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [showSearchSection, setShowSearchSection] = useState(false)
  const [overallStatus, setOverallStatus] = useState('')
  const [failedFiles, setFailedFiles] = useState<string[]>([])
  const [expandedContent, setExpandedContent] = useState<{ [key: string]: string }>({})
  const [userFiles, setUserFiles] = useState<any[]>([])
  const [userWorkspaces, setUserWorkspaces] = useState<any[]>([])
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null)
  const [showAddWorkspacePopup, setShowAddWorkspacePopup] = useState(false)
  const [newWorkspaceName, setNewWorkspaceName] = useState('')
  const [uploadProgress, setUploadProgress] = useState<{[key: string]: number}>({})
  const [currentlyProcessing, setCurrentlyProcessing] = useState<string[]>([])
  const [completedFiles, setCompletedFiles] = useState<string[]>([])
  const [selectedFile, setSelectedFile] = useState<any | null>(null)
  const [showFileViewer, setShowFileViewer] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [fileToDelete, setFileToDelete] = useState<any | null>(null)
  const [expandedWorkspaces, setExpandedWorkspaces] = useState<Set<string>>(new Set())
  
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    checkAuth()
  }, [])

  // Handle highlight parameter from dashboard navigation
  useEffect(() => {
    const highlight = searchParams.get('highlight')
    if (highlight && userFiles.length > 0 && userWorkspaces.length > 0) {
      setTimeout(() => {
        // If it's a file highlight, we need to open its workspace first
        if (highlight.startsWith('file_')) {
          const fileId = highlight.replace('file_', '')
          const file = userFiles.find(f => f.id === fileId)
          
          if (file) {
            // Find which workspace this file belongs to
            const workspace = userWorkspaces.find(w => w.id === file.workspace_id)
            
            if (workspace) {
              // First, expand the workspace
              setExpandedWorkspaces(prev => new Set([...prev, workspace.id.toString()]))
              
              // Then wait for the workspace to expand and highlight the file
              const highlightFile = (attemptCount = 0) => {
                const fileElement = document.getElementById(highlight)
                
                if (fileElement) {
                  fileElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
                  // Add highlight effect to the file
                  fileElement.classList.add('ring-2', 'ring-emerald-500', 'ring-opacity-75', 'bg-emerald-500/10')
                  setTimeout(() => {
                    fileElement.classList.remove('ring-2', 'ring-emerald-500', 'ring-opacity-75', 'bg-emerald-500/10')
                  }, 4000)
                } else if (attemptCount < 5) {
                  // Try again with increasing delays
                  setTimeout(() => highlightFile(attemptCount + 1), (attemptCount + 1) * 300)
                }
              }
              
              // Start the highlighting process
              setTimeout(() => highlightFile(), 800)
            }
          }
        } else {
          // Handle workspace highlight (existing logic)
          const element = document.getElementById(highlight)
          if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' })
            // Add a temporary highlight effect
            element.classList.add('ring-2', 'ring-emerald-500', 'ring-opacity-50')
            setTimeout(() => {
              element.classList.remove('ring-2', 'ring-emerald-500', 'ring-opacity-50')
            }, 3000)
          }
        }
      }, 1500)
    }
  }, [searchParams, userFiles, userWorkspaces, setExpandedWorkspaces])

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
        // Pre-fill username with authenticated user's name
        const username = userData.username || `${userData.first_name}_${userData.last_name}`.toLowerCase()
        setUploadUsername(username)
        setSearchUsername(username)
        
        // Get or create the user in the ingestion service to load their data
        const ingestionUser = await getOrCreateUser(username)
        if (ingestionUser) {
          await loadUserData(ingestionUser.id)
        }
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

  const loadUserData = async (userId: number) => {
    try {
      // Load user's files
      const filesResponse = await fetch(`/api/files?user_id=${userId}`)
      if (filesResponse.ok) {
        const filesData = await filesResponse.json()
        setUserFiles(filesData)
      }

      // Load user's workspaces
      const workspacesResponse = await fetch(`/api/workspaces?owner_id=${userId}`)
      if (workspacesResponse.ok) {
        const workspacesData = await workspacesResponse.json()
        setUserWorkspaces(workspacesData)
      }
    } catch (error) {
      console.error('Failed to load user data:', error)
    }
  }

  const getOrCreateUser = async (username: string, isSearch = false) => {
    const setMsg = isSearch ? setWorkspaceMessage : setMessage
    
    setMsg({ type: 'success', text: `Checking for user '${username}'...` })
    
    try {
      // First, try to find the user
      const existingResponse = await fetch(`/api/users?username=${encodeURIComponent(username)}`)
      if (existingResponse.ok) {
        const existingUsers = await existingResponse.json()
        if (existingUsers && existingUsers.length > 0) {
          setMsg({ type: 'success', text: `Found existing user '${username}'` })
          return existingUsers[0]
        }
      }

      if (isSearch) {
        setMsg({ type: 'error', text: `User '${username}' not found` })
        return null
      }

      // If user doesn't exist, create them (only for upload, not search)
      setMsg({ type: 'success', text: `Creating new user '${username}'...` })
      const createResponse = await fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username })
      })

      if (createResponse.ok) {
        const newUser = await createResponse.json()
        setMsg({ type: 'success', text: `Successfully created user '${username}'` })
        return newUser
      } else {
        throw new Error('Failed to create user')
      }
    } catch (error) {
      console.error('User operation failed:', error)
      setMsg({ type: 'error', text: `Failed to get user '${username}'` })
      return null
    }
  }

  const getOrCreateWorkspace = async (workspaceName: string, userId: number, isSearch = false) => {
    const setMsg = isSearch ? setWorkspaceMessage : setMessage
    
    setMsg({ type: 'success', text: `Looking for workspace '${workspaceName}'...` })
    
    try {
      // First, get all workspaces for this user
      const existingResponse = await fetch(`/api/workspaces?owner_id=${userId}`)
      if (existingResponse.ok) {
        const existingWorkspaces = await existingResponse.json()
        
        // Find workspace by name (case-insensitive)
        const foundWorkspace = existingWorkspaces.find((workspace: any) => 
          workspace.name.toLowerCase() === workspaceName.toLowerCase()
        )
        
        if (foundWorkspace) {
          setMsg({ type: 'success', text: `Found workspace '${workspaceName}' (ID: ${foundWorkspace.id})` })
          return foundWorkspace
        }
      }

      if (isSearch) {
        setMsg({ type: 'error', text: `Workspace '${workspaceName}' not found for this user` })
        return null
      }

      // If workspace doesn't exist, create it (only for upload, not search)
      setMsg({ type: 'success', text: `Creating new workspace '${workspaceName}'...` })
      const createResponse = await fetch('/api/workspaces', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: workspaceName, owner_id: userId })
      })

      if (createResponse.ok) {
        const newWorkspace = await createResponse.json()
        setMsg({ type: 'success', text: `Successfully created workspace '${workspaceName}' (ID: ${newWorkspace.id})` })
        return newWorkspace
      } else {
        throw new Error('Failed to create workspace')
      }
    } catch (error) {
      console.error('Workspace operation failed:', error)
      setMsg({ type: 'error', text: `Failed to get workspace '${workspaceName}'` })
      return null
    }
  }

  const handleFileSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    setSelectedFiles(files)
    if (files && files.length > 0) {
      setMessage({ type: 'success', text: `Selected ${files.length} file${files.length > 1 ? 's' : ''} for upload.` })
    }
  }

  const handleFileUpload = async () => {
    const files = selectedFiles
    if (!files || !uploadUsername.trim() || !uploadWorkspace.trim()) {
      setMessage({ type: 'error', text: 'Please fill in all fields and choose at least one file.' })
      return
    }

    setIsUploading(true)
    setFailedFiles([])
    setUploadProgress({})
    setCurrentlyProcessing([])
    setCompletedFiles([])
    
    try {
      // Get or create user
      const user = await getOrCreateUser(uploadUsername.trim())
      if (!user) {
        setIsUploading(false)
        return
      }
      
      // Get or create workspace
      const workspace = await getOrCreateWorkspace(uploadWorkspace.trim(), user.id)
      if (!workspace) {
        setIsUploading(false)
        return
      }
      
      // Upload files sequentially like the original frontend
      let doneCount = 0
      const totalFiles = files.length
      updateOverallStatus(doneCount, totalFiles, 0) // Initialize overall status
      
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        const fileName = file.name
        
        setMessage({ type: 'success', text: `Uploading file ${i + 1} of ${files.length}: '${fileName}'...` })
        setUploadProgress(prev => ({ ...prev, [fileName]: 50 })) // Show uploading
        
        const formData = new FormData()
        formData.append('file', file)

        try {
          const response = await fetch(`/api/upload?workspace_id=${workspace.id}`, {
            method: 'POST',
            body: formData,
          })

          if (response.ok || response.status === 202) {
            const result = await response.json()
            const location = response.headers.get('Location')
            
            // Upload completed, now processing
            setUploadProgress(prev => ({ ...prev, [fileName]: 100 }))
            setCurrentlyProcessing(prev => [...prev, fileName])
            setMessage({ type: 'success', text: `Processing '${fileName}'...` })
            
            // Poll for processing status if location header is provided (async)
            if (location) {
              pollFileStatus(fileName, location, (finalStatus) => {
                setCurrentlyProcessing(prev => prev.filter(f => f !== fileName))
                
                if (finalStatus.status === 3) {
                  setFailedFiles(prev => {
                    const newFailed = [...prev, fileName]
                    // Update overall status with current counts
                    const currentCompleted = completedFiles.length
                    updateOverallStatus(currentCompleted, totalFiles, newFailed.length)
                    return newFailed
                  })
                } else if (finalStatus.status === 2) {
                  setCompletedFiles(prev => {
                    const newCompleted = [...prev, fileName]
                    // Update overall status with current counts
                    const currentFailed = failedFiles.length
                    updateOverallStatus(newCompleted.length, totalFiles, currentFailed)
                    return newCompleted
                  })
                }
              })
            } else {
              // No polling needed, file is ready
              setCurrentlyProcessing(prev => prev.filter(f => f !== fileName))
              setCompletedFiles(prev => {
                const newCompleted = [...prev, fileName]
                updateOverallStatus(newCompleted.length, totalFiles, failedFiles.length)
                return newCompleted
              })
            }
          } else {
            const error = await response.json()
            throw new Error(error.detail || `Upload failed for ${fileName}`)
          }
        } catch (error) {
          console.error(`Upload error for ${fileName}:`, error)
          setMessage({ type: 'error', text: `Failed to upload ${fileName}: ${error}` })
          setFailedFiles(prev => {
            const newFailed = [...prev, fileName]
            updateOverallStatus(completedFiles.length, totalFiles, newFailed.length)
            return newFailed
          })
          setUploadProgress(prev => ({ ...prev, [fileName]: -1 })) // Error state
        }
      }
      
    } catch (error) {
      console.error('Upload process failed:', error)
      setMessage({ type: 'error', text: 'Upload process failed' })
    } finally {
      setIsUploading(false)
      
      // Show final completion message like original frontend
      setTimeout(() => {
        if (failedFiles.length > 0) {
          setMessage({ 
            type: 'error', 
            text: `Completed with errors. Failed files: ${failedFiles.join(', ')}` 
          })
        } else if (selectedFiles && selectedFiles.length > 0) {
          setMessage({ 
            type: 'success', 
            text: `Successfully uploaded and processed all ${selectedFiles.length} files!` 
          })
        }
      }, 2000) // Show after processing is likely done
      
      setSelectedFiles(null)
      // Clear the file input
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
      if (fileInput) fileInput.value = ''
      // Refresh user data to show new files using ingestion user ID
      if (user) {
        const username = user.username || `${user.first_name}_${user.last_name}`.toLowerCase()
        const ingestionUser = await getOrCreateUser(username)
        if (ingestionUser) {
          await loadUserData(ingestionUser.id)
        }
      }
    }
  }
  
  const pollFileStatus = (fileName: string, statusUrl: string, callback: (status: any) => void) => {
    setTimeout(() => {
      fetch(statusUrl)
        .then(response => {
          if (!response.ok) {
            throw new Error(`Failed to fetch status for '${fileName}'`)
          }
          return response.json()
        })
        .then(data => {
          setMessage({ type: 'success', text: `${fileName}: ${getStatusText(data.status)}` })

          if (data.status === 3) {
            setMessage({ type: 'error', text: `${fileName}: Error` })
            callback(data)
            return
          }

          if (data.status === 2) {
            callback(data)
            return
          }

          // Keep polling if still processing
          pollFileStatus(fileName, statusUrl, callback)
        })
        .catch(error => {
          console.error(error)
          setMessage({ type: 'error', text: `Failed to fetch status for '${fileName}'` })
        })
    }, 1000)
  }

  const updateOverallStatus = (done: number, total: number, failed: number) => {
    const finished = done + failed === total
    if (failed > 0) {
      setOverallStatus(`Overall: Done ${finished ? done : done} of ${total} / Errors ${failed}`)
      return
    }
    if (finished) {
      setOverallStatus(`Overall: Done ${done} of ${total}`)
    } else {
      const processing = total - done - failed
      setOverallStatus(`Overall: Processing ${processing} / Done ${done} of ${total}`)
    }
  }

  const getStatusText = (status: number) => {
    switch (status) {
      case 1: return 'Processing'
      case 2: return 'Done'
      case 3: return 'Error'
      default: return 'Unknown'
    }
  }

  const selectWorkspace = async () => {
    if (!searchUsername.trim() || !searchWorkspace.trim()) {
      setWorkspaceMessage({ type: 'error', text: 'Please enter both username and workspace name.' })
      return
    }

    // Find the user (do not create)
    const user = await findUser(searchUsername.trim())
    if (!user) return

    // Find the workspace for this user (do not create)
    const workspace = await findWorkspace(searchWorkspace.trim(), user.id)
    if (!workspace) return

    // Set the current workspace for searching
    setCurrentWorkspaceId(workspace.id)
    setWorkspaceMessage({ type: 'success', text: `Selected workspace: ${searchWorkspace.trim()} (ID: ${workspace.id})` })
    
    // Show the search section
    setShowSearchSection(true)
    setSearchResults([])
  }

  const performSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      return
    }

    if (!currentWorkspaceId) {
      setWorkspaceMessage({ type: 'error', text: 'Please select a workspace first.' })
      return
    }

    try {
      const response = await fetch(`/api/search?query=${encodeURIComponent(searchQuery.trim())}&workspace_id=${currentWorkspaceId}`)
      
      if (response.ok) {
        const results = await response.json()
        setSearchResults(results || [])
      } else {
        setWorkspaceMessage({ type: 'error', text: 'Search failed' })
        setSearchResults([])
      }
    } catch (error) {
      console.error('Search failed:', error)
      setWorkspaceMessage({ type: 'error', text: 'Search failed' })
      setSearchResults([])
    }
  }

  const toggleContent = async (s3Key: string) => {
    if (expandedContent[s3Key]) {
      // Hide content
      const newExpanded = { ...expandedContent }
      delete newExpanded[s3Key]
      setExpandedContent(newExpanded)
      return
    }

    // Fetch and show content
    try {
      const response = await fetch(`/api/file-content?s3_key=${encodeURIComponent(s3Key)}`)
      if (response.ok) {
        const data = await response.json()
        setExpandedContent({ ...expandedContent, [s3Key]: data.content })
      } else {
        setWorkspaceMessage({ type: 'error', text: 'Failed to fetch file content' })
      }
    } catch (error) {
      console.error('Failed to fetch file content:', error)
      setWorkspaceMessage({ type: 'error', text: 'Failed to fetch file content' })
    }
  }

  // Function to find a user by name (for search) - does NOT create
  const findUser = async (username: string) => {
    setWorkspaceMessage({ type: 'success', text: `Looking for user '${username}'...` })
    
    try {
      const response = await fetch(`/api/users?username=${encodeURIComponent(username)}`)
      if (response.ok) {
        const existingUsers = await response.json()
        if (existingUsers && existingUsers.length > 0) {
          setWorkspaceMessage({ type: 'success', text: `Found user '${username}'` })
          return existingUsers[0]
        }
      }
      
      setWorkspaceMessage({ type: 'error', text: `User '${username}' not found` })
      return null
    } catch (error) {
      console.error('Failed to find user:', error)
      setWorkspaceMessage({ type: 'error', text: `Failed to find user '${username}'` })
      return null
    }
  }

  // Function to find a workspace by name and user (for search) - does NOT create
  const findWorkspace = async (workspaceName: string, userId: number) => {
    setWorkspaceMessage({ type: 'success', text: `Looking for workspace '${workspaceName}'...` })
    
    try {
      // First, get all workspaces for this user
      const response = await fetch(`/api/workspaces?owner_id=${userId}`)
      if (response.ok) {
        const existingWorkspaces = await response.json()
        
        // Find workspace by name (case-insensitive)
        const foundWorkspace = existingWorkspaces.find((workspace: any) => 
          workspace.name.toLowerCase() === workspaceName.toLowerCase()
        )
        
        if (foundWorkspace) {
          setWorkspaceMessage({ type: 'success', text: `Found workspace '${workspaceName}' (ID: ${foundWorkspace.id})` })
          return foundWorkspace
        }
      }
      
      setWorkspaceMessage({ type: 'error', text: `Workspace '${workspaceName}' not found for this user` })
      return null
    } catch (error) {
      console.error('Failed to find workspace:', error)
      setWorkspaceMessage({ type: 'error', text: `Failed to find workspace '${workspaceName}'` })
      return null
    }
  }

  const createNewWorkspace = async () => {
    if (!newWorkspaceName.trim() || !user) {
      setMessage({ type: 'error', text: 'Please enter a workspace name.' })
      return
    }

    try {
      // First, get or create the user in the ingestion service
      const username = user.username || `${user.first_name}_${user.last_name}`.toLowerCase()
      const ingestionUser = await getOrCreateUser(username)
      if (!ingestionUser) {
        return
      }

      const response = await fetch('/api/workspaces', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newWorkspaceName.trim(), owner_id: ingestionUser.id })
      })

      if (response.ok) {
        const newWorkspace = await response.json()
        setMessage({ type: 'success', text: `Successfully created workspace '${newWorkspaceName.trim()}'` })
        
        // Refresh workspaces using the ingestion user ID
        await loadUserData(ingestionUser.id)
        
        // Set the new workspace as selected after a brief delay to ensure state update
        setTimeout(() => {
          setUploadWorkspace(newWorkspaceName.trim())
        }, 100)
        
        // Close popup
        setShowAddWorkspacePopup(false)
        setNewWorkspaceName('')
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to create workspace' })
      }
    } catch (error) {
      console.error('Failed to create workspace:', error)
      setMessage({ type: 'error', text: 'Failed to create workspace' })
    }
  }

  const loadWorkspaceFiles = async (workspaceName: string) => {
    if (!workspaceName || !user) return

    try {
      const workspace = userWorkspaces.find(w => w.name === workspaceName)
      if (!workspace) return

      const filesResponse = await fetch(`/api/files?workspace_id=${workspace.id}`)
      if (filesResponse.ok) {
        const workspaceFiles = await filesResponse.json()
        // Filter user files to show files from the selected workspace
        setUserFiles(workspaceFiles)
        setMessage({ type: 'success', text: `Loaded ${workspaceFiles.length} files from workspace '${workspaceName}'` })
      }
    } catch (error) {
      console.error('Failed to load workspace files:', error)
      setMessage({ type: 'error', text: 'Failed to load workspace files' })
    }
  }

  const handleDeleteFile = (file: any) => {
    setFileToDelete(file)
    setShowDeleteConfirm(true)
  }

  const confirmDeleteFile = async () => {
    if (!fileToDelete) return

    try {
      const response = await fetch(`/api/files/${fileToDelete.id}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        // Refresh file list
        if (user) {
          const username = user.username || `${user.first_name}_${user.last_name}`.toLowerCase()
          const ingestionUser = await getOrCreateUser(username)
          if (ingestionUser) {
            await loadUserData(ingestionUser.id)
          }
        }
        setMessage({ type: 'success', text: 'File deleted successfully' })
      } else {
        setMessage({ type: 'error', text: 'Failed to delete file' })
      }
    } catch (error) {
      console.error('Failed to delete file:', error)
      setMessage({ type: 'error', text: 'Failed to delete file' })
    } finally {
      setShowDeleteConfirm(false)
      setFileToDelete(null)
    }
  }

  const handleViewFile = (file: any) => {
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
    <div className="relative min-h-full bg-gray-900">
      <GradientOrbs />
      
      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-4">QuickResolve - File Management & AI Chat</h1>
          <nav className="flex justify-center space-x-8">
            <a href="#upload" className="text-emerald-400 font-medium">File Upload</a>
            <a href="#search" className="text-white/60 hover:text-white transition-colors">Search</a>
          </nav>
        </div>

        {/* Upload Section */}
        <div id="upload" className="mb-12">
          <GlassCard className="p-8">
            <h2 className="text-2xl font-semibold text-white mb-6">Upload Files</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <div>
                <label className="block text-white/80 text-sm font-medium mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={uploadUsername}
                  readOnly
                  placeholder="Enter your username"
                  className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-3 text-white/80 placeholder-white/60 cursor-not-allowed"
                />
              </div>
              
              <div>
                <label className="block text-white/80 text-sm font-medium mb-2">
                  Workspace
                </label>
                <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-2">
                  <select
                    value={uploadWorkspace}
                    onChange={(e) => {
                      setUploadWorkspace(e.target.value)
                      loadWorkspaceFiles(e.target.value)
                    }}
                    className="flex-1 bg-white/10 border border-white/20 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="">Select workspace...</option>
                    {userWorkspaces.map((workspace) => (
                      <option key={workspace.id} value={workspace.name}>
                        {workspace.name}
                      </option>
                    ))}
                  </select>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setShowAddWorkspacePopup(true)}
                    className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-4 py-3 rounded-lg font-medium whitespace-nowrap text-center sm:text-left"
                  >
                    <span className="sm:hidden">Add New Workspace</span>
                    <span className="hidden sm:inline">+ Add</span>
                  </motion.button>
                </div>
              </div>
              
              <div>
                <label className="block text-white/80 text-sm font-medium mb-2">
                  Choose Files
                </label>
                <input
                  type="file"
                  multiple
                  onChange={handleFileSelection}
                  disabled={isUploading}
                  className="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-3 text-white file:bg-emerald-500 file:text-white file:border-0 file:rounded file:px-3 file:py-1 file:mr-3 hover:file:bg-emerald-600 disabled:opacity-50"
                />
              </div>
            </div>

            {/* Upload Button */}
            <div className="mb-6">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleFileUpload}
                disabled={!selectedFiles || !uploadUsername.trim() || !uploadWorkspace.trim() || isUploading}
                className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-6 py-3 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
              >
                <Upload size={20} />
                <span>
                  {isUploading ? 'Uploading...' : selectedFiles ? `Upload ${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''}` : 'Upload Files'}
                </span>
              </motion.button>
            </div>

            {/* Progress Section */}
            {isUploading && selectedFiles && (
              <div className="mb-6">
                <div className="bg-white/5 border border-white/10 rounded-lg p-4">
                  <h3 className="text-white font-medium mb-3">Upload Progress</h3>
                  <div className="space-y-3">
                    {Array.from(selectedFiles).map((file, index) => (
                      <FileProgressBar
                        key={`${file.name}-${index}`}
                        fileName={file.name}
                        progress={uploadProgress[file.name] || 0}
                        isProcessing={currentlyProcessing.includes(file.name)}
                        isCompleted={completedFiles.includes(file.name)}
                        isFailed={failedFiles.includes(file.name)}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Messages */}
            {/* {message && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className={`mb-4 p-4 rounded-lg ${
                  message.type === 'success' 
                    ? 'bg-green-500/20 border border-green-500/30 text-green-400'
                    : 'bg-red-500/20 border border-red-500/30 text-red-400'
                }`}
              >
                {message.text}
              </motion.div>
            )} */}

            {overallStatus && (
              <div className="text-white/80 text-sm font-medium p-3 bg-white/5 rounded-lg">
                {overallStatus}
              </div>
            )}
          </GlassCard>
        </div>

        {/* Search Section */}
        <div id="search">
          <GlassCard className="p-8">
            <h2 className="text-2xl font-semibold text-white mb-6">Search Files</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <div>
                <label className="block text-white/80 text-sm font-medium mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={searchUsername}
                  readOnly
                  placeholder="Enter username to search"
                  className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-3 text-white/80 placeholder-white/60 cursor-not-allowed"
                />
              </div>
              
              <div>
                <label className="block text-white/80 text-sm font-medium mb-2">
                  Workspace
                </label>
                <select
                  value={searchWorkspace}
                  onChange={(e) => {
                    setSearchWorkspace(e.target.value)
                    loadWorkspaceFiles(e.target.value)
                  }}
                  className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="">Select workspace to search...</option>
                  {userWorkspaces.map((workspace) => (
                    <option key={workspace.id} value={workspace.name}>
                      {workspace.name}
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="flex items-end">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={selectWorkspace}
                  className="w-full bg-gradient-to-r from-blue-500 to-purple-500 text-white px-6 py-3 rounded-lg font-medium"
                >
                  Select Workspace
                </motion.button>
              </div>
            </div>

            {/* Workspace Message */}
            {workspaceMessage && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className={`mb-6 p-4 rounded-lg ${
                  workspaceMessage.type === 'success' 
                    ? 'bg-green-500/20 border border-green-500/30 text-green-400'
                    : 'bg-red-500/20 border border-red-500/30 text-red-400'
                }`}
              >
                {workspaceMessage.text}
              </motion.div>
            )}

            {/* Search Input */}
            {showSearchSection && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                <div className="flex gap-4">
                  <div className="flex-1">
                    <label className="block text-white/80 text-sm font-medium mb-2">
                      Search Query
                    </label>
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Enter your search term"
                      className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-3 text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                  <div className="flex items-end">
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={performSearch}
                      className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-8 py-3 rounded-lg font-medium"
                    >
                      <Search size={20} />
                    </motion.button>
                  </div>
                </div>

                {/* Search Results */}
                <div>
                  <h3 className="text-white text-lg font-semibold mb-4">Results:</h3>
                  {searchResults.length > 0 ? (
                    <div className="space-y-4">
                      {searchResults.map((hit, index) => (
                        <motion.div
                          key={index}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: index * 0.1 }}
                          className="bg-white/5 border border-white/10 rounded-lg p-4"
                        >
                          <div className="flex items-center justify-between mb-3">
                            <div>
                              <strong className="text-white">File:</strong> 
                              <span className="text-white/80 ml-2">{hit.payload.s3_key}</span>
                            </div>
                            <div className="flex items-center space-x-4">
                              <span className="text-emerald-400 text-sm">
                                Score: {hit.score.toFixed(4)}
                              </span>
                              <button
                                onClick={() => toggleContent(hit.payload.s3_key)}
                                className="bg-emerald-500 hover:bg-emerald-600 text-white px-3 py-1 rounded text-sm transition-colors"
                              >
                                {expandedContent[hit.payload.s3_key] ? 'Hide Content' : 'Show Content'}
                              </button>
                            </div>
                          </div>
                          {expandedContent[hit.payload.s3_key] && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              className="mt-3 p-4 bg-white/5 rounded border-l-4 border-emerald-500"
                            >
                              <pre className="whitespace-pre-wrap text-white/90 text-sm">
                                {expandedContent[hit.payload.s3_key]}
                              </pre>
                            </motion.div>
                          )}
                        </motion.div>
                      ))}
                    </div>
                  ) : searchQuery ? (
                    <p className="text-white/60">No results found.</p>
                  ) : (
                    <p className="text-white/60">Enter a search query to see results.</p>
                  )}
                </div>
              </motion.div>
            )}
          </GlassCard>
        </div>

        {/* Workspace Repository Section */}
        {user && (
          <div className="mt-12">
            <GlassCard className="p-8">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-semibold text-white flex items-center space-x-2">
                  <Folder className="text-emerald-400" size={28} />
                  <span>Workspace Repository</span>
                </h2>
                <div className="text-white/60 text-sm">
                  {userWorkspaces.length} workspace{userWorkspaces.length !== 1 ? 's' : ''} • {userFiles.length} total files
                </div>
              </div>

              {userWorkspaces.length > 0 ? (
                <div className="space-y-6">
                  <WorkspaceRepository
                    workspaces={userWorkspaces.map(workspace => ({
                      ...workspace,
                      files: userFiles.filter(file => file.workspace_id === workspace.id)
                    }))}
                    onDeleteFile={(file, workspaceId) => handleDeleteFile(file)}
                    onViewFile={(file) => handleViewFile(file)}
                    expandedWorkspaces={expandedWorkspaces}
                    setExpandedWorkspaces={setExpandedWorkspaces}
                  />
                </div>
              ) : (
                <div className="text-center py-12">
                  <Folder className="mx-auto text-white/40 mb-4" size={48} />
                  <p className="text-white/60 text-lg">No workspaces yet</p>
                  <p className="text-white/40 text-sm mt-2">
                    Create your first workspace using the form above
                  </p>
                </div>
              )}
            </GlassCard>
          </div>
        )}

        {/* Add Workspace Popup */}
        {showAddWorkspacePopup && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-gray-800 rounded-lg max-w-md w-full"
            >
              <div className="flex items-center justify-between p-6 border-b border-white/10">
                <h3 className="text-white font-semibold text-lg">Add New Workspace</h3>
                <button
                  onClick={() => {
                    setShowAddWorkspacePopup(false)
                    setNewWorkspaceName('')
                  }}
                  className="text-white/60 hover:text-white text-xl leading-none"
                >
                  ×
                </button>
              </div>
              
              <div className="p-6">
                <div className="mb-4">
                  <label className="block text-white/80 text-sm font-medium mb-2">
                    Workspace Name
                  </label>
                  <input
                    type="text"
                    value={newWorkspaceName}
                    onChange={(e) => setNewWorkspaceName(e.target.value)}
                    placeholder="Enter workspace name"
                    className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-3 text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        createNewWorkspace()
                      }
                    }}
                  />
                </div>
                
                <div className="flex justify-end space-x-3">
                  <button
                    onClick={() => {
                      setShowAddWorkspacePopup(false)
                      setNewWorkspaceName('')
                    }}
                    className="px-4 py-2 text-white/60 hover:text-white border border-white/20 rounded-lg hover:border-white/40 transition-colors"
                  >
                    Cancel
                  </button>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={createNewWorkspace}
                    disabled={!newWorkspaceName.trim()}
                    className="px-6 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Create Workspace
                  </motion.button>
                </div>
              </div>
            </motion.div>
          </div>
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

        {/* Delete File Confirmation */}
        {showDeleteConfirm && fileToDelete && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-white/10 backdrop-blur-lg rounded-xl border border-white/20 max-w-md w-full"
            >
              <div className="flex items-center justify-between p-6 border-b border-white/10">
                <h3 className="text-white font-semibold text-lg flex items-center space-x-2">
                  <Trash2 size={20} className="text-red-400" />
                  <span>Delete File</span>
                </h3>
              </div>
              
              <div className="p-6">
                <p className="text-white/80 mb-4">
                  Are you sure you want to delete this file?
                </p>
                <div className="bg-white/5 border border-white/10 rounded-lg p-3 mb-6">
                  <p className="text-white font-medium">{fileToDelete.name}</p>
                  <p className="text-white/60 text-sm">
                    {new Date(fileToDelete.created_at).toLocaleDateString()}
                  </p>
                </div>
                <p className="text-red-400/80 text-sm mb-6">
                  This action cannot be undone. The file will be permanently removed from your workspace.
                </p>
                
                <div className="flex justify-end space-x-3">
                  <button
                    onClick={() => {
                      setShowDeleteConfirm(false)
                      setFileToDelete(null)
                    }}
                    className="px-4 py-2 text-white/60 hover:text-white border border-white/20 rounded-lg hover:border-white/40 transition-colors"
                  >
                    Cancel
                  </button>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={confirmDeleteFile}
                    className="px-6 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg font-medium"
                  >
                    Delete File
                  </motion.button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  )
}

// User File Card Component
function UserFileCard({ file }: { file: any }) {
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

  const getStatusIcon = (status: number) => {
    switch (status) {
      case 1: return <Clock size={16} />
      case 2: return <CheckCircle size={16} />
      case 3: return <AlertCircle size={16} />
      default: return <Clock size={16} />
    }
  }

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="bg-white/5 border border-white/10 rounded-lg p-4 hover:border-emerald-500/30 transition-all cursor-pointer"
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
      
      <div className="flex items-center space-x-2 text-sm">
        <div className={`flex items-center space-x-1 ${getStatusColor(file.status)}`}>
          {getStatusIcon(file.status)}
          <span>{getStatusText(file.status)}</span>
        </div>
      </div>
    </motion.div>
  )
}

// File Progress Bar Component
interface FileProgressBarProps {
  fileName: string
  progress: number
  isProcessing: boolean
  isCompleted: boolean
  isFailed: boolean
}

function FileProgressBar({ fileName, progress, isProcessing, isCompleted, isFailed }: FileProgressBarProps) {
  const getProgressColor = () => {
    if (isFailed) return 'bg-red-500'
    if (isCompleted) return 'bg-green-500'
    if (isProcessing) return 'bg-blue-500'
    return 'bg-emerald-500'
  }

  const getStatusText = () => {
    if (isFailed) return 'Failed'
    if (isCompleted) return 'Completed'
    if (isProcessing) return 'Processing...'
    if (progress === 100) return 'Uploaded'
    if (progress > 0) return 'Uploading...'
    return 'Waiting...'
  }

  const getStatusIcon = () => {
    if (isFailed) return <AlertCircle className="text-red-400" size={16} />
    if (isCompleted) return <CheckCircle className="text-green-400" size={16} />
    if (isProcessing) return <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
    return <Clock className="text-white/60" size={16} />
  }

  const displayProgress = isFailed ? 0 : isCompleted ? 100 : progress

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {getStatusIcon()}
          <span className="text-white text-sm truncate max-w-xs" title={fileName}>
            {fileName}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-white/60 text-xs">
            {getStatusText()}
          </span>
          {!isFailed && (
            <span className="text-white/60 text-xs">
              {displayProgress}%
            </span>
          )}
        </div>
      </div>
      
      <div className="w-full bg-white/10 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all duration-300 ${getProgressColor()}`}
          style={{ width: `${displayProgress}%` }}
        />
      </div>
    </div>
  )
}

// Workspace Repository Component
interface WorkspaceRepositoryProps {
  workspaces: Array<{
    id: string
    name: string
    files?: Array<{
      id: string
      name: string
      size?: number
      created_at: string
      status: number
    }>
  }>
  onDeleteFile: (file: any, workspaceId: string) => void
  onViewFile: (file: any) => void
  expandedWorkspaces: Set<string>
  setExpandedWorkspaces: (workspaces: Set<string>) => void
}

function WorkspaceRepository({ workspaces, onDeleteFile, onViewFile, expandedWorkspaces, setExpandedWorkspaces }: WorkspaceRepositoryProps) {

  const toggleWorkspace = (workspaceId: string) => {
    const newExpanded = new Set(expandedWorkspaces)
    if (newExpanded.has(workspaceId)) {
      newExpanded.delete(workspaceId)
    } else {
      newExpanded.add(workspaceId)
    }
    setExpandedWorkspaces(newExpanded)
  }

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
      default: return '📄'
    }
  }

  if (workspaces.length === 0) {
    return (
      <div className="text-center text-white/60 py-8">
        <p>No workspaces found. Create a workspace to get started.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {workspaces.map((workspace) => (
        <div 
          key={workspace.id} 
          id={`workspace_${workspace.id}`}
          className="bg-white/5 rounded-lg border border-white/10 overflow-hidden"
        >
          <button
            onClick={() => toggleWorkspace(workspace.id)}
            className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-white/5 transition-colors"
          >
            <div className="flex items-center space-x-3">
              <span className="text-2xl">📁</span>
              <div>
                <h3 className="text-white font-medium">{workspace.name}</h3>
                <p className="text-white/60 text-sm">{workspace.files?.length || 0} files</p>
              </div>
            </div>
            <motion.div
              animate={{ rotate: expandedWorkspaces.has(workspace.id) ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <span className="text-white/60">▼</span>
            </motion.div>
          </button>

          {expandedWorkspaces.has(workspace.id) && workspace.files && workspace.files.length > 0 && (
            <div className="px-4 pb-4 space-y-2">
              {workspace.files.map((file, index) => (
                <div 
                  key={file.id || index}
                  id={`file_${file.id}`}
                  className="flex items-center justify-between bg-white/5 rounded-lg p-3 border border-white/10"
                >
                  <div className="flex items-center space-x-3 flex-1 min-w-0">
                    <span className="text-xl">{getFileIcon(file.name)}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-white text-sm font-medium truncate">{file.name}</p>
                      <p className="text-white/60 text-xs">
                        {file.size ? `${(file.size / 1024).toFixed(1)} KB` : 'Unknown size'} • {new Date(file.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => onViewFile(file)}
                      className="p-2 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/20 rounded-lg transition-colors"
                      title="View file"
                    >
                      👁️
                    </button>
                    <button
                      onClick={() => onDeleteFile(file, workspace.id)}
                      className="p-2 text-red-400 hover:text-red-300 hover:bg-red-500/20 rounded-lg transition-colors"
                      title="Delete file"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {expandedWorkspaces.has(workspace.id) && (!workspace.files || workspace.files.length === 0) && (
            <div className="px-4 pb-4 text-center text-white/60 py-4">
              <p>No files in this workspace</p>
            </div>
          )}
        </div>
      ))}
    </div>
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