create extension if not exists "pg_net" with schema "extensions";

drop policy "ms_activity_public_read_demo" on "public"."ms_activity_log";

drop policy "ms_holdings_public_read_demo" on "public"."ms_holdings";

drop policy "ms_portfolio_public_read_demo" on "public"."ms_portfolio_snapshots";

drop policy "ms_profiles_public_read_demo" on "public"."ms_profiles";

drop policy "ms_watchlist_public_insert_demo" on "public"."ms_watchlist";

drop policy "ms_watchlist_public_read_demo" on "public"."ms_watchlist";

drop policy "ms_watchlist_public_update_demo" on "public"."ms_watchlist";

revoke delete on table "public"."Test Table" from "anon";

revoke insert on table "public"."Test Table" from "anon";

revoke references on table "public"."Test Table" from "anon";

revoke select on table "public"."Test Table" from "anon";

revoke trigger on table "public"."Test Table" from "anon";

revoke truncate on table "public"."Test Table" from "anon";

revoke update on table "public"."Test Table" from "anon";

revoke delete on table "public"."Test Table" from "authenticated";

revoke insert on table "public"."Test Table" from "authenticated";

revoke references on table "public"."Test Table" from "authenticated";

revoke select on table "public"."Test Table" from "authenticated";

revoke trigger on table "public"."Test Table" from "authenticated";

revoke truncate on table "public"."Test Table" from "authenticated";

revoke update on table "public"."Test Table" from "authenticated";

revoke delete on table "public"."Test Table" from "service_role";

revoke insert on table "public"."Test Table" from "service_role";

revoke references on table "public"."Test Table" from "service_role";

revoke select on table "public"."Test Table" from "service_role";

revoke trigger on table "public"."Test Table" from "service_role";

revoke truncate on table "public"."Test Table" from "service_role";

revoke update on table "public"."Test Table" from "service_role";

revoke delete on table "public"."ms_activity_log" from "anon";

revoke insert on table "public"."ms_activity_log" from "anon";

revoke references on table "public"."ms_activity_log" from "anon";

revoke select on table "public"."ms_activity_log" from "anon";

revoke trigger on table "public"."ms_activity_log" from "anon";

revoke truncate on table "public"."ms_activity_log" from "anon";

revoke update on table "public"."ms_activity_log" from "anon";

revoke delete on table "public"."ms_activity_log" from "authenticated";

revoke insert on table "public"."ms_activity_log" from "authenticated";

revoke references on table "public"."ms_activity_log" from "authenticated";

revoke select on table "public"."ms_activity_log" from "authenticated";

revoke trigger on table "public"."ms_activity_log" from "authenticated";

revoke truncate on table "public"."ms_activity_log" from "authenticated";

revoke update on table "public"."ms_activity_log" from "authenticated";

revoke delete on table "public"."ms_activity_log" from "service_role";

revoke insert on table "public"."ms_activity_log" from "service_role";

revoke references on table "public"."ms_activity_log" from "service_role";

revoke select on table "public"."ms_activity_log" from "service_role";

revoke trigger on table "public"."ms_activity_log" from "service_role";

revoke truncate on table "public"."ms_activity_log" from "service_role";

revoke update on table "public"."ms_activity_log" from "service_role";

revoke delete on table "public"."ms_holdings" from "anon";

revoke insert on table "public"."ms_holdings" from "anon";

revoke references on table "public"."ms_holdings" from "anon";

revoke select on table "public"."ms_holdings" from "anon";

revoke trigger on table "public"."ms_holdings" from "anon";

revoke truncate on table "public"."ms_holdings" from "anon";

revoke update on table "public"."ms_holdings" from "anon";

revoke delete on table "public"."ms_holdings" from "authenticated";

revoke insert on table "public"."ms_holdings" from "authenticated";

revoke references on table "public"."ms_holdings" from "authenticated";

revoke select on table "public"."ms_holdings" from "authenticated";

revoke trigger on table "public"."ms_holdings" from "authenticated";

revoke truncate on table "public"."ms_holdings" from "authenticated";

revoke update on table "public"."ms_holdings" from "authenticated";

