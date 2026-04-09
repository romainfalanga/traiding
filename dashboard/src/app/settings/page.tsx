"use client";

import SettingsForm from "@/components/settings/SettingsForm";

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-screen-2xl space-y-6">
      <h1 className="text-2xl font-bold text-white">Settings</h1>
      <SettingsForm />
    </div>
  );
}
