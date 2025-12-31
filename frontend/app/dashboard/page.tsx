"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface Project {
    id: number;
    name: string;
    status: string;
    provider: string; // 'image' | 'github'
    repo_url: string;
    domain?: string;
    webhook_token: string;
    last_deployed_at?: string;
    env_vars?: Record<string, string>;
    port: number;
}

export default function Dashboard() {
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const router = useRouter();

    // Form State
    const [name, setName] = useState("");
    const [provider, setProvider] = useState("image"); // image, github, postgres, redis
    const [repoUrl, setRepoUrl] = useState("");
    const [port, setPort] = useState("80");
    const [domain, setDomain] = useState("");
    const [envVars, setEnvVars] = useState<{ key: string, value: string }[]>([{ key: "", value: "" }]);

    const fetchProjects = async () => {
        const token = getToken();
        if (!token) return router.push("/login");

        try {
            const res = await fetch("/api/v1/projects/", {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
                const data = await res.json();
                setProjects(data);
            } else if (res.status === 401) {
                router.push("/login");
            }
        } catch (error) {
            console.error("Fetch projects failed:", error);
            // Optionally set an error state here
        } finally {
            setLoading(false);
        }
    };

    const getToken = () => {
        return document.cookie
            .split("; ")
            .find((row) => row.startsWith("token="))
            ?.split("=")[1];
    };

    useEffect(() => {
        fetchProjects();
        // Poll every 5 seconds for status updates
        const interval = setInterval(fetchProjects, 5000);
        return () => clearInterval(interval);
    }, []);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        const token = getToken();

        // Handle Presets
        let finalRepoUrl = repoUrl;
        let finalProvider = provider;
        let finalPort = parseInt(port);

        if (provider === "postgres") {
            finalRepoUrl = "postgres:15-alpine";
            finalProvider = "image";
            finalPort = 5432;
        } else if (provider === "redis") {
            finalRepoUrl = "redis:7-alpine";
            finalProvider = "image";
            finalPort = 6379;
        }

        const formattedEnvVars = envVars.reduce((acc: Record<string, string>, curr: { key: string, value: string }) => {
            if (curr.key) acc[curr.key] = curr.value;
            return acc;
        }, {} as Record<string, string>);

        const res = await fetch("/api/v1/projects/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({
                name,
                repo_url: finalRepoUrl,
                provider: finalProvider,
                port: finalPort,
                domain: domain || null,
                env_vars: formattedEnvVars
            }),
        });

        if (!res.ok) {
            const errorData = await res.json().catch(() => ({ detail: "Unknown error" }));
            console.error("Project creation failed:", errorData);
            alert(`Failed to create project: ${errorData.detail || "Unknown error"}`);
            return;
        }

        setIsModalOpen(false);
        // Reset form
        setName("");
        setRepoUrl("");
        setProvider("image");
        setEnvVars([{ key: "", value: "" }]);
        fetchProjects();
    };

    const handleDeploy = async (id: number) => {
        const token = getToken();
        await fetch(`/api/v1/projects/${id}/deploy`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
        });
        alert("Deployment Queued");
        fetchProjects();
    };

    if (loading) return (
        <div className="min-h-screen bg-zinc-950 flex items-center justify-center text-white">
            <div className="animate-pulse">Loading AuraOps...</div>
        </div>
    );

    return (
        <div className="min-h-screen bg-zinc-950 text-zinc-100 p-8 font-sans selection:bg-indigo-500/30">
            <div className="max-w-7xl mx-auto">
                <header className="flex justify-between items-center mb-12 border-b border-zinc-800 pb-6">
                    <div>
                        <h1 className="text-4xl font-bold bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
                            Dashboard
                        </h1>
                        <p className="text-zinc-500 mt-2">Manage your deployments and services</p>
                    </div>
                    <button
                        onClick={() => setIsModalOpen(true)}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-lg font-medium transition-all shadow-[0_0_20px_rgba(79,70,229,0.3)] hover:shadow-[0_0_30px_rgba(79,70,229,0.5)]"
                    >
                        + New Project
                    </button>
                </header>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {projects.map((project) => (
                        <div key={project.id} className="group bg-zinc-900 border border-zinc-800 hover:border-zinc-700 rounded-xl p-6 transition-all hover:shadow-xl hover:shadow-black/50 overflow-hidden relative">
                            <div className="absolute top-0 right-0 p-4 opacity-50 text-6xl text-zinc-800 -z-10 font-bold rotate-12 group-hover:rotate-0 transition-transform">
                                {project.id}
                            </div>

                            <div className="flex justify-between items-start mb-6">
                                <div>
                                    <h3 className="text-xl font-bold text-white mb-1">{project.name}</h3>
                                    <span className="text-xs font-mono text-zinc-500 bg-zinc-950 px-2 py-1 rounded">
                                        {project.provider === 'image' ? 'Docker Image' : 'GitHub Repo'}
                                    </span>
                                </div>
                                <StatusBadge status={project.status} />
                            </div>

                            <div className="space-y-3 mb-8">
                                <div className="text-sm text-zinc-400 truncate">
                                    <span className="text-zinc-600 block text-xs uppercase tracking-wider mb-1">Source</span>
                                    {project.repo_url}
                                </div>
                                <div className="text-sm text-zinc-400">
                                    <span className="text-zinc-600 block text-xs uppercase tracking-wider mb-1">Internal URL</span>
                                    <code className="bg-zinc-950 px-2 py-1 rounded text-xs select-all text-indigo-300">
                                        http://auraops-app-{project.id}:{project.port || 80}
                                    </code>
                                </div>
                                <div className="text-sm text-zinc-400">
                                    <span className="text-zinc-600 block text-xs uppercase tracking-wider mb-1">Webhook Token</span>
                                    <code className="bg-zinc-950 px-2 py-1 rounded text-xs select-all text-zinc-300">
                                        {project.webhook_token}
                                    </code>
                                </div>
                            </div>

                            <div className="flex gap-3 mt-auto">
                                <button
                                    onClick={() => handleDeploy(project.id)}
                                    className="flex-1 bg-white/5 hover:bg-white/10 border border-white/10 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                                >
                                    {project.status === 'stopped' ? 'Deploy' : 'Redeploy'}
                                </button>
                                {project.domain && (
                                    <a
                                        href={`http://${project.domain}`}
                                        target="_blank"
                                        className="flex-1 text-center bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                                    >
                                        Visit
                                    </a>
                                )}
                            </div>
                        </div>
                    ))}

                    {projects.length === 0 && (
                        <div className="col-span-full flex flex-col items-center justify-center py-24 text-zinc-500 border-2 border-dashed border-zinc-800 rounded-xl bg-zinc-900/50">
                            <p className="text-xl mb-4">No projects yet</p>
                            <button onClick={() => setIsModalOpen(true)} className="text-indigo-400 hover:text-indigo-300 underline">
                                Create your first project
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-lg p-8 shadow-2xl relative">
                        <button
                            onClick={() => setIsModalOpen(false)}
                            className="absolute top-4 right-4 text-zinc-500 hover:text-white"
                        >
                            ✕
                        </button>

                        <h2 className="text-2xl font-bold mb-6 text-white">New Project</h2>

                        <form onSubmit={handleCreate} className="space-y-6">
                            <div>
                                <label className="block text-sm font-medium text-zinc-400 mb-2">Project Name</label>
                                <input
                                    required
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                                    placeholder="my-awesome-app"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-zinc-400 mb-2">Type</label>
                                <div className="grid grid-cols-4 gap-2">
                                    {['image', 'github', 'postgres', 'redis'].map((type) => (
                                        <button
                                            key={type}
                                            type="button"
                                            onClick={() => setProvider(type)}
                                            className={`px-3 py-2 rounded-md text-sm capitalize border transition-all ${provider === type
                                                ? 'bg-indigo-600 border-indigo-500 text-white'
                                                : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700'
                                                }`}
                                        >
                                            {type}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {(provider === 'image' || provider === 'github') && (
                                <div>
                                    <label className="block text-sm font-medium text-zinc-400 mb-2">
                                        {provider === 'github' ? 'Git Repository URL' : 'Docker Image Name'}
                                    </label>
                                    <input
                                        required
                                        value={repoUrl}
                                        onChange={(e) => setRepoUrl(e.target.value)}
                                        className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-indigo-500"
                                        placeholder={provider === 'github' ? 'https://github.com/user/repo' : 'nginx:latest'}
                                    />
                                </div>
                            )}

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-zinc-400 mb-2">Port (Internal)</label>
                                    <input
                                        type="number"
                                        value={port}
                                        onChange={(e) => setPort(e.target.value)}
                                        className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-indigo-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-zinc-400 mb-2">Domain (Optional)</label>
                                    <input
                                        value={domain}
                                        onChange={(e) => setDomain(e.target.value)}
                                        className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-indigo-500"
                                        placeholder="app.localhost"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-zinc-400 mb-2">Environment Variables</label>
                                <div className="space-y-2">
                                    {envVars.map((env, index) => (
                                        <div key={index} className="flex gap-2">
                                            <input
                                                placeholder="KEY"
                                                value={env.key}
                                                onChange={(e) => {
                                                    const newEnv = [...envVars];
                                                    newEnv[index].key = e.target.value;
                                                    setEnvVars(newEnv);
                                                }}
                                                className="flex-1 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                                            />
                                            <input
                                                placeholder="VALUE"
                                                value={env.value}
                                                onChange={(e) => {
                                                    const newEnv = [...envVars];
                                                    newEnv[index].value = e.target.value;
                                                    setEnvVars(newEnv);
                                                }}
                                                className="flex-1 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                                            />
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    const newEnv = envVars.filter((_, i) => i !== index);
                                                    setEnvVars(newEnv);
                                                }}
                                                className="text-red-500 hover:text-red-400 px-2"
                                            >
                                                ×
                                            </button>
                                        </div>
                                    ))}
                                    <button
                                        type="button"
                                        onClick={() => setEnvVars([...envVars, { key: "", value: "" }])}
                                        className="text-xs text-indigo-400 hover:text-indigo-300"
                                    >
                                        + Add Variable
                                    </button>
                                </div>
                            </div>

                            <button
                                type="submit"
                                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 rounded-lg transition-colors mt-4"
                            >
                                Create Service
                            </button>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

function StatusBadge({ status }: { status: string }) {
    const styles = {
        running: "bg-green-500/10 text-green-400 border-green-500/20",
        stopped: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
        building: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20 animate-pulse",
        failed: "bg-red-500/10 text-red-400 border-red-500/20",
    };

    // @ts-ignore
    const className = styles[status] || styles.stopped;

    return (
        <span className={`px-3 py-1 rounded-full text-xs font-medium border ${className} capitalize`}>
            {status}
        </span>
    );
}
