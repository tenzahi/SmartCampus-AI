"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import Navbar from "@/components/Navbar";

export default function DashboardPage() {
  const { token } = useAuth();
  const router = useRouter();

  // Sécurité : Si pas de token, on renvoie au login
  useEffect(() => {
    if (!token) {
      router.push("/login");
    }
  }, [token, router]);

  if (!token) return null; // On attend la redirection

  return (
    <div className="min-h-screen bg-[#F8FAFC] font-sans">
      <Navbar />
      
      <main className="max-w-4xl mx-auto p-6 md:p-10">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
          <h1 className="text-3xl font-extrabold text-slate-800 tracking-tight">Mon Espace Candidat</h1>
          <p className="text-slate-500 mt-2">Bienvenue dans votre tableau de bord personnel.</p>
          
          <div className="mt-8 p-6 bg-sky-50 rounded-xl border border-sky-100 text-slate-700">
            <h2 className="font-bold mb-2 flex items-center gap-2">
              <span className="text-xl">🎉</span> Votre conversation a été sauvegardée !
            </h2>
            <p className="text-sm">
              Grâce à la fonctionnalité de rattachement (Claim), toutes vos discussions avec l'assistant IA sont désormais liées à votre compte. 
              Vous pouvez continuer votre parcours d'orientation en toute sécurité.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}