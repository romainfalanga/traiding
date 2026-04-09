"use client";

import { classNames } from "@/lib/utils";

interface PostTradeCardProps {
  whatWorked: string | null;
  whatFailed: string | null;
  alternativeAction: string | null;
  recurringPattern: string | null;
}

interface SectionProps {
  title: string;
  content: string;
  borderColor: string;
  bgColor: string;
  textColor: string;
  dotColor: string;
}

function Section({
  title,
  content,
  borderColor,
  bgColor,
  textColor,
  dotColor,
}: SectionProps) {
  return (
    <div
      className={classNames(
        "rounded-lg border p-3",
        borderColor,
        bgColor
      )}
    >
      <div className="flex items-center gap-2">
        <div className={classNames("h-2 w-2 rounded-full", dotColor)} />
        <span
          className={classNames(
            "text-[10px] font-semibold uppercase tracking-wider",
            textColor
          )}
        >
          {title}
        </span>
      </div>
      <p className="mt-1.5 text-xs text-gray-300 leading-relaxed">{content}</p>
    </div>
  );
}

export default function PostTradeCard({
  whatWorked,
  whatFailed,
  alternativeAction,
  recurringPattern,
}: PostTradeCardProps) {
  const hasSomething =
    whatWorked || whatFailed || alternativeAction || recurringPattern;

  if (!hasSomething) return null;

  return (
    <div className="space-y-2">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">
        Post-Trade Analysis
      </span>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {whatWorked && (
          <Section
            title="What Worked"
            content={whatWorked}
            borderColor="border-green-500/20"
            bgColor="bg-green-500/5"
            textColor="text-green-400"
            dotColor="bg-green-400"
          />
        )}
        {whatFailed && (
          <Section
            title="What Failed"
            content={whatFailed}
            borderColor="border-red-500/20"
            bgColor="bg-red-500/5"
            textColor="text-red-400"
            dotColor="bg-red-400"
          />
        )}
        {alternativeAction && (
          <Section
            title="Alternative Action"
            content={alternativeAction}
            borderColor="border-blue-500/20"
            bgColor="bg-blue-500/5"
            textColor="text-blue-400"
            dotColor="bg-blue-400"
          />
        )}
        {recurringPattern && (
          <Section
            title="Recurring Pattern"
            content={recurringPattern}
            borderColor="border-yellow-500/20"
            bgColor="bg-yellow-500/5"
            textColor="text-yellow-400"
            dotColor="bg-yellow-400"
          />
        )}
      </div>
    </div>
  );
}
