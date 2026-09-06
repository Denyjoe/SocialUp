export interface AffiliateSummary {
  referral_code: string;
  commission_percent: string;
  total_referrals: number;
  total_commission_earned: string;
}

export interface Referral {
  id: number;
  email: string;
  date_joined: string;
  orders_count: number;
  commission_earned: string;
}
