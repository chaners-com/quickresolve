'use client'

import { useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { ParticleField } from '../components/ParticleField'
import { GradientOrbs } from '../components/GradientOrbs'
import { GlassCard } from '../components/GlassCard'

export default function SignupPage() {
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    companyName: '',
    teamSize: ''
  })
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [passwordStrength, setPasswordStrength] = useState(0)
  const router = useRouter()

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))

    // Calculate password strength
    if (name === 'password') {
      let strength = 0
      if (value.length >= 8) strength++
      if (/[A-Z]/.test(value)) strength++
      if (/[a-z]/.test(value)) strength++
      if (/[0-9]/.test(value)) strength++
      if (/[^A-Za-z0-9]/.test(value)) strength++
      setPasswordStrength(strength)
    }
  }

  const validateForm = () => {
    if (!formData.firstName.trim()) {
      setError('First name is required')
      return false
    }
    if (!formData.lastName.trim()) {
      setError('Last name is required')
      return false
    }
    if (!formData.email.trim()) {
      setError('Email is required')
      return false
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      setError('Please enter a valid email address')
      return false
    }
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long')
      return false
    }
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      return false
    }
    return true
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) return

    setIsLoading(true)
    setError('')

    try {
      const response = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          firstName: formData.firstName,
          lastName: formData.lastName,
          username: formData.username || undefined,
          email: formData.email,
          password: formData.password,
          companyName: formData.companyName || undefined,
          teamSize: formData.teamSize || undefined,
        }),
      })

      const data = await response.json()

      if (response.ok) {
        // Success! The server has set secure HTTP-only cookies
        window.location.href = '/dashboard'
      } else {
        setError(data.error || 'Registration failed')
      }
    } catch (error) {
      setError('Network error. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const getPasswordStrengthText = () => {
    switch (passwordStrength) {
      case 0:
      case 1: return 'Weak'
      case 2:
      case 3: return 'Fair'
      case 4: return 'Good'
      case 5: return 'Strong'
      default: return 'Weak'
    }
  }

  const getPasswordStrengthColor = () => {
    switch (passwordStrength) {
      case 0:
      case 1: return 'bg-red-500'
      case 2:
      case 3: return 'bg-yellow-500'
      case 4: return 'bg-blue-500'
      case 5: return 'bg-green-500'
      default: return 'bg-red-500'
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <GradientOrbs />
      <ParticleField />
      
      <div className="relative min-h-screen flex items-center justify-center px-4 sm:px-6 lg:px-8 py-12">
        <div className="max-w-md w-full">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            {/* Header */}
            <div className="text-center mb-8">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ duration: 0.5 }}
                className="inline-flex items-center gap-2 rounded-full glass-premium px-4 py-2 mb-6"
              >
                <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-white/90 text-sm">Create Account</span>
              </motion.div>

              <Link href="/" className="text-4xl font-extrabold gradient-text mb-6 block">
                QuickResolve
              </Link>
              <h1 className="text-3xl font-bold text-white mb-2">
                Join us today
              </h1>
              <p className="text-white/70">
                Create your account and get started
              </p>
            </div>

            {/* Signup Form Card */}
            <GlassCard hoverable={false}>
              <form className="space-y-6" onSubmit={handleSubmit}>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="bg-red-500/20 border border-red-400/50 rounded-lg p-4"
                  >
                    <p className="text-white text-sm">{error}</p>
                  </motion.div>
                )}

                <div className="space-y-4">
                  {/* Name Fields */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="firstName" className="block text-sm font-medium text-white/90 mb-2">
                        First Name *
                      </label>
                      <input
                        id="firstName"
                        name="firstName"
                        type="text"
                        required
                        value={formData.firstName}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-lg glass-premium text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                        placeholder="First name"
                      />
                    </div>
                    <div>
                      <label htmlFor="lastName" className="block text-sm font-medium text-white/90 mb-2">
                        Last Name *
                      </label>
                      <input
                        id="lastName"
                        name="lastName"
                        type="text"
                        required
                        value={formData.lastName}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-lg glass-premium text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                        placeholder="Last name"
                      />
                    </div>
                  </div>

                  {/* Username (Optional) */}
                  <div>
                    <label htmlFor="username" className="block text-sm font-medium text-white/90 mb-2">
                      Username (Optional)
                    </label>
                    <input
                      id="username"
                      name="username"
                      type="text"
                      value={formData.username}
                      onChange={handleInputChange}
                      className="w-full px-4 py-3 rounded-lg glass-premium text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                      placeholder="Choose a username"
                    />
                  </div>

                  {/* Email */}
                  <div>
                    <label htmlFor="email" className="block text-sm font-medium text-white/90 mb-2">
                      Email address *
                    </label>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={formData.email}
                      onChange={handleInputChange}
                      className="w-full px-4 py-3 rounded-lg glass-premium text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                      placeholder="Enter your email"
                    />
                  </div>

                  {/* Company Information */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="companyName" className="block text-sm font-medium text-white/90 mb-2">
                        Company Name (Optional)
                      </label>
                      <input
                        id="companyName"
                        name="companyName"
                        type="text"
                        value={formData.companyName}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-lg glass-premium text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                        placeholder="Your company"
                      />
                    </div>
                    <div>
                      <label htmlFor="teamSize" className="block text-sm font-medium text-white/90 mb-2">
                        Team Size (Optional)
                      </label>
                      <select
                        id="teamSize"
                        name="teamSize"
                        value={formData.teamSize}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-lg glass-premium text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                      >
                        <option value="">Select team size</option>
                        <option value="1-10">1-10 people</option>
                        <option value="11-50">11-50 people</option>
                        <option value="51-200">51-200 people</option>
                        <option value="201-1000">201-1000 people</option>
                        <option value="+1000">1000+ people</option>
                      </select>
                    </div>
                  </div>

                  {/* Password */}
                  <div>
                    <label htmlFor="password" className="block text-sm font-medium text-white/90 mb-2">
                      Password *
                    </label>
                    <div className="relative">
                      <input
                        id="password"
                        name="password"
                        type={showPassword ? 'text' : 'password'}
                        autoComplete="new-password"
                        required
                        value={formData.password}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 pr-12 rounded-lg glass-premium text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                        placeholder="Create a password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/60 hover:text-white transition-colors"
                      >
                        {showPassword ? '👁️' : '🔒'}
                      </button>
                    </div>
                    {formData.password && (
                      <div className="mt-2">
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-white/70">Password strength:</span>
                          <span className={`font-medium ${passwordStrength >= 4 ? 'text-green-400' : passwordStrength >= 2 ? 'text-yellow-400' : 'text-red-400'}`}>
                            {getPasswordStrengthText()}
                          </span>
                        </div>
                        <div className="w-full bg-white/20 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full transition-all ${getPasswordStrengthColor()}`}
                            style={{ width: `${(passwordStrength / 5) * 100}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Confirm Password */}
                  <div>
                    <label htmlFor="confirmPassword" className="block text-sm font-medium text-white/90 mb-2">
                      Confirm Password *
                    </label>
                    <div className="relative">
                      <input
                        id="confirmPassword"
                        name="confirmPassword"
                        type={showConfirmPassword ? 'text' : 'password'}
                        autoComplete="new-password"
                        required
                        value={formData.confirmPassword}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 pr-12 rounded-lg glass-premium text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                        placeholder="Confirm your password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/60 hover:text-white transition-colors"
                      >
                        {showConfirmPassword ? '👁️' : '🔒'}
                      </button>
                    </div>
                    {formData.confirmPassword && formData.password !== formData.confirmPassword && (
                      <p className="text-red-400 text-sm mt-1">Passwords do not match</p>
                    )}
                  </div>
                </div>

                {/* Terms and Conditions */}
                <div className="flex items-start">
                  <input
                    id="terms"
                    name="terms"
                    type="checkbox"
                    required
                    className="h-4 w-4 text-emerald-500 focus:ring-emerald-500 bg-white/10 border-white/30 rounded mt-1"
                  />
                  <label htmlFor="terms" className="ml-2 block text-sm text-white/70">
                    I agree to the{' '}
                    <Link href="/terms" className="text-emerald-400 hover:text-emerald-300 transition-colors">
                      Terms of Service
                    </Link>
                    {' '}and{' '}
                    <Link href="/privacy" className="text-emerald-400 hover:text-emerald-300 transition-colors">
                      Privacy Policy
                    </Link>
                  </label>
                </div>

                <div>
                  <motion.button
                    type="submit"
                    disabled={isLoading}
                    whileHover={{ scale: isLoading ? 1 : 1.05 }}
                    whileTap={{ scale: isLoading ? 1 : 0.95 }}
                    className="w-full py-3 px-4 bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold rounded-full shadow-lg hover:shadow-emerald-500/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                  >
                    {isLoading ? (
                      <div className="flex items-center justify-center">
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2"></div>
                        Creating account...
                      </div>
                    ) : (
                      'Create Account'
                    )}
                  </motion.button>
                </div>

                <div className="text-center">
                  <p className="text-white/70">
                    Already have an account?{' '}
                    <Link 
                      href="/login" 
                      className="text-emerald-400 hover:text-emerald-300 font-medium transition-colors"
                    >
                      Sign in
                    </Link>
                  </p>
                </div>
              </form>
            </GlassCard>

            {/* Additional Options */}
            <div className="mt-6 text-center">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8, delay: 0.3 }}
              >
                <Link 
                  href="/" 
                  className="text-white/60 hover:text-white/80 text-sm transition-colors"
                >
                  ← Back to homepage
                </Link>
              </motion.div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}