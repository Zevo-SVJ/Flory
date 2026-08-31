/**
 * Supabase schema types.
 *
 * Hand-written to match `supabase/migrations/`. Once you have a project linked
 * you can regenerate these with:
 *   npx supabase gen types typescript --linked > types/database.ts
 */

import type { AnalysisResult } from '@/lib/analysis/types'

export type Json = string | number | boolean | null | { [key: string]: Json } | Json[]

export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string
          email: string | null
          full_name: string | null
          avatar_url: string | null
          onboarding_completed_at: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id: string
          email?: string | null
          full_name?: string | null
          avatar_url?: string | null
          onboarding_completed_at?: string | null
        }
        Update: {
          email?: string | null
          full_name?: string | null
          avatar_url?: string | null
          onboarding_completed_at?: string | null
        }
        Relationships: []
      }
      user_preferences: {
        Row: {
          user_id: string
          spend_categories: string[]
          buying_priorities: string[]
          currency: string
          created_at: string
          updated_at: string
        }
        Insert: {
          user_id: string
          spend_categories?: string[]
          buying_priorities?: string[]
          currency?: string
        }
        Update: {
          spend_categories?: string[]
          buying_priorities?: string[]
          currency?: string
        }
        Relationships: []
      }
      analyses: {
        Row: {
          id: string
          user_id: string
          input_type: string
          input_url: string | null
          input_storage_path: string | null
          category: string | null
          title: string | null
          status: string
          score: number | null
          verdict: string | null
          summary: string | null
          currency: string
          price_minor: number | null
          best_price_minor: number | null
          result: AnalysisResult | null
          engine: string | null
          is_fixture: boolean
          share_slug: string | null
          shared_at: string | null
          error_message: string | null
          created_at: string
          completed_at: string | null
        }
        Insert: {
          user_id: string
          input_type: string
          input_url?: string | null
          input_storage_path?: string | null
          category?: string | null
          status?: string
        }
        Update: {
          category?: string | null
          title?: string | null
          status?: string
          score?: number | null
          verdict?: string | null
          summary?: string | null
          currency?: string
          price_minor?: number | null
          best_price_minor?: number | null
          result?: AnalysisResult | null
          engine?: string | null
          is_fixture?: boolean
          share_slug?: string | null
          shared_at?: string | null
          error_message?: string | null
          completed_at?: string | null
        }
        Relationships: []
      }
    }
    Views: Record<never, never>
    Functions: {
      get_public_analysis: {
        Args: { slug: string }
        Returns: {
          share_slug: string
          title: string | null
          score: number | null
          verdict: string | null
          summary: string | null
          currency: string
          price_minor: number | null
          best_price_minor: number | null
          signals: Json
          is_fixture: boolean
        }[]
      }
    }
    Enums: Record<never, never>
  }
}
