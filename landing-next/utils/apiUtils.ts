// Utility for API calls with retry logic
export async function fetchWithRetry(
  url: string, 
  options: RequestInit = {}, 
  maxRetries: number = 3,
  retryDelay: number = 1000
): Promise<Response> {
  let lastError: Error = new Error('Unknown error')
  
  for (let i = 0; i <= maxRetries; i++) {
    try {
      const response = await fetch(url, options)
      return response
    } catch (error) {
      lastError = error as Error
      console.error(`API call attempt ${i + 1} failed:`, error)
      
      if (i < maxRetries) {
        console.log(`Retrying in ${retryDelay}ms...`)
        await new Promise(resolve => setTimeout(resolve, retryDelay))
        retryDelay *= 2 // Exponential backoff
      }
    }
  }
  
  throw lastError
}

export function isServiceUnavailableError(error: any): boolean {
  return error instanceof TypeError && 
         (error.message.includes('fetch') || error.message.includes('ECONNREFUSED'))
}