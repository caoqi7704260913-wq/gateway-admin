import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import CryptoJS from 'crypto-js'

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000'
const hmacKey = import.meta.env.VITE_GATEWAY_HMAC_KEY || ''

const instance: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 生成 HMAC 签名
function generateHmacSignature(data: any): {
  signature: string
  timestamp: string
  nonce: string
} {
  const timestamp = String(Math.floor(Date.now() / 1000))
  const nonce = Math.random().toString(36).substring(2, 15)
  
  // 构建签名字符串：timestamp + nonce + body
  const bodyStr = data ? JSON.stringify(data) : ''
  const message = `${timestamp}${nonce}${bodyStr}`
  
  // 生成 HMAC-SHA256 签名
  const signature = CryptoJS.HmacSHA256(message, hmacKey).toString(CryptoJS.enc.Hex)
  
  return { signature, timestamp, nonce }
}

// 请求拦截器
instance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 添加 Token
    const token = localStorage.getItem('token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // 添加 HMAC 签名（仅当配置了密钥时）
    if (hmacKey && config.headers) {
      const { signature, timestamp, nonce } = generateHmacSignature(config.data)
      config.headers['X-Signature'] = signature
      config.headers['X-Timestamp'] = timestamp
      config.headers['X-Nonce'] = nonce
    }
    
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
instance.interceptors.response.use(
  (response) => {
    const res = response.data

    // 如果是标准格式 { code, message, data }，且 code 是数字类型
    if (res && typeof res === 'object' && 'code' in res && typeof res.code === 'number') {
      if (res.code === 200 || res.code === 0) {
        return res.data
      }
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }

    // 直接返回数据（后端直接返回对象或数组）
    return res
  },
  (error) => {
    console.error('HTTP Error:', error)
    if (error.response) {
      const { status, data } = error.response
      console.error('Error Response:', status, data)
      switch (status) {
        case 401:
          ElMessage.error('登录已过期，请重新登录')
          localStorage.removeItem('token')
          window.location.href = '/login'
          break
        case 403:
          ElMessage.error('没有权限访问')
          break
        case 404:
          ElMessage.error('请求资源不存在')
          break
        case 500:
          ElMessage.error('服务器错误')
          break
        default:
          ElMessage.error(data?.detail || data?.message || '请求失败')
      }
    } else {
      ElMessage.error('网络错误，请检查网络连接')
    }
    return Promise.reject(error)
  }
)

export default instance
