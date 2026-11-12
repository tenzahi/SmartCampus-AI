"use client";
import { useState, useEffect, useRef } from "react";
import { createGuestSession, sendMessage } from "@/lib/api";
import Navbar from "@/components/Navbar";

export default function Home() {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [session, setSession] = useState<{ id: string; token: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Initialiser une session visiteur au chargement (avec réutilisation)
  useEffect(() => {
    async function init() {
      const welcomeMessage = "Bonjour ! Je suis SmartCampus AI. Je suis là pour vous aider à trouver la formation idéale à l'IIT ou à l'ISB. Que souhaitez-vous savoir ?";
      
      try {
        // 1. On regarde si on a déjà une session dans le navigateur
        const savedSessionId = localStorage.getItem("guest_session_id");
        const savedToken = localStorage.getItem("guest_token");

        if (savedSessionId && savedToken) {
          // 2. On vérifie qu'elle est encore valide (pas expirée)
          try {
            const check = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/chat/sessions/me`, {
              headers: {
                'x_guest_session': savedSessionId,
                'x_guest_token': savedToken
              }
            });
            
            if (check.ok) {
              // 3. Elle est valide, on la réutilise
              setSession({ id: savedSessionId, token: savedToken });
              setMessages([{ role: "assistant", content: welcomeMessage }]);
              setIsInitializing(false);
              return;
            }
          } catch (e) {
            // Session expirée ou invalide (erreur réseau), on continue pour en créer une nouvelle
            console.warn("Ancienne session invalide, création d'une nouvelle.");
          }
        }

        // 4. Aucune session valide, on en crée une nouvelle
        const data = await createGuestSession();
        setSession({ id: data.guest_session_id, token: data.guest_token });
        
        // 💾 Sauvegarde de la session dans le navigateur
        localStorage.setItem("guest_session_id", data.guest_session_id);
        localStorage.setItem("guest_token", data.guest_token);
        
        setMessages([{ role: "assistant", content: welcomeMessage }]);
      } catch (err) {
        console.error(err);
        setMessages([{ role: "assistant", content: "Erreur de connexion au serveur. Veuillez rafraîchir la page." }]);
      } finally {
        setIsInitializing(false);
      }
    }
    init();
  }, []);

  // Scroll automatique vers le bas
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !session || loading) return;

    const userMsg = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const data = await sendMessage(session.id, session.token, userMsg);
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", content: "Désolé, une erreur technique est survenue. Veuillez réessayer." }]);
    } finally {
      setLoading(false);
      // Remettre le focus sur l'input
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-[#F3F4F6] font-sans selection:bg-sky-200">
      <Navbar />

      {/* 💬 Zone de Chat */}
      <main className="flex-1 overflow-y-auto w-full max-w-3xl mx-auto px-4 py-8 flex flex-col gap-6 scrollbar-thin scrollbar-thumb-slate-300 scrollbar-track-transparent">
        
        {isInitializing && (
          <div className="flex flex-col justify-center items-center h-full gap-4">
            <div className="animate-spin rounded-full h-12 w-12 border-[3px] border-sky-100 border-t-sky-500 shadow-lg shadow-sky-100"></div>
            <p className="text-sm text-slate-500 font-medium animate-pulse">Initialisation de votre session sécurisée...</p>
          </div>
        )}

        {!isInitializing && messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-in fade-in slide-in-from-bottom-4 duration-500`}>
            
            {/* Avatar de l'IA */}
            {msg.role === "assistant" && (
              <div className="w-10 h-10 bg-white rounded-2xl flex items-center justify-center mr-4 mt-1 flex-shrink-0 border border-slate-200/60 shadow-sm">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 text-sky-500">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.499 5.229 50.552 50.552 0 00-2.658.813m-15.482 0A50.57 50.57 0 0112 13.489a50.57 50.57 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
                </svg>
              </div>
            )}
            
            <div 
              className={`max-w-[85%] md:max-w-[75%] p-4 text-[15px] leading-relaxed shadow-sm ${
                msg.role === "user" 
                  ? "bg-gradient-to-br from-sky-600 to-indigo-600 text-white rounded-[20px] rounded-tr-[4px] shadow-indigo-500/20" 
                  : "bg-white border border-slate-200/60 text-slate-700 rounded-[20px] rounded-tl-[4px]"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {/* Indicateur de frappe (Loading) */}
        {loading && (
          <div className="flex justify-start animate-in fade-in slide-in-from-bottom-2">
            <div className="w-10 h-10 bg-white rounded-2xl flex items-center justify-center mr-4 mt-1 flex-shrink-0 border border-slate-200/60 shadow-sm">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 text-sky-500">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.499 5.229 50.552 50.552 0 00-2.658.813m-15.482 0A50.57 50.57 0 0112 13.489a50.57 50.57 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
              </svg>
            </div>
            <div className="bg-white border border-slate-200/60 p-4 rounded-[20px] rounded-tl-[4px] shadow-sm flex gap-1.5 items-center h-[52px]">
              <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
          </div>
        )}
        <div ref={bottomRef} className="h-4" />
      </main>

      {/* ⌨️ Barre de saisie (Input) Moderne */}
      <footer className="bg-gradient-to-t from-[#F3F4F6] via-[#F3F4F6]/90 to-transparent pt-6 pb-6 sticky bottom-0 z-10">
        <div className="max-w-3xl mx-auto px-4 md:px-6">
          <form 
            onSubmit={handleSend} 
            className="relative flex items-end gap-2 bg-white border border-slate-200 rounded-2xl p-2.5 shadow-[0_8px_30px_rgb(0,0,0,0.06)] focus-within:ring-4 focus-within:ring-sky-500/10 focus-within:border-sky-400 transition-all duration-300"
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Posez votre question sur les formations, débouchés..."
              className="w-full bg-transparent text-slate-800 text-[15px] px-3 py-3.5 focus:outline-none placeholder:text-slate-400"
              disabled={loading || isInitializing}
            />
            <button 
              type="submit" 
              disabled={loading || !input.trim() || isInitializing} 
              className="bg-slate-900 text-white p-3.5 rounded-xl font-semibold hover:bg-slate-800 disabled:opacity-30 disabled:hover:bg-slate-900 transition-all duration-300 flex items-center justify-center flex-shrink-0 group shadow-md"
            >
              {/* Icône d'envoi SVG */}
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform duration-300">
                <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
              </svg>
            </button>
          </form>
          
          <p className="text-center text-[11px] text-slate-400 mt-4 font-medium">
            SmartCampus AI est une IA. Vérifiez toujours les informations importantes auprès de l'administration.
          </p>
        </div>
      </footer>
    </div>
  );
}