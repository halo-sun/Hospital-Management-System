"""Unit tests for the DocumentService — upload security rules.

Covers the Phase 4 file-handling policy with real temp files:
extension allow-list, magic-byte verification, max-size enforcement
before any full read, uuid4 storage naming, path-traversal-safe
resolution, and the upload/list/delete round-trip (with the
repository mocked).
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from src.services.document_service import (
    ALLOWED_EXTENSIONS,
    DocumentService,
    MAX_FILE_SIZE,
    random_storage_name,
    resolve_upload_path,
    validate_document_file,
)

# ── Real file fixtures (security checks need real bytes) ──────


@pytest.fixture
def files_dir(tmp_path: Path) -> Path:
    """A scratch directory for upload sources and the storage base."""
    return tmp_path


def _write(file_path: Path, content: bytes) -> Path:
    file_path.write_bytes(content)
    return file_path


@pytest.fixture
def pdf_file(files_dir: Path) -> Path:
    """A file with real PDF magic bytes."""
    return _write(files_dir / "scan.pdf", b"%PDF-1.4\n%test")


@pytest.fixture
def png_file(files_dir: Path) -> Path:
    """A file with real PNG magic bytes."""
    return _write(files_dir / "photo.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)


@pytest.fixture
def jpg_file(files_dir: Path) -> Path:
    """A file with real JPEG magic bytes."""
    return _write(files_dir / "xray.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 32)


@pytest.fixture
def dcm_file(files_dir: Path) -> Path:
    """A file with a DICOM magic at offset 128."""
    return _write(files_dir / "study.dcm", b"\x00" * 128 + b"DICM")


@pytest.fixture
def fake_pdf(files_dir: Path) -> Path:
    """A file named .pdf whose content is NOT a PDF (spoof attempt)."""
    return _write(files_dir / "evil.pdf", b"MZ\x90\x00 not a pdf")


@pytest.fixture
def big_file(files_dir: Path) -> Path:
    """A file over the size cap."""
    return _write(files_dir / "huge.pdf", b"%PDF" + b"x" * (MAX_FILE_SIZE + 1))


# ── validate_document_file ────────────────────────────────────


class TestValidateDocumentFile:
    """Extension allow-list, size cap, magic-byte checks."""

    def test_missing_file_rejected(self) -> None:
        valid, msg = validate_document_file("/nonexistent/file.pdf")
        assert valid is False
        assert "not found" in msg.lower()

    def test_disallowed_extension_rejected(self, files_dir: Path) -> None:
        f = _write(files_dir / "notes.txt", b"hello")
        valid, msg = validate_document_file(str(f))
        assert valid is False
        assert "unsupported file type" in msg.lower()
        assert ".pdf" in msg  # lists the allow-list

    def test_valid_pdf_accepted(self, pdf_file: Path) -> None:
        valid, msg = validate_document_file(str(pdf_file))
        assert valid is True
        assert msg == ""

    def test_valid_png_accepted(self, png_file: Path) -> None:
        assert validate_document_file(str(png_file))[0] is True

    def test_valid_jpg_accepted(self, jpg_file: Path) -> None:
        assert validate_document_file(str(jpg_file))[0] is True

    def test_valid_dcm_accepted(self, dcm_file: Path) -> None:
        assert validate_document_file(str(dcm_file))[0] is True

    def test_magic_byte_mismatch_rejected(self, fake_pdf: Path) -> None:
        """A .pdf that isn't a PDF is rejected — extension alone is not trusted."""
        valid, msg = validate_document_file(str(fake_pdf))
        assert valid is False
        assert "content does not match" in msg.lower()

    def test_empty_file_rejected(self, files_dir: Path) -> None:
        f = _write(files_dir / "empty.pdf", b"")
        valid, msg = validate_document_file(str(f))
        assert valid is False
        assert "empty" in msg.lower()

    def test_oversize_file_rejected_before_read(self, big_file: Path) -> None:
        """The size cap trips before any content is read/copied."""
        with patch("src.services.document_service._matches_magic_bytes") as magic:
            valid, msg = validate_document_file(str(big_file))
            assert valid is False
            assert "too large" in msg.lower()
            magic.assert_not_called()  # never reached the content check

    def test_size_check_happens_before_copy(self, big_file: Path) -> None:
        """Enforcement happens at validation time (service stores after)."""
        service = DocumentService(repo=MagicMock())
        ok, msg, _ = service.upload_document("PAT-1", str(big_file))
        assert ok is False
        assert "too large" in msg.lower()
        service._repo.create_document.assert_not_called()


