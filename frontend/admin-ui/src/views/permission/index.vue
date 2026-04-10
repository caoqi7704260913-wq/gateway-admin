<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>权限管理</span>
          <el-button type="primary" @click="handleAdd">新增权限</el-button>
        </div>
      </template>

      <el-table :data="tableData" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="权限名称" />
        <el-table-column prop="code" label="权限代码" />
        <el-table-column prop="type" label="类型" width="100" />
        <el-table-column prop="description" label="描述" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const tableData = ref([
  { id: 1, name: '用户查看', code: 'user:view', type: '按钮', description: '查看用户列表' },
  { id: 2, name: '用户新增', code: 'user:add', type: '按钮', description: '新增用户' }
])

const handleAdd = () => {}
const handleEdit = (row: any) => {}
const handleDelete = (row: any) => {}
</script>

<style scoped>
.page-container {
  padding: 20px;
}
</style>
