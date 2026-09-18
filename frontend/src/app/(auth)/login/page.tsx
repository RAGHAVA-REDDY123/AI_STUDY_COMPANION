"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Brain, Lock, Mail, User as UserIcon, ArrowRight, AlertCircle } from "lucide-react";
import { ApiClient } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("learner@aiprof.com");
  const [password, setPassword] = useState("Learner123!");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isRegister) {
        await ApiClient.request("/auth/register", {
          method: "POST",
          body: JSON.stringify({ email, password, full_name: fullName }),
        });
      }

      // Login to obtain JWT
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData.toString(),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Invalid credentials" }));
        throw new Error(err.detail || "Authentication failed");
      }

      const tokenData = await res.json();
      localStorage.setItem("study_companion_token", tokenData.access_token);
      router.push("/dashboard");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to authenticate");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-background">
      <div className="w-full max-w-md bg-surface border border-gray-800 rounded-2xl p-8 shadow-2xl">
        <div className="flex flex-col items-center mb-8">
          <div className="bg-primary-600 p-3 rounded-xl text-white mb-3 shadow-lg shadow-blue-500/20">
            <Brain className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">AI Study Companion</h2>
          <p className="text-sm text-gray-400 mt-1">
            {isRegister ? "Create your candidate learning account" : "Sign in to your learning workspace"}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-rose-950/50 border border-rose-800 text-rose-300 text-sm flex items-start gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-400 mb-1.5">Full Name</label>
              <div className="relative">
                <UserIcon className="w-5 h-5 absolute left-3.5 top-3 text-gray-500" />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Alex Mercer"
                  className="w-full pl-11 pr-4 py-2.5 rounded-lg bg-surface-raised border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:border-primary-500 transition-colors text-sm"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-400 mb-1.5">Email Address</label>
            <div className="relative">
              <Mail className="w-5 h-5 absolute left-3.5 top-3 text-gray-500" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="learner@aiprof.com"
                className="w-full pl-11 pr-4 py-2.5 rounded-lg bg-surface-raised border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:border-primary-500 transition-colors text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-400 mb-1.5">Password</label>
            <div className="relative">
              <Lock className="w-5 h-5 absolute left-3.5 top-3 text-gray-500" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-11 pr-4 py-2.5 rounded-lg bg-surface-raised border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:border-primary-500 transition-colors text-sm"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 bg-primary-600 hover:bg-primary-500 text-white font-medium py-3 rounded-lg transition-all flex items-center justify-center gap-2 text-sm disabled:opacity-50 shadow-lg shadow-blue-500/20"
          >
            {loading ? "Processing..." : isRegister ? "Create Account" : "Sign In to Workspace"}
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="mt-6 pt-6 border-t border-gray-800 text-center">
          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              setError(null);
            }}
            className="text-sm text-gray-400 hover:text-white transition-colors"
          >
            {isRegister ? "Already have an account? Sign In" : "Don't have an account? Create one"}
          </button>
        </div>

        <div className="mt-4 p-3 rounded-lg bg-blue-950/30 border border-blue-900/50 text-xs text-blue-300">
          <p className="font-semibold mb-1">Preloaded Seed Accounts:</p>
          <p>• Learner: <code>learner@aiprof.com</code> / <code>Learner123!</code></p>
          <p>• Admin: <code>admin@aiprof.com</code> / <code>AdminPassword123!</code></p>
        </div>
      </div>
    </div>
  );
}
