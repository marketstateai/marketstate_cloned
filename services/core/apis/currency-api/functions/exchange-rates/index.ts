import { createClient } from "jsr:@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
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

function getPositiveInteger(value: string | null, fallback: number, max: number) {
  const parsed = Number.parseInt(value ?? "", 10);

  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback;
  }

  return Math.min(parsed, max);
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (req.method !== "GET") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }

  const supabaseUrl =
    Deno.env.get("MARKETSTATE_SUPABASE_URL") ??
    Deno.env.get("SUPABASE_URL");

  const supabaseAnonKey =
    Deno.env.get("MARKETSTATE_SUPABASE_PUBLISHABLE_KEY") ??
    Deno.env.get("SUPABASE_ANON_KEY") ??
    Deno.env.get("SUPABASE_PUBLISHABLE_KEY");

  if (!supabaseUrl || !supabaseAnonKey) {
    return jsonResponse(
      {
        error:
          "Missing MARKETSTATE_SUPABASE_URL or MARKETSTATE_SUPABASE_PUBLISHABLE_KEY",
      },
      500,
    );
  }

  const url = new URL(req.url);

  const currency = url.searchParams.get("currency")?.trim().toUpperCase() ?? "";
  const date = url.searchParams.get("date")?.trim() ?? "";
  const startDate = url.searchParams.get("start_date")?.trim() ?? "";
  const endDate = url.searchParams.get("end_date")?.trim() ?? "";
  const limit = getPositiveInteger(url.searchParams.get("limit"), 100, 1000);
  const page = getPositiveInteger(url.searchParams.get("page"), 1, 100000);

  const from = (page - 1) * limit;
  const to = from + limit - 1;

  const supabase = createClient(supabaseUrl, supabaseAnonKey);

  let query = supabase
    .from("exchange_rates_current")
    .select("exchange_rate_sk,currency,rate,date", {
      count: "exact",
    })
    .order("date", { ascending: false })
    .order("currency", { ascending: true })
    .range(from, to);

  if (currency) {
    query = query.eq("currency", currency);
  }

  if (date) {
    query = query.eq("date", date);
  }

  if (startDate) {
    query = query.gte("date", startDate);
  }

  if (endDate) {
    query = query.lte("date", endDate);
  }

  const { data, error, count } = await query;

  if (error) {
    return jsonResponse({ error: error.message }, 500);
  }

  return jsonResponse({
    data,
    pagination: {
      page,
      limit,
      total: count ?? 0,
      total_pages: count ? Math.ceil(count / limit) : 0,
    },
    filters: {
      currency: currency || null,
      date: date || null,
      start_date: startDate || null,
      end_date: endDate || null,
    },
  });
});
