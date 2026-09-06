import { apiClient } from "../client";
import type { LoginResponse, UserProfile } from "../../types/api";

export interface RegisterPayload {
  email: string;
  password: string;
  phone_number?: string;
  referral_code?: string;
  turnstile_token?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export async function register(payload: RegisterPayload): Promise<UserProfile> {
  const { data } = await apiClient.post<UserProfile>("/auth/register/", payload);
  return data;
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>("/auth/login/", payload);
  return data;
}

export async function logout(refresh: string): Promise<void> {
  await apiClient.post("/auth/logout/", { refresh });
}

export async function fetchMe(): Promise<UserProfile> {
  const { data } = await apiClient.get<UserProfile>("/auth/me/");
  return data;
}

export async function fetchApiKey(): Promise<string> {
  const { data } = await apiClient.get<{ api_key: string }>("/auth/api-key/");
  return data.api_key;
}

export async function regenerateApiKey(): Promise<string> {
  const { data } = await apiClient.post<{ api_key: string }>("/auth/api-key/regenerate/");
  return data.api_key;
}

export async function verifyEmail(token: string): Promise<void> {
  await apiClient.post("/auth/verify-email/", { token });
}

export async function resendVerificationEmail(): Promise<void> {
  await apiClient.post("/auth/resend-verification-email/");
}

export async function googleAuth(idToken: string, referralCode?: string): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>("/auth/google/", {
    id_token: idToken,
    referral_code: referralCode,
  });
  return data;
}

export async function sendPhoneOtp(phoneNumber?: string): Promise<{ detail: string }> {
  const { data } = await apiClient.post("/auth/phone/send-otp/", { phone_number: phoneNumber });
  return data;
}

export async function verifyPhoneOtp(code: string): Promise<{ detail: string }> {
  const { data } = await apiClient.post("/auth/phone/verify-otp/", { code });
  return data;
}

export async function requestPasswordReset(email: string): Promise<{ detail: string }> {
  const { data } = await apiClient.post("/auth/password-reset/", { email });
  return data;
}

export async function confirmPasswordReset(payload: {
  uid: string;
  token: string;
  new_password: string;
}): Promise<{ detail: string }> {
  const { data } = await apiClient.post("/auth/password-reset/confirm/", payload);
  return data;
}



