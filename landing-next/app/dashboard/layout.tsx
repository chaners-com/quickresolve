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
  User as UserIcon,
  Settings,
  LogOut,
  Bell
} from 'lucide-react'
import { GradientOrbs } from '../components/GradientOrbs'
import SecureAuthGuard, { useAuth } from '../components/SecureAuthGuard'
import { User } from '../../types/auth'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <SecureAuthGuard>
      <DashboardLayoutContent>{children}</DashboardLayoutContent>
    </SecureAuthGuard>
  )
}

function DashboardLayoutContent({ 
  children 
}: { 
  children: React.ReactNode 
}) {
  const { user, logout } = useAuth()
  const pathname = usePathname()

  const handleLogout = async () => {
    await logout()
  }

  const navItems = [
    { href: '/dashboard', icon: Home, label: 'Dashboard' },
    { href: '/dashboard/files', icon: Folder, label: 'Files' },
    { href: '/dashboard/chat', icon: MessageSquare, label: 'AI Chat' },
    { href: '/dashboard/analytics', icon: BarChart3, label: 'Analytics' },
    { href: '/dashboard/profile', icon: UserIcon, label: 'Profile' },
    { href: '/dashboard/settings', icon: Settings, label: 'Settings' }
  ]

  return (
    <div className="fixed inset-0 bg-gray-900 overflow-hidden">
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
                  {user?.first_name?.[0] || 'U'}{user?.last_name?.[0] || 'U'}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium truncate">
                  {user?.first_name || 'User'} {user?.last_name || ''}
                </p>
                <p className="text-white/60 text-xs truncate">
                  {user?.email || 'user@example.com'}
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
      <div className="ml-64 h-full overflow-auto bg-gray-900">
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
