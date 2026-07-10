import axios, { type AxiosInstance } from 'axios'
import { useAuth0 } from '@auth0/auth0-react'
import { useMemo } from 'react'

// Dev "act as user": the chosen app_user id is kept in localStorage and sent as X-Dev-User so
// the backend resolves that identity instead of the see-all dev ADMIN. Ignored once Auth0 is on.
export const ACT_AS_KEY = 'actAsUser'
export const getActAs = () => localStorage.getItem(ACT_AS_KEY) || ''
export function setActAs(userId: string) {
  if (userId) localStorage.setItem(ACT_AS_KEY, userId)
  else localStorage.removeItem(ACT_AS_KEY)
  // simplest reliable refresh: reload so every query refetches under the new identity
  window.location.reload()
}

/**
 * Axios instance that attaches the Auth0 access token when the user is authenticated.
 * In dev (no Auth0 configured) isAuthenticated is false, so no token is sent and the
 * backend falls back to its dev user (or the act-as user, via X-Dev-User).
 */
export function useApi(): AxiosInstance {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0()

  return useMemo(() => {
    const instance = axios.create({
      baseURL: (import.meta.env.VITE_API_BASE as string) || '/api',
    })
    instance.interceptors.request.use(async (config) => {
      const actAs = getActAs()
      if (actAs) config.headers['X-Dev-User'] = actAs
      if (isAuthenticated) {
        try {
          const token = await getAccessTokenSilently()
          config.headers.Authorization = `Bearer ${token}`
        } catch {
          /* proceed unauthenticated */
        }
      }
      return config
    })
    return instance
  }, [getAccessTokenSilently, isAuthenticated])
}
