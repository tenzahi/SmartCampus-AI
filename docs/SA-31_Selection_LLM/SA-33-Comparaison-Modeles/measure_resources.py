# -*- coding: utf-8 -*-
"""SA-33 : mesure de la consommation de ressources de chaque modèle Ollama (CPU, RAM, vitesse)."""
import json, time, threading, subprocess, urllib.request, statistics, sys
import psutil

MODELS = ["gemma4:e4b", "llama3.2:3b", "qwen3.5:4b"]
URL = "http://localhost:11434"
SYSTEM = ("Tu es SmartCampus AI, l'assistant d'orientation universitaire de l'IIT et de l'ISB (Sfax, Tunisie). "
          "Réponds dans la langue du candidat, n'invente aucune information officielle, 120 mots maximum.")
PROMPTS = [
    "Bonjour, je viens d'avoir mon bac. Quelle différence entre la Licence, la Préparatoire et l'Ingénierie ?",
    "عسلامة، عندي باك رياضيات و نحب الإعلامية، شنوة تنصحني نقرا؟",
    "ahla, 3andi bac info w n7eb na9ra ingénierie, chnowa el 7al?",
    "Salut, j'ai eu 14 de moyenne, nheb nekhdem fel IA, quelle formation me conseilles-tu ?",
]
OUT = sys.argv[1] if len(sys.argv) > 1 else "ressources.json"


def post(path, payload, timeout=900):
    req = urllib.request.Request(URL + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def get(path):
    with urllib.request.urlopen(URL + path, timeout=30) as r:
        return json.loads(r.read().decode())


def ollama_rss():
    tot = 0
    for p in psutil.process_iter(["name"]):
        n = (p.info["name"] or "").lower()
        if "ollama" in n or "llama" in n:
            try:
                tot += p.memory_info().rss
            except psutil.Error:
                pass
    return tot


class Sampler(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True); self.stop = False; self.cpu = []; self.rss = []; self.sysram = []
    def run(self):
        psutil.cpu_percent(None)
        while not self.stop:
            time.sleep(0.5)
            self.cpu.append(psutil.cpu_percent(None))
            self.rss.append(ollama_rss())
            self.sysram.append(psutil.virtual_memory().used)


def unload_all():
    for m in MODELS:
        subprocess.run(["ollama", "stop", m], capture_output=True)
    time.sleep(4)


res = {"machine": {"cpu": "Intel Core i5-8250U (4 cœurs / 8 threads)", "ram_go": round(psutil.virtual_memory().total / 2**30, 1),
                   "gpu": "aucun (calcul sur CPU)"}, "modeles": {}}
for m in MODELS:
    unload_all()
    base_rss, base_sys = ollama_rss(), psutil.virtual_memory().used
    s = Sampler(); s.start()
    runs = []
    for i, p in enumerate(PROMPTS):
        t0 = time.time()
        d = post("/api/chat", {"model": m, "stream": False, "think": False,
                               "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": p}],
                               "options": {"temperature": 0.2, "seed": 42, "num_predict": 300}})
        runs.append({"wall_s": round(time.time() - t0, 2), "load_s": d.get("load_duration", 0) / 1e9,
                     "prompt_tok": d.get("prompt_eval_count"), "prompt_s": d.get("prompt_eval_duration", 0) / 1e9,
                     "gen_tok": d.get("eval_count"), "gen_s": d.get("eval_duration", 0) / 1e9})
        if i == 0:
            ps = get("/api/ps")
        print(m, i, runs[-1], flush=True)
    s.stop = True; s.join()
    info = next((x for x in ps.get("models", []) if x.get("name") == m or x.get("model") == m), {})
    warm = runs[1:]
    res["modeles"][m] = {
        "taille_memoire_ollama_go": round(info.get("size", 0) / 1e9, 2),
        "contexte": info.get("context_length"),
        "rss_pic_go": round((max(s.rss) - base_rss) / 2**30, 2),
        "ram_systeme_pic_go": round((max(s.sysram) - base_sys) / 2**30, 2),
        "cpu_moyen_pct": round(statistics.mean(s.cpu), 1),
        "cpu_pic_pct": round(max(s.cpu), 1),
        "chargement_s": round(runs[0]["load_s"], 1),
        "lecture_tok_s": round(sum(r["prompt_tok"] or 0 for r in warm) / max(1e-9, sum(r["prompt_s"] for r in warm)), 1),
        "generation_tok_s": round(sum(r["gen_tok"] or 0 for r in warm) / max(1e-9, sum(r["gen_s"] for r in warm)), 2),
        "temps_moyen_s": round(statistics.mean(r["wall_s"] for r in warm), 1),
        "runs": runs,
    }
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
unload_all()
print("FIN", json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "runs"} for k, v in res["modeles"].items()}, ensure_ascii=False, indent=1))
