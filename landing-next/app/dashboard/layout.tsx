'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { 
  Home,
  Folder,
  MessageSquare,
  BarChart3,
  User,
  Settings,
  LogOut,
  Bell
} from 'lucide-react'
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

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()
  const pathname = usePathname()

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

  const handleLogout = () => {
    localStorage.removeItem('authToken')
    localStorage.removeItem('user')
    router.push('/login')
  }

  const navItems = [
    { href: '/dashboard', icon: Home, label: 'Dashboard' },
    { href: '/dashboard/files', icon: Folder, label: 'Files' },
    { href: '/dashboard/chat', icon: MessageSquare, label: 'AI Chat' },
    { href: '/dashboard/analytics', icon: BarChart3, label: 'Analytics' },
    { href: '/dashboard/profile', icon: User, label: 'Profile' },
    { href: '/dashboard/settings', icon: Settings, label: 'Settings' }
  ]

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
            {navItems.map((item) => (
              <NavItem 
                key={item.href}
                href={item.href}
                icon={<item.icon size={20} />} 
                label={item.label} 
                active={pathname === item.href}
              />
            ))}
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
      <div className="ml-64 min-h-screen">
        {children}
      </div>
    </div>
  )
}

// Navigation Item Component
function NavItem({ 
  href,
  icon, 
  label, 
  active = false
}: { 
  href: string
  icon: React.ReactNode
  label: string
  active?: boolean
}) {
  return (
    <Link href={href}>
      <motion.div
        whileHover={{ scale: 1.02 }}
        className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-all cursor-pointer ${
          active 
            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
            : 'text-white/70 hover:text-white hover:bg-white/5'
        }`}
      >
        {icon}
        <span className="font-medium">{label}</span>
      </motion.div>
    </Link>
  )
}
