"""
Management command to reindex all successfully processed documents into ChromaDB.

Use this after changes to index_document() that affect chunk metadata (e.g. adding
well_num tagging). It drops existing ChromaDB data for each doc and re-parses
the original file on disk.

Usage:
    python manage.py reindex_documents
    python manage.py reindex_documents --doc-id 42
    python manage.py reindex_documents --dry-run
"""
import logging
import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.ingestion.models import UploadedFile
from apps.ingestion.parsers import parse_pdf, parse_word
from apps.ingestion.tasks import _remove_status_table_rows

logger = logging.getLogger('apps')


class Command(BaseCommand):
    help = 'Reindex uploaded documents into ChromaDB (rebuilds well_num metadata)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--doc-id',
            type=int,
            default=None,
            help='Reindex a single document by ID. Omit to reindex all.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List documents that would be reindexed without doing anything.',
        )

    def handle(self, *args, **options):
        doc_id = options['doc_id']
        dry_run = options['dry_run']

        qs = UploadedFile.objects.filter(
            status=UploadedFile.Status.SUCCESS,
            file_type__in=['pdf', 'docx'],
        )
        if doc_id:
            qs = qs.filter(id=doc_id)

        if not qs.exists():
            self.stdout.write(self.style.WARNING('No matching documents found.'))
            return

        self.stdout.write(f"Found {qs.count()} document(s) to reindex.")

        if dry_run:
            for f in qs:
                self.stdout.write(f"  [dry-run] {f.id}: {f.original_name}")
            return

        # Wipe global vectorstore so stale chunks (without well_num) are removed
        self._drop_global_vectorstore()

        ok = 0
        errors = 0
        for uploaded in qs:
            self.stdout.write(f"Reindexing [{uploaded.id}] {uploaded.original_name} ...")
            try:
                self._reindex_one(uploaded)
                self.stdout.write(self.style.SUCCESS(f"  OK"))
                ok += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  FAILED: {e}"))
                logger.exception(f"reindex_documents: error on doc {uploaded.id}")
                errors += 1

        self.stdout.write(f"\nDone — {ok} succeeded, {errors} failed.")

    # ------------------------------------------------------------------ #

    def _drop_global_vectorstore(self):
        """Delete the global ChromaDB collection directory so it's rebuilt clean."""
        global_dir = settings.CHROMA_PERSIST_DIR
        # Only wipe the global collection, not per-doc subdirs
        # ChromaDB stores collections as sqlite + subdirs inside persist_dir.
        # The safest approach is to delete and recreate the global collection
        # via the Chroma client rather than deleting files.
        try:
            from apps.chatbot import rag_pipeline
            # Reset cached instance so it gets recreated
            rag_pipeline._global_vectorstore = None

            import chromadb
            client = chromadb.PersistentClient(path=global_dir)
            try:
                client.delete_collection("ezzaouia_global")
                self.stdout.write("  Dropped global collection 'ezzaouia_global'.")
            except Exception:
                self.stdout.write("  Global collection not found — will be created fresh.")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Could not drop global collection: {e}"))

    def _reindex_one(self, uploaded):
        from apps.chatbot.rag_pipeline import index_document, get_vectorstore_for_doc
        from apps.chatbot import rag_pipeline

        filepath = uploaded.file.path
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not on disk: {filepath}")

        # Parse
        if uploaded.file_type == 'pdf':
            text, error = parse_pdf(filepath)
        else:
            text, error = parse_word(filepath)

        if error:
            raise RuntimeError(f"Parse error: {error}")

        text = _remove_status_table_rows(text)

        # Drop per-doc vectorstore cache and collection
        if uploaded.id in rag_pipeline._vectorstores:
            del rag_pipeline._vectorstores[uploaded.id]

        try:
            import chromadb
            from apps.chatbot.rag_pipeline import _get_doc_collection_name
            per_doc_dir = os.path.join(settings.CHROMA_PERSIST_DIR, f"doc_{uploaded.id}")
            client = chromadb.PersistentClient(path=per_doc_dir)
            col_name = _get_doc_collection_name(uploaded.id)
            try:
                client.delete_collection(col_name)
            except Exception:
                pass
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    Could not drop per-doc collection: {e}"))

        # Reindex
        chunks = index_document(
            text,
            metadata={
                'filename': uploaded.original_name,
                'file_type': uploaded.file_type,
                'uploaded_by': str(uploaded.uploaded_by),
                'doc_id': str(uploaded.id),
            },
            doc_id=uploaded.id,
        )
        self.stdout.write(f"  Indexed {chunks} chunks for doc {uploaded.id}.")