# ── Storage naming / path resolution ──────────────────────────


class TestStorageSecurity:
    """uuid4 names and path-traversal-safe resolution."""

    def test_random_storage_name_keeps_extension(self) -> None:
        """Storage names are random and keep only the extension."""
        name1 = random_storage_name("/some/dir/Scan Final.PDF")
        name2 = random_storage_name("/some/dir/Scan Final.PDF")
        assert name1 != name2  # random
        assert name1.endswith(".pdf")
        # No original filename residue — storage name is purely random.
        assert "Scan" not in name1 and "Final" not in name1

    def test_storage_name_is_hex_uuid(self) -> None:
        name = random_storage_name("a.png")
        stem = name[:-4]
        assert len(stem) == 32  # uuid4().hex
        int(stem, 16)  # raises if not hex

    def test_resolve_within_base(self, files_dir: Path) -> None:
        base = str(files_dir / "uploads")
        os.makedirs(base, exist_ok=True)
        resolved = resolve_upload_path(base, "abc.pdf")
        assert resolved is not None
        assert resolved.startswith(os.path.realpath(base) + os.sep)

    def test_resolve_traversal_blocked(self, files_dir: Path) -> None:
        base = str(files_dir / "uploads")
        os.makedirs(base, exist_ok=True)
        # A traversal attempt must NOT resolve inside the base.
        assert resolve_upload_path(base, "../../etc/passwd") is None
        assert resolve_upload_path(base, "..") is None


# ── Service upload / list / delete ────────────────────────────


@pytest.fixture
def service() -> DocumentService:
    """A DocumentService with a mocked repository."""
    return DocumentService(repo=MagicMock())


@pytest.fixture
def mock_repo(service: DocumentService) -> MagicMock:
    """Access the mocked DocumentRepository."""
    return service._repo


class TestUpload:
    """upload_document stores securely and records metadata."""

    def test_upload_success(self, service: DocumentService,
                            mock_repo: MagicMock, pdf_file: Path,
                            tmp_path: Path) -> None:
        """A valid file is stored under a random name and recorded."""
        with patch(
            "src.services.document_service.UPLOAD_DIR", str(tmp_path / "uploads"),
        ):
            mock_repo.create_document.return_value = 11
            ok, msg, doc_id = service.upload_document(
                "PAT-00001", str(pdf_file), uploaded_by=7,
            )
            assert ok is True
            assert doc_id == 11

            call_data = mock_repo.create_document.call_args.args[0]
            assert call_data["patient_id"] == "PAT-00001"
            # Original filename kept as metadata only…
            assert call_data["document_name"] == "scan.pdf"
            # …while the stored path is a random uuid4 name inside the base.
            stored = call_data["file_path"]
            assert stored.startswith(os.path.realpath(str(tmp_path / "uploads")) + os.sep)
            assert os.path.basename(stored).endswith(".pdf")
            assert os.path.exists(stored)  # the file was actually written
            assert call_data["uploaded_by"] == 7
            assert call_data["file_type"] == "PDF"
            assert call_data["file_size"] == len(b"%PDF-1.4\n%test")

    def test_upload_missing_patient_rejected(self, service: DocumentService,
                                             mock_repo: MagicMock,
                                             pdf_file: Path) -> None:
        ok, msg, _ = service.upload_document("", str(pdf_file))
        assert ok is False
        assert "patient" in msg.lower()
        mock_repo.create_document.assert_not_called()

    def test_upload_invalid_file_rejected(self, service: DocumentService,
                                          mock_repo: MagicMock,
                                          fake_pdf: Path) -> None:
        """A spoofed file never reaches the repository."""
        ok, msg, _ = service.upload_document("PAT-1", str(fake_pdf))
        assert ok is False
        mock_repo.create_document.assert_not_called()

    def test_upload_traversal_never_stored(self, service: DocumentService,
                                           mock_repo: MagicMock,
                                           pdf_file: Path,
                                           tmp_path: Path) -> None:
        """Even a hostile storage name cannot escape the upload base."""
        with (
            patch("src.services.document_service.UPLOAD_DIR", str(tmp_path / "uploads")),
            patch(
                "src.services.document_service.random_storage_name",
                return_value="../../evil.pdf",
            ),
        ):
            ok, msg, _ = service.upload_document("PAT-1", str(pdf_file))
            assert ok is False
            mock_repo.create_document.assert_not_called()


