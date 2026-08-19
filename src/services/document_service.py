"""Document service – patient document storage with upload security.

Implements the file-handling security rules from the start (this is
new code, so nothing is retrofitted later):

* **Extension allow-list** — only ``.pdf``, ``.jpg``, ``.jpeg``,
  ``.png``, ``.dcm`` are accepted.
* **Magic-byte content verification** — the file's leading bytes must
  match its declared extension; the extension alone is never trusted.
* **Max file size enforced before full read** — the size is checked
  via ``os.path.getsize`` *before* any content is copied.
* **Random storage filename** — files are stored under a ``uuid4``
  name; the original filename is kept only as ``document_name``
  metadata.
* **Path-traversal-safe resolution** — every resolved path (store and
  delete) is confirmed to stay inside the configured upload base
  directory via ``os.path.realpath`` + ``commonpath``.

The validation helpers (``validate_document_file`` /
``resolve_upload_path``) are module-level so the visit-level test
report upload path (``ClinicalController``) can reuse the exact same
rules instead of maintaining a second, weaker implementation.
"""
from __future__ import annotations

import logging
import os
import shutil
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.config import app_config
from src.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)

# ── Upload policy ──────────────────────────────────────────────

# Extension allow-list (lowercase, with leading dot).
ALLOWED_EXTENSIONS: Tuple[str, ...] = (".pdf", ".jpg", ".jpeg", ".png", ".dcm")

# Maximum upload size in bytes (10 MB) — checked before any full read.
MAX_FILE_SIZE: int = 10 * 1024 * 1024

# Upload base directory — every stored file must resolve inside this.
UPLOAD_DIR: str = os.path.join(app_config.ASSETS_DIR, "patient_documents")

# Map extension → magic-byte signature to verify.
_MAGIC_BYTES: Dict[str, bytes] = {
    ".pdf": b"%PDF",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG\r\n\x1a\n",
    ".dcm": b"DICM",  # DICOM preamble: "DICM" at byte offset 128
}

# DICOM stores its magic at offset 128 in the preamble.
_DICOM_MAGIC_OFFSET: int = 128


# ── Shared validation helpers (also used by the test-report path) ─

def validate_document_file(
    file_path: str,
    allowed_extensions: Tuple[str, ...] = ALLOWED_EXTENSIONS,
    max_size: int = MAX_FILE_SIZE,
) -> Tuple[bool, str]:
    """Validate a file against the upload policy.

    Checks, in order: existence, extension allow-list, size cap
    (before any content read), and magic-byte content verification.

    Args:
        file_path: The source file path.
        allowed_extensions: Extensions permitted (default allow-list).
        max_size: Maximum size in bytes.

    Returns:
        Tuple of (valid, error_message).
    """
    if not file_path or not os.path.isfile(file_path):
        return False, "File not found."

    name, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext not in allowed_extensions:
        allowed = ", ".join(allowed_extensions)
        return False, f"Unsupported file type '{ext}'. Allowed: {allowed}."

    # Size check BEFORE reading/copying the content.
    try:
        size = os.path.getsize(file_path)
    except OSError:
        return False, "Could not read the file."
    if size <= 0:
        return False, "The selected file is empty."
    if size > max_size:
        return False, (
            f"File is too large ({size / (1024 * 1024):.1f} MB). "
            f"Maximum size is {max_size / (1024 * 1024):.0f} MB."
        )

    if not _matches_magic_bytes(file_path, ext):
        return False, (
            "File content does not match its extension and was rejected."
        )

    return True, ""


def _matches_magic_bytes(file_path: str, ext: str) -> bool:
    """Verify the file's leading bytes match its extension.

    Args:
        file_path: The source file path.
        ext: Lowercase extension (with dot).

    Returns:
        True if the magic bytes match (or no signature is defined).
    """
    signature = _MAGIC_BYTES.get(ext)
    if signature is None:
        return True  # Extension in the allow-list but no signature defined
    try:
        with open(file_path, "rb") as fh:
            if ext == ".dcm":
                fh.seek(_DICOM_MAGIC_OFFSET)
                head = fh.read(len(signature))
            else:
                head = fh.read(len(signature))
        return head == signature
    except OSError:
        return False


def resolve_upload_path(base_dir: str, filename: str) -> Optional[str]:
    """Resolve ``base_dir/filename`` and confirm it stays inside base_dir.

    Path-traversal guard: after joining and realpath-ing, the result
    must share ``base_dir`` as a common prefix.  Returns None when the
    resolved path would escape the base directory (or doesn't exist
    for deletion purposes — existence is the caller's concern).

    Args:
        base_dir: The configured upload base directory.
        filename: The storage filename (never user-supplied path text).

    Returns:
        The safe absolute path, or None if it escapes the base dir.
    """
    base = os.path.realpath(base_dir)
    candidate = os.path.realpath(os.path.join(base, filename))
    if candidate != base and not candidate.startswith(base + os.sep):
        return None
    return candidate


