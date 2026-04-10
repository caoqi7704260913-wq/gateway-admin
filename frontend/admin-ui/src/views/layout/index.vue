<template>
  <el-container class="layout-container">
    <el-aside width="200px">
      <div class="logo">
        <el-icon><Shop /></el-icon>
        <span>后台管理</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/admin">
          <el-icon><User /></el-icon>
          <span>管理员</span>
        </el-menu-item>
        <el-menu-item index="/role">
          <el-icon><UserFilled /></el-icon>
          <span>角色</span>
        </el-menu-item>
        <el-menu-item index="/permission">
          <el-icon><Key /></el-icon>
          <span>权限</span>
        </el-menu-item>
        <el-menu-item index="/menu">
          <el-icon><Menu /></el-icon>
          <span>菜单</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-icon><UserFilled /></el-icon>
              {{ userStore.userInfo?.username || '管理员' }}
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)

const handleCommand = async (command: string) => {
  if (command === 'logout') {
    await userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.el-aside {
  background-color: #304156;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  background-color: #2b3a4a;
}

.logo .el-icon {
  margin-right: 8px;
  font-size: 24px;
}

.el-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 0 12px;
}
</style>
