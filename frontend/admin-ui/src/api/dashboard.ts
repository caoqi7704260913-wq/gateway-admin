import request from './request'

export interface DashboardStats {
  total_users: number
  today_visits: number
  online_users: number
  system_messages: number
}

export const getDashboardStats = () => {
  return request.get<DashboardStats>('/admin-service/api/dashboard/stats')
}