revoke delete on table "public"."ms_holdings" from "service_role";

revoke insert on table "public"."ms_holdings" from "service_role";

revoke references on table "public"."ms_holdings" from "service_role";

revoke select on table "public"."ms_holdings" from "service_role";

revoke trigger on table "public"."ms_holdings" from "service_role";

revoke truncate on table "public"."ms_holdings" from "service_role";

revoke update on table "public"."ms_holdings" from "service_role";

revoke delete on table "public"."ms_portfolio_snapshots" from "anon";

revoke insert on table "public"."ms_portfolio_snapshots" from "anon";

revoke references on table "public"."ms_portfolio_snapshots" from "anon";

revoke select on table "public"."ms_portfolio_snapshots" from "anon";

revoke trigger on table "public"."ms_portfolio_snapshots" from "anon";

revoke truncate on table "public"."ms_portfolio_snapshots" from "anon";

revoke update on table "public"."ms_portfolio_snapshots" from "anon";

revoke delete on table "public"."ms_portfolio_snapshots" from "authenticated";

revoke insert on table "public"."ms_portfolio_snapshots" from "authenticated";

revoke references on table "public"."ms_portfolio_snapshots" from "authenticated";

revoke select on table "public"."ms_portfolio_snapshots" from "authenticated";

revoke trigger on table "public"."ms_portfolio_snapshots" from "authenticated";

revoke truncate on table "public"."ms_portfolio_snapshots" from "authenticated";

revoke update on table "public"."ms_portfolio_snapshots" from "authenticated";

revoke delete on table "public"."ms_portfolio_snapshots" from "service_role";

revoke insert on table "public"."ms_portfolio_snapshots" from "service_role";

revoke references on table "public"."ms_portfolio_snapshots" from "service_role";

revoke select on table "public"."ms_portfolio_snapshots" from "service_role";

revoke trigger on table "public"."ms_portfolio_snapshots" from "service_role";

revoke truncate on table "public"."ms_portfolio_snapshots" from "service_role";

revoke update on table "public"."ms_portfolio_snapshots" from "service_role";

revoke delete on table "public"."ms_profiles" from "anon";

revoke insert on table "public"."ms_profiles" from "anon";

revoke references on table "public"."ms_profiles" from "anon";

revoke select on table "public"."ms_profiles" from "anon";

revoke trigger on table "public"."ms_profiles" from "anon";

revoke truncate on table "public"."ms_profiles" from "anon";

revoke update on table "public"."ms_profiles" from "anon";

revoke delete on table "public"."ms_profiles" from "authenticated";

revoke insert on table "public"."ms_profiles" from "authenticated";

revoke references on table "public"."ms_profiles" from "authenticated";

revoke select on table "public"."ms_profiles" from "authenticated";

revoke trigger on table "public"."ms_profiles" from "authenticated";

revoke truncate on table "public"."ms_profiles" from "authenticated";

revoke update on table "public"."ms_profiles" from "authenticated";

revoke delete on table "public"."ms_profiles" from "service_role";

revoke insert on table "public"."ms_profiles" from "service_role";

revoke references on table "public"."ms_profiles" from "service_role";

revoke select on table "public"."ms_profiles" from "service_role";

revoke trigger on table "public"."ms_profiles" from "service_role";

revoke truncate on table "public"."ms_profiles" from "service_role";

revoke update on table "public"."ms_profiles" from "service_role";

revoke delete on table "public"."ms_watchlist" from "anon";

revoke insert on table "public"."ms_watchlist" from "anon";

revoke references on table "public"."ms_watchlist" from "anon";

revoke select on table "public"."ms_watchlist" from "anon";

revoke trigger on table "public"."ms_watchlist" from "anon";

revoke truncate on table "public"."ms_watchlist" from "anon";

revoke update on table "public"."ms_watchlist" from "anon";

revoke delete on table "public"."ms_watchlist" from "authenticated";

revoke insert on table "public"."ms_watchlist" from "authenticated";

revoke references on table "public"."ms_watchlist" from "authenticated";

revoke select on table "public"."ms_watchlist" from "authenticated";

revoke trigger on table "public"."ms_watchlist" from "authenticated";

