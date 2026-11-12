"use client";
import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";

export default function Navbar() {
  const { token, logout } = useAuth();

  return (
    <header className="bg-white/80 backdrop-blur-md border-b border-slate-200/60 px-4 md:px-8 py-3.5 flex justify-between items-center sticky top-0 z-50 shadow-[0_2px_10px_rgba(0,0,0,0.02)]">
      
      {/* Logo (Cliquable pour retourner à l'accueil) */}
      <Link href="/" className="flex items-center gap-3 group">
        <div className="w-11 h-11 bg-gradient-to-br from-sky-400 to-indigo-500 rounded-[14px] flex items-center justify-center shadow-md shadow-sky-200/50 group-hover:scale-105 transition-transform duration-200">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="white" className="w-6 h-6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.499 5.229 50.552 50.552 0 00-2.658.813m-15.482 0A50.57 50.57 0 0112 13.489a50.57 50.57 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
          </svg>
        </div>
        <div>
          <h1 className="text-[17px] font-extrabold text-slate-800 tracking-tight">SmartCampus AI</h1>
          <p className="text-[11px] text-emerald-600 font-semibold flex items-center gap-1.5 mt-0.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            Assistant en ligne
          </p>
        </div>
      </Link>

      {/* Boutons à droite (Changement dynamique selon la connexion) */}
      <div className="flex items-center gap-3">
        {token ? (
          <>
            {/* Bouton Dashboard (Visible si connecté) */}
            <Link 
              href="/dashboard" 
              className="hidden sm:flex text-[13px] font-bold text-slate-700 bg-white border border-slate-200 px-5 py-2.5 rounded-full hover:bg-slate-50 hover:border-slate-300 shadow-sm transition-all duration-200 items-center gap-2"
            >
              Mon Espace
            </Link>
            
            {/* Bouton Déconnexion (Visible si connecté) */}
            <button 
              onClick={logout}
              className="text-[13px] font-bold text-white bg-slate-900 px-5 py-2.5 rounded-full hover:bg-slate-800 shadow-sm transition-all duration-200 flex items-center gap-2 group"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
              </svg>
              <span className="hidden sm:inline">Déconnexion</span>
            </button>
          </>
        ) : (
          /* Bouton Espace Candidat (Visible si non connecté) */
          <Link 
            href="/login" 
            className="text-[13px] font-bold text-slate-700 bg-white border border-slate-200 px-5 py-2.5 rounded-full hover:bg-slate-50 hover:border-slate-300 shadow-sm transition-all duration-200 flex items-center gap-2 group"
          >
            Espace Candidat
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-3.5 h-3.5 text-slate-400 group-hover:translate-x-0.5 transition-transform">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
          </Link>
        )}
      </div>
    </header>
  );
}