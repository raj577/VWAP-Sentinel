export interface FyersStatus {
  status: string;
  message: string;
  token_present: boolean;
  token_age_hours: number | null;
  last_success_at: string | null;
  checked_at: string;
}

export interface IngestionJob {
  id: number;
  job_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  total_instruments: number;
  successful_instruments: number;
  failed_instruments: number;
  candles_inserted: number;
  candles_updated: number;
  error_summary: string | null;
  triggered_by: string;
}

export interface MarketDataStatus {
  timeframe: string;
  instruments_total: number;
  instruments_active: number;
  candles_total: number;
  latest_candle_at: string | null;
  fyers: FyersStatus;
  last_job: IngestionJob | null;
}

export interface Instrument {
  id: number;
  fyers_symbol: string;
  underlying_symbol: string;
  exchange: string;
  instrument_type: string;
  expiry_date: string;
  lot_size: number | null;
  tick_size: number | null;
  is_active: boolean;
  first_available_timestamp: string | null;
}

export interface InstrumentPage {
  items: Instrument[];
  total: number;
  page: number;
  page_size: number;
}

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface CandlePage {
  symbol: string;
  timeframe: string;
  items: Candle[];
  total: number;
  limit: number;
  offset: number;
}

export interface AvwapPoint {
  timestamp: string;
  close: number;
  avwap: number | null;
  session_vwap: number | null;
  atr: number | null;
}

export interface AvwapResponse {
  symbol: string;
  underlying_symbol: string;
  expiry_date: string;
  timeframe: string;
  anchor_timestamp: string | null;
  latest: AvwapPoint | null;
  points: AvwapPoint[];
}

export interface JobPage {
  items: IngestionJob[];
  total: number;
  page: number;
  page_size: number;
}

export interface ScanResultCandle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ScanResultRow {
  id: number;
  symbol: string;
  expiry_date: string;
  last_price: number;
  avwap: number;
  session_vwap: number | null;
  distance_pct: number;
  candle_count: number;
  avg_body_ratio: number;
  max_body_ratio: number;
  classification: string;
  detected_at: string;
  pattern_start: string | null;
  pattern_end: string | null;
  latest_atr: number | null;
  candles: ScanResultCandle[];
}

export interface ScanRun {
  id: number;
  scan_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  instruments_scanned: number;
  failed_instruments: number;
  matches_count: number;
  config_version: string;
  data_freshness_at: string | null;
  error_summary: string | null;
  triggered_by: string;
}

export interface ScanRunPage {
  items: ScanRun[];
  total: number;
  page: number;
  page_size: number;
}

export interface ScanRunDetail extends ScanRun {
  results: ScanResultRow[];
}

export interface ChartPoint {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  avwap: number | null;
  session_vwap: number | null;
}

export interface ChartPatternInfo {
  scan_run_id: number;
  classification: string;
  detected_at: string;
  candle_count: number;
  distance_pct: number;
  pattern_start: string | null;
  pattern_end: string | null;
}

export interface ScanChartResponse {
  symbol: string;
  underlying_symbol: string;
  expiry_date: string;
  timeframe: string;
  scan_run_id: number | null;
  scan_completed_at: string | null;
  pattern: ChartPatternInfo | null;
  points: ChartPoint[];
}

export interface ScanComparison {
  base_run_id: number;
  compare_run_id: number;
  appeared: string[];
  disappeared: string[];
  persisted: string[];
}

export interface SymbolAppearance {
  scan_run_id: number;
  completed_at: string | null;
  classification: string;
  distance_pct: number;
}

export interface SymbolAppearances {
  symbol: string;
  first_seen_at: string | null;
  latest_seen_at: string | null;
  appearances: SymbolAppearance[];
}

export interface SchedulerSettings {
  id: number;
  scheduler_enabled: boolean;
  scan_interval_minutes: number;
  market_open_time: string;
  market_close_time: string;
  timezone: string;
  allow_manual_outside_market_hours: boolean;
  market_holidays: string[];
  last_run_at: string | null;
  next_run_at: string | null;
  updated_by: string | null;
  updated_at: string;
}

export interface SchedulerStatus {
  settings: SchedulerSettings;
  market_open: boolean;
  server_time: string;
  active_job: PipelineJob | null;
  last_scan_run: ScanRun | null;
  data_freshness_at: string | null;
}

export interface PipelineJob {
  id: number;
  job_type: string;
  trigger_source: string;
  status: string;
  stage: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  total_instruments: number;
  processed_instruments: number;
  failed_instruments: number;
  candles_fetched: number;
  candles_inserted: number;
  candles_updated: number;
  error_summary: string | null;
  cancellation_requested_at: string | null;
  ingestion_job_id: number | null;
  scan_run_id: number | null;
  created_at: string;
}

export interface PipelineJobPage {
  items: PipelineJob[];
  total: number;
  page: number;
  page_size: number;
}

export interface PipelineJobLog {
  id: number;
  job_id: number;
  symbol: string;
  status: string;
  candles_processed: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface PipelineLogPage {
  items: PipelineJobLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface PipelineSummary {
  counts: Record<string, number>;
  total_jobs: number;
  active_job: PipelineJob | null;
  last_completed_at: string | null;
  last_failed_at: string | null;
  last_scan_run_id: number | null;
  data_freshness_at: string | null;
}

export interface AdminUser {
  id: string;
  full_name: string;
  email: string;
  account_status: string;
  email_verified_at: string | null;
  last_login_at: string | null;
  created_at: string;
  roles: string[];
}

export interface AdminUserPage {
  items: AdminUser[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditLogRow {
  id: string;
  actor_user_id: string | null;
  target_user_id: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  meta: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}
