"use client";

/**
 * Admin API client for DeerFlow admin dashboard.
 * Provides typed fetch helpers for user CRUD, run monitoring, and system stats.
 */

import { fetch } from "@/core/api/fetcher";

const API_BASE = "/api/v1/admin";

// ============================================================================
// Types
// ============================================================================

export interface User {
  id: string;
  email: string;
  system_role: "admin" | "user";
  created_at: string;
  oauth_provider: string | null;
  token_version: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateUserRequest {
  email: string;
  password: string;
}

export interface UpdateUserRequest {
  email?: string;
  system_role?: "admin" | "user";
}

export interface ResetPasswordRequest {
  new_password: string;
}

export interface SystemStats {
  total_users: number;
  total_runs: number;
  total_threads: number;
  total_feedback: number;
  database_backend: string;
  models: string[];
}

export interface FeedbackStats {
  total: number;
  positive: number;
  negative: number;
  positive_rate: number;
}

export interface Run {
  run_id: string;
  thread_id: string;
  assistant_id: string;
  user_id: string;
  status: string;
  model_name: string;
  message_count: number;
  total_tokens: number;
  llm_call_count: number;
  first_human_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Thread {
  thread_id: string;
  assistant_id: string;
  user_id: string;
  display_name: string;
  status: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Users API
// ============================================================================

export async function listUsers(
  page = 1,
  pageSize = 20,
  search?: string,
): Promise<PaginatedResponse<User>> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (search) params.set("search", search);
  const res = await fetch(`${API_BASE}/users?${params}`);
  return res.json();
}

export async function createUser(data: CreateUserRequest): Promise<User> {
  const res = await fetch(`${API_BASE}/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function updateUser(
  userId: string,
  data: UpdateUserRequest,
): Promise<User> {
  const res = await fetch(`${API_BASE}/users/${userId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function deleteUser(userId: string): Promise<void> {
  await fetch(`${API_BASE}/users/${userId}`, { method: "DELETE" });
}

export async function resetUserPassword(
  userId: string,
  data: ResetPasswordRequest,
): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/users/${userId}/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

// ============================================================================
// Runs API
// ============================================================================

export async function listRuns(
  page = 1,
  pageSize = 20,
  status?: string,
  userId?: string,
): Promise<PaginatedResponse<Run>> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (status) params.set("status", status);
  if (userId) params.set("user_id", userId);
  const res = await fetch(`${API_BASE}/runs?${params}`);
  return res.json();
}

// ============================================================================
// Threads API
// ============================================================================

export async function listThreads(
  page = 1,
  pageSize = 20,
  userId?: string,
): Promise<PaginatedResponse<Thread>> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (userId) params.set("user_id", userId);
  const res = await fetch(`${API_BASE}/threads?${params}`);
  return res.json();
}

// ============================================================================
// Stats API
// ============================================================================

export async function getSystemStats(): Promise<SystemStats> {
  const res = await fetch(`${API_BASE}/stats`);
  return res.json();
}

export async function getFeedbackStats(): Promise<FeedbackStats> {
  const res = await fetch(`${API_BASE}/feedback-stats`);
  return res.json();
}
