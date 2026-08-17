export type User = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
};

export type Tenant = {
  id: string;
  name: string;
  slug: string;
  status: "active" | "archived";
  created_at: string;
};

export type TenantMember = {
  tenant_id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: "owner" | "admin" | "member";
  created_at: string;
};

export type TenantInvitation = {
  id: string;
  email: string;
  role: "owner" | "admin" | "member";
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
};

export type CrawlTarget = {
  id: string;
  tenant_id: string;
  name: string;
  target_url: string;
  target_host: string;
  handler_name: string;
  enabled: boolean;
  schedule_cron: string | null;
  schedule_timezone: string;
  schedule_enabled: boolean;
  next_run_at: string | null;
  archived_at: string | null;
};

export type CrawlJob = {
  id: string;
  tenant_id: string;
  crawl_target_id: string;
  status: string;
  dispatch_state: string;
  attempt_count: number;
  error_message: string | null;
  result: Record<string, unknown> | null;
  scheduled_for: string | null;
  retry_of_job_id: string | null;
  dispatched_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
};
