"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface Project {
    id: number;
    name: string;
    status: string;
    repo_url: string;
    domain?: string;
    webhook_token: string;
}

export default function Dashboard() {
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    const fetchProjects = async () => {
        // Need to get token from cookie for header
        const token = document.cookie
            .split("; ")
            .find((row) => row.startsWith("token="))
            ?.split("=")[1];

        if (!token) return router.push("/login");

        try {
            const res = await fetch("http://localhost:8000/api/v1/projects/", {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
                const data = await res.json();
                setProjects(data);
            }
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchProjects();
    }, []);

    const handleCreate = async () => {
        // Minimal mock for creation
        const name = prompt("Project Name:");
        if (!name) return;
        const repo = prompt("Docker Image (e.g. nginx:alpine):");

        const token = document.cookie
            .split("; ")
            .find((row) => row.startsWith("token="))
            ?.split("=")[1];

        await fetch("http://localhost:8000/api/v1/projects/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({ name, repo_url: repo, port: 80 }),
        });
        fetchProjects();
    };

    const handleDeploy = async (id: number) => {
        const token = document.cookie
            .split("; ")
            .find((row) => row.startsWith("token="))
            ?.split("=")[1];

        await fetch(`http://localhost:8000/api/v1/projects/${id}/deploy`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
        });
        alert("Deployment Queued/Started");
        fetchProjects();
    };

    if (loading) return <div className="p-10">Loading...</div>;

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-zinc-900 p-8">
            <div className="max-w-7xl mx-auto">
                <div className="flex justify-between items-center mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
                    <button
                        onClick={handleCreate}
                        className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700"
                    >
                        New Project
                    </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {projects.map((project) => (
                        <div key={project.id} className="bg-white dark:bg-zinc-800 rounded-lg shadow p-6">
                            <div className="flex justify-between items-start mb-4">
                                <h3 className="text-xl font-semibold dark:text-white">{project.name}</h3>
                                <span className={`px-2 py-1 text-xs rounded-full ${project.status === 'running' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                                    }`}>
                                    {project.status}
                                </span>
                            </div>
                            <p className="text-sm text-gray-500 mb-4 font-mono">{project.repo_url}</p>

                            <div className="space-y-2">
                                <p className="text-xs text-gray-400">Webhook Token: {project.webhook_token}</p>
                            </div>

                            <div className="mt-6 flex space-x-3">
                                <button
                                    onClick={() => handleDeploy(project.id)}
                                    className="flex-1 bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-50"
                                >
                                    Deploy
                                </button>
                                {project.domain && (
                                    <a
                                        href={`http://${project.domain}`}
                                        target="_blank"
                                        className="flex-1 text-center bg-indigo-50 text-indigo-700 px-4 py-2 rounded text-sm hover:bg-indigo-100"
                                    >
                                        Visit
                                    </a>
                                )}
                            </div>
                        </div>
                    ))}

                    {projects.length === 0 && (
                        <div className="col-span-full text-center py-12 text-gray-500">
                            No projects yet. Create one to get started.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
