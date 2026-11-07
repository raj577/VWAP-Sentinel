import { apiGet } from "@/lib/api";
import type {
  AdminUser,
  AdminUserPage,
  AuditLogRow,
  AvwapResponse,

  CandlePage,
  Instrument,
  InstrumentPage,
  JobPage,
  ScanChartResponse,
  ScanComparison,
  PipelineJob,
  PipelineJobPage,
  PipelineLogPage,
  PipelineSummary,
  SchedulerSettings,
  SchedulerStatus,
  ScanResultRow,
  ScanRunDetail,
  ScanRunPage,
  SymbolAppearances,
  MarketDataStatus,
} from "@/types/api";

export function getMarketDataStatus(): Promise<MarketDataStatus> {
  return apiGet<MarketDataStatus>("/market-data/status");
}

export function getInstruments(
  params: { page?: number; pageSize?: number; active?: boolean; q?: string; underlying?: string; expiry?: string } = {},
): Promise<InstrumentPage> {
  const query = new URLSearchParams({
    page: String(params.page ?? 1),
    page_size: String(params.pageSize ?? 50),
  });
  if (params.active !== undefined) query.set("active", String(params.active));
  if (params.q) query.set("q", params.q);
  if (params.underlying) query.set("underlying", params.underlying);
  if (params.expiry) query.set("expiry", params.expiry);
  return apiGet<InstrumentPage>(`/market-data/instruments?${query.toString()}`);
}

export async function getInstrument(symbol: string): Promise<Instrument> {
  return apiGet<Instrument>(
    `/market-data/instruments/${encodeURIComponent(symbol)}`,
  );
}

export function getCandles(
  symbol: string,
  params: { limit?: number; offset?: number } = {},
): Promise<CandlePage> {
  const query = new URLSearchParams({
    limit: String(params.limit ?? 500),
    offset: String(params.offset ?? 0),
  });
  return apiGet<CandlePage>(
    `/market-data/candles/${encodeURIComponent(symbol)}?${query.toString()}`,
  );
}

export function getAvwap(
  symbol: string,
  params: { limit?: number } = {},
): Promise<AvwapResponse> {
  const query = new URLSearchParams({
    limit: String(params.limit ?? 200),
  });
  return apiGet<AvwapResponse>(
    `/market-data/avwap/${encodeURIComponent(symbol)}?${query.toString()}`,
  );
}

export function getIngestionJobs(
  adminKey: string,
  params: { page?: number; pageSize?: number } = {},
): Promise<JobPage> {
  const query = new URLSearchParams({
    page: String(params.page ?? 1),
    page_size: String(params.pageSize ?? 20),
  });
  return apiGet<JobPage>(`/admin/market-data/jobs?${query.toString()}`, {
    headers: { "X-Admin-Key": adminKey },
  });
}

export function getScans(
  adminKey: string,
  params: { page?: number; pageSize?: number } = {},
): Promise<ScanRunPage> {
  const query = new URLSearchParams({
    page: String(params.page ?? 1),
    page_size: String(params.pageSize ?? 20),
  });
  return apiGet<ScanRunPage>(`/admin/scans?${query.toString()}`, {
    headers: { "X-Admin-Key": adminKey },
  });
}

export function getLatestScan(adminKey: string): Promise<ScanRunDetail> {
  return apiGet<ScanRunDetail>("/admin/scans/latest", {
    headers: { "X-Admin-Key": adminKey },
  });
}

export function getScanDetail(
  adminKey: string,
  runId: number,
): Promise<ScanRunDetail> {
  return apiGet<ScanRunDetail>(`/admin/scans/${runId}`, {
    headers: { "X-Admin-Key": adminKey },
  });
}

export function getCurrentScan(
  headers?: Record<string, string>,
): Promise<ScanRunDetail> {
  return apiGet<ScanRunDetail>("/scanner/current", { headers });
}

export function getScanHistory(
  params: {
    page?: number;
    pageSize?: number;
    symbol?: string;
    classification?: string;
  } = {},
  headers?: Record<string, string>,
): Promise<ScanRunPage> {
  const query = new URLSearchParams({
    page: String(params.page ?? 1),
    page_size: String(params.pageSize ?? 20),
  });
  if (params.symbol) query.set("symbol", params.symbol);
  if (params.classification) query.set("classification", params.classification);
  return apiGet<ScanRunPage>(`/scanner/history?${query.toString()}`, {
    headers,
  });
}

