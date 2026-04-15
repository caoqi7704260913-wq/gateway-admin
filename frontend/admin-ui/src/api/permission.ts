import request from './request'

export interface Permission {
  id: number
  code: string
  name: string
  description?: string
  created_at: string
}

export interface PermissionListParams {
  page: number
  page_size: number
  name?: string
}

export interface PermissionListResponse {
  total: number
  items: Permission[]
}

export function getPermissionList(params: PermissionListParams) {
  return request.get<PermissionListResponse>('/admin-service/api/permissions/', { params })
}

export function createPermission(data: { code: string; name: string; description?: string }) {
  return request.post<Permission>('/admin-service/api/permissions/', data)
}

export function updatePermission(id: number, data: { name?: string; description?: string }) {
  return request.put<Permission>(`/admin-service/api/permissions/${id}`, data)
}

export function deletePermission(id: number) {
  return request.delete(`/admin-service/api/permissions/${id}`)
}
