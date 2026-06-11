import { createClient } from '@supabase/supabase-js'

// Browser client. The anon key is publishable — safe to ship to the frontend.
// It handles sign-up / sign-in and stores the session; we read the access token
// from it to authenticate calls to our own backend.
export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY,
)
