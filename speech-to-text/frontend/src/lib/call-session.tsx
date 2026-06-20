/**
 * Call session store — persists call data across page navigation.
 *
 * The live call page populates this store when the call ends.
 * The post-call page reads from it to request AI analysis.
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Concept, TranscriptLine } from "./use-pipeline";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type CustomerProfile = {
  name: string;
  risk_appetite: "conservative" | "moderate" | "aggressive";
  investment_horizon: string;
  esg_preference: string;
  preferred_sectors: string;
  total_aum: number;
  kyc_status: string;
  onboarding_date: string;
};

export type PostCallAnalysis = {
  summary: string;
  tags: string[];
  sentiment: {
    overall_score: number;
    overall_label: string;
    bands: Array<{
      from_percent: number;
      to_percent: number;
      tone: "positive" | "neutral" | "concerned";
    }>;
    peaks: Array<{
      at_percent: number;
      label: string;
      tone: "positive" | "neutral" | "concerned";
    }>;
  };
  emotional_topics: Array<{
    emotion: "fear" | "joy" | "concern" | "confidence" | "frustration";
    topic: string;
    quote: string;
    explanation: string;
  }>;
  risk_tolerance: {
    known_profile: "conservative" | "moderate" | "aggressive";
    detected_appetite: "conservative" | "moderate" | "aggressive";
    shift_detected: boolean;
    evidence: string[];
    comparison_notes: string;
  };
  action_items: Array<{
    priority: "HIGH" | "MED" | "LOW";
    text: string;
    due_suggestion: string;
  }>;
};

export type CallSessionData = {
  transcriptLines: TranscriptLine[];
  concepts: Concept[];
  customerProfile: CustomerProfile | null;
  callDurationSeconds: number;
  clientName: string;
};

type CallSessionState = {
  /** The saved call data (null if no call has been saved yet) */
  sessionData: CallSessionData | null;
  /** Save call data when call ends */
  saveSession: (data: CallSessionData) => void;
  /** Clear session (e.g. when starting a new call) */
  clearSession: () => void;
};

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const CallSessionContext = createContext<CallSessionState | null>(null);

export function CallSessionProvider({ children }: { children: ReactNode }) {
  const [sessionData, setSessionData] = useState<CallSessionData | null>(null);

  const saveSession = useCallback((data: CallSessionData) => {
    setSessionData(data);
  }, []);

  const clearSession = useCallback(() => {
    setSessionData(null);
  }, []);

  const value = useMemo<CallSessionState>(
    () => ({ sessionData, saveSession, clearSession }),
    [sessionData, saveSession, clearSession],
  );

  return (
    <CallSessionContext.Provider value={value}>
      {children}
    </CallSessionContext.Provider>
  );
}

export function useCallSession() {
  const ctx = useContext(CallSessionContext);
  if (!ctx) throw new Error("useCallSession must be used within CallSessionProvider");
  return ctx;
}

// ---------------------------------------------------------------------------
// API helper — calls the backend post-call analysis endpoint
// ---------------------------------------------------------------------------

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchPostCallAnalysis(
  session: CallSessionData,
): Promise<PostCallAnalysis> {
  const body = {
    transcript_lines: session.transcriptLines.map((l) => ({
      text: l.text,
      speaker: l.speaker,
      timestamp: l.timestamp,
    })),
    concepts: session.concepts.map((c) => ({
      index: c.index,
      topic: c.topic,
      intent: c.intent,
      entities: c.entities,
      text: c.text,
      data_requests: c.data_requests,
      executed_queries: c.executed_queries,
    })),
    customer_profile: session.customerProfile,
  };

  const res = await fetch(`${API_BASE}/api/post-call-analysis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  const data = await res.json();
  if (data.status === "error") {
    throw new Error(data.message || "Analysis generation failed");
  }

  return data.analysis as PostCallAnalysis;
}

export async function fetchCustomerProfile(): Promise<CustomerProfile> {
  const res = await fetch(`${API_BASE}/api/customer-profile`);
  if (!res.ok) throw new Error(`Failed to fetch profile: ${res.status}`);
  const data = await res.json();
  if (data.status === "error") throw new Error(data.message);
  return data.profile as CustomerProfile;
}
