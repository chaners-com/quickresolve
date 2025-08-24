'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { 
  User, 
  Mail, 
  Building, 
  Users, 
  Lock, 
  Save,
  ArrowLeft,
  Eye,
  EyeOff
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
        body: JSON.stringify(profileForm)
      })

      if (response.ok) {
        const updatedUser = await response.json()
        setUser(updatedUser)
        setMessage({ type: 'success', text: 'Profile updated successfully!' })
        
        // Update localStorage
        localStorage.setItem('user', JSON.stringify(updatedUser))
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
      
      <div className="container mx-auto px-6 py-8 max-w-4xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => router.push('/dashboard')}
              className="text-white/60 hover:text-white transition-colors"
            >
              <ArrowLeft size={24} />
            </button>
            <h1 className="text-3xl font-bold text-white">Profile Settings</h1>
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

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar */}
          <div className="lg:col-span-1">
            <GlassCard className="p-6">
              <div className="flex items-center space-x-3 mb-6">
                <div className="w-16 h-16 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full flex items-center justify-center">
                  <span className="text-white font-semibold text-xl">
                    {user?.first_name?.[0]}{user?.last_name?.[0]}
                  </span>
                </div>
                <div>
                  <h3 className="text-white font-semibold">
                    {user?.first_name} {user?.last_name}
                  </h3>
                  <p className="text-white/60 text-sm">{user?.email}</p>
                </div>
              </div>

              <nav className="space-y-2">
                <button
                  onClick={() => setActiveTab('profile')}
                  className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
                    activeTab === 'profile'
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'text-white/70 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <User size={18} />
                  <span>Profile Information</span>
                </button>
                
                <button
                  onClick={() => setActiveTab('password')}
                  className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
                    activeTab === 'password'
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'text-white/70 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Lock size={18} />
                  <span>Change Password</span>
                </button>
              </nav>

              <div className="mt-6 pt-6 border-t border-white/10">
                <div className="text-sm text-white/60">
                  <p className="mb-2">Member since</p>
                  <p className="text-white">
                    {new Date(user?.created_at || '').toLocaleDateString()}
                  </p>
                </div>
              </div>
            </GlassCard>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            <GlassCard className="p-6">
              {activeTab === 'profile' && (
                <div>
                  <h2 className="text-xl font-semibold text-white mb-6">Profile Information</h2>
                  
                  <form onSubmit={handleProfileSubmit} className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-white/80 text-sm font-medium mb-2">
                          First Name
                        </label>
                        <div className="relative">
                          <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40" size={18} />
                          <input
                            type="text"
                            name="first_name"
                            value={profileForm.first_name}
                            onChange={(e) => handleInputChange(e, 'profile')}
                            className="pl-10 w-full px-4 py-3 glass-premium rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                            placeholder="Enter your first name"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-white/80 text-sm font-medium mb-2">
                          Last Name
                        </label>
                        <div className="relative">
                          <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40" size={18} />
                          <input
                            type="text"
                            name="last_name"
                            value={profileForm.last_name}
                            onChange={(e) => handleInputChange(e, 'profile')}
                            className="pl-10 w-full px-4 py-3 glass-premium rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                            placeholder="Enter your last name"
                          />
                        </div>
                      </div>
                    </div>

                    <div>
                      <label className="block text-white/80 text-sm font-medium mb-2">
                        Username
                      </label>
                      <div className="relative">
                        <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40" size={18} />
                        <input
                          type="text"
                          name="username"
                          value={profileForm.username}
                          onChange={(e) => handleInputChange(e, 'profile')}
                          className="pl-10 w-full px-4 py-3 glass-premium rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                          placeholder="Enter your username"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-white/80 text-sm font-medium mb-2">
                        Email
                      </label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40" size={18} />
                        <input
                          type="email"
                          name="email"
                          value={profileForm.email}
                          onChange={(e) => handleInputChange(e, 'profile')}
                          className="pl-10 w-full px-4 py-3 glass-premium rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                          placeholder="Enter your email"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-white/80 text-sm font-medium mb-2">
                        Company Name
                      </label>
                      <div className="relative">
                        <Building className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40" size={18} />
                        <input
                          type="text"
                          name="company_name"
                          value={profileForm.company_name}
                          onChange={(e) => handleInputChange(e, 'profile')}
                          className="pl-10 w-full px-4 py-3 glass-premium rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                          placeholder="Enter your company name"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-white/80 text-sm font-medium mb-2">
                        Team Size
                      </label>
                      <div className="relative">
                        <Users className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40" size={18} />
                        <select
                          name="team_size"
                          value={profileForm.team_size}
                          onChange={(e) => handleInputChange(e, 'profile')}
                          className="pl-10 w-full px-4 py-3 glass-premium rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        >
                          <option value="">Select team size</option>
                          <option value="1-5">1-5 people</option>
                          <option value="6-20">6-20 people</option>
                          <option value="21-50">21-50 people</option>
                          <option value="51-200">51-200 people</option>
                          <option value="200+">200+ people</option>
                        </select>
                      </div>
                    </div>

                    <div className="flex justify-end">
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        type="submit"
                        disabled={isSaving}
                        className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-6 py-3 rounded-lg font-medium flex items-center space-x-2 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Save size={18} />
                        <span>{isSaving ? 'Saving...' : 'Save Changes'}</span>
                      </motion.button>
                    </div>
                  </form>
                </div>
              )}

              {activeTab === 'password' && (
                <div>
                  <h2 className="text-xl font-semibold text-white mb-6">Change Password</h2>
                  
                  <form onSubmit={handlePasswordSubmit} className="space-y-6 max-w-md">
                    <div>
                      <label className="block text-white/80 text-sm font-medium mb-2">
                        Current Password
                      </label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40" size={18} />
                        <input
                          type="password"
                          name="current_password"
                          value={passwordForm.current_password}
                          onChange={(e) => handleInputChange(e, 'password')}
                          className="pl-10 w-full px-4 py-3 glass-premium rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                          placeholder="Enter current password"
                          required
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-white/80 text-sm font-medium mb-2">
                        New Password
                      </label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40" size={18} />
                        <input
                          type={showPassword ? 'text' : 'password'}
                          name="new_password"
                          value={passwordForm.new_password}
                          onChange={(e) => handleInputChange(e, 'password')}
                          className="pl-10 pr-10 w-full px-4 py-3 glass-premium rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                          placeholder="Enter new password"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/40 hover:text-white"
                        >
                          {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                        </button>
                      </div>
                    </div>

                    <div>
                      <label className="block text-white/80 text-sm font-medium mb-2">
                        Confirm New Password
                      </label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40" size={18} />
                        <input
                          type={showConfirmPassword ? 'text' : 'password'}
                          name="confirm_password"
                          value={passwordForm.confirm_password}
                          onChange={(e) => handleInputChange(e, 'password')}
                          className="pl-10 pr-10 w-full px-4 py-3 glass-premium rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                          placeholder="Confirm new password"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/40 hover:text-white"
                        >
                          {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                        </button>
                      </div>
                    </div>

                    <div className="pt-4">
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        type="submit"
                        disabled={isSaving}
                        className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-6 py-3 rounded-lg font-medium flex items-center space-x-2 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Lock size={18} />
                        <span>{isSaving ? 'Changing...' : 'Change Password'}</span>
                      </motion.button>
                    </div>
                  </form>
                </div>
              )}
            </GlassCard>
          </div>
        </div>
      </div>
    </div>
  )
}