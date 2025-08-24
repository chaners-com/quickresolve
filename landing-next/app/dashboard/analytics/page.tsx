'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { 
  BarChart3, 
  FileText, 
  MessageSquare, 
  TrendingUp,
  Calendar,
  ArrowLeft
} from 'lucide-react'
import { GlassCard } from '../../components/GlassCard'
import { GradientOrbs } from '../../components/GradientOrbs'

interface User {
  id: number
  email: string
  username?: string
  first_name?: string
  last_name?: string
}

interface AnalyticsData {
  totalFiles: number
  processedFiles: number
  totalQueries: number
  averageProcessingTime: number
  monthlyUploads: number[]
  fileTypes: { [key: string]: number }
}

export default function AnalyticsPage() {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [analytics, setAnalytics] = useState<AnalyticsData>({
    totalFiles: 0,
    processedFiles: 0,
    totalQueries: 0,
    averageProcessingTime: 0,
    monthlyUploads: [10, 15, 8, 25, 18, 30, 22, 35, 28, 40, 32, 45],
    fileTypes: {
      'PDF': 45,
      'DOCX': 30,
      'TXT': 15,
      'XLSX': 10
    }
  })
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
        await loadAnalytics(userData.id)
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

  const loadAnalytics = async (userId: number) => {
    try {
      // This would typically fetch real analytics data
      const response = await fetch(`/api/analytics?user_id=${userId}`)
      if (response.ok) {
        const data = await response.json()
        setAnalytics(data)
      }
    } catch (error) {
      console.error('Failed to load analytics:', error)
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
      
      <div className="container mx-auto px-6 py-8">
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
              <h1 className="text-3xl font-bold text-white">Analytics</h1>
              <p className="text-white/60 mt-1">Track your usage and document insights</p>
            </div>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Total Files"
            value={analytics.totalFiles.toString()}
            icon={<FileText size={24} />}
            change="+12%"
            positive={true}
          />
          <MetricCard
            title="Processed"
            value={analytics.processedFiles.toString()}
            icon={<BarChart3 size={24} />}
            change="+8%"
            positive={true}
          />
          <MetricCard
            title="AI Queries"
            value={analytics.totalQueries.toString()}
            icon={<MessageSquare size={24} />}
            change="+25%"
            positive={true}
          />
          <MetricCard
            title="Avg Processing"
            value={`${analytics.averageProcessingTime}s`}
            icon={<TrendingUp size={24} />}
            change="-5%"
            positive={true}
          />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Monthly Uploads Chart */}
          <GlassCard className="p-6">
            <h3 className="text-white font-semibold mb-4 flex items-center space-x-2">
              <Calendar size={20} />
              <span>Monthly Uploads</span>
            </h3>
            <div className="h-64 flex items-end justify-between space-x-2">
              {analytics.monthlyUploads.map((value, index) => (
                <motion.div
                  key={index}
                  initial={{ height: 0 }}
                  animate={{ height: `${(value / Math.max(...analytics.monthlyUploads)) * 100}%` }}
                  transition={{ delay: index * 0.1, duration: 0.5 }}
                  className="bg-gradient-to-t from-emerald-500 to-teal-500 rounded-t flex-1 min-h-[20px]"
                  title={`Month ${index + 1}: ${value} files`}
                />
              ))}
            </div>
            <div className="flex justify-between text-white/60 text-sm mt-2">
              <span>Jan</span>
              <span>Jun</span>
              <span>Dec</span>
            </div>
          </GlassCard>

          {/* File Types Distribution */}
          <GlassCard className="p-6">
            <h3 className="text-white font-semibold mb-4 flex items-center space-x-2">
              <FileText size={20} />
              <span>File Types</span>
            </h3>
            <div className="space-y-4">
              {Object.entries(analytics.fileTypes).map(([type, count]) => {
                const total = Object.values(analytics.fileTypes).reduce((a, b) => a + b, 0)
                const percentage = (count / total) * 100
                
                return (
                  <div key={type} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="text-white/80 font-medium">{type}</span>
                      <span className="text-white/60 text-sm">{count} files</span>
                    </div>
                    <div className="flex-1 mx-4">
                      <div className="bg-white/10 rounded-full h-2">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${percentage}%` }}
                          className="bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full h-2"
                        />
                      </div>
                    </div>
                    <span className="text-white/60 text-sm">{percentage.toFixed(0)}%</span>
                  </div>
                )
              })}
            </div>
          </GlassCard>
        </div>

        {/* Usage Insights */}
        <GlassCard className="p-6">
          <h3 className="text-white font-semibold mb-4">Usage Insights</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <InsightCard
              title="Most Active Day"
              value="Wednesday"
              description="Peak upload activity"
            />
            <InsightCard
              title="Average File Size"
              value="2.4 MB"
              description="Across all uploads"
            />
            <InsightCard
              title="Processing Success"
              value="97.3%"
              description="Files processed successfully"
            />
          </div>
        </GlassCard>
      </div>
    </div>
  )
}

function MetricCard({ 
  title, 
  value, 
  icon, 
  change, 
  positive 
}: { 
  title: string
  value: string
  icon: React.ReactNode
  change: string
  positive: boolean
}) {
  return (
    <GlassCard className="p-6">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-white/60 text-sm font-medium">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
          <div className={`text-sm font-medium mt-1 ${
            positive ? 'text-green-400' : 'text-red-400'
          }`}>
            {change}
          </div>
        </div>
        <div className="text-emerald-400/60">
          {icon}
        </div>
      </div>
    </GlassCard>
  )
}

function InsightCard({ 
  title, 
  value, 
  description 
}: { 
  title: string
  value: string
  description: string
}) {
  return (
    <div className="text-center">
      <h4 className="text-white font-medium mb-2">{title}</h4>
      <p className="text-2xl font-bold text-emerald-400 mb-1">{value}</p>
      <p className="text-white/60 text-sm">{description}</p>
    </div>
  )
}
