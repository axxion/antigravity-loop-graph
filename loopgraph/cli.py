"""
LoopGraph Command Line Interface.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from loopgraph.antigravity_scaffold import scaffold_antigravity_integration
from loopgraph.core.state import TaskStatus
from loopgraph.engine import EngineConfig, GraphEngine
from loopgraph.memory.board import BoardManager
from loopgraph.memory.ledger import LedgerManager
from loopgraph.memory.vision import VisionManager


def log(msg: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[\033[94mloopgraph\033[0m {now}] {msg}", flush=True)


def cmd_init(args) -> int:
    proj = Path(args.project).resolve()
    proj.mkdir(parents=True, exist_ok=True)

    v_mgr = VisionManager(proj)
    b_mgr = BoardManager(proj)
    l_mgr = LedgerManager(proj)

    v_mgr.ensure_exists()
    b_mgr.ensure_exists()
    l_mgr.ensure_exists()

    cfg_file = proj / "config.json"
    if not cfg_file.exists():
        example_cfg = {
            "model": "glm-5.3-flash",
            "base_url": "https://api.z.ai/api/paas/v4/",
            "api_key_env": "ZAI_API_KEY",
            "verify_model": None,
            "max_loop_iters": 25,
            "budget_tokens": 2000000,
        }
        import json
        cfg_file.write_text(json.dumps(example_cfg, indent=2), encoding="utf-8")

    scaffolded = scaffold_antigravity_integration(proj)

    log(f"✅ Proje hafıza dosyaları hazırlandı: {proj}")
    log("  - VISION.md (Proje hedefleri)")
    log("  - BOARD.md  (Geliştirme panosu)")
    log("  - LEDGER.md (İş defteri)")
    log("  - config.json (Model yapılandırması)")
    if scaffolded:
        log("  - .agents/skills/loopgraph/SKILL.md ve .agents/rules/loopgraph.md (Antigravity IDE Native Mode)")
    return 0


def cmd_status(args) -> int:
    proj = Path(args.project).resolve()
    if not proj.is_dir():
        log(f"Hata: Klasör bulunamadı: {proj}")
        return 1

    b_mgr = BoardManager(proj)
    tasks = b_mgr.parse()

    print("\n" + "=" * 60)
    print(f"  LOOPGRAPH PROJE DURUMU: {proj.name}")
    print("=" * 60)
    if not tasks:
        print("  Henüz tanımlı görev yok. 'loopgraph plan' komutuyla analiz yapabilirsiniz.\n")
        return 0

    print(f"  Toplam Görev: {len(tasks)}\n")
    for t in sorted(tasks, key=lambda x: (x.priority, x.id)):
        status_icons = {
            TaskStatus.DONE: "✅ DONE",
            TaskStatus.IN_PROGRESS: "🔄 IN_PROGRESS",
            TaskStatus.BLOCKED: "⚠️ BLOCKED",
            TaskStatus.FAILED: "❌ FAILED",
            TaskStatus.TODO: "⏳ TODO",
        }
        icon = status_icons.get(t.status, str(t.status))
        print(f"  [{t.id}] {icon:<15} (Öncelik: {t.priority}) - {t.title}")
        if t.acceptance:
            for c in t.acceptance:
                print(f"       · {c}")
    print("=" * 60 + "\n")
    return 0


def cmd_run(args) -> int:
    proj = Path(args.project).resolve()
    if not proj.is_dir():
        log(f"Hata: Klasör bulunamadı: {proj}")
        return 2

    cfg = EngineConfig.from_file_or_defaults(args.config)
    if args.tasks:
        max_tasks = args.tasks
    else:
        max_tasks = 3

    if args.model:
        cfg.model = args.model
    if args.verify_model:
        cfg.verify_model = args.verify_model
    if args.budget_tokens:
        cfg.budget_tokens = args.budget_tokens
    if args.max_iters:
        cfg.max_loop_iters = args.max_iters

    def step_listener(event_type: str, data: any):
        if event_type == "node_start":
            node_name = data.get("node")
            task = data.get("task")
            if task:
                log(f"▶ Graf Düğümü: [{node_name.upper()}] → Görev: [{task.id}] {task.title}")
            else:
                log(f"▶ Graf Düğümü: [{node_name.upper()}]")
        elif event_type == "loop_step":
            it = data.get("iteration")
            tool = data.get("tool")
            prev = data.get("preview")
            log(f"  ↳ [Döngü Adım {it}] Araç: {tool} | {prev}")
        elif event_type == "node_finish":
            node_name = data.get("node")
            sig = data.get("signal")
            log(f"✔ [{node_name.upper()}] bitti. Sinyal: {sig}")

    engine = GraphEngine(project_path=proj, config=cfg, on_step=step_listener)

    if not engine.llm.is_configured:
        log("⚠️  BİLGİ: Harici LLM API Anahtarı bulunamadı.")
        log("   [Mod 1 - Antigravity IDE (Önerilen)]: Antigravity sohbetinde doğrudan")
        log("          'LoopGraph ile VISION.md planını çıkar' diyerek IDE'nin kendi yapay zeka")
        log("          motorunu API anahtarı olmadan kullanabilirsiniz.")
        log(f"   [Mod 2 - Harici CLI]: Ortam değişkenini ayarlayabilirsiniz: $env:{cfg.api_key_env}='anahtariniz'")
        log("          (Desteklenen: ZAI_API_KEY, OPENAI_API_KEY, DEEPSEEK_API_KEY, GROQ_API_KEY)")
        return 2

    log(f"Graf Motoru Başlatılıyor... Proje: {proj}")
    log(f"Model: {cfg.model} | Doğrulayıcı Model: {cfg.verify_model or cfg.model}")
    log(f"Maksimum Görev Sayısı: {max_tasks} | Token Bütçesi: {cfg.budget_tokens:,}")

    report = engine.run(max_tasks=max_tasks, stop_on_fail=args.stop_on_fail)

    log("\n" + "=" * 50)
    log("🏁 GRAF ÇALIŞMASI TAMAMLANDI")
    log(f"   Tamamlanan Görevler: {report.completed_tasks}")
    log(f"   Engellenen Görevler: {report.blocked_tasks}")
    log(f"   Başarısız Görevler:  {report.failed_tasks}")
    log(f"   Toplam Kullanılan Token: {report.tokens_used:,}")
    log("=" * 50)
    return 0


def cmd_plan(args) -> int:
    proj = Path(args.project).resolve()
    if not proj.is_dir():
        log(f"Hata: Klasör bulunamadı: {proj}")
        return 2

    cfg = EngineConfig.from_file_or_defaults(args.config)
    engine = GraphEngine(project_path=proj, config=cfg)

    log(f"Proje analiz ediliyor ve pano güncelleniyor: {proj}")
    if not engine.llm.is_configured:
        log("💡 BİLGİ: Harici LLM API Anahtarı bulunamadı, dahili yerel planlayıcı (Heuristic Planner) devrede.")
    
    tasks = engine.plan_only()
    log(f"✅ Analiz tamamlandı. Toplam {len(tasks)} görev panoya (BOARD.md) yazıldı:")
    for t in sorted(tasks, key=lambda x: (x.priority, x.id)):
        log(f"  [{t.id}] (Öncelik {t.priority}) {t.title}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="loopgraph",
        description="LoopGraph — Otonom Döngü ve Graf Mühendisliği Motoru",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Alt komutlar")

    # init
    p_init = subparsers.add_parser("init", help="Projede VISION, BOARD, LEDGER şablonlarını kurar")
    p_init.add_argument("project", default=".", nargs="?", help="Proje klasörü (varsayılan: .)")

    # status
    p_status = subparsers.add_parser("status", help="Projenin mevcut görev durumunu gösterir")
    p_status.add_argument("project", default=".", nargs="?", help="Proje klasörü (varsayılan: .)")

    # plan
    p_plan = subparsers.add_parser("plan", help="Projeyi analiz edip BOARD.md dosyasını oluşturur")
    p_plan.add_argument("project", default=".", nargs="?", help="Proje klasörü")
    p_plan.add_argument("--config", help="config.json dosya yolu")

    # run & loop (aliases)
    for cmd_name in ("run", "loop"):
        p_r = subparsers.add_parser(cmd_name, help="Projeyi otonom döngü ve graf ile geliştirir")
        p_r.add_argument("project", default=".", nargs="?", help="Proje klasörü (varsayılan: .)")
        p_r.add_argument("--config", help="config.json dosya yolu")
        p_r.add_argument("--tasks", type=int, default=3, help="Kaç görev tamamlanacak (varsayılan: 3)")
        p_r.add_argument("--model", help="LLM model adı")
        p_r.add_argument("--verify-model", help="Doğrulayıcı LLM model adı")
        p_r.add_argument("--max-iters", type=int, default=25, help="Görev başına maksimum araç iterasyonu")
        p_r.add_argument("--budget-tokens", type=int, default=2_000_000, help="Toplam token tavanı")
        p_r.add_argument("--stop-on-fail", action="store_true", help="İlk başarısız görevde dur")

    # If no subcommand provided, support legacy positional argument: loopgraph <project> [flags]
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-") and sys.argv[1] not in ("init", "status", "plan", "run", "loop"):
        # Legacy mode: default to loop
        sys.argv.insert(1, "loop")

    args = parser.parse_args()

    if args.subcommand == "init":
        return cmd_init(args)
    elif args.subcommand == "status":
        return cmd_status(args)
    elif args.subcommand == "plan":
        return cmd_plan(args)
    elif args.subcommand in ("run", "loop"):
        return cmd_run(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
