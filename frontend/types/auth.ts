export interface AuthUser {
  id: string;
  full_name: string;
  email: string;
  account_status: string;
  email_verified_at: string | null;
  last_login_at: string | null;
  created_at: string;
  roles: string[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  csrf_token: string;
  user: AuthUser;
}

export interface AuthMessage {
  message: string;
  dev_token?: string | null;
}

export interface AuthSession {
  id: string;
  device_name: string | null;
  user_agent: string | null;
  ip_address: string | null;
  created_at: string;
  last_activity_at: string | null;
  current: boolean;
}

export interface SessionList {
  sessions: AuthSession[];
}
