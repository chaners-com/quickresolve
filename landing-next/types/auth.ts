// Shared authentication types
export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  username: string
  company_name?: string
  team_size?: string
  is_active: boolean
  created_at: string
  updated_at?: string
}

export interface SessionData {
  user: User
  expires: string
  csrfToken: string
  authToken?: string // JWT token for backend authentication
  [key: string]: any
}

export interface Workspace {
  id: number
  name: string
  description?: string
  owner_id: number
  created_at: string
}

export interface FileItem {
  id: string
  name: string
  s3_key: string
  workspace_id: number
  status: number
  created_at: string
}

export interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}