import os
import shutil

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST
from apps.core.views import serve_react

from apps.ingestion.models import UploadedFile

WELLS = [
    "EZZ1",
    "EZZ2",
    "EZZ4",
    "EZZ5",
    "EZZ6",
    "EZZ7",
    "EZZ8",
    "EZZ9",
    "EZZ10",
    "EZZ11",
    "EZZ12",
    "EZZ14",
    "EZZ15",
    "EZZ16",
    "EZZ17",
    "EZZ18",
]


def _safe_file_size(uploaded_file):
    if not uploaded_file.file:
        return 0
    try:
        return int(uploaded_file.file.size or 0)
    except Exception:
        return 0


def _format_size(num_bytes):
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(max(num_bytes, 0))

    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024

    return "0 B"


@login_required
def bibliotheque(request):
    # Frontend is now rendered by React SPA.
    return serve_react(request)

    qs = UploadedFile.objects.filter(status="success").select_related("uploaded_by")

    search = request.GET.get("q", "").strip()
    file_type = request.GET.get("type", "").strip()
    year = request.GET.get("year", "").strip()
    well = request.GET.get("well", "").strip()

    if search:
        qs = qs.filter(original_name__icontains=search)
    if file_type in ("pdf", "docx", "xlsx"):
        qs = qs.filter(file_type=file_type)
    if year.isdigit():
        qs = qs.filter(created_at__year=int(year))
    if well and well in WELLS:
        qs = qs.filter(original_name__icontains=well)

    qs = qs.order_by("-created_at")

    all_docs_qs = UploadedFile.objects.filter(status="success")
    total_size_bytes = sum(_safe_file_size(doc) for doc in all_docs_qs.only("id", "file"))
    stats = {
        "total": all_docs_qs.count(),
        "pdf": all_docs_qs.filter(file_type="pdf").count(),
        "docx": all_docs_qs.filter(file_type="docx").count(),
        "xlsx": all_docs_qs.filter(file_type="xlsx").count(),
        "total_size_bytes": total_size_bytes,
        "total_size_human": _format_size(total_size_bytes),
    }

    available_years = [d.year for d in all_docs_qs.dates("created_at", "year", order="DESC")]

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    page_docs = list(page_obj.object_list)
    for doc in page_docs:
        size_bytes = _safe_file_size(doc)
        doc.file_size_bytes = size_bytes
        doc.file_size_human = _format_size(size_bytes) if size_bytes else "Non disponible"
        doc.can_delete = bool(request.user.is_admin or doc.uploaded_by_id == request.user.id)

    context = {
        "stats": stats,
        "search": search,
        "filter_type": file_type,
        "filter_year": year,
        "filter_well": well,
        "available_years": available_years,
        "wells": WELLS,
        "page_obj": page_obj,
        "page_docs": page_docs,
    }
    return render(request, "bibliotheque/index.html", context)


@login_required
@require_POST
def delete_document(request, pk):
    doc = get_object_or_404(UploadedFile, pk=pk)
    can_delete = bool(request.user.is_admin or doc.uploaded_by_id == request.user.id)
    if not can_delete:
        return JsonResponse({"error": "Permission refusee."}, status=403)

    if doc.file and os.path.exists(doc.file.path):
        os.remove(doc.file.path)

    try:
        from apps.chatbot.rag_pipeline import _vectorstores

        chroma_path = os.path.join(settings.CHROMA_PERSIST_DIR, f"doc_{pk}")
        if os.path.exists(chroma_path):
            shutil.rmtree(chroma_path, ignore_errors=True)
        _vectorstores.pop(pk, None)
    except Exception:
        pass

    doc.delete()
    return JsonResponse({"success": True})


@login_required
@require_GET
def api_documents(request):
    """GET /api/library/documents/ - JSON listing for React."""
    qs = UploadedFile.objects.filter(status="success").select_related("uploaded_by")

    search = request.GET.get("q", "").strip()
    file_type = request.GET.get("type", "").strip()
    year = request.GET.get("year", "").strip()
    well = request.GET.get("well", "").strip()
    uploaded_by = request.GET.get("uploaded_by", "").strip()

    if search:
        qs = qs.filter(original_name__icontains=search)
    if file_type in ("pdf", "docx", "xlsx"):
        qs = qs.filter(file_type=file_type)
    if year.isdigit():
        qs = qs.filter(created_at__year=int(year))
    if well and well in WELLS:
        qs = qs.filter(original_name__icontains=well)
    if uploaded_by:
        qs = qs.filter(uploaded_by__username=uploaded_by)

    qs = qs.order_by("-created_at")

    all_docs_qs = UploadedFile.objects.filter(status="success")
    total_size_bytes = sum(_safe_file_size(doc) for doc in all_docs_qs.only("id", "file"))
    uploaders = sorted(
        all_docs_qs.exclude(uploaded_by__isnull=True)
        .values_list("uploaded_by__username", flat=True)
        .distinct()
    )
    stats = {
        "total": all_docs_qs.count(),
        "pdf": all_docs_qs.filter(file_type="pdf").count(),
        "docx": all_docs_qs.filter(file_type="docx").count(),
        "xlsx": all_docs_qs.filter(file_type="xlsx").count(),
        "total_size_human": _format_size(total_size_bytes),
    }
    available_years = [d.year for d in all_docs_qs.dates("created_at", "year", order="DESC")]

    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    results = []
    for doc in page_obj.object_list:
        size_bytes = _safe_file_size(doc)
        results.append({
            "id": doc.id,
            "original_name": doc.original_name,
            "file_type": doc.file_type,
            "created_at": doc.created_at.strftime("%d/%m/%Y %H:%M"),
            "uploaded_by": doc.uploaded_by.username if doc.uploaded_by else "",
            "status": doc.status,
            "file_size_human": _format_size(size_bytes) if size_bytes else "N/A",
            "can_delete": bool(request.user.is_admin or doc.uploaded_by_id == request.user.id),
        })

    return JsonResponse({
        "results": results,
        "stats": stats,
        "available_years": available_years,
        "wells": WELLS,
        "uploaders": uploaders,
        "page": page_obj.number,
        "pages": paginator.num_pages,
        "total": paginator.count,
    })


@login_required
@require_POST
def api_delete_document(request, pk):
    """POST /api/library/documents/<id>/delete/."""
    return delete_document(request, pk)
