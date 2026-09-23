import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && window.location.pathname !== '/') {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      window.location.href = '/'
    }
    return Promise.reject(err)
  }
)

export function errMsg(err) {
  return err?.response?.data?.detail || err?.message || '请求失败'
}

export default api