class TestListAndDelete:
    """list_documents / get_document / delete_document."""

    def test_list_delegates(self, service: DocumentService,
                            mock_repo: MagicMock) -> None:
        rows = [{"document_id": 1, "document_name": "scan.pdf"}]
        mock_repo.find_by_patient.return_value = rows
        assert service.list_documents("PAT-1") == rows
        mock_repo.find_by_patient.assert_called_once_with("PAT-1")

    def test_get_delegates(self, service: DocumentService,
                           mock_repo: MagicMock) -> None:
        mock_repo.find_by_id.return_value = {"document_id": 3}
        assert service.get_document(3) == {"document_id": 3}
        mock_repo.find_by_id.assert_called_once_with(3)

    def test_delete_not_found(self, service: DocumentService,
                              mock_repo: MagicMock) -> None:
        mock_repo.find_by_id.return_value = None
        ok, msg = service.delete_document(99)
        assert ok is False
        assert "not found" in msg.lower()

    def test_delete_removes_row_and_file(self, service: DocumentService,
                                         mock_repo: MagicMock,
                                         tmp_path: Path) -> None:
        """Deleting removes the stored file (safe path) and the row."""
        base = tmp_path / "uploads"
        base.mkdir()
        stored = base / "abcd1234.pdf"
        stored.write_bytes(b"%PDF")
        mock_repo.find_by_id.return_value = {
            "document_id": 1, "file_path": str(stored),
        }
        with patch("src.services.document_service.UPLOAD_DIR", str(base)):
            ok, msg = service.delete_document(1)
            assert ok is True
            assert not stored.exists()  # file removed
            mock_repo.delete_document.assert_called_once_with(1)

    def test_delete_never_removes_outside_base(self, service: DocumentService,
                                               mock_repo: MagicMock,
                                               tmp_path: Path) -> None:
        """A stored path pointing outside the base dir is never removed."""
        victim = tmp_path / "victim.pdf"
        victim.write_bytes(b"%PDF")
        mock_repo.find_by_id.return_value = {
            "document_id": 1, "file_path": str(victim),
        }
        base = tmp_path / "uploads"
        base.mkdir()
        with patch("src.services.document_service.UPLOAD_DIR", str(base)):
            service.delete_document(1)
            assert victim.exists()  # untouched — outside the base
            mock_repo.delete_document.assert_called_once_with(1)

    def test_delete_without_file_skips_removal(self, service: DocumentService,
                                               mock_repo: MagicMock) -> None:
        mock_repo.find_by_id.return_value = {
            "document_id": 1, "file_path": "",
        }
        ok, _ = service.delete_document(1)
        assert ok is True
        mock_repo.delete_document.assert_called_once_with(1)
