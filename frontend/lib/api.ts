import {
  AuthResponse,
  User,
  DatasetSummary,
  DatasetDetail,
  DatasetPreview,
  DatasetProfile,
  AnalysisResponse,
  AnalysisPlan,
  Report,
  HealthStatus,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_PREFIX = `${API_BASE}/api/v1`;

class ApiClient {
  private getToken(): string | null {
    if (typeof window !== "undefined") {
      return localStorage.getItem("querypilot_token");
    }
    return null;
  }

  public setToken(token: string) {
    if (typeof window !== "undefined") {
      localStorage.setItem("querypilot_token", token);
    }
  }

  public clearToken() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("querypilot_token");
      localStorage.removeItem("querypilot_user");
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_PREFIX}${endpoint}`;
    const token = this.getToken();

    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errorMsg = `Request failed (${res.status})`;
      try {
        const errorData = await res.json();
        errorMsg = errorData.detail || errorData.message || errorMsg;
      } catch {
        // ignore json parse error
      }
      throw new Error(errorMsg);
    }

    // Check if response is empty (e.g. 204 or void)
    const contentType = res.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      return res.json() as Promise<T>;
    }
    return res.text() as unknown as Promise<T>;
  }

  // Auth
  async register(email: string, password: string):Promise<AuthResponse> {
    const res = await this.request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    this.setToken(res.access_token);
    if (typeof window !== "undefined") {
      localStorage.setItem("querypilot_user", JSON.stringify(res.user));
    }
    return res;
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const res = await this.request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    this.setToken(res.access_token);
    if (typeof window !== "undefined") {
      localStorage.setItem("querypilot_user", JSON.stringify(res.user));
    }
    return res;
  }

  async logout(): Promise<void> {
    try {
      await this.request("/auth/logout", { method: "POST" });
    } catch {
      // ignore logout failure on backend
    } finally {
      this.clearToken();
    }
  }

  async getMe(): Promise<User> {
    return this.request<User>("/auth/me");
  }

  // Health
  async getHealth(): Promise<HealthStatus> {
    return this.request<HealthStatus>("/health");
  }

  // Datasets
  async getDatasets(): Promise<DatasetSummary[]> {
    return this.request<DatasetSummary[]>("/datasets");
  }

  async getDataset(id: string): Promise<DatasetDetail> {
    return this.request<DatasetDetail>(`/datasets/${id}`);
  }

  async uploadDataset(file: File, name?: string): Promise<DatasetDetail> {
    const formData = new FormData();
    formData.append("file", file);
    if (name) {
      formData.append("name", name);
    }
    return this.request<DatasetDetail>("/datasets/upload", {
      method: "POST",
      body: formData,
    });
  }

  async previewDataset(id: string, page = 1, pageSize = 25): Promise<DatasetPreview> {
    return this.request<DatasetPreview>(`/datasets/${id}/preview?page=${page}&page_size=${pageSize}`);
  }

  async getDatasetProfile(id: string): Promise<DatasetProfile> {
    return this.request<DatasetProfile>(`/datasets/${id}/profile`);
  }

  async deleteDataset(id: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/datasets/${id}`, {
      method: "DELETE",
    });
  }

  // Analyses
  async getAnalyses(datasetId?: string): Promise<AnalysisResponse[]> {
    const query = datasetId ? `?dataset_id=${datasetId}` : "";
    return this.request<AnalysisResponse[]>(`/analyses${query}`);
  }

  async getAnalysis(id: string): Promise<AnalysisResponse> {
    return this.request<AnalysisResponse>(`/analyses/${id}`);
  }

  async createAnalysis(datasetId: string, question: string, planOverride?: AnalysisPlan): Promise<AnalysisResponse> {
    return this.request<AnalysisResponse>("/analyses", {
      method: "POST",
      body: JSON.stringify({
        dataset_id: datasetId,
        question,
        plan_override: planOverride,
      }),
    });
  }

  async deleteAnalysis(id: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/analyses/${id}`, {
      method: "DELETE",
    });
  }

  // Reports
  async getReports(): Promise<Report[]> {
    return this.request<Report[]>("/reports");
  }

  async createReport(analysisId: string, format = "csv"): Promise<Report> {
    return this.request<Report>("/reports", {
      method: "POST",
      body: JSON.stringify({ analysis_id: analysisId, format }),
    });
  }

  getReportDownloadUrl(reportId: string): string {
    return `${API_PREFIX}/reports/${reportId}/download`;
  }
}

export const api = new ApiClient();
