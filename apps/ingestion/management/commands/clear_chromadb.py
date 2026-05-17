"""
Management command to wipe all ChromaDB indexed data.

Deletes:
  - The global collection 'ezzaouia_global'
  - All per-document collections (doc_* subdirectories)

Usage:
    python manage.py clear_chromadb
    python manage.py clear_chromadb --reset-status   # also marks DB files as 'pending'
    python manage.py clear_chromadb --dry-run
"""
import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.ingestion.models import UploadedFile


class Command(BaseCommand):
    help = 'Supprime tous les documents indexés dans ChromaDB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-status',
            action='store_true',
            help='Remet le statut des fichiers PDF/DOCX à "pending" dans la base de données.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui serait supprimé sans rien faire.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        reset_status = options['reset_status']
        chroma_dir = settings.CHROMA_PERSIST_DIR

        if not os.path.isdir(chroma_dir):
            self.stdout.write(self.style.WARNING(f'Répertoire ChromaDB introuvable : {chroma_dir}'))
            return

        # ── 1. Collection globale ─────────────────────────────────────────
        self.stdout.write('Suppression de la collection globale "ezzaouia_global"...')
        if not dry_run:
            try:
                import chromadb
                client = chromadb.PersistentClient(path=chroma_dir)
                client.delete_collection('ezzaouia_global')
                self.stdout.write(self.style.SUCCESS('  OK — collection globale supprimée.'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Collection globale absente ou erreur : {e}'))
        else:
            self.stdout.write('  [dry-run] collection globale "ezzaouia_global" serait supprimée.')

        # ── 2. Collections par document (doc_* dirs) ──────────────────────
        doc_dirs = [
            d for d in os.listdir(chroma_dir)
            if d.startswith('doc_') and os.path.isdir(os.path.join(chroma_dir, d))
        ]

        if not doc_dirs:
            self.stdout.write('Aucun répertoire par document trouvé.')
        else:
            self.stdout.write(f'Suppression de {len(doc_dirs)} répertoire(s) par document...')
            for d in doc_dirs:
                full_path = os.path.join(chroma_dir, d)
                if dry_run:
                    self.stdout.write(f'  [dry-run] {full_path}')
                else:
                    try:
                        shutil.rmtree(full_path)
                        self.stdout.write(f'  Supprimé : {full_path}')
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  Erreur sur {full_path} : {e}'))

        # ── 3. Reset caches mémoire rag_pipeline ─────────────────────────
        if not dry_run:
            try:
                from apps.chatbot import rag_pipeline
                rag_pipeline._global_vectorstore = None
                rag_pipeline._vectorstores = {}
                self.stdout.write('  Caches mémoire RAG réinitialisés.')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Impossible de réinitialiser les caches : {e}'))

        # ── 4. (Optionnel) Reset statut BDD ──────────────────────────────
        if reset_status:
            qs = UploadedFile.objects.filter(
                status=UploadedFile.Status.SUCCESS,
                file_type__in=['pdf', 'docx'],
            )
            count = qs.count()
            self.stdout.write(f'Reset statut BDD : {count} fichier(s) → pending...')
            if not dry_run:
                qs.update(status=UploadedFile.Status.PENDING)
                self.stdout.write(self.style.SUCCESS(f'  {count} fichier(s) remis à "pending".'))
            else:
                self.stdout.write(f'  [dry-run] {count} fichier(s) seraient remis à "pending".')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n[dry-run] Aucune modification effectuée.'))
        else:
            self.stdout.write(self.style.SUCCESS('\nChromaDB entièrement vidé.'))
