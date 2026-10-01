export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      admin_audit_log: {
        Row: {
          action: string
          admin_id: string
          created_at: string | null
          id: string
          metadata: Json | null
          target_id: string | null
          target_type: string | null
        }
        Insert: {
          action: string
          admin_id: string
          created_at?: string | null
          id?: string
          metadata?: Json | null
          target_id?: string | null
          target_type?: string | null
        }
        Update: {
          action?: string
          admin_id?: string
          created_at?: string | null
          id?: string
          metadata?: Json | null
          target_id?: string | null
          target_type?: string | null
        }
        Relationships: []
      }
      brews: {
        Row: {
          abv: number | null
          completed_at: string | null
          created_at: string | null
          fg: number | null
          id: string
          name: string
          notes: string | null
          og: number | null
          recipe_id: string | null
          sg: number | null
          started_at: string | null
          status: string
          type: string
          updated_at: string | null
          user_id: string
          volume: number | null
          volume_unit: string | null
          yeast: string | null
        }
        Insert: {
          abv?: number | null
          completed_at?: string | null
          created_at?: string | null
          fg?: number | null
          id?: string
          name: string
          notes?: string | null
          og?: number | null
          recipe_id?: string | null
          sg?: number | null
          started_at?: string | null
          status?: string
          type: string
          updated_at?: string | null
          user_id: string
          volume?: number | null
          volume_unit?: string | null
          yeast?: string | null
        }
        Update: {
          abv?: number | null
          completed_at?: string | null
          created_at?: string | null
          fg?: number | null
          id?: string
          name?: string
          notes?: string | null
          og?: number | null
          recipe_id?: string | null
          sg?: number | null
          started_at?: string | null
          status?: string
          type?: string
          updated_at?: string | null
          user_id?: string
          volume?: number | null
          volume_unit?: string | null
          yeast?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "brews_recipe_id_fkey"
            columns: ["recipe_id"]
            isOneToOne: false
            referencedRelation: "recipes"
            referencedColumns: ["id"]
          },
        ]
      }
      checkpoints: {
        Row: {
          brew_id: string
          completed_at: string | null
          created_at: string | null
          description: string | null
          duration_hours: number | null
          id: string
          is_safety: boolean | null
          name: string
          order_num: number
          scheduled_at: string | null
          state: string
          user_id: string
        }
        Insert: {
          brew_id: string
          completed_at?: string | null
          created_at?: string | null
          description?: string | null
          duration_hours?: number | null
          id?: string
          is_safety?: boolean | null
          name: string
          order_num?: number
          scheduled_at?: string | null
          state?: string
          user_id: string
        }
        Update: {
          brew_id?: string
          completed_at?: string | null
          created_at?: string | null
          description?: string | null
          duration_hours?: number | null
          id?: string
          is_safety?: boolean | null
          name?: string
          order_num?: number
          scheduled_at?: string | null
          state?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "checkpoints_brew_id_fkey"
            columns: ["brew_id"]
            isOneToOne: false
            referencedRelation: "brews"
            referencedColumns: ["id"]
          },
        ]
      }
      content_reports: {
        Row: {
          admin_note: string | null
          created_at: string | null
          id: string
          reason: string
          reporter_id: string
          reviewed_by: string | null
          status: string
          target_id: string
          target_type: string
          updated_at: string | null
        }
        Insert: {
          admin_note?: string | null
          created_at?: string | null
          id?: string
          reason: string
          reporter_id: string
          reviewed_by?: string | null
          status?: string
          target_id: string
          target_type: string
          updated_at?: string | null
        }
        Update: {
          admin_note?: string | null
          created_at?: string | null
          id?: string
          reason?: string
          reporter_id?: string
          reviewed_by?: string | null
          status?: string
          target_id?: string
          target_type?: string
          updated_at?: string | null
        }
        Relationships: []
      }
      forum_channels: {
        Row: {
          created_at: string | null
          description: string | null
          icon: string | null
          id: string
          is_locked: boolean | null
          name: string
          slug: string
          sort_order: number | null
        }
        Insert: {
          created_at?: string | null
          description?: string | null
          icon?: string | null
          id?: string
          is_locked?: boolean | null
          name: string
          slug: string
          sort_order?: number | null
        }
        Update: {
          created_at?: string | null
          description?: string | null
          icon?: string | null
          id?: string
          is_locked?: boolean | null
          name?: string
          slug?: string
          sort_order?: number | null
        }
        Relationships: []
      }
      forum_posts: {
        Row: {
          content: string
          created_at: string | null
          id: string
          is_solution: boolean | null
          thread_id: string
          updated_at: string | null
          user_id: string
        }
        Insert: {
          content: string
          created_at?: string | null
          id?: string
          is_solution?: boolean | null
          thread_id: string
          updated_at?: string | null
          user_id: string
        }
        Update: {
          content?: string
          created_at?: string | null
          id?: string
          is_solution?: boolean | null
          thread_id?: string
          updated_at?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "forum_posts_thread_id_fkey"
            columns: ["thread_id"]
            isOneToOne: false
            referencedRelation: "forum_threads"
            referencedColumns: ["id"]
          },
        ]
      }
      forum_threads: {
        Row: {
          brew_id: string | null
          channel_id: string
          checkpoint_id: string | null
          created_at: string | null
          first_post_content: string | null
          id: string
          is_locked: boolean | null
          is_pinned: boolean | null
          is_resolved: boolean | null
          last_post_at: string | null
          linked_recipe_id: string | null
          reply_count: number | null
          title: string
          updated_at: string | null
          user_id: string
          view_count: number | null
        }
        Insert: {
          brew_id?: string | null
          channel_id: string
          checkpoint_id?: string | null
          created_at?: string | null
          first_post_content?: string | null
          id?: string
          is_locked?: boolean | null
          is_pinned?: boolean | null
          is_resolved?: boolean | null
          last_post_at?: string | null
          linked_recipe_id?: string | null
          reply_count?: number | null
          title: string
          updated_at?: string | null
          user_id: string
          view_count?: number | null
        }
        Update: {
          brew_id?: string | null
          channel_id?: string
          checkpoint_id?: string | null
          created_at?: string | null
          first_post_content?: string | null
          id?: string
          is_locked?: boolean | null
          is_pinned?: boolean | null
          is_resolved?: boolean | null
          last_post_at?: string | null
          linked_recipe_id?: string | null
          reply_count?: number | null
          title?: string
          updated_at?: string | null
          user_id?: string
          view_count?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "forum_threads_brew_id_fkey"
            columns: ["brew_id"]
            isOneToOne: false
            referencedRelation: "brews"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "forum_threads_channel_id_fkey"
            columns: ["channel_id"]
            isOneToOne: false
            referencedRelation: "forum_channels"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "forum_threads_checkpoint_id_fkey"
            columns: ["checkpoint_id"]
            isOneToOne: false
            referencedRelation: "checkpoints"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "forum_threads_linked_recipe_id_fkey"
            columns: ["linked_recipe_id"]
            isOneToOne: false
            referencedRelation: "recipes"
            referencedColumns: ["id"]
          },
        ]
      }
      gravity_logs: {
        Row: {
          brew_id: string
          gravity: number
          id: string
          logged_at: string | null
          notes: string | null
          temp_unit: string | null
          temperature: number | null
          user_id: string
        }
        Insert: {
          brew_id: string
          gravity: number
          id?: string
          logged_at?: string | null
          notes?: string | null
          temp_unit?: string | null
          temperature?: number | null
          user_id: string
        }
        Update: {
          brew_id?: string
          gravity?: number
          id?: string
          logged_at?: string | null
          notes?: string | null
          temp_unit?: string | null
          temperature?: number | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "gravity_logs_brew_id_fkey"
            columns: ["brew_id"]
            isOneToOne: false
            referencedRelation: "brews"
            referencedColumns: ["id"]
          },
        ]
      }
      notebook_cells: {
        Row: {
          content: string
          created_at: string | null
          id: string
          kind: string
          metadata: Json | null
          order_num: number
          session_id: string
          user_id: string
        }
        Insert: {
          content?: string
          created_at?: string | null
          id?: string
          kind: string
          metadata?: Json | null
          order_num?: number
          session_id: string
          user_id: string
        }
        Update: {
          content?: string
          created_at?: string | null
          id?: string
          kind?: string
          metadata?: Json | null
          order_num?: number
          session_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "notebook_cells_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "notebook_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      notebook_sessions: {
        Row: {
          brew_id: string | null
          created_at: string | null
          id: string
          title: string
          updated_at: string | null
          user_id: string
        }
        Insert: {
          brew_id?: string | null
          created_at?: string | null
          id?: string
          title?: string
          updated_at?: string | null
          user_id: string
        }
        Update: {
          brew_id?: string | null
          created_at?: string | null
          id?: string
          title?: string
          updated_at?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "notebook_sessions_brew_id_fkey"
            columns: ["brew_id"]
            isOneToOne: false
            referencedRelation: "brews"
            referencedColumns: ["id"]
          },
        ]
      }
      notifications: {
        Row: {
          body: string | null
          brew_id: string | null
          checkpoint_id: string | null
          created_at: string | null
          id: string
          is_read: boolean | null
          link_id: string | null
          link_type: string | null
          title: string
          type: string
          user_id: string
        }
        Insert: {
          body?: string | null
          brew_id?: string | null
          checkpoint_id?: string | null
          created_at?: string | null
          id?: string
          is_read?: boolean | null
          link_id?: string | null
          link_type?: string | null
          title: string
          type: string
          user_id: string
        }
        Update: {
          body?: string | null
          brew_id?: string | null
          checkpoint_id?: string | null
          created_at?: string | null
          id?: string
          is_read?: boolean | null
          link_id?: string | null
          link_type?: string | null
          title?: string
          type?: string
          user_id?: string
        }
        Relationships: []
      }
      post_reactions: {
        Row: {
          created_at: string | null
          id: string
          post_id: string
          type: string
          user_id: string
        }
        Insert: {
          created_at?: string | null
          id?: string
          post_id: string
          type: string
          user_id: string
        }
        Update: {
          created_at?: string | null
          id?: string
          post_id?: string
          type?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "post_reactions_post_id_fkey"
            columns: ["post_id"]
            isOneToOne: false
            referencedRelation: "forum_posts"
            referencedColumns: ["id"]
          },
        ]
      }
      profiles: {
        Row: {
          avatar_url: string | null
          ban_reason: string | null
          banned_until: string | null
          bio: string | null
          created_at: string | null
          display_name: string | null
          id: string
          is_admin: boolean | null
          is_banned: boolean | null
          location: string | null
          plan: string
          plan_expires_at: string | null
          role: string | null
          settings: Json | null
          signature: string | null
          stripe_customer_id: string | null
          stripe_subscription_id: string | null
          subscription_status: string
          username: string
        }
        Insert: {
          avatar_url?: string | null
          ban_reason?: string | null
          banned_until?: string | null
          bio?: string | null
          created_at?: string | null
          display_name?: string | null
          id: string
          is_admin?: boolean | null
          is_banned?: boolean | null
          location?: string | null
          plan?: string
          plan_expires_at?: string | null
          role?: string | null
          settings?: Json | null
          signature?: string | null
          stripe_customer_id?: string | null
          stripe_subscription_id?: string | null
          subscription_status?: string
          username: string
        }
        Update: {
          avatar_url?: string | null
          ban_reason?: string | null
          banned_until?: string | null
          bio?: string | null
          created_at?: string | null
          display_name?: string | null
          id?: string
          is_admin?: boolean | null
          is_banned?: boolean | null
          location?: string | null
          plan?: string
          plan_expires_at?: string | null
          role?: string | null
          settings?: Json | null
          signature?: string | null
          stripe_customer_id?: string | null
          stripe_subscription_id?: string | null
          subscription_status?: string
          username?: string
        }
        Relationships: []
      }
      recipe_likes: {
        Row: {
          created_at: string | null
          id: string
          recipe_id: string
          type: string
          user_id: string
        }
        Insert: {
          created_at?: string | null
          id?: string
          recipe_id: string
          type?: string
          user_id: string
        }
        Update: {
          created_at?: string | null
          id?: string
          recipe_id?: string
          type?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "recipe_likes_recipe_id_fkey"
            columns: ["recipe_id"]
            isOneToOne: false
            referencedRelation: "recipes"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "recipe_likes_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      recipes: {
        Row: {
          attributed_to_username: string | null
          created_at: string | null
          description: string | null
          difficulty: string
          forked_from: string | null
          id: string
          ingredients: Json | null
          is_featured: boolean | null
          is_public: boolean | null
          name: string
          source: string | null
          steps: Json | null
          tags: string[] | null
          target_abv: number | null
          target_fg: number | null
          target_og: number | null
          time_days: number
          type: string
          updated_at: string | null
          user_id: string
          yeast: string | null
          yield_amount: number | null
          yield_unit: string | null
        }
        Insert: {
          attributed_to_username?: string | null
          created_at?: string | null
          description?: string | null
          difficulty?: string
          forked_from?: string | null
          id?: string
          ingredients?: Json | null
          is_featured?: boolean | null
          is_public?: boolean | null
          name: string
          source?: string | null
          steps?: Json | null
          tags?: string[] | null
          target_abv?: number | null
          target_fg?: number | null
          target_og?: number | null
          time_days?: number
          type: string
          updated_at?: string | null
          user_id: string
          yeast?: string | null
          yield_amount?: number | null
          yield_unit?: string | null
        }
        Update: {
          attributed_to_username?: string | null
          created_at?: string | null
          description?: string | null
          difficulty?: string
          forked_from?: string | null
          id?: string
          ingredients?: Json | null
          is_featured?: boolean | null
          is_public?: boolean | null
          name?: string
          source?: string | null
          steps?: Json | null
          tags?: string[] | null
          target_abv?: number | null
          target_fg?: number | null
          target_og?: number | null
          time_days?: number
          type?: string
          updated_at?: string | null
          user_id?: string
          yeast?: string | null
          yield_amount?: number | null
          yield_unit?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "recipes_forked_from_fkey"
            columns: ["forked_from"]
            isOneToOne: false
            referencedRelation: "recipes"
            referencedColumns: ["id"]
          },
        ]
      }
      resource_locations: {
        Row: {
          address: string | null
          category: string
          city: string | null
          country: string | null
          created_at: string | null
          description: string | null
          id: string
          is_online: boolean | null
          is_verified: boolean | null
          lat: number | null
          lng: number | null
          name: string
          phone: string | null
          state: string | null
          tags: string[] | null
          updated_at: string | null
          website: string | null
          zip: string | null
        }
        Insert: {
          address?: string | null
          category?: string
          city?: string | null
          country?: string | null
          created_at?: string | null
          description?: string | null
          id?: string
          is_online?: boolean | null
          is_verified?: boolean | null
          lat?: number | null
          lng?: number | null
          name: string
          phone?: string | null
          state?: string | null
          tags?: string[] | null
          updated_at?: string | null
          website?: string | null
          zip?: string | null
        }
        Update: {
          address?: string | null
          category?: string
          city?: string | null
          country?: string | null
          created_at?: string | null
          description?: string | null
          id?: string
          is_online?: boolean | null
          is_verified?: boolean | null
          lat?: number | null
          lng?: number | null
          name?: string
          phone?: string | null
          state?: string | null
          tags?: string[] | null
          updated_at?: string | null
          website?: string | null
          zip?: string | null
        }
        Relationships: []
      }
      safety_acks: {
        Row: {
          acknowledged_at: string | null
          alert_id: string
          id: string
          user_id: string
        }
        Insert: {
          acknowledged_at?: string | null
          alert_id: string
          id?: string
          user_id: string
        }
        Update: {
          acknowledged_at?: string | null
          alert_id?: string
          id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "safety_acks_alert_id_fkey"
            columns: ["alert_id"]
            isOneToOne: false
            referencedRelation: "safety_alerts"
            referencedColumns: ["id"]
          },
        ]
      }
      safety_alerts: {
        Row: {
          code: string
          created_at: string | null
          description: string
          id: string
          level: number
          name: string
          tag: string
          when_applicable: string
        }
        Insert: {
          code: string
          created_at?: string | null
          description: string
          id?: string
          level: number
          name: string
          tag: string
          when_applicable: string
        }
        Update: {
          code?: string
          created_at?: string | null
          description?: string
          id?: string
          level?: number
          name?: string
          tag?: string
          when_applicable?: string
        }
        Relationships: []
      }
      site_config: {
        Row: {
          key: string
          updated_at: string | null
          updated_by: string | null
          value: Json
        }
        Insert: {
          key: string
          updated_at?: string | null
          updated_by?: string | null
          value?: Json
        }
        Update: {
          key?: string
          updated_at?: string | null
          updated_by?: string | null
          value?: Json
        }
        Relationships: []
      }
      support_tickets: {
        Row: {
          assigned_to: string | null
          created_at: string | null
          description: string
          id: string
          priority: string | null
          status: string | null
          subject: string
          updated_at: string | null
          user_id: string
        }
        Insert: {
          assigned_to?: string | null
          created_at?: string | null
          description: string
          id?: string
          priority?: string | null
          status?: string | null
          subject: string
          updated_at?: string | null
          user_id: string
        }
        Update: {
          assigned_to?: string | null
          created_at?: string | null
          description?: string
          id?: string
          priority?: string | null
          status?: string | null
          subject?: string
          updated_at?: string | null
          user_id?: string
        }
        Relationships: []
      }
      themes: {
        Row: {
          created_at: string | null
          id: string
          is_active: boolean | null
          name: string
          tokens: Json
          updated_at: string | null
          user_id: string
        }
        Insert: {
          created_at?: string | null
          id?: string
          is_active?: boolean | null
          name: string
          tokens: Json
          updated_at?: string | null
          user_id: string
        }
        Update: {
          created_at?: string | null
          id?: string
          is_active?: boolean | null
          name?: string
          tokens?: Json
          updated_at?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "themes_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      thread_reads: {
        Row: {
          last_read_at: string | null
          thread_id: string
          user_id: string
        }
        Insert: {
          last_read_at?: string | null
          thread_id: string
          user_id: string
        }
        Update: {
          last_read_at?: string | null
          thread_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "thread_reads_thread_id_fkey"
            columns: ["thread_id"]
            isOneToOne: false
            referencedRelation: "forum_threads"
            referencedColumns: ["id"]
          },
        ]
      }
      thread_subscriptions: {
        Row: {
          created_at: string
          thread_id: string
          user_id: string
        }
        Insert: {
          created_at?: string
          thread_id: string
          user_id: string
        }
        Update: {
          created_at?: string
          thread_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "thread_subscriptions_thread_id_fkey"
            columns: ["thread_id"]
            isOneToOne: false
            referencedRelation: "forum_threads"
            referencedColumns: ["id"]
          },
        ]
      }
      ticket_messages: {
        Row: {
          content: string
          created_at: string | null
          id: string
          is_staff: boolean | null
          ticket_id: string
          user_id: string
        }
        Insert: {
          content: string
          created_at?: string | null
          id?: string
          is_staff?: boolean | null
          ticket_id: string
          user_id: string
        }
        Update: {
          content?: string
          created_at?: string | null
          id?: string
          is_staff?: boolean | null
          ticket_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "ticket_messages_ticket_id_fkey"
            columns: ["ticket_id"]
            isOneToOne: false
            referencedRelation: "support_tickets"
            referencedColumns: ["id"]
          },
        ]
      }
      user_badges: {
        Row: {
          badge_type: string
          earned_at: string | null
          id: string
          user_id: string
        }
        Insert: {
          badge_type: string
          earned_at?: string | null
          id?: string
          user_id: string
        }
        Update: {
          badge_type?: string
          earned_at?: string | null
          id?: string
          user_id?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      admin_ai_overview: { Args: never; Returns: Json }
      get_user_reputation: { Args: { p_user_id: string }; Returns: number }
      is_admin: { Args: never; Returns: boolean }
      search_nearby_shops: {
        Args: {
          p_category?: string
          p_lat: number
          p_lng: number
          p_radius_mi?: number
        }
        Returns: {
          address: string
          category: string
          city: string
          description: string
          distance_miles: number
          id: string
          is_online: boolean
          is_verified: boolean
          name: string
          phone: string
          state: string
          tags: string[]
          website: string
          zip: string
        }[]
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends (DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never) = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends (PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never) = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
