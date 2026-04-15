<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>用户总数</span>
              <el-icon class="icon"><User /></el-icon>
            </div>
          </template>
          <div class="stat-value">{{ stats.total_users.toLocaleString() }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>今日访问</span>
              <el-icon class="icon"><TrendCharts /></el-icon>
            </div>
          </template>
          <div class="stat-value">{{ stats.today_visits }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>在线用户</span>
              <el-icon class="icon"><UserFilled /></el-icon>
            </div>
          </template>
          <div class="stat-value">{{ stats.online_users }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>系统消息</span>
              <el-icon class="icon"><Bell /></el-icon>
            </div>
          </template>
          <div class="stat-value">{{ stats.system_messages }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <span>欢迎使用后台管理系统</span>
          </template>
          <div class="welcome">
            <p>当前用户: {{ userStore.userInfo?.username }}</p>
            <p>登录时间: {{ new Date().toLocaleString() }}</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { getDashboardStats, type DashboardStats } from '@/api/dashboard'

const userStore = useUserStore()
const stats = ref<DashboardStats>({
  total_users: 0,
  today_visits: 0,
  online_users: 0,
  system_messages: 0
})

const loadStats = async () => {
  try {
    stats.value = await getDashboardStats()
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header .icon {
  font-size: 24px;
  color: #409eff;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.welcome {
  font-size: 16px;
  line-height: 2;
  color: #606266;
}
</style>
