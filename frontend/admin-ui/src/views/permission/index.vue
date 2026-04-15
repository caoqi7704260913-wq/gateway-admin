<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>权限管理</span>
          <el-button type="primary" @click="handleAdd">新增权限</el-button>
        </div>
      </template>

      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="权限名称">
          <el-input v-model="searchForm.name" placeholder="请输入权限名称" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="权限名称" />
        <el-table-column prop="code" label="权限代码" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        :page-sizes="[50, 100, 200]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadData"
        @current-change="loadData"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px" @close="handleDialogClose">
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
        <el-form-item label="权限代码" prop="code" v-if="!isEdit">
          <el-input v-model="formData.code" placeholder="例如: user:view" />
        </el-form-item>
        <el-form-item label="权限名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入权限名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="formData.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { getPermissionList, createPermission, updatePermission, deletePermission, type Permission } from '@/api/permission'

const searchForm = reactive({ name: '' })
const tableData = ref<Permission[]>([])
const loading = ref(false)
const pagination = reactive({ page: 1, page_size: 50, total: 0 })
const dialogVisible = ref(false)
const dialogTitle = ref('')
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref<FormInstance>()
const formData = reactive({ code: '', name: '', description: '' })
const editingPermissionId = ref<number>(0)

const formRules: FormRules = {
  code: [{ required: true, message: '请输入权限代码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入权限名称', trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getPermissionList({
      page: pagination.page,
      page_size: pagination.page_size,
      name: searchForm.name || undefined
    })
    tableData.value = res.items
    pagination.total = res.total
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  searchForm.name = ''
  pagination.page = 1
  loadData()
}

const handleAdd = () => {
  isEdit.value = false
  dialogTitle.value = '新增权限'
  dialogVisible.value = true
}

const handleEdit = (row: Permission) => {
  isEdit.value = true
  dialogTitle.value = '编辑权限'
  Object.assign(formData, { code: row.code, name: row.name, description: row.description })
  editingPermissionId.value = row.id
  dialogVisible.value = true
}

const handleDelete = (row: Permission) => {
  ElMessageBox.confirm(`确定删除权限"${row.name}"？`, '提示', { type: 'warning' }).then(async () => {
    try {
      await deletePermission(row.id)
      ElMessage.success('删除成功')
      loadData()
    } catch {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitLoading.value = true
    try {
      if (isEdit.value) {
        await updatePermission(editingPermissionId.value, {
          name: formData.name,
          description: formData.description
        })
        dialogVisible.value = false
        ElMessage.success('更新成功')
        await loadData()
      } else {
        await createPermission(formData)
        dialogVisible.value = false
        ElMessage.success('创建成功')
        await loadData()
      }
    } catch (error: any) {
      console.error('提交错误:', error)
      const errorMsg = error.response?.data?.detail || error.message || (isEdit.value ? '更新失败' : '创建失败')
      ElMessage.error(errorMsg)
    } finally {
      submitLoading.value = false
    }
  })
}

const handleDialogClose = () => {
  formRef.value?.resetFields()
  editingPermissionId.value = 0
  Object.assign(formData, { code: '', name: '', description: '' })
}

onMounted(() => loadData())
</script>

<style scoped>
.page-container { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.search-form { margin-bottom: 20px; }
</style>
