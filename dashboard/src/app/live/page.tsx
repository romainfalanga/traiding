"use client";

import EventFeed from "@/components/live/EventFeed";
import MultiAgentView from "@/components/live/MultiAgentView";
import ConsensusResult from "@/components/live/ConsensusResult";
import TechnicalSummary from "@/components/live/TechnicalSummary";
import LivePnL from "@/components/live/LivePnL";

export default function LivePage() {
  return (
    <div className="mx-auto max-w-screen-2xl space-y-6">
      <h1 className="text-2xl font-bold text-white">Live</h1>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left Column: Event Feed */}
        <div className="lg:col-span-1">
          <div className="sticky top-20 h-[calc(100vh-10rem)]">
            <EventFeed />
          </div>
        </div>

        {/* Right Column: Agent Views + Consensus + Technical + PnL */}
        <div className="space-y-6 lg:col-span-2">
          <MultiAgentView />
          <ConsensusResult />
          <TechnicalSummary />
        </div>
      </div>

      {/* Bottom Bar: Live PnL */}
      <LivePnL />
    </div>
  );
}
