"""
Tâches Celery asynchrones — traitement des fichiers uploadés.
"""
import logging
import os
from celery import shared_task
from .models import UploadedFile
from .parsers import parse_excel, parse_pdf, parse_word

logger = logging.getLogger('apps')


@shared_task(bind=True, max_retries=3)
def process_uploaded_file(self, file_id):
    try:
        uploaded = UploadedFile.objects.get(id=file_id)
        uploaded.status = UploadedFile.Status.PROCESSING
        uploaded.save()

        filepath  = uploaded.file.path
        file_type = uploaded.file_type
        text      = ""   # ← variable partagée pour l'indexation RAG

        logger.info(f"Traitement fichier {file_id} : {uploaded.original_name}")

        if file_type == 'xlsx':
            records, error = parse_excel(filepath)
            if error:
                raise Exception(error)
            uploaded.rows_extracted = len(records)
            logger.info(f"Excel traité : {len(records)} lignes")

        elif file_type == 'pdf':
            text, error = parse_pdf(filepath)
            if error:
                raise Exception(error)
            uploaded.rows_extracted = len(text.split('\n'))
            logger.info(f"PDF traité : {uploaded.rows_extracted} lignes")

        elif file_type == 'docx':
            text, error = parse_word(filepath)
            if error:
                raise Exception(error)
            uploaded.rows_extracted = len(text.split('\n'))
            logger.info(f"Word traité : {uploaded.rows_extracted} lignes")

        # ── Petroleum document validation ────────────────────────
        if file_type in ['pdf', 'docx'] and text:
            from apps.chatbot.rag_pipeline import is_petroleum_document
            if not is_petroleum_document(text):
                uploaded.status = 'rejected'
                uploaded.error_msg = 'Document not related to petroleum/MARETAP'
                uploaded.save()
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception as e:
                    logger.warning(f"Impossible de supprimer {filepath} : {e}")
                logger.info(f"Fichier {file_id} rejeté : non pétrolier")
                return f"Fichier {file_id} rejeté : non pétrolier"

        # ── Indexation RAG pour PDF et Word ──────────────────────
        # Indexation RAG avec doc_id pour isolation
        if file_type in ['pdf', 'docx'] and text:
            from apps.chatbot.rag_pipeline import index_document
            chunks = index_document(
                text,
                metadata={
                    'filename':    uploaded.original_name,
                    'file_type':   file_type,
                    'uploaded_by': str(uploaded.uploaded_by),
                    'doc_id':      str(uploaded.id),
                },
                doc_id=uploaded.id,
            )
            logger.info(f"RAG : {chunks} chunks indexés pour doc_{uploaded.id}")

        uploaded.status    = UploadedFile.Status.SUCCESS
        uploaded.error_msg = ''
        uploaded.save()

        return f"Fichier {file_id} traité avec succès"

    except UploadedFile.DoesNotExist:
        logger.error(f"Fichier {file_id} introuvable")
        return f"Fichier {file_id} introuvable"

    except Exception as exc:
        logger.error(f"Erreur traitement fichier {file_id} : {exc}")
        try:
            uploaded.status    = UploadedFile.Status.ERROR
            uploaded.error_msg = str(exc)
            uploaded.save()
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=60)