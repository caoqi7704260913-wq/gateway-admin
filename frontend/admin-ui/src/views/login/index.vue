<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <el-icon><Shop /></el-icon>
          <span>后台管理系统</span>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="0"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <el-form-item v-if="showCaptcha" prop="captcha">
          <div class="captcha-container">
            <el-input
              v-model="form.captcha"
              placeholder="请输入验证码"
              prefix-icon="Key"
              size="large"
              style="flex: 1"
            />
            <img
              :src="captchaImage"
              alt="验证码"
              class="captcha-image"
              @click="refreshCaptcha"
            />
          </div>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            style="width: 100%"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'
import request from '@/api/request'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const showCaptcha = ref(false)
const captchaImage = ref('')
const captchaId = ref('')
const loginFailCount = ref(Number(localStorage.getItem('loginFailCount') || 0))

const form = reactive({
  username: '',
  password: '',
  captcha: ''
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  captcha: [
    { required: true, message: '请输入验证码', trigger: 'blur' }
  ]
}

// 获取验证码
const getCaptcha = async () => {
  try {
    const res = await request.get('/admin-service/api/captcha/generate')
    captchaId.value = res.captcha_id
    captchaImage.value = res.image
  } catch (error) {
    console.error('获取验证码失败:', error)
  }
}

// 刷新验证码
const refreshCaptcha = () => {
  form.captcha = ''
  getCaptcha()
}

// 如果已经有失败记录，直接显示验证码
if (loginFailCount.value >= 3) {
  showCaptcha.value = true
  getCaptcha()
}

const handleLogin = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      await userStore.login({
        username: form.username,
        password: form.password,
        device: navigator.userAgent,
        captcha_id: showCaptcha.value ? captchaId.value : undefined,
        captcha: showCaptcha.value ? form.captcha : undefined
      })
      ElMessage.success('登录成功')
      loginFailCount.value = 0
      localStorage.removeItem('loginFailCount')
      router.push('/')
    } catch (error: any) {
      loginFailCount.value++
      localStorage.setItem('loginFailCount', String(loginFailCount.value))
      // 失败3次后显示验证码
      if (loginFailCount.value >= 3 && !showCaptcha.value) {
        showCaptcha.value = true
        await getCaptcha()
        ElMessage.warning('连续登录失败，请输入验证码')
      } else {
        ElMessage.error(error.response?.data?.detail || '登录失败，请检查用户名和密码')
      }
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: bold;
  color: #303133;
}

.card-header .el-icon {
  margin-right: 8px;
  font-size: 24px;
  color: #409eff;
}

.captcha-container {
  display: flex;
  gap: 10px;
  width: 100%;
}

.captcha-image {
  height: 40px;
  cursor: pointer;
  border-radius: 4px;
  border: 1px solid #dcdfe6;
  transition: all 0.3s;
}

.captcha-image:hover {
  border-color: #409eff;
  box-shadow: 0 0 5px rgba(64, 158, 255, 0.3);
}
</style>
