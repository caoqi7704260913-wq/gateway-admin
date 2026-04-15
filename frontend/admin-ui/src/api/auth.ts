import request from './request'

export interface LoginData {
  username: string
  password: string
  device?: string
}

export interface UserInfo {
  id: number
  username: string
  nickname?: string
  role?: string
}

export interface LoginResponse {
  token: string
  user?: UserInfo
}

export const login = (data: LoginData) => {
  return request.post('/admin-service/api/auth/login', data) as any as Promise<LoginResponse>
}

export const logout = () => {
  return request.post('/admin-service/api/auth/logout')
}

export const getUserInfo = () => {
  return request.get('/admin-service/api/auth/userinfo') as any as Promise<UserInfo>
}
