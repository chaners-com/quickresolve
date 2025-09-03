'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  User, 
  Mail, 
  Building, 
  Users, 
  Lock, 
  Save,
  ArrowLeft,
  Eye,
  EyeOff,
  Edit3,
  Shield,
  CheckCircle,
  Settings
} from 'lucide-react'
import { GlassCard } from '../components/GlassCard'
import { GradientOrbs } from '../components/GradientOrbs'

interface User {
  id: number
  email: string
  username?: string
  first_name?: string
  last_name?: string
  company_name?: string
  team_size?: string
  is_active: boolean
  created_at: string
}

export default function ProfilePage() {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [activeTab, setActiveTab] = useState<'profile' | 'password'>('profile')
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  
  // Profile form states
  const [profileForm, setProfileForm] = useState({
    first_name: '',
    last_name: '',
    username: '',
    email: '',
    company_name: '',
    team_size: ''
  })

  // Password form states
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  })

  const router = useRouter()

  useEffect(() => {
    loadUserData()
  }, [])

  const loadUserData = async () => {
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
        setProfileForm({
          first_name: userData.first_name || '',
          last_name: userData.last_name || '',
          username: userData.username || '',
          email: userData.email || '',
          company_name: userData.company_name || '',
          team_size: userData.team_size || ''
        })
      } else {
        localStorage.removeItem('authToken')
        localStorage.removeItem('user')
        router.push('/login')
      }
    } catch (error) {
      console.error('Failed to load user data:', error)
      router.push('/login')
    } finally {
      setIsLoading(false)
    }
  }

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setMessage(null)

    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch('/api/auth/update-profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          first_name: profileForm.first_name,
          last_name: profileForm.last_name,
          email: profileForm.email,
          company_name: profileForm.company_name,
          team_size: profileForm.team_size
        })
      })

      if (response.ok) {
        const updatedUser = await response.json()
        setUser(updatedUser)
        setMessage({ type: 'success', text: 'Profile updated successfully!' })
        
        // Update localStorage
        localStorage.setItem('user', JSON.stringify(updatedUser))
        
        // Clear success message after 3 seconds
        setTimeout(() => {
          setMessage(null)
        }, 3000)
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to update profile' })
      }
    } catch (error) {
      console.error('Error updating profile:', error)
      setMessage({ type: 'error', text: 'Network error. Please try again.' })
    } finally {
      setIsSaving(false)
    }
  }

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setMessage({ type: 'error', text: 'New passwords do not match' })
      return
    }

    if (passwordForm.new_password.length < 8) {
      setMessage({ type: 'error', text: 'Password must be at least 8 characters long' })
      return
    }

    if (!/[A-Z]/.test(passwordForm.new_password)) {
      setMessage({ type: 'error', text: 'Password must contain at least one uppercase letter' })
      return
    }

    if (!/[a-z]/.test(passwordForm.new_password)) {
      setMessage({ type: 'error', text: 'Password must contain at least one lowercase letter' })
      return
    }

    if (!/\d/.test(passwordForm.new_password)) {
      setMessage({ type: 'error', text: 'Password must contain at least one number' })
      return
    }

    setIsSaving(true)
    setMessage(null)

    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch('/api/auth/change-password', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password
        })
      })

      if (response.ok) {
        setMessage({ type: 'success', text: 'Password changed successfully!' })
        setPasswordForm({
          current_password: '',
          new_password: '',
          confirm_password: ''
        })
        
        // Clear success message after 3 seconds
        setTimeout(() => {
          setMessage(null)
        }, 3000)
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to change password' })
      }
    } catch (error) {
      console.error('Error changing password:', error)
      setMessage({ type: 'error', text: 'Network error. Please try again.' })
    } finally {
      setIsSaving(false)
    }
  }

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
    formType: 'profile' | 'password'
  ) => {
    const { name, value } = e.target
    
    if (formType === 'profile') {
      setProfileForm(prev => ({
        ...prev,
        [name]: value
      }))
    } else {
      setPasswordForm(prev => ({
        ...prev,
        [name]: value
      }))
    }
  }

  if (isLoading) {
    return (
      <div className="relative min-h-screen bg-gray-900">
        <GradientOrbs />
        <div className="flex items-center justify-center min-h-screen">
          <div className="flex items-center space-x-3 text-white">
            <div className="w-8 h-8 border-2 border-white/20 border-t-emerald-400 rounded-full animate-spin"></div>
            <span className="text-lg">Loading your profile...</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="relative min-h-screen bg-gray-900">
      <GradientOrbs />
      
      <div className="container mx-auto px-4 sm:px-6 py-6 lg:py-8 max-w-7xl">
        {/* Modern Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-4 mb-6">
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => router.push('/dashboard')}
              className="flex items-center justify-center w-10 h-10 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 hover:border-emerald-500/50 transition-all duration-200 text-white/70 hover:text-white"
            >
              <ArrowLeft size={18} />
            </motion.button>
            <div>
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-white">
                Account Settings
              </h1>
              <p className="text-white/60 text-sm lg:text-base mt-1">
                Manage your profile and security settings
              </p>
            </div>
          </div>

          {/* User Info Banner */}
          <GlassCard className="p-6 border-emerald-500/20">
            <div className="flex flex-col sm:flex-row items-start sm:items-center space-y-4 sm:space-y-0 sm:space-x-6">
              <div className="relative">
                <div className="w-20 h-20 bg-gradient-to-br from-emerald-400 to-teal-500 rounded-2xl flex items-center justify-center shadow-lg">
                  <span className="text-white font-bold text-2xl">
                    {user?.first_name?.[0]}{user?.last_name?.[0]}
                  </span>
                </div>
                <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-green-500 rounded-full border-2 border-gray-900 flex items-center justify-center">
                  <CheckCircle size={12} className="text-white" />
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="text-xl sm:text-2xl font-bold text-white mb-1 truncate">
                  {user?.first_name} {user?.last_name}
                </h2>
                <p className="text-emerald-400 font-medium mb-2 break-all sm:break-normal">
                  {user?.email}
                </p>
                <div className="flex flex-wrap items-center gap-3 text-sm text-white/60">
                  <span className="flex items-center space-x-1">
                    <User size={14} />
                    <span>{user?.username || 'No username'}</span>
                  </span>
                  <span className="flex items-center space-x-1">
                    <Building size={14} />
                    <span>{user?.company_name || 'No company'}</span>
                  </span>
                  <span className="flex items-center space-x-1">
                    <Users size={14} />
                    <span>{user?.team_size || 'Team size not set'}</span>
                  </span>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Message Display */}
        <AnimatePresence>
          {message && (
            <motion.div
              initial={{ opacity: 0, y: -20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className={`mb-6 p-4 rounded-xl border backdrop-blur-sm ${
                message.type === 'success' 
                  ? 'bg-green-500/10 border-green-500/30 text-green-400'
                  : 'bg-red-500/10 border-red-500/30 text-red-400'
              }`}
            >
              <div className="flex items-center space-x-2">
                {message.type === 'success' ? (
                  <CheckCircle size={18} />
                ) : (
                  <Settings size={18} />
                )}
                <span className="font-medium">{message.text}</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8">
          {/* Navigation Tabs */}
          <div className="lg:col-span-3">
            <GlassCard className="p-2">
              <nav className="space-y-1">
                <button
                  onClick={() => setActiveTab('profile')}
                  className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 text-left ${
                    activeTab === 'profile'
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-lg'
                      : 'text-white/70 hover:text-white hover:bg-white/5 hover:border-white/10 border border-transparent'
                  }`}
                >
                  <Edit3 size={18} />
                  <span className="font-medium">Edit Profile</span>
                </button>
                
                <button
                  onClick={() => setActiveTab('password')}
                  className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 text-left ${
                    activeTab === 'password'
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-lg'
                      : 'text-white/70 hover:text-white hover:bg-white/5 hover:border-white/10 border border-transparent'
                  }`}
                >
                  <Shield size={18} />
                  <span className="font-medium">Security</span>
                </button>
              </nav>

              <div className="mt-6 pt-6 border-t border-white/10">
                <div className="px-4">
                  <h3 className="text-white/60 text-sm font-medium mb-3">Account Status</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-white/60">Status</span>
                      <span className="text-green-400 font-medium">Active</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-white/60">Member since</span>
                      <span className="text-white">
                        {new Date(user?.created_at || '').getFullYear()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </GlassCard>
          </div>

          {/* Content Area */}
          <div className="lg:col-span-9">
            <GlassCard className="p-6 lg:p-8">
              <AnimatePresence mode="wait">
                {activeTab === 'profile' && (
                  <motion.div
                    key="profile"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="mb-8">
                      <h2 className="text-2xl font-bold text-white mb-2">Profile Information</h2>
                      <p className="text-white/60">Update your account profile information and preferences.</p>
                    </div>
                    
                    <form onSubmit={handleProfileSubmit} className="space-y-6">
                      {/* Name Fields */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <label className="block text-white/90 text-sm font-semibold mb-3">
                            First Name
                          </label>
                          <div className="relative group">
                            <User className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white/40 group-focus-within:text-emerald-400 transition-colors" size={16} />
                            <input
                              type="text"
                              name="first_name"
                              value={profileForm.first_name}
                              onChange={(e) => handleInputChange(e, 'profile')}
                              className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/20 rounded-xl text-white placeholder-white/50 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all backdrop-blur-sm"
                              placeholder="Enter your first name"
                            />
                          </div>
                        </div>

                        <div>
                          <label className="block text-white/90 text-sm font-semibold mb-3">
                            Last Name
                          </label>
                          <div className="relative group">
                            <User className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white/40 group-focus-within:text-emerald-400 transition-colors" size={16} />
                            <input
                              type="text"
                              name="last_name"
                              value={profileForm.last_name}
                              onChange={(e) => handleInputChange(e, 'profile')}
                              className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/20 rounded-xl text-white placeholder-white/50 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all backdrop-blur-sm"
                              placeholder="Enter your last name"
                            />
                          </div>
                        </div>
                      </div>

                      {/* Username & Email */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <label className="block text-white/90 text-sm font-semibold mb-3">
                            Username
                          </label>
                          <div className="relative group">
                            <User className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white/40 group-focus-within:text-emerald-400 transition-colors" size={16} />
                            <input
                              type="text"
                              name="username"
                              value={profileForm.username}
                              readOnly
                              className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/20 rounded-xl text-white/60 placeholder-white/50 cursor-not-allowed backdrop-blur-sm"
                              placeholder="Username cannot be changed"
                            />
                          </div>
                        </div>

                        <div>
                          <label className="block text-white/90 text-sm font-semibold mb-3">
                            Email Address
                          </label>
                          <div className="relative group">
                            <Mail className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white/40 group-focus-within:text-emerald-400 transition-colors" size={16} />
                            <input
                              type="email"
                              name="email"
                              value={profileForm.email}
                              onChange={(e) => handleInputChange(e, 'profile')}
                              className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/20 rounded-xl text-white placeholder-white/50 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all backdrop-blur-sm"
                              placeholder="Enter your email"
                            />
                          </div>
                        </div>
                      </div>

                      {/* Company & Team Size */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <label className="block text-white/90 text-sm font-semibold mb-3">
                            Company Name
                          </label>
                          <div className="relative group">
                            <Building className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white/40 group-focus-within:text-emerald-400 transition-colors" size={16} />
                            <input
                              type="text"
                              name="company_name"
                              value={profileForm.company_name}
                              onChange={(e) => handleInputChange(e, 'profile')}
                              className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/20 rounded-xl text-white placeholder-white/50 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all backdrop-blur-sm"
                              placeholder="Enter your company name"
                            />
                          </div>
                        </div>

                        <div>
                          <label className="block text-white/90 text-sm font-semibold mb-3">
                            Team Size
                          </label>
                          <div className="relative group">
                            <Users className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white/40 group-focus-within:text-emerald-400 transition-colors" size={16} />
                            <select
                              name="team_size"
                              value={profileForm.team_size}
                              onChange={(e) => handleInputChange(e, 'profile')}
                              className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/20 rounded-xl text-white focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all backdrop-blur-sm appearance-none cursor-pointer"
                            >
                              <option value="" className="bg-gray-800 text-white">Select team size</option>
                              <option value="1-5" className="bg-gray-800 text-white">1-5 people</option>
                              <option value="6-20" className="bg-gray-800 text-white">6-20 people</option>
                              <option value="21-50" className="bg-gray-800 text-white">21-50 people</option>
                              <option value="51-200" className="bg-gray-800 text-white">51-200 people</option>
                              <option value="200+" className="bg-gray-800 text-white">200+ people</option>
                            </select>
                            <div className="absolute inset-y-0 right-0 flex items-center pr-4 pointer-events-none">
                              <svg className="w-4 h-4 text-white/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Save Button */}
                      <div className="flex justify-end pt-6 border-t border-white/10">
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          type="submit"
                          disabled={isSaving}
                          className="px-8 py-3 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-xl font-semibold flex items-center space-x-2 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                        >
                          <Save size={18} />
                          <span>{isSaving ? 'Saving...' : 'Save Changes'}</span>
                        </motion.button>
                      </div>
                    </form>
                  </motion.div>
                )}

                {activeTab === 'password' && (
                  <motion.div
                    key="password"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="mb-8">
                      <h2 className="text-2xl font-bold text-white mb-2">Change Password</h2>
                      <p className="text-white/60">Update your password to keep your account secure.</p>
                    </div>
                    
                    <form onSubmit={handlePasswordSubmit} className="space-y-6 max-w-md">
                      {/* Current Password */}
                      <div>
                        <label className="block text-white/90 text-sm font-semibold mb-3">
                          Current Password
                        </label>
                        <div className="relative group">
                          <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white/40 group-focus-within:text-emerald-400 transition-colors" size={16} />
                          <input
                            type="password"
                            name="current_password"
                            value={passwordForm.current_password}
                            onChange={(e) => handleInputChange(e, 'password')}
                            className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/20 rounded-xl text-white placeholder-white/50 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all backdrop-blur-sm"
                            placeholder="Enter current password"
                            required
                          />
                        </div>
                      </div>

                      {/* New Password */}
                      <div>
                        <label className="block text-white/90 text-sm font-semibold mb-3">
                          New Password
                        </label>
                        <div className="relative group">
                          <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white/40 group-focus-within:text-emerald-400 transition-colors" size={16} />
                          <input
                            type={showPassword ? 'text' : 'password'}
                            name="new_password"
                            value={passwordForm.new_password}
                            onChange={(e) => handleInputChange(e, 'password')}
                            className="w-full pl-12 pr-12 py-3 bg-white/5 border border-white/20 rounded-xl text-white placeholder-white/50 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all backdrop-blur-sm"
                            placeholder="Enter new password"
                            required
                          />
                          <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute right-4 top-1/2 transform -translate-y-1/2 text-white/40 hover:text-emerald-400 transition-colors"
                          >
                            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                          </button>
                        </div>
                        
                        {/* Password Requirements */}
                        <div className="mt-4 p-4 bg-white/5 rounded-lg border border-white/10">
                          <div className="text-xs text-white/60 mb-2 font-medium">Password Requirements:</div>
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className={`flex items-center space-x-2 ${
                              passwordForm.new_password.length >= 8 ? 'text-green-400' : 'text-white/40'
                            }`}>
                              <span className="w-1 h-1 rounded-full bg-current"></span>
                              <span>8+ characters</span>
                            </div>
                            <div className={`flex items-center space-x-2 ${
                              /[A-Z]/.test(passwordForm.new_password) ? 'text-green-400' : 'text-white/40'
                            }`}>
                              <span className="w-1 h-1 rounded-full bg-current"></span>
                              <span>Uppercase</span>
                            </div>
                            <div className={`flex items-center space-x-2 ${
                              /[a-z]/.test(passwordForm.new_password) ? 'text-green-400' : 'text-white/40'
                            }`}>
                              <span className="w-1 h-1 rounded-full bg-current"></span>
                              <span>Lowercase</span>
                            </div>
                            <div className={`flex items-center space-x-2 ${
                              /\d/.test(passwordForm.new_password) ? 'text-green-400' : 'text-white/40'
                            }`}>
                              <span className="w-1 h-1 rounded-full bg-current"></span>
                              <span>Number</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Confirm Password */}
                      <div>
                        <label className="block text-white/90 text-sm font-semibold mb-3">
                          Confirm New Password
                        </label>
                        <div className="relative group">
                          <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white/40 group-focus-within:text-emerald-400 transition-colors" size={16} />
                          <input
                            type={showConfirmPassword ? 'text' : 'password'}
                            name="confirm_password"
                            value={passwordForm.confirm_password}
                            onChange={(e) => handleInputChange(e, 'password')}
                            className="w-full pl-12 pr-12 py-3 bg-white/5 border border-white/20 rounded-xl text-white placeholder-white/50 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all backdrop-blur-sm"
                            placeholder="Confirm new password"
                            required
                          />
                          <button
                            type="button"
                            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                            className="absolute right-4 top-1/2 transform -translate-y-1/2 text-white/40 hover:text-emerald-400 transition-colors"
                          >
                            {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                          </button>
                        </div>
                      </div>

                      {/* Change Password Button */}
                      <div className="pt-6 border-t border-white/10">
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          type="submit"
                          disabled={isSaving}
                          className="px-8 py-3 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-xl font-semibold flex items-center space-x-2 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                        >
                          <Shield size={18} />
                          <span>{isSaving ? 'Updating...' : 'Update Password'}</span>
                        </motion.button>
                      </div>
                    </form>
                  </motion.div>
                )}
              </AnimatePresence>
            </GlassCard>
          </div>
        </div>
      </div>
    </div>
  )
}