def random_storage_name(original_path: str) -> str:
    """Return a random uuid4 storage filename with the original extension.

    The original filename is never used for storage — only its
    extension is preserved so the file remains identifiable.

    Args:
        original_path: The source file path.

    Returns:
        Storage filename like ``a1b2c3d4....pdf``.
    """
    ext = os.path.splitext(original_path)[1].lower()
    return f"{uuid.uuid4().hex}{ext}"


# ── Service ────────────────────────────────────────────────────


class DocumentService:
    """Handles patient document storage, listing, and deletion."""

    def __init__(self, repo: Optional[DocumentRepository] = None) -> None:
        """Initialize DocumentService.

        Args:
            repo: Repository to use (injectable for tests).
                Defaults to the real ``DocumentRepository``.
        """
        self._repo = repo or DocumentRepository()

    # ── Upload ─────────────────────────────────────────────────

    def upload_document(
        self,
        patient_id: str,
        file_path: str,
        uploaded_by: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        """Validate and store a document for a patient.

        The file is validated (extension, size, magic bytes), stored
        under a random uuid4 name inside the upload directory, and its
        metadata recorded in ``patient_documents``.  The original
        filename is kept only as metadata.

        Args:
            patient_id: The patient the document belongs to.
            file_path: Source file path.
            uploaded_by: User uploading (audit metadata).

        Returns:
            Tuple of (success, message, document_id_or_None).
        """
        if not patient_id or not str(patient_id).strip():
            return False, "Patient is required.", None

        valid, msg = validate_document_file(file_path)
        if not valid:
            return False, msg, None

        storage_name = random_storage_name(file_path)
        dest_path = resolve_upload_path(UPLOAD_DIR, storage_name)
        if dest_path is None:
            logger.error(
                "Path traversal blocked for storage name: %r", storage_name,
            )
            return False, "Upload failed. Please try again.", None

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        try:
            shutil.copy2(file_path, dest_path)
        except OSError as e:
            logger.error("Failed to copy document file: %s", e)
            return False, "Failed to save the file.", None

        try:
            file_size = os.path.getsize(dest_path)
        except OSError:
            file_size = os.path.getsize(file_path)

        file_type = os.path.splitext(file_path)[1].lstrip(".").upper()

        data: Dict[str, Any] = {
            "patient_id": patient_id,
            "document_name": os.path.basename(file_path),
            "file_path": dest_path,
            "file_type": file_type,
            "file_size": file_size,
            "uploaded_by": uploaded_by,
            "upload_date": datetime.now(),
        }
        document_id = self._repo.create_document(data)

        logger.info(
            "Document uploaded: id=%d patient=%s size=%d",
            document_id, patient_id, file_size,
        )
        return True, "Document uploaded successfully.", document_id

    # ── Queries ────────────────────────────────────────────────

    def list_documents(self, patient_id: str) -> List[Dict[str, Any]]:
        """Return all documents for a patient, newest first.

        Args:
            patient_id: The patient ID.

        Returns:
            List of document records.
        """
        return self._repo.find_by_patient(patient_id)

    def get_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Return a document record by ID.

        Args:
            document_id: The document ID.

        Returns:
            Document record or None.
        """
        return self._repo.find_by_id(document_id)

    # ── Delete ─────────────────────────────────────────────────

    def delete_document(self, document_id: int) -> Tuple[bool, str]:
        """Delete a document record and its stored file.

        The stored file is only removed if its resolved path is
        confirmed to stay inside the upload base directory.

        Args:
            document_id: The document ID.

        Returns:
            Tuple of (success, message).
        """
        doc = self._repo.find_by_id(document_id)
        if not doc:
            return False, "Document not found."

        stored = doc.get("file_path", "")
        if stored:
            # Never trust the stored path blindly — resolve and verify
            # it still lives inside the upload directory.
            resolved = resolve_upload_path(
                UPLOAD_DIR, os.path.basename(stored),
            )
            if resolved is not None and os.path.isfile(resolved):
                try:
                    os.remove(resolved)
                except OSError as e:
                    logger.warning("Failed to remove document file: %s", e)

        self._repo.delete_document(document_id)
        logger.info("Document deleted: %s", document_id)
        return True, "Document deleted successfully."
