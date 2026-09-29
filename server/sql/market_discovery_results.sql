create table if not exists public.market_discovery_results (
  id uuid not null default gen_random_uuid(),
  mission_id uuid not null references public.missions(id) on delete cascade,
  company_name text not null,
  website text not null,
  summary text null,
  industry text null,
  country text null,
  match_score double precision null default 0,
  confidence double precision null default 0,
  evidence jsonb null default '[]'::jsonb,
  products jsonb null default '[]'::jsonb,
  use_cases jsonb null default '[]'::jsonb,
  technologies jsonb null default '[]'::jsonb,
  customer_logos jsonb null default '[]'::jsonb,
  missing_information jsonb null default '[]'::jsonb,
  metadata jsonb null default '{}'::jsonb,
  created_at timestamp with time zone null default now(),
  constraint market_discovery_results_pkey primary key (id)
) tablespace pg_default;

create index if not exists idx_market_discovery_mission_id
  on public.market_discovery_results using btree (mission_id)
  tablespace pg_default;

create index if not exists idx_market_discovery_company_name
  on public.market_discovery_results using btree (company_name)
  tablespace pg_default;

create index if not exists idx_market_discovery_website
  on public.market_discovery_results using btree (website)
  tablespace pg_default;

create index if not exists idx_market_discovery_evidence
  on public.market_discovery_results using gin (evidence)
  tablespace pg_default;
