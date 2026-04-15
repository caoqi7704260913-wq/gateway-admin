import request from './request'

export interface Menu {
  id: number
  name: string
  path: string
  icon?: string
  component?: string
  sort: number
  status: number
  created_at: string
}

export function getMenuList(params: { page: number; page_size: number; name?: string }) {
  return request.get<{ total: number; items: Menu[] }>('/admin-service/api/menus/', { params })
}

export function createMenu(data: Omit<Menu, 'id' | 'created_at'>) {
  return request.post<Menu>('/admin-service/api/menus/', data)
}

export function updateMenu(id: number, data: Partial<Omit<Menu, 'id' | 'created_at'>>) {
  return request.put<Menu>(`/admin-service/api/menus/${id}`, data)
}

export function deleteMenu(id: number) {
  return request.delete(`/admin-service/api/menus/${id}`)
}
