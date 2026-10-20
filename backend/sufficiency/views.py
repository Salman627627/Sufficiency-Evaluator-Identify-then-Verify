import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from . import llm, pipeline
from .models import Run
from .samples import SAMPLES

def health(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET required"}, status=405)
    return JsonResponse({"status": "ok", "llm_mode": llm.mode(), "methods": pipeline.METHODS})

def samples(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET required"}, status=405)
    return JsonResponse({"samples": SAMPLES})

@csrf_exempt
def evaluate(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        body = json.loads(request.body or "{}")
        if not isinstance(body, dict):
            return JsonResponse({"error": "JSON object required"}, status=400)
    except ValueError:
        return JsonResponse({"error": "invalid JSON"}, status=400)
    ids = body.get("sample_ids", [])
    chosen = [s for s in SAMPLES if s["id"] in ids] + body.get("custom", [])
    methods = [m for m in body.get("methods", pipeline.METHODS) if m in pipeline.METHODS]
    if not chosen or not methods:
        return JsonResponse({"error": "select at least one sample and method"}, status=400)
    summary, cases = pipeline.run(chosen, methods)
    run = Run.objects.create(mode=llm.mode(), summary=summary, cases=cases)
    return JsonResponse({"run_id": run.id, "mode": run.mode, "summary": summary, "cases": cases})

def runs(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET required"}, status=405)
    return JsonResponse({"runs": [{"id": r.id, "created": r.created.isoformat(), "mode": r.mode, "summary": r.summary}
                                  for r in Run.objects.order_by("-id")[:20]]})
