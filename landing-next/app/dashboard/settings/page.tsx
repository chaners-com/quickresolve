'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { 
  Settings as SettingsIcon, 
  Bell,
  Shield,
  Palette,
  Database,
  ArrowLeft,
  Save
} from 'lucide-react'
import { GlassCard } from '../../components/GlassCard'
import { GradientOrbs } from '../../components/GradientOrbs'

interface User {
  id: number
  email: string
  first_name?: string
  last_name?: string
}

interface UserSettings {
  notifications: {
    email: boolean
    push: boolean
    processing_complete: boolean
    weekly_summary: boolean
  }
  privacy: {
    data_retention_days: number
    allow_analytics: boolean
    share_usage_data: boolean
  }
  appearance: {
    theme: 'dark' | 'light'
    compact_mode: boolean
  }
}

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [settings, setSettings] = useState<UserSettings>({
    notifications: {
      email: true,
      push: true,
      processing_complete: true,
      weekly_summary: false
    },
    privacy: {
      data_retention_days: 365,
      allow_analytics: true,
      share_usage_data: false
    },
    appearance: {
      theme: 'dark',
      compact_mode: false
    }
  })
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
        await loadSettings(userData.id)
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

  const loadSettings = async (userId: number) => {
    try {
      // This would typically load user settings from the backend
      const response = await fetch(`/api/settings?user_id=${userId}`)
      if (response.ok) {
        const userSettings = await response.json()
        setSettings(userSettings)
      }
    } catch (error) {
      console.error('Failed to load settings:', error)
    }
  }

  const saveSettings = async () => {
    setIsSaving(true)
    setMessage(null)

    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch('/api/settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(settings)
      })

      if (response.ok) {
        setMessage({ type: 'success', text: 'Settings saved successfully!' })
      } else {
        setMessage({ type: 'error', text: 'Failed to save settings' })
      }
    } catch (error) {
      console.error('Error saving settings:', error)
      setMessage({ type: 'error', text: 'Network error. Please try again.' })
    } finally {
      setIsSaving(false)
    }
  }

  const updateSetting = (category: keyof UserSettings, key: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value
      }
    }))
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
            <div>
              <h1 className="text-3xl font-bold text-white">Settings</h1>
              <p className="text-white/60 mt-1">Manage your preferences and configuration</p>
              {/* TODO: actual data */}
              <p className="text-white/60 mt-1">Mock data -- Soon to be updated</p> 
            </div>
          </div>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={saveSettings}
            disabled={isSaving}
            className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-6 py-3 rounded-lg font-medium flex items-center space-x-2 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save size={18} />
            <span>{isSaving ? 'Saving...' : 'Save Settings'}</span>
          </motion.button>
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

        <div className="space-y-6">
          {/* Notifications */}
          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center space-x-2">
              <Bell size={20} />
              <span>Notifications</span>
            </h2>
            
            <div className="space-y-4">
              <ToggleOption
                title="Email Notifications"
                description="Receive updates via email"
                checked={settings.notifications.email}
                onChange={(value) => updateSetting('notifications', 'email', value)}
              />
              
              <ToggleOption
                title="Push Notifications"
                description="Browser push notifications"
                checked={settings.notifications.push}
                onChange={(value) => updateSetting('notifications', 'push', value)}
              />
              
              <ToggleOption
                title="Processing Complete"
                description="Notify when file processing is complete"
                checked={settings.notifications.processing_complete}
                onChange={(value) => updateSetting('notifications', 'processing_complete', value)}
              />
              
              <ToggleOption
                title="Weekly Summary"
                description="Weekly usage and activity summary"
                checked={settings.notifications.weekly_summary}
                onChange={(value) => updateSetting('notifications', 'weekly_summary', value)}
              />
            </div>
          </GlassCard>

          {/* Privacy & Security */}
          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center space-x-2">
              <Shield size={20} />
              <span>Privacy & Security</span>
            </h2>
            
            <div className="space-y-6">
              <div>
                <label className="block text-white/80 text-sm font-medium mb-2">
                  Data Retention Period
                </label>
                <select
                  value={settings.privacy.data_retention_days}
                  onChange={(e) => updateSetting('privacy', 'data_retention_days', parseInt(e.target.value))}
                  className="w-full px-4 py-3 glass-premium rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value={30}>30 days</option>
                  <option value={90}>90 days</option>
                  <option value={180}>6 months</option>
                  <option value={365}>1 year</option>
                  <option value={-1}>Never delete</option>
                </select>
                <p className="text-white/60 text-sm mt-1">
                  How long to keep your uploaded documents
                </p>
              </div>
              
              <ToggleOption
                title="Allow Analytics"
                description="Help improve the service with usage analytics"
                checked={settings.privacy.allow_analytics}
                onChange={(value) => updateSetting('privacy', 'allow_analytics', value)}
              />
              
              <ToggleOption
                title="Share Usage Data"
                description="Share anonymized usage data for research"
                checked={settings.privacy.share_usage_data}
                onChange={(value) => updateSetting('privacy', 'share_usage_data', value)}
              />
            </div>
          </GlassCard>

          {/* Appearance */}
          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center space-x-2">
              <Palette size={20} />
              <span>Appearance</span>
            </h2>
            
            <div className="space-y-6">
              <div>
                <label className="block text-white/80 text-sm font-medium mb-2">
                  Theme
                </label>
                <select
                  value={settings.appearance.theme}
                  onChange={(e) => updateSetting('appearance', 'theme', e.target.value)}
                  className="w-full px-4 py-3 glass-premium rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="dark">Dark</option>
                  <option value="light">Light</option>
                </select>
              </div>
              
              <ToggleOption
                title="Compact Mode"
                description="Use a more compact interface layout"
                checked={settings.appearance.compact_mode}
                onChange={(value) => updateSetting('appearance', 'compact_mode', value)}
              />
            </div>
          </GlassCard>

          {/* Storage & Data */}
          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center space-x-2">
              <Database size={20} />
              <span>Storage & Data</span>
            </h2>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-white/5 rounded-lg border border-white/10">
                <div>
                  <h3 className="text-white font-medium">Clear Cache</h3>
                  <p className="text-white/60 text-sm">Clear temporary files and cache</p>
                </div>
                <button className="bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-lg transition-colors">
                  Clear
                </button>
              </div>
              
              <div className="flex items-center justify-between p-4 bg-red-500/10 rounded-lg border border-red-500/20">
                <div>
                  <h3 className="text-red-400 font-medium">Delete All Data</h3>
                  <p className="text-white/60 text-sm">Permanently delete all your data</p>
                </div>
                <button className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg transition-colors">
                  Delete
                </button>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  )
}

function ToggleOption({ 
  title, 
  description, 
  checked, 
  onChange 
}: { 
  title: string
  description: string
  checked: boolean
  onChange: (value: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between py-3">
      <div className="flex-1">
        <h3 className="text-white font-medium">{title}</h3>
        <p className="text-white/60 text-sm">{description}</p>
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          checked ? 'bg-emerald-500' : 'bg-white/20'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            checked ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  )
}