revoke truncate on table "public"."ms_watchlist" from "authenticated";

revoke update on table "public"."ms_watchlist" from "authenticated";

revoke delete on table "public"."ms_watchlist" from "service_role";

revoke insert on table "public"."ms_watchlist" from "service_role";

revoke references on table "public"."ms_watchlist" from "service_role";

revoke select on table "public"."ms_watchlist" from "service_role";

revoke trigger on table "public"."ms_watchlist" from "service_role";

revoke truncate on table "public"."ms_watchlist" from "service_role";

revoke update on table "public"."ms_watchlist" from "service_role";

alter table "public"."ms_activity_log" drop constraint "ms_activity_log_user_id_activity_text_activity_time_key";

alter table "public"."ms_activity_log" drop constraint "ms_activity_log_user_id_fkey";

alter table "public"."ms_holdings" drop constraint "ms_holdings_price_check";

alter table "public"."ms_holdings" drop constraint "ms_holdings_quantity_check";

alter table "public"."ms_holdings" drop constraint "ms_holdings_user_id_fkey";

alter table "public"."ms_holdings" drop constraint "ms_holdings_user_id_symbol_key";

alter table "public"."ms_portfolio_snapshots" drop constraint "ms_portfolio_snapshots_user_id_as_of_date_key";

alter table "public"."ms_portfolio_snapshots" drop constraint "ms_portfolio_snapshots_user_id_fkey";

alter table "public"."ms_profiles" drop constraint "ms_profiles_auth_user_id_fkey";

alter table "public"."ms_profiles" drop constraint "ms_profiles_auth_user_id_key";

alter table "public"."ms_profiles" drop constraint "ms_profiles_email_key";

alter table "public"."ms_watchlist" drop constraint "ms_watchlist_price_check";

alter table "public"."ms_watchlist" drop constraint "ms_watchlist_user_id_fkey";

alter table "public"."ms_watchlist" drop constraint "ms_watchlist_user_id_symbol_key";

drop function if exists "public"."ms_get_portal_payload"(p_email text);

alter table "public"."Test Table" drop constraint "Test Table_pkey";

alter table "public"."ms_activity_log" drop constraint "ms_activity_log_pkey";

alter table "public"."ms_holdings" drop constraint "ms_holdings_pkey";

alter table "public"."ms_portfolio_snapshots" drop constraint "ms_portfolio_snapshots_pkey";

alter table "public"."ms_profiles" drop constraint "ms_profiles_pkey";

alter table "public"."ms_watchlist" drop constraint "ms_watchlist_pkey";

drop index if exists "public"."Test Table_pkey";

drop index if exists "public"."idx_ms_activity_user_time";

drop index if exists "public"."idx_ms_holdings_user";

drop index if exists "public"."idx_ms_snapshots_user_date";

drop index if exists "public"."idx_ms_watchlist_user";

drop index if exists "public"."ms_activity_log_pkey";

drop index if exists "public"."ms_activity_log_user_id_activity_text_activity_time_key";

drop index if exists "public"."ms_holdings_pkey";

drop index if exists "public"."ms_holdings_user_id_symbol_key";

drop index if exists "public"."ms_portfolio_snapshots_pkey";

drop index if exists "public"."ms_portfolio_snapshots_user_id_as_of_date_key";

drop index if exists "public"."ms_profiles_auth_user_id_key";

drop index if exists "public"."ms_profiles_email_key";

drop index if exists "public"."ms_profiles_pkey";

drop index if exists "public"."ms_watchlist_pkey";

drop index if exists "public"."ms_watchlist_user_id_symbol_key";

drop table "public"."Test Table";

drop table "public"."ms_activity_log";

drop table "public"."ms_holdings";

drop table "public"."ms_portfolio_snapshots";

drop table "public"."ms_profiles";

drop table "public"."ms_watchlist";

drop sequence if exists "public"."ms_activity_log_id_seq";

drop sequence if exists "public"."ms_holdings_id_seq";

drop sequence if exists "public"."ms_portfolio_snapshots_id_seq";

drop sequence if exists "public"."ms_watchlist_id_seq";


