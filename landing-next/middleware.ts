import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { jwtVerify } from 'jose'
import { applySecurityHeaders } from './lib/security'

// TODO: Debug this code for solving auth redirection problem

function getJWTSecret(): Uint8Array {
  const secret = process.env.JWT_SECRET
  
  // Only validate in production or when actually using the secret
  if (process.env.NODE_ENV === 'production') {
    if (!secret) {
      throw new Error('JWT_SECRET environment variable is required in production')
    }
    if (secret.length < 64) {
      throw new Error('JWT_SECRET must be at least 64 characters long for security')
    }
  }
  
  // Provide a build-time fallback that meets length requirements
  const secretToUse = secret || 'build-time-fallback-secret-that-is-exactly-64-chars-long-for-build'
  return new TextEncoder().encode(secretToUse)
}

// Define protected routes that require authentication
const protectedRoutes = [
  '/dashboard',
  '/dashboard/files',
  '/dashboard/chat',
  '/dashboard/analytics',
  '/dashboard/profile',
  '/dashboard/settings'
]

// Define public routes that don't require authentication
const publicRoutes = [
  '/',
  '/login',
  '/signup',
  '/api/auth/login',
  '/api/auth/signup',
  '/product',
  '/solutions',
  '/pricing',
  '/security',
  '/widget'
]

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  
  // Create response with security headers
  let response = NextResponse.next()
  
  // Allow all API routes to pass through (they handle their own auth)
  if (pathname.startsWith('/api/')) {
    return applySecurityHeaders(response)
  }
  
  // Allow public routes
  if (publicRoutes.includes(pathname)) {
    return applySecurityHeaders(response)
  }
  
  // Check if the route is protected
  const isProtectedRoute = protectedRoutes.some(route => 
    pathname === route || pathname.startsWith(route + '/')
  )
  
  if (isProtectedRoute) {
    // Check for session cookie
    const sessionCookie = request.cookies.get('auth-session')?.value
    
    console.error(`[Middleware] Protected route: ${pathname}`)
    console.error(`[Middleware] Session cookie exists: ${!!sessionCookie}`)
    if (sessionCookie) {
      console.error(`[Middleware] Session cookie length: ${sessionCookie.length}`)
      console.error(`[Middleware] Session cookie preview: ${sessionCookie.substring(0, 50)}...`)
    }
    
    if (!sessionCookie) {
      // No session cookie - redirect to login
      console.error(`[Middleware] No session cookie, redirecting to login`)
      const loginUrl = new URL('/login', request.url)
      loginUrl.searchParams.set('redirect', pathname)
      return NextResponse.redirect(loginUrl)
    }
    
    // Validate JWT token using the same logic as auth.ts
    try {
      const JWT_SECRET = getJWTSecret()
      console.error(`[Middleware] JWT_SECRET loaded, length: ${JWT_SECRET.length}`)
      
      const { payload } = await jwtVerify(sessionCookie, JWT_SECRET, {
        algorithms: ['HS256'],
      })
      
      // Check if session is expired (same logic as auth.ts)
      const session = payload as any
      if (session.expires && new Date(session.expires) < new Date()) {
        console.error(`[Middleware] Session expired, redirecting to login`)
        const loginUrl = new URL('/login', request.url)
        loginUrl.searchParams.set('redirect', pathname)
        return NextResponse.redirect(loginUrl)
      }
      
      console.error(`[Middleware] Valid session found for user:`, session.user?.email)
      return applySecurityHeaders(response)
      
    } catch (error) {
      console.error(`[Middleware] Invalid session token, redirecting to login:`, error instanceof Error ? error.message : error)
      
      // Clear invalid session cookie
      const loginUrl = new URL('/login', request.url)
      loginUrl.searchParams.set('redirect', pathname)
      const redirectResponse = NextResponse.redirect(loginUrl)
      
      // Clear the invalid session cookie
      redirectResponse.cookies.set('auth-session', '', {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: 0,
        path: '/',
      })
      
      return applySecurityHeaders(redirectResponse)
    }
  }
  
  // For any other routes, allow them to proceed
  return applySecurityHeaders(response)
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    // '/((?!api|_next/static|_next/image|favicon.ico).*)',

    // TODO: rm this, temporary solution
    '/disabled-for-debugging',
  ],
}