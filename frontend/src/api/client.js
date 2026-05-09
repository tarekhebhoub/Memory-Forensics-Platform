import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60_000,
});

// ─── Token storage ───
export const tokens = {
  get access() { return localStorage.getItem("mfp.access") || ""; },
  get refresh() { return localStorage.getItem("mfp.refresh") || ""; },
  set(access, refresh) {
    if (access)  localStorage.setItem("mfp.access", access);
    if (refresh) localStorage.setItem("mfp.refresh", refresh);
  },
  clear() { localStorage.removeItem("mfp.access"); localStorage.removeItem("mfp.refresh"); },
};

// ─── Request interceptor: attach JWT ───
api.interceptors.request.use((config) => {
  const t = tokens.access;
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// ─── Response interceptor: refresh on 401 ───
let refreshing = null;
api.interceptors.response.use(
  (resp) => resp,
  async (err) => {
    const original = err.config;
    if (err.response && err.response.status === 401 && !original._retried && tokens.refresh) {
      original._retried = true;
      try {
        refreshing ||= axios.post(`${API_BASE}/auth/token/refresh/`, { refresh: tokens.refresh });
        const { data } = await refreshing;
        tokens.set(data.access, data.refresh || tokens.refresh);
        refreshing = null;
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      } catch (e) {
        refreshing = null;
        tokens.clear();
        if (typeof window !== "undefined") window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

// ─── Endpoint helpers ───
export const Auth = {
  login: (username, password) =>
    axios.post(`${API_BASE}/auth/token/`, { username, password }).then(r => r.data),
  me: () => api.get("/auth/users/me/").then(r => r.data),
  changePassword: (old_password, new_password) =>
    api.post("/auth/users/change-password/", { old_password, new_password }).then(r => r.data),
  roles: () => api.get("/auth/users/roles/").then(r => r.data),
  users: {
    list:   () => api.get("/auth/users/").then(r => r.data),
    create: (payload) => api.post("/auth/users/", payload).then(r => r.data),
    update: (id, payload) => api.patch(`/auth/users/${id}/`, payload).then(r => r.data),
    remove: (id) => api.delete(`/auth/users/${id}/`).then(r => r.data),
  },
};

export const Cases = {
  list:   (params) => api.get("/cases/", { params }).then(r => r.data),
  get:    (id) => api.get(`/cases/${id}/`).then(r => r.data),
  create: (data) => api.post("/cases/", data).then(r => r.data),
  update: (id, data) => api.patch(`/cases/${id}/`, data).then(r => r.data),
  remove: (id) => api.delete(`/cases/${id}/`).then(r => r.data),
  setStatus: (id, status) => api.post(`/cases/${id}/status/`, { status }).then(r => r.data),
  assign: (id, user_ids) => api.post(`/cases/${id}/assign/`, { user_ids }).then(r => r.data),
  custody: (id) => api.get(`/cases/${id}/custody/`).then(r => r.data),
  notes: {
    list:   (case_id) => api.get("/cases/notes/", { params: { case: case_id } }).then(r => r.data),
    create: (data) => api.post("/cases/notes/", data).then(r => r.data),
    remove: (id) => api.delete(`/cases/notes/${id}/`).then(r => r.data),
  },
};

export const Evidence = {
  list:   (params) => api.get("/evidence/", { params }).then(r => r.data),
  get:    (id) => api.get(`/evidence/${id}/`).then(r => r.data),
  upload: (case_id, file, opts = {}) => {
    const fd = new FormData();
    fd.append("case", case_id);
    fd.append("file", file);
    if (opts.description) fd.append("description", opts.description);
    if (opts.os_hint)     fd.append("os_hint", opts.os_hint);
    return api.post("/evidence/upload/", fd, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: opts.onProgress,
      timeout: 0,                  // no client-side timeout for big files
      maxContentLength: Infinity,
      maxBodyLength: Infinity,
    }).then(r => r.data);
  },
  verify:  (id) => api.post(`/evidence/${id}/verify/`).then(r => r.data),
  analyze: (id, mode = "standard") =>
    api.post(`/evidence/${id}/analyze/`, { mode }).then(r => r.data),
  deepAnalyze: (id) =>
    api.post(`/evidence/${id}/deep-analyze/`).then(r => r.data),
  remove:  (id) => api.delete(`/evidence/${id}/`).then(r => r.data),

  upload_chunked: {
    init: (data) => api.post("/evidence/uploads/init/", data).then(r => r.data),
    chunk: (uid, idx, blob) => {
      const fd = new FormData();
      fd.append("chunk_index", idx);
      fd.append("chunk", blob);
      return api.post(`/evidence/uploads/${uid}/chunk/`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      }).then(r => r.data);
    },
    finalize: (uid, opts = {}) => api.post(`/evidence/uploads/${uid}/finalize/`, opts).then(r => r.data),
  },
};

export const Analysis = {
  jobs:   (params) => api.get("/analysis/jobs/", { params }).then(r => r.data),
  job:    (id) => api.get(`/analysis/jobs/${id}/`).then(r => r.data),
  pluginResult: (job_id, plugin) =>
    api.get(`/analysis/jobs/${job_id}/result/${plugin}/`).then(r => r.data),
};

export const IOCs = {
  list:   (params) => api.get("/ioc/", { params }).then(r => r.data),
  remove: (id) => api.delete(`/ioc/${id}/`).then(r => r.data),
};

export const Timeline = {
  list:   (params) => api.get("/timeline/events/", { params }).then(r => r.data),
};

export const Reports = {
  list:   (params) => api.get("/reports/", { params }).then(r => r.data),
  create: (data) => api.post("/reports/", data).then(r => r.data),
  regenerate: (id) => api.post(`/reports/${id}/regenerate/`).then(r => r.data),
  downloadUrl: (id) => `${API_BASE}/reports/${id}/download/`,
  download: async (id, filename = "report") => {
    const r = await api.get(`/reports/${id}/download/`, { responseType: "blob" });
    const ext = (r.headers["content-type"] || "").includes("pdf") ? "pdf" : "html";
    const blob = new Blob([r.data], { type: r.headers["content-type"] || "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}.${ext}`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};

export const AI = {
  insights:  (case_id) => api.get("/ai/insights/", { params: { case: case_id } }).then(r => r.data),
  summarize: (case_id) => api.post(`/ai/insights/summarize/${case_id}/`).then(r => r.data),
  classify:  (case_id) => api.post(`/ai/insights/classify/${case_id}/`).then(r => r.data),
  recommend: (case_id) => api.post(`/ai/insights/recommend/${case_id}/`).then(r => r.data),
};

export const Audit = {
  list: (params) => api.get("/audit/events/", { params }).then(r => r.data),
};

export default api;
