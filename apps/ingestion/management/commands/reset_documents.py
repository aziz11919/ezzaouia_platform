"""
Management command -- reinitialisation complete des documents et de ChromaDB.

Supprime :
  1. Tous les objets UploadedFile de la base de donnees
  2. Les fichiers physiques dans media/uploads/ et media/chat_uploads/
  3. Tout le contenu de chroma_db/ (collections + sqlite3)
  4. Recreee un repertoire chroma_db/ vide
  5. Reinitialise les caches memoire du pipeline RAG

NE TOUCHE PAS :
  - Les tables DWH (DimDate, FactProduction, DimWell, etc.)
  - Les utilisateurs et leurs donnees
  - Les sessions et messages du chatbot (sauf avec --also-clear-chat)

Usage :
    python manage.py reset_documents
    python manage.py reset_documents --dry-run
    python manage.py reset_documents --also-clear-chat
"""
import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.ingestion.models import UploadedFile

SEP = '-' * 60
SEP2 = '=' * 60


class Command(BaseCommand):
    help = 'Reinitialisation complete : documents BDD + fichiers media + ChromaDB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui serait supprime sans rien faire.',
        )
        parser.add_argument(
            '--also-clear-chat',
            action='store_true',
            help='Supprime aussi les sessions et messages du chatbot.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        also_clear_chat = options['also_clear_chat']

        if dry_run:
            self.stdout.write(self.style.WARNING(
                'MODE DRY-RUN -- aucune modification ne sera effectuee.\n'
            ))

        totals = {'db_files': 0, 'media_files': 0, 'chroma_entries': 0, 'chat_sessions': 0}

        # -- 1. Suppression BDD -------------------------------------------
        self.stdout.write(SEP)
        self.stdout.write('ETAPE 1 -- Suppression des documents en base de donnees')
        self.stdout.write(SEP)

        qs = UploadedFile.objects.all()
        totals['db_files'] = qs.count()
        self.stdout.write('  %d objet(s) UploadedFile trouve(s).' % totals['db_files'])

        if not dry_run and totals['db_files'] > 0:
            qs.delete()
            self.stdout.write(self.style.SUCCESS(
                '  OK -- %d objet(s) supprime(s).' % totals['db_files']
            ))
        elif dry_run:
            self.stdout.write(
                '  [dry-run] %d objet(s) seraient supprimes.' % totals['db_files']
            )

        # -- 2. Suppression fichiers physiques ----------------------------
        self.stdout.write('\n' + SEP)
        self.stdout.write('ETAPE 2 -- Suppression des fichiers physiques (media/)')
        self.stdout.write(SEP)

        media_root = settings.MEDIA_ROOT
        media_dirs = [
            os.path.join(media_root, 'uploads'),
            os.path.join(media_root, 'chat_uploads'),
        ]

        for media_dir in media_dirs:
            if not os.path.isdir(media_dir):
                self.stdout.write('  Repertoire absent (ignore) : %s' % media_dir)
                continue

            count = sum(len(files) for _, _, files in os.walk(media_dir))
            self.stdout.write('  %s  ->  %d fichier(s)' % (media_dir, count))
            totals['media_files'] += count

            if not dry_run:
                shutil.rmtree(media_dir)
                os.makedirs(media_dir, exist_ok=True)
                self.stdout.write(self.style.SUCCESS('  OK -- vide et recree.'))
            else:
                self.stdout.write(
                    '  [dry-run] %d fichier(s) seraient supprimes.' % count
                )

        # -- 3. Reinitialisation ChromaDB ---------------------------------
        self.stdout.write('\n' + SEP)
        self.stdout.write('ETAPE 3 -- Reinitialisation de ChromaDB')
        self.stdout.write(SEP)

        chroma_dir = settings.CHROMA_PERSIST_DIR
        if os.path.isdir(chroma_dir):
            entries = os.listdir(chroma_dir)
            totals['chroma_entries'] = len(entries)
            preview = ', '.join(entries[:8]) + ('...' if len(entries) > 8 else '')
            self.stdout.write('  Repertoire : %s' % chroma_dir)
            self.stdout.write('  %d entree(s) : %s' % (totals['chroma_entries'], preview))

            if not dry_run:
                for entry in entries:
                    entry_path = os.path.join(chroma_dir, entry)
                    try:
                        if os.path.isdir(entry_path):
                            shutil.rmtree(entry_path)
                        else:
                            os.remove(entry_path)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(
                            '  Erreur suppression %s : %s' % (entry, e)
                        ))
                self.stdout.write(self.style.SUCCESS(
                    '  OK -- ChromaDB entierement vide (repertoire conserve car bind mount).'
                ))
            else:
                self.stdout.write(
                    '  [dry-run] %d entree(s) seraient supprimees.' % totals['chroma_entries']
                )
        else:
            self.stdout.write(self.style.WARNING(
                '  Repertoire ChromaDB introuvable : %s' % chroma_dir
            ))
            if not dry_run:
                os.makedirs(chroma_dir, exist_ok=True)
                self.stdout.write('  Repertoire vide cree.')

        # -- 4. Reset caches memoire RAG ----------------------------------
        self.stdout.write('\n' + SEP)
        self.stdout.write('ETAPE 4 -- Reinitialisation des caches memoire RAG')
        self.stdout.write(SEP)

        if not dry_run:
            try:
                from apps.chatbot import rag_pipeline
                rag_pipeline._global_vectorstore = None
                rag_pipeline._vectorstores = {}
                if hasattr(rag_pipeline, '_llm'):
                    rag_pipeline._llm = None
                if hasattr(rag_pipeline, '_embeddings'):
                    rag_pipeline._embeddings = None
                self.stdout.write(self.style.SUCCESS('  OK -- caches RAG reinitialises.'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    '  Impossible de reinitialiser les caches : %s' % e
                ))
        else:
            self.stdout.write('  [dry-run] caches RAG seraient reinitialises.')

        # -- 5. (Optionnel) Suppression chat ------------------------------
        if also_clear_chat:
            self.stdout.write('\n' + SEP)
            self.stdout.write('ETAPE 5 -- Suppression des sessions chatbot')
            self.stdout.write(SEP)

            from apps.chatbot.models import ChatSession, ChatMessage
            session_count = ChatSession.objects.count()
            msg_count = ChatMessage.objects.count()
            totals['chat_sessions'] = session_count
            self.stdout.write('  %d session(s), %d message(s)' % (session_count, msg_count))

            if not dry_run:
                ChatSession.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(
                    '  OK -- %d session(s) supprimee(s).' % session_count
                ))
            else:
                self.stdout.write(
                    '  [dry-run] %d session(s) seraient supprimees.' % session_count
                )

        # -- Recapitulatif ------------------------------------------------
        self.stdout.write('\n' + SEP2)
        if dry_run:
            self.stdout.write(self.style.WARNING(
                'DRY-RUN TERMINE -- aucune modification effectuee.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                'RESET TERMINE -- plateforme prete pour un import propre.'
            ))
        self.stdout.write(SEP2)
        self.stdout.write('  Documents BDD supprimes   : %d' % totals['db_files'])
        self.stdout.write('  Fichiers media supprimes  : %d' % totals['media_files'])
        self.stdout.write('  Entrees ChromaDB supprimees: %d' % totals['chroma_entries'])
        if also_clear_chat:
            self.stdout.write('  Sessions chatbot supprimees: %d' % totals['chat_sessions'])
        self.stdout.write(SEP2)

        # -- Verification post-reset --------------------------------------
        if not dry_run:
            self.stdout.write('\nVERIFICATION :')
            db_remaining = UploadedFile.objects.count()
            chroma_remaining = len(os.listdir(chroma_dir)) if os.path.isdir(chroma_dir) else 0
            media_files_remaining = sum(
                len(files)
                for d in media_dirs
                if os.path.isdir(d)
                for _, _, files in os.walk(d)
            )
            ok = lambda n: 'OK' if n == 0 else 'PROBLEME'
            self.stdout.write('  UploadedFile.objects.count() = %d  [%s]' % (db_remaining, ok(db_remaining)))
            self.stdout.write('  chroma_db/ entrees restantes = %d  [%s]' % (chroma_remaining, ok(chroma_remaining)))
            self.stdout.write('  Fichiers media restants      = %d  [%s]' % (media_files_remaining, ok(media_files_remaining)))
