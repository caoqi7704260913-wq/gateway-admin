import request from './request'

export interface Admin {
  id: number
  username: string
  nickname?: string
  email?: string
  role_id?: number
  status: number
  created_at: string
  updated_at?: string
}

export interface AdminListParams {
  page?: number
  page_size?: number
  username?: string
  status?: number
}

export interface AdminListResponse {
  total: number
  items: Admin[]
}

export interface AdminCreateData {
  username: string
  password: string
  nickname?: string
  email?: string
  role_id?: number
}

export interface AdminUpdateData {
  nickname?: string
  email?: string
  role_id?: number
  status?: number
}

// 获取管理员列表
export const getAdminList = (params: AdminListParams) => {
  return request.get('/admin-service/api/admins/', { params }) as any as Promise<AdminListResponse>
}

// 获取管理员详情
export const getAdminDetail = (id: number) => {
  return request.get(`/admin-service/api/admins/${id}`) as any as Promise<Admin>
}

// 创建管理员
export const createAdmin = (data: AdminCreateData) => {
  return request.post('/admin-service/api/admins/', data) as any as Promise<Admin>
}

// 更新管理员
export const updateAdmin = (id: number, data: AdminUpdateData) => {
  return request.put(`/admin-service/api/admins/${id}`, data) as any as Promise<Admin>
}

// 删除管理员
export const deleteAdmin = (id: number) => {
  return request.delete(`/admin-service/api/admins/${id}`) as any as Promise<{ message: string }>
}
