"""
Chroma vector storage module

ChromaDB-based vector storage implementation, supporting CRUD operations on documents.
Provides vector similarity retrieval and metadata filtering.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None
    Settings = None


class ChromaStorage:
    """
    Chroma vector storage class.

    Wraps the ChromaDB client, providing persistent storage and retrieval for documents.
    Supports vector similarity search, metadata filtering, and document management.

    Usage examples:
        >>> from kb.storage.chroma_storage import ChromaStorage
        >>> storage = ChromaStorage(path="~/.knowledge-base/db/chroma")
        >>> storage.add_documents(
        ...     ids=["doc1", "doc2"],
        ...     embeddings=[[0.1, 0.2], [0.3, 0.4]],
        ...     metadatas=[{"source": "file1"}, {"source": "file2"}],
        ...     documents=["text1", "text2"]
        ... )
        >>> results = storage.query(
        ...     embedding=[0.15, 0.25],
        ...     top_k=2
        ... )
    """

    def __init__(
        self,
        path: str,
        collection_name: str = "knowledge",
        **kwargs: Any
    ) -> None:
        """
        Initialize Chroma storage client.

        Args:
            path: Chroma database persistence path.
            collection_name: Collection name, defaults to "knowledge".
            **kwargs: Additional configuration parameters.

        Raises:
            ImportError: chromadb package not installed.
            ValueError: Invalid path.
        """
        if chromadb is None or Settings is None:
            raise ImportError(
                "chromadb package is required. Install it with: pip install chromadb"
            )

        # Expand path
        expanded_path = os.path.expanduser(path)
        self.path = Path(expanded_path)

        # Ensure directory exists
        self.path.mkdir(parents=True, exist_ok=True)

        self.collection_name = collection_name
        self.extra_kwargs = kwargs

        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=str(self.path),
            settings=Settings(
                anonymized_telemetry=False,
                **kwargs
            )
        )

        # Get or create collection.
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )

    def add_documents(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[str]] = None,
        **kwargs: Any
    ) -> bool:
        """
        Add documents to Chroma collection.

        Args:
            ids: List of document IDs.
            embeddings: List of document vectors.
            metadatas: List of document metadata, optional.
            documents: List of original document texts, optional.
            **kwargs: Additional add parameters.

        Returns:
            bool: Whether addition was successful.

        Raises:
            ValueError: Invalid parameters or length mismatch.
            Exception: Addition failed.
        """
        if not ids:
            raise ValueError("IDs list cannot be empty")

        if not embeddings:
            raise ValueError("Embeddings list cannot be empty")

        if len(ids) != len(embeddings):
            raise ValueError(
                f"IDs and embeddings must have the same length. "
                f"Got {len(ids)} IDs and {len(embeddings)} embeddings"
            )

        if metadatas is not None and len(metadatas) != len(ids):
            raise ValueError(
                f"Metadatas length must match IDs length. "
                f"Got {len(metadatas)} metadatas and {len(ids)} IDs"
            )

        if documents is not None and len(documents) != len(ids):
            raise ValueError(
                f"Documents length must match IDs length. "
                f"Got {len(documents)} documents and {len(ids)} IDs"
            )

        try:
            # Ensure metadatas is not None
            final_metadatas = metadatas if metadatas is not None else [{} for _ in ids]

            # Ensure documents is not None
            final_documents = documents if documents is not None else ["" for _ in ids]

            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=final_metadatas,
                documents=final_documents,
                **kwargs
            )
            return True

        except Exception as e:
            raise Exception(f"Failed to add documents: {str(e)}")

    def query(
        self,
        embedding: List[float],
        top_k: int = 5,
        where_filter: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Vector similarity retrieval.

        Args:
            embedding: Query vector.
            top_k: Number of most similar documents to return, defaults to 5.
            where_filter: Metadata filter conditions, optional.
                Examples:{"source": "file1", "category": "tech"}
            **kwargs: Additional query parameters.

        Returns:
            Dict[str, Any]: Query results containing the following fields:
                - ids: List of matching document IDs
                - distances: List of distances
                - metadatas: List of metadata.
                - documents: List of document texts

        Raises:
            ValueError: Query vector is empty.
            Exception: Query failed.
        """
        if not embedding:
            raise ValueError("Query embedding cannot be empty")

        try:
            query_params: Dict[str, Any] = {
                "query_embeddings": [embedding],
                "n_results": top_k,
            }

            if where_filter is not None:
                query_params["where"] = where_filter

            query_params.update(kwargs)

            results = self.collection.query(**query_params)

            # Format return results
            return {
                "ids": results["ids"][0] if results["ids"] else [],
                "distances": results["distances"][0] if results["distances"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else [],
                "documents": results["documents"][0] if results["documents"] else [],
            }

        except Exception as e:
            raise Exception(f"Failed to query documents: {str(e)}")

    def delete(self, ids: List[str], **kwargs: Any) -> bool:
        """
        Delete documents.

        Args:
            ids: List of document IDs to delete.
            **kwargs: Additional delete parameters.

        Returns:
            bool: Whether deletion was successful.

        Raises:
            ValueError: ID list is empty.
            Exception: Deletion failed.
        """
        if not ids:
            raise ValueError("IDs list cannot be empty")

        try:
            self.collection.delete(ids=ids, **kwargs)
            return True

        except Exception as e:
            raise Exception(f"Failed to delete documents: {str(e)}")

    def count(self) -> int:
        """
        Get number of documents in collection.

        Returns:
            int: Number of documents.

        Raises:
            Exception: Query failed.
        """
        try:
            return self.collection.count()
        except Exception as e:
            raise Exception(f"Failed to count documents: {str(e)}")

    def get(
        self,
        ids: Optional[List[str]] = None,
        where_filter: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Get documents (without vector retrieval).

        Args:
            ids: List of document IDs, optional.
            where_filter: Metadata filter conditions, optional.
            limit: Result count limit, optional.
            **kwargs: Additional query parameters.

        Returns:
            Dict[str, Any]: Query results containing the following fields:
                - ids: List of document IDs.
                - embeddings: List of vectors.
                - metadatas: List of metadata.
                - documents: List of document texts

        Raises:
            Exception: Query failed.
        """
        try:
            get_params: Dict[str, Any] = {}

            if ids is not None:
                get_params["ids"] = ids

            if where_filter is not None:
                get_params["where"] = where_filter

            if limit is not None:
                get_params["limit"] = limit

            get_params.update(kwargs)

            results = self.collection.get(**get_params)

            return {
                "ids": results["ids"] if results["ids"] else [],
                "embeddings": results["embeddings"] if results["embeddings"] else [],
                "metadatas": results["metadatas"] if results["metadatas"] else [],
                "documents": results["documents"] if results["documents"] else [],
            }

        except Exception as e:
            raise Exception(f"Failed to get documents: {str(e)}")

    def update(
        self,
        ids: List[str],
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[str]] = None,
        **kwargs: Any
    ) -> bool:
        """
        Update documents.

        Args:
            ids: List of document IDs.
            embeddings: New vector list, optional.
            metadatas: New metadata list, optional.
            documents: New document text list, optional.
            **kwargs: Additional update parameters.

        Returns:
            bool: Whether update was successful.

        Raises:
            ValueError: Invalid parameters or length mismatch.
            Exception: Update failed.
        """
        if not ids:
            raise ValueError("IDs list cannot be empty")

        try:
            update_params: Dict[str, Any] = {
                "ids": ids,
            }

            if embeddings is not None:
                update_params["embeddings"] = embeddings

            if metadatas is not None:
                update_params["metadatas"] = metadatas

            if documents is not None:
                update_params["documents"] = documents

            update_params.update(kwargs)

            self.collection.update(**update_params)
            return True

        except Exception as e:
            raise Exception(f"Failed to update documents: {str(e)}")

    def peek(self, limit: int = 10) -> Dict[str, Any]:
        """
        Preview documents in collection.

        Args:
            limit: Number to preview, defaults to 10.

        Returns:
            Dict[str, Any]: Preview results.

        Raises:
            Exception: Query failed.
        """
        try:
            results = self.collection.peek(limit=limit)

            return {
                "ids": results["ids"] if results["ids"] else [],
                "embeddings": results["embeddings"] if results["embeddings"] else [],
                "metadatas": results["metadatas"] if results["metadatas"] else [],
                "documents": results["documents"] if results["documents"] else [],
            }

        except Exception as e:
            raise Exception(f"Failed to peek documents: {str(e)}")

    def reset(self) -> bool:
        """
        Reset collection (delete all documents).

        Returns:
            bool: Whether reset was successful.

        Raises:
            Exception: Reset failed.
        """
        try:
            # Delete and recreate collection
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            return True

        except Exception as e:
            raise Exception(f"Failed to reset collection: {str(e)}")

    def close(self):
        """Release ChromaDB client resources."""
        self.client = None
        self.collection = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
