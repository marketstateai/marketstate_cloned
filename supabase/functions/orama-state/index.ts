import { createClient } from "jsr:@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, PUT, OPTIONS",
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...corsHeaders,
      "Content-Type": "application/json",
    },
  });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (req.method !== "GET" && req.method !== "PUT") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }

  const supabaseUrl =
    Deno.env.get("MARKETSTATE_SUPABASE_URL") ??
    Deno.env.get("SUPABASE_URL");

  const supabaseAnonKey =
    Deno.env.get("MARKETSTATE_SUPABASE_PUBLISHABLE_KEY") ??
    Deno.env.get("SUPABASE_ANON_KEY") ??
    Deno.env.get("SUPABASE_PUBLISHABLE_KEY");

  const authorization = req.headers.get("Authorization");

  if (!supabaseUrl || !supabaseAnonKey) {
    return jsonResponse(
      { error: "Missing MARKETSTATE_SUPABASE_URL or MARKETSTATE_SUPABASE_PUBLISHABLE_KEY" },
      500,
    );
  }

  if (!authorization) {
    return jsonResponse({ error: "Missing Authorization header" }, 401);
  }

  const supabase = createClient(supabaseUrl, supabaseAnonKey, {
    global: {
      headers: {
        Authorization: authorization,
      },
    },
  });

  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser();

  if (userError || !user) {
    return jsonResponse({ error: userError?.message ?? "User not found" }, 401);
  }

  if (req.method === "GET") {
    const { data, error } = await supabase
      .from("orama_user_backups")
      .select("state, state_version, updated_at")
      .eq("user_id", user.id)
      .maybeSingle();

    if (error) {
      return jsonResponse({ error: error.message }, 500);
    }

    return jsonResponse({
      user_id: user.id,
      state: data?.state ?? null,
      state_version: data?.state_version ?? null,
      updated_at: data?.updated_at ?? null,
    });
  }

  let payload: { state?: unknown; state_version?: number };
  try {
    payload = await req.json();
  } catch {
    return jsonResponse({ error: "Invalid JSON body" }, 400);
  }

  if (!payload || typeof payload !== "object" || payload.state == null) {
    return jsonResponse({ error: "Missing state payload" }, 400);
  }

  const stateVersion =
    typeof payload.state_version === "number" && Number.isInteger(payload.state_version)
      ? payload.state_version
      : 1;

  const { data, error } = await supabase
    .from("orama_user_backups")
    .upsert(
      {
        user_id: user.id,
        state: payload.state,
        state_version: stateVersion,
      },
      { onConflict: "user_id" },
    )
    .select("state, state_version, updated_at")
    .single();

  if (error) {
    return jsonResponse({ error: error.message }, 500);
  }

  return jsonResponse({
    user_id: user.id,
    state: data.state,
    state_version: data.state_version,
    updated_at: data.updated_at,
  });
});
