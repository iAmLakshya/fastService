from typing import TYPE_CHECKING, Any, Generic, TypeVar, get_args, get_origin

from app.infrastructure.persistence.adapters import MongoAdapter, get_registry
from app.infrastructure.persistence.adapters.protocols import DatabaseType
from app.infrastructure.persistence.document import BaseDocument

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection

DocT = TypeVar("DocT")


def _extract_document_type(cls: type) -> type[BaseDocument] | None:
    for base in getattr(cls, "__orig_bases__", []):
        origin = get_origin(base)
        if origin is not None:
            args = get_args(base)
            if args and isinstance(args[0], type) and issubclass(args[0], BaseDocument):
                return args[0]
    return None


class BaseDocumentRepository(Generic[DocT]):
    collection_name: str
    document_class: type[DocT] | None = None
    adapter_name: str | None = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.document_class is None:
            doc_type = _extract_document_type(cls)
            if doc_type is not None:
                cls.document_class = doc_type  # type: ignore[assignment]
                if hasattr(doc_type, "__collection_name__"):
                    cls.collection_name = doc_type.__collection_name__

    def __init__(self) -> None:
        self._adapter: MongoAdapter | None = None

    def _get_adapter(self) -> MongoAdapter:
        if self._adapter is None:
            registry = get_registry()
            if self.adapter_name:
                self._adapter = registry.get_typed(self.adapter_name, MongoAdapter)
            else:
                adapter = registry.get_default(DatabaseType.DOCUMENT)
                if not isinstance(adapter, MongoAdapter):
                    raise TypeError("Default document adapter is not MongoAdapter")
                self._adapter = adapter
        return self._adapter

    @property
    def _collection(self) -> "AsyncIOMotorCollection":
        return self._get_adapter().collection(self.collection_name)

    def _to_model(self, doc: dict[str, Any] | None) -> DocT | None:
        if doc is None:
            return None
        if self.document_class is not None:
            return self.document_class.from_document(doc)
        return doc

    def _to_models(self, docs: list[dict[str, Any]]) -> list[DocT]:
        if self.document_class is not None:
            return [self.document_class.from_document(d) for d in docs]
        return docs

    def _to_document(self, obj: DocT | dict[str, Any]) -> dict[str, Any]:
        if isinstance(obj, BaseDocument):
            obj.update_timestamp()
            return obj.to_document()
        return obj

    async def find_by_id(self, document_id: str) -> DocT | None:
        doc = await self._collection.find_one({"_id": document_id})
        return self._to_model(doc)

    async def find_one(self, filter: dict[str, Any]) -> DocT | None:
        doc = await self._collection.find_one(filter)
        return self._to_model(doc)

    async def find_many(
        self,
        filter: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 100,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[DocT]:
        cursor = self._collection.find(filter or {})
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return self._to_models(docs)

    async def count_documents(self, filter: dict[str, Any] | None = None) -> int:
        return await self._collection.count_documents(filter or {})

    async def distinct(self, field: str, filter: dict[str, Any] | None = None) -> list[Any]:
        return await self._collection.distinct(field, filter or {})

    async def aggregate(self, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cursor = self._collection.aggregate(pipeline)
        return await cursor.to_list(length=None)

    async def insert_one(self, document: DocT | dict[str, Any]) -> DocT:
        doc_data = self._to_document(document)
        result = await self._collection.insert_one(doc_data)
        inserted = await self.find_by_id(str(result.inserted_id))
        if inserted is None:
            raise RuntimeError(f"Document not found after insert: {result.inserted_id}")
        return inserted

    async def insert_many(self, documents: list[DocT | dict[str, Any]]) -> list[DocT]:
        if not documents:
            return []
        docs_data = [self._to_document(d) for d in documents]
        await self._collection.insert_many(docs_data)
        return self._to_models(docs_data)

    async def update_one(
        self,
        filter: dict[str, Any],
        update: dict[str, Any],
        upsert: bool = False,
    ) -> DocT | None:
        await self._collection.update_one(filter, {"$set": update}, upsert=upsert)
        return await self.find_one(filter)

    async def update_many(
        self,
        filter: dict[str, Any],
        update: dict[str, Any],
    ) -> int:
        result = await self._collection.update_many(filter, {"$set": update})
        return result.modified_count

    async def delete_one(self, filter: dict[str, Any]) -> bool:
        result = await self._collection.delete_one(filter)
        return result.deleted_count > 0

    async def delete_many(self, filter: dict[str, Any]) -> int:
        result = await self._collection.delete_many(filter)
        return result.deleted_count

    async def replace_one(
        self,
        filter: dict[str, Any],
        replacement: DocT | dict[str, Any],
        upsert: bool = False,
    ) -> DocT | None:
        doc_data = self._to_document(replacement)
        await self._collection.replace_one(filter, doc_data, upsert=upsert)
        return await self.find_one(filter)

    async def save(self, document: DocT) -> DocT:
        doc_data = self._to_document(document)
        doc_id = doc_data.get("_id")
        if doc_id:
            await self._collection.replace_one({"_id": doc_id}, doc_data, upsert=True)
        else:
            await self._collection.insert_one(doc_data)
        result = self._to_model(doc_data)
        if result is None:
            raise RuntimeError("Failed to convert document after save")
        return result
