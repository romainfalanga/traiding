"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { classNames } from "@/lib/utils";

type ConnectionStatus = "connected" | "disconnected" | "connecting";

export default function Footer() {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");

  useEffect(() => {
    // Check Supabase connection by pinging a lightweight query
    const checkConnection = async () => {
      try {
        const { error } = await supabase
          .from("portfolio")
          .select("id")
          .limit(1);
        setStatus(error ? "disconnected" : "connected");
      } catch {
        setStatus("disconnected");
      }
    };

    checkConnection();

    // Re-check periodically
    const interval = setInterval(checkConnection, 30_000);
    return () => clearInterval(interval);
  }, []);

  const statusColor: Record<ConnectionStatus, string> = {
    connected: "bg-green-400",
    disconnected: "bg-red-400",
    connecting: "bg-yellow-400 animate-pulse-dot",
  };

  const statusLabel: Record<ConnectionStatus, string> = {
    connected: "Connected",
    disconnected: "Disconnected",
    connecting: "Connecting...",
  };

  return (
    <footer className="border-t border-gray-800 bg-gray-950/80 px-4 py-3 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-screen-2xl items-center justify-between text-xs text-gray-500">
        <span>Macro Pulse v1.0 &mdash; Paper Trading</span>

        <div className="flex items-center gap-2">
          <div
            className={classNames(
              "h-2 w-2 rounded-full",
              statusColor[status]
            )}
          />
          <span>{statusLabel[status]}</span>
        </div>
      </div>
    </footer>
  );
}
