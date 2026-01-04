from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import Field

from app.infrastructure import BaseDocument, SoftDeletableDocument


class SampleProfile(BaseDocument):
    __collection_name__ = "profiles"

    name: str
    email: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SampleSoftDeletableProfile(SoftDeletableDocument):
    __collection_name__ = "profiles"

    name: str


class TestBaseDocument:
    def test_create_with_defaults(self) -> None:
        profile = SampleProfile(name="John", email="john@example.com")

        assert profile.id is not None
        assert len(profile.id) == 36
        assert profile.name == "John"
        assert profile.email == "john@example.com"
        assert profile.created_at is not None
        assert profile.updated_at is not None
        assert profile.metadata == {}

    def test_create_with_custom_id(self) -> None:
        profile = SampleProfile(id="custom-id", name="John", email="john@example.com")

        assert profile.id == "custom-id"

    def test_to_document(self) -> None:
        profile = SampleProfile(name="John", email="john@example.com")
        doc = profile.to_document()

        assert doc["_id"] == profile.id
        assert doc["name"] == "John"
        assert doc["email"] == "john@example.com"
        assert "created_at" in doc
        assert "updated_at" in doc

    def test_from_document(self) -> None:
        now = datetime.now(UTC)
        doc = {
            "_id": "test-id",
            "name": "Jane",
            "email": "jane@example.com",
            "created_at": now,
            "updated_at": now,
            "metadata": {"key": "value"},
        }

        profile = SampleProfile.from_document(doc)

        assert profile.id == "test-id"
        assert profile.name == "Jane"
        assert profile.email == "jane@example.com"
        assert profile.metadata == {"key": "value"}

    def test_update_timestamp(self) -> None:
        profile = SampleProfile(name="John", email="john@example.com")
        original_updated = profile.updated_at

        profile.update_timestamp()

        assert profile.updated_at >= original_updated

    def test_collection_name(self) -> None:
        assert SampleProfile.__collection_name__ == "profiles"

    def test_model_config_aliases(self) -> None:
        doc = {"_id": "test-id", "name": "John", "email": "john@example.com"}
        profile = SampleProfile.model_validate(doc)

        assert profile.id == "test-id"


class TestSoftDeletableDocumentClass:
    def test_default_not_deleted(self) -> None:
        profile = SampleSoftDeletableProfile(name="John")

        assert profile.is_deleted is False
        assert profile.deleted_at is None

    def test_soft_delete(self) -> None:
        profile = SampleSoftDeletableProfile(name="John")

        profile.soft_delete()

        assert profile.is_deleted is True
        assert profile.deleted_at is not None

    def test_restore(self) -> None:
        profile = SampleSoftDeletableProfile(name="John")
        profile.soft_delete()

        profile.restore()

        assert profile.is_deleted is False
        assert profile.deleted_at is None

    def test_to_document_includes_soft_delete_fields(self) -> None:
        profile = SampleSoftDeletableProfile(name="John")
        profile.soft_delete()

        doc = profile.to_document()

        assert doc["is_deleted"] is True
        assert doc["deleted_at"] is not None

    def test_from_document_with_deleted_state(self) -> None:
        now = datetime.now(UTC)
        doc = {
            "_id": "test-id",
            "name": "John",
            "is_deleted": True,
            "deleted_at": now,
            "created_at": now,
            "updated_at": now,
        }

        profile = SampleSoftDeletableProfile.from_document(doc)

        assert profile.is_deleted is True
        assert profile.deleted_at == now


class TestDocumentValidation:
    def test_missing_required_field_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SampleProfile(email="john@example.com")  # type: ignore[call-arg]

    def test_extra_fields_ignored(self) -> None:
        doc = {
            "_id": "test-id",
            "name": "John",
            "email": "john@example.com",
            "extra_field": "should be ignored",
        }

        profile = SampleProfile.from_document(doc)
        assert not hasattr(profile, "extra_field")

    def test_nested_metadata(self) -> None:
        profile = SampleProfile(
            name="John",
            email="john@example.com",
            metadata={
                "preferences": {"theme": "dark", "language": "en"},
                "tags": ["admin", "verified"],
            },
        )

        doc = profile.to_document()
        assert doc["metadata"]["preferences"]["theme"] == "dark"
        assert "admin" in doc["metadata"]["tags"]