export function getScanHistoryDetail(
  runId: number,
  headers?: Record<string, string>,
): Promise<ScanRunDetail> {
  return apiGet<ScanRunDetail>(`/scanner/history/${runId}`, { headers });
}

export function getScanResult(
  resultId: number,
  headers?: Record<string, string>,
): Promise<ScanResultRow> {
  return apiGet<ScanResultRow>(`/scanner/results/${resultId}`, { headers });
}

export function getScanChart(
  symbol: string,
  limit = 240,
  headers?: Record<string, string>,
): Promise<ScanChartResponse> {
  return apiGet<ScanChartResponse>(
    `/scanner/chart/${encodeURIComponent(symbol)}?limit=${limit}`,
    { headers },
  );
}

export function getScanComparison(
  baseRunId: number,
  compareRunId: number,
  headers?: Record<string, string>,
): Promise<ScanComparison> {
  const query = new URLSearchParams({
    base_run_id: String(baseRunId),
    compare_run_id: String(compareRunId),
  });
  return apiGet<ScanComparison>(`/scanner/comparison?${query.toString()}`, {
    headers,
  });
}

export function getSymbolAppearances(
  symbol: string,
  headers?: Record<string, string>,
): Promise<SymbolAppearances> {
  return apiGet<SymbolAppearances>(
    `/scanner/symbols/${encodeURIComponent(symbol)}/appearances`,
    { headers },
  );
}


export function getSchedulerStatus(adminKey: string): Promise<SchedulerStatus> {
  return apiGet<SchedulerStatus>("/admin/scheduler/status", {
    headers: { "X-Admin-Key": adminKey },
  });
}

export function getSchedulerSettings(
  adminKey: string,
): Promise<SchedulerSettings> {
  return apiGet<SchedulerSettings>("/admin/scheduler/settings", {
    headers: { "X-Admin-Key": adminKey },
  });
}

export function getPipelineJobs(
  adminKey: string,
  params: { page?: number; pageSize?: number; status?: string } = {},
): Promise<PipelineJobPage> {
  const query = new URLSearchParams({
    page: String(params.page ?? 1),
    page_size: String(params.pageSize ?? 20),
  });
  if (params.status) query.set("status", params.status);
  return apiGet<PipelineJobPage>(`/admin/pipeline/jobs?${query.toString()}`, {
    headers: { "X-Admin-Key": adminKey },
  });
}

export function getPipelineJob(
  adminKey: string,
  jobId: number,
): Promise<PipelineJob> {
  return apiGet<PipelineJob>(`/admin/pipeline/jobs/${jobId}`, {
    headers: { "X-Admin-Key": adminKey },
  });
}

export function getPipelineJobLogs(
  adminKey: string,
  jobId: number,
  params: { page?: number; pageSize?: number } = {},
): Promise<PipelineLogPage> {
  const query = new URLSearchParams({
    page: String(params.page ?? 1),
    page_size: String(params.pageSize ?? 200),
  });
  return apiGet<PipelineLogPage>(
    `/admin/pipeline/jobs/${jobId}/logs?${query.toString()}`,
    { headers: { "X-Admin-Key": adminKey } },
  );
}

export function getPipelineSummary(
  adminKey: string,
): Promise<PipelineSummary> {
  return apiGet<PipelineSummary>("/admin/pipeline/summary", {
    headers: { "X-Admin-Key": adminKey },
  });
}

export function getAdminUsers(
  adminKey: string,
  params: {
    page?: number;
    pageSize?: number;
    search?: string;
    role?: string;
    status?: string;
    sort?: string;
  } = {},
): Promise<AdminUserPage> {
  const query = new URLSearchParams({
    page: String(params.page ?? 1),
    page_size: String(params.pageSize ?? 20),
  });
  if (params.search) query.set("search", params.search);
  if (params.role) query.set("role", params.role);
  if (params.status) query.set("account_status", params.status);
  if (params.sort) query.set("sort", params.sort);
  return apiGet<AdminUserPage>(`/admin/users?${query.toString()}`, {
    headers: { "X-Admin-Key": adminKey },
  });
}

export function getAdminUser(
  adminKey: string,
  userId: string,
): Promise<AdminUser> {
  return apiGet<AdminUser>(`/admin/users/${userId}`, {
    headers: { "X-Admin-Key": adminKey },
  });
}

export function getAuditLogs(
  adminKey: string,
  limit = 100,
): Promise<AuditLogRow[]> {
  return apiGet<AuditLogRow[]>(`/admin/audit-logs?limit=${limit}`, {
    headers: { "X-Admin-Key": adminKey },
  });
}
