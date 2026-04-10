import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, logout as logoutApi, getUserInfo } from '@/api/auth'
import type { LoginData } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const userInfo = ref<{ id: number; username: string; nickname?: string; role?: string } | null>(null)

  const login = async (data: LoginData) => {
    const res = await loginApi(data)
    token.value = res.token
    userInfo.value = res.user ?? null
    localStorage.setItem('token', res.token)
    if (res.user) {
      localStorage.setItem('userInfo', JSON.stringify(res.user))
    }
    return res
  }

  const logout = async () => {
    try {
      await logoutApi()
    } finally {
      token.value = ''
      userInfo.value = null
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
    }
  }

  const fetchUserInfo = async () => {
    try {
      const res = await getUserInfo()
      userInfo.value = res
      localStorage.setItem('userInfo', JSON.stringify(res))
    } catch {
      logout()
    }
  }

  return {
    token,
    userInfo,
    login,
    logout,
    fetchUserInfo
  }
})
