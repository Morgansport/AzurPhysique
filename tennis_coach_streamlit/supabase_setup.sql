-- À exécuter dans le SQL Editor d'un projet Supabase.
-- L'application Streamlit utilise uniquement la clé service_role côté serveur.
create table if not exists public.tennis_dashboard_state (
  id text primary key,
  content jsonb not null,
  updated_at timestamptz not null default now()
);
alter table public.tennis_dashboard_state enable row level security;
-- Ne créer AUCUNE policy publique pour cette table.
-- La clé service_role (conservée dans les secrets Streamlit) accède côté serveur uniquement.
