create table if not exists companies (
    id bigserial primary key,
    name text not null,
    domain text,
    created_at timestamptz not null default now()
);

create table if not exists customers (
    id bigserial primary key,
    company_id bigint not null references companies(id) on delete cascade,
    name text not null,
    phone text,
    email text,
    created_at timestamptz not null default now()
);

create table if not exists campaigns (
    id bigserial primary key,
    company_id bigint not null references companies(id) on delete cascade,
    name text not null,
    objective text,
    created_at timestamptz not null default now()
);

create table if not exists webhook_events (
    id bigserial primary key,
    event_type text not null,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);
