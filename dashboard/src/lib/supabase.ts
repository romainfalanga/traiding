import { createBrowserClient } from "@supabase/ssr";
import { RealtimeChannel } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createBrowserClient(supabaseUrl, supabaseAnonKey);

export type RealtimeCallback<T> = (payload: {
  eventType: "INSERT" | "UPDATE" | "DELETE";
  new: T;
  old: T;
}) => void;

/**
 * Subscribe to realtime changes on a Supabase table.
 * Returns the channel so callers can unsubscribe when done.
 */
export function subscribeToTable<T extends Record<string, unknown>>(
  table: string,
  callback: RealtimeCallback<T>,
  filter?: string
): RealtimeChannel {
  let channel = supabase
    .channel(`realtime:${table}`)
    .on<T>(
      "postgres_changes" as any,
      {
        event: "*",
        schema: "public",
        table,
        ...(filter ? { filter } : {}),
      },
      (payload: any) => {
        callback({
          eventType: payload.eventType,
          new: payload.new as T,
          old: payload.old as T,
        });
      }
    )
    .subscribe();

  return channel;
}

/**
 * Unsubscribe from a realtime channel.
 */
export function unsubscribe(channel: RealtimeChannel): void {
  supabase.removeChannel(channel);
}
