"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
    const [isRegistering, setIsRegistering] = useState(false);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const router = useRouter();

    const handleAuth = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        try {
            const url = isRegistering
                ? "http://localhost:8000/api/v1/auth/register"
                : "http://localhost:8000/api/v1/auth/token";

            const options: RequestInit = {
                method: "POST",
                headers: {
                    "Content-Type": isRegistering ? "application/json" : "application/x-www-form-urlencoded"
                },
            };

            if (isRegistering) {
                options.body = JSON.stringify({ email, password });
            } else {
                options.body = new URLSearchParams({
                    username: email,
                    password: password,
                });
            }

            const res = await fetch(url, options);

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Authentication failed");
            }

            const data = await res.json();
            // Simple cookie set for MVP. In prod use httpOnly via API route proxy
            document.cookie = `token=${data.access_token}; path=/`;
            router.push("/dashboard");
        } catch (err: any) {
            setError(err.message);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-zinc-950 px-4">
            <div className="w-full max-w-sm space-y-8">
                <div className="text-center">
                    <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-white mb-2">
                        AuraOps
                    </h1>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                        {isRegistering ? "Create your admin account" : "Sign in to manage your fleet"}
                    </p>
                </div>

                <div className="bg-white dark:bg-zinc-900 py-8 px-6 shadow-xl rounded-2xl border border-gray-100 dark:border-zinc-800">
                    <form className="space-y-6" onSubmit={handleAuth}>
                        {error && (
                            <div className="p-3 text-sm text-red-500 bg-red-50 dark:bg-red-900/20 rounded-lg text-center font-medium">
                                {error}
                            </div>
                        )}

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Email address
                                </label>
                                <input
                                    type="email"
                                    required
                                    className="block w-full rounded-lg border-0 bg-gray-50 dark:bg-zinc-800 py-2.5 px-4 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-700 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6 transition-all"
                                    placeholder="admin@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Password
                                </label>
                                <input
                                    type="password"
                                    required
                                    className="block w-full rounded-lg border-0 bg-gray-50 dark:bg-zinc-800 py-2.5 px-4 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-700 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6 transition-all"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            className="flex w-full justify-center rounded-lg bg-indigo-600 py-2.5 px-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 transition-colors"
                        >
                            {isRegistering ? "Create Account" : "Sign In"}
                        </button>
                    </form>

                    <div className="mt-6 text-center text-sm">
                        <button
                            onClick={() => {
                                setIsRegistering(!isRegistering);
                                setError("");
                            }}
                            className="font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300 transition-colors"
                        >
                            {isRegistering
                                ? "Already have an account? Sign in"
                                : "No account? Create one"}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
