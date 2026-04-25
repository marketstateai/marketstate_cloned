(function initSupabaseClient() {
  const config = window.MARKETSTATE_CONFIG || {};
  const supabaseUrl = config.SUPABASE_URL || "";
  const supabaseAnonKey = config.SUPABASE_ANON_KEY || "";

  window.marketstateSupabase = null;

  if (!window.supabase) {
    console.warn("Supabase client library failed to load.");
    return;
  }

  if (!supabaseUrl || !supabaseAnonKey) {
    console.info("Supabase config missing. App stays in mock mode.");
    return;
  }

  window.marketstateSupabase = window.supabase.createClient(
    supabaseUrl,
    supabaseAnonKey,
    {
      auth: {
        persistSession: true,
        autoRefreshToken: true
      }
    }
  );

  console.info("Supabase client initialized.");
})();
