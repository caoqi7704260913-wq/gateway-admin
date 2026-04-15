import request from './request'

export interface Role {
  id: number
  code: string
  name: string
  description?: string
  status: number
  created_at: string
  updated_at?: string
  permission_ids: number[]
}

export interface RoleListParams {
  page: number
  page_size: number
  name?: string
  status?: number
}

export interface RoleListResponse {
  total: number
  items: Role[]
}

export interface RoleCreateData {
  code: string
  name: string
  description?: string
  status?: number
  permission_ids?: number[]
}

export interface RoleUpdateData {
  name?: string
  description?: string
  status?: number
  permission_ids?: number[]
}

/**
 * 获取角色列表
 */
export function getRoleList(params: RoleListParams) {
  return request.get<RoleListResponse>('/admin-service/api/roles/', { params })
}

/**
 * 创建角色
 */
export function createRole(data: RoleCreateData) {
  return request.post<Role>('/admin-service/api/roles/', data)
}

/**
 * 更新角色
 */
export function updateRole(id: number, data: RoleUpdateData) {
  return request.put<Role>(`/admin-service/api/roles/${id}`, data)
}

/**
 * 删除角色
 */
export function deleteRole(id: number) {
  return request.delete(`/admin-service/api/roles/${id}`)
}
