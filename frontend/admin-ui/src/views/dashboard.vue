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
          <div class="stat-value">1,234</div>
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
          <div class="stat-value">567</div>
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
          <div class="stat-value">89</div>
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
          <div class="stat-value">12</div>
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
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
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
