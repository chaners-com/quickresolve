'use client'

import { usePathname } from 'next/navigation'
import { SiteHeader } from './SiteHeader'

export function ConditionalSiteHeader() {
  const pathname = usePathname()
  
  // Don't show the site header on dashboard pages
  const isDashboardPage = pathname.startsWith('/dashboard')
  
  if (isDashboardPage) {
    return null
  }
  
  return <SiteHeader />
}