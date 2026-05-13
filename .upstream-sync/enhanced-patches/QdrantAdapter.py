import asyncio
from typing import List, Optional, Any, Union
from pydantic import BaseModel
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
    FilterSelector,
)

from cognee.infrastructure.databases.exceptions import MissingQueryParameterError
from cognee.infrastructure.engine import DataPoint
from cognee.infrastructure.engine.utils import parse_id
from cognee.modules.storage.utils import get_own_properties
from cognee.infrastructure.databases.vector.exceptions import CollectionNotFoundError

from ..embeddings.EmbeddingEngine import EmbeddingEngine
from ..models.ScoredResult import ScoredResult
from ..utils import normalize_distances
from ..vector_db_interface import VectorDBInterface


class IndexSchema(DataPoint):
    """
    Represents a schema for an index data point containing an ID and text.

    Attributes:
    - id: A string representing the unique identifier for the data point.
    - text: A string representing the content of the data point.
    - metadata: A dictionary with default index fields for the schema.
    """

    id: str
    text: str

    metadata: dict = {"index_fields": ["text"]}


class QdrantAdapter(VectorDBInterface):
    """
    Qdrant vector database adapter for Cognee.

    Provides high-performance vector similarity search with Qdrant,
    supporting both in-memory and persistent storage modes.
    """

    name = "Qdrant"
    url: str
    api_key: Optional[str]
    client: Optional[QdrantClient]
    embedding_engine: EmbeddingEngine
    VECTOR_DB_LOCK: asyncio.Lock

    def __init__(
        self,
        url: Optional[str],
        api_key: Optional[str],
        embedding_engine: EmbeddingEngine,
    ):
        """
        Initialize Qdrant adapter.

        Parameters:
        -----------
        - url: Qdrant server URL (e.g., "http://localhost:6333")
        - api_key: Optional API key for authentication
        - embedding_engine: Embedding engine for vectorization
        """
        self.url = url
        self.api_key = api_key
        self.embedding_engine = embedding_engine
        self.client = None
        self.VECTOR_DB_LOCK = asyncio.Lock()

    async def get_connection(self) -> QdrantClient:
        """
        Establishes and returns a connection to Qdrant.

        If a connection already exists, it will return the existing connection.

        Returns:
        --------
        - QdrantClient: An active connection to Qdrant.
        """
        if self.client is None:
            # Parse URL to extract host and port
            if self.url and not self.url.startswith("http"):
                # Assume host:port format
                if ":" in self.url:
                    host, port = self.url.split(":")
                    self.url = f"http://{host}:{port}"
                else:
                    self.url = f"http://{self.url}"

            self.client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
                timeout=30,
            )

        return self.client

    async def embed_data(self, data: List[str]) -> List[List[float]]:
        """
        Embeds the provided textual data into vector representation.

        Uses the embedding engine to convert the list of strings into a list of float vectors.

        Parameters:
        -----------
        - data (List[str]): A list of strings representing the data to be embedded.

        Returns:
        --------
        - List[List[float]]: A list of embedded vectors corresponding to the input data.
        """
        return await self.embedding_engine.embed_text(data)

    async def has_collection(self, collection_name: str) -> bool:
        """
        Checks if the specified collection exists in Qdrant.

        Returns True if the collection is present, otherwise False.

        Parameters:
        -----------
        - collection_name (str): The name of the collection to check.

        Returns:
        --------
        - bool: True if the collection exists, otherwise False.
        """
        try:
            client = await self.get_connection()
            collections = client.get_collections()
            collection_names = [col.name for col in collections.collections]
            return collection_name in collection_names
        except Exception as e:
            return False

    async def create_collection(
        self,
        collection_name: str,
        payload_schema: Optional[Any] = None,
    ):
        """
        Create a new collection in Qdrant.

        Parameters:
        -----------
        - collection_name (str): The name of the new collection to create.
        - payload_schema (Optional[Any]): Schema for payloads (not directly used in Qdrant).
        """
        if not await self.has_collection(collection_name):
            async with self.VECTOR_DB_LOCK:
                if not await self.has_collection(collection_name):
                    client = await self.get_connection()
                    vector_size = self.embedding_engine.get_vector_size()

                    client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=vector_size,
                            distance=Distance.COSINE,
                        ),
                    )

    async def get_collection(self, collection_name: str):
        """
        Get collection information from Qdrant.

        Parameters:
        -----------
        - collection_name (str): The name of the collection.

        Returns:
        --------
        - Collection info or raises CollectionNotFoundError.
        """
        if not await self.has_collection(collection_name):
            raise CollectionNotFoundError(f"Collection '{collection_name}' not found!")

        client = await self.get_connection()
        return client.get_collection(collection_name)

    async def create_data_points(self, collection_name: str, data_points: List[DataPoint]):
        """
        Insert new data points into the specified collection.

        Parameters:
        -----------
        - collection_name (str): The name of the collection where data points will be added.
        - data_points (List[DataPoint]): A list of data points to be added to the collection.
        """
        if not await self.has_collection(collection_name):
            async with self.VECTOR_DB_LOCK:
                if not await self.has_collection(collection_name):
                    await self.create_collection(collection_name)

        client = await self.get_connection()

        # Embed data points
        data_vectors = await self.embed_data(
            [DataPoint.get_embeddable_data(data_point) for data_point in data_points]
        )

        # Create Qdrant points
        points = []
        for data_point_index, data_point in enumerate(data_points):
            properties = get_own_properties(data_point)
            properties["id"] = str(properties["id"])

            point = PointStruct(
                id=str(data_point.id),
                vector=data_vectors[data_point_index],
                payload=properties,
            )
            points.append(point)

        # Remove duplicates by ID
        unique_points = {point.id: point for point in points}.values()

        # Batch upsert
        async with self.VECTOR_DB_LOCK:
            client.upsert(
                collection_name=collection_name,
                points=list(unique_points),
            )

    async def retrieve(self, collection_name: str, data_point_ids: List[str]):
        """
        Retrieve data points from a collection using their IDs.

        Parameters:
        -----------
        - collection_name (str): The name of the collection from which to retrieve data points.
        - data_point_ids (List[str]): A list of IDs of the data points to retrieve.

        Returns:
        --------
        - List[ScoredResult]: Retrieved data points with scores (0 for retrieve).
        """
        client = await self.get_connection()

        # Retrieve points from Qdrant
        records = client.retrieve(
            collection_name=collection_name,
            ids=data_point_ids,
        )

        return [
            ScoredResult(
                id=parse_id(record.id),
                payload=record.payload,
                score=0,
            )
            for record in records
        ]

    async def search(
        self,
        collection_name: str,
        query_text: Optional[str] = None,
        query_vector: Optional[List[float]] = None,
        limit: Optional[int] = 15,
        with_vector: bool = False,
        normalized: bool = True,
    ):
        """
        Perform a search in the specified collection using either a text query or a vector query.

        Parameters:
        -----------
        - collection_name (str): The name of the collection in which to perform the search.
        - query_text (Optional[str]): An optional text query to search for in the collection.
        - query_vector (Optional[List[float]]): An optional vector representation for searching.
        - limit (Optional[int]): The maximum number of results to return from the search.
        - with_vector (bool): Whether to return the vector representations with search results.
        - normalized (bool): Whether to normalize scores.

        Returns:
        --------
        - List[ScoredResult]: Search results with similarity scores.
        """
        if query_text is None and query_vector is None:
            raise MissingQueryParameterError()

        if query_text and not query_vector:
            query_vector = (await self.embedding_engine.embed_text([query_text]))[0]

        client = await self.get_connection()

        if limit is None or limit <= 0:
            collection_info = client.get_collection(collection_name)
            limit = collection_info.points_count or 10

        # Qdrant search will break if limit is 0
        if limit <= 0:
            return []

        # Perform search
        search_results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            with_vectors=with_vector,
        )

        if not search_results:
            return []

        # Convert to ScoredResult
        results = [
            ScoredResult(
                id=parse_id(result.id),
                payload=result.payload,
                score=result.score if not normalized else float(result.score),
            )
            for result in search_results
        ]

        return results

    async def batch_search(
        self,
        collection_name: str,
        query_texts: List[str],
        limit: Optional[int] = None,
        with_vectors: bool = False,
    ):
        """
        Perform a batch search using multiple text queries against a collection.

        Parameters:
        -----------
        - collection_name (str): The name of the collection to conduct the batch search in.
        - query_texts (List[str]): A list of text queries to use for the search.
        - limit (Optional[int]): The maximum number of results to return for each query.
        - with_vectors (bool): Whether to include vector representations with search results.

        Returns:
        --------
        - List[List[ScoredResult]]: Search results for each query.
        """
        query_vectors = await self.embedding_engine.embed_text(query_texts)

        return await asyncio.gather(
            *[
                self.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    with_vector=with_vectors,
                )
                for query_vector in query_vectors
            ]
        )

    async def delete_data_points(
        self, collection_name: str, data_point_ids: Union[List[str], list[str]]
    ):
        """
        Delete specified data points from a collection.

        Parameters:
        -----------
        - collection_name (str): The name of the collection from which to delete data points.
        - data_point_ids (Union[List[str], list[str]]): A list of IDs of the data points to delete.
        """
        client = await self.get_connection()

        # Delete points by IDs
        client.delete(
            collection_name=collection_name,
            points_selector=data_point_ids,
        )

    async def prune(self):
        """
        Remove all collections and data from the Qdrant database.
        """
        client = await self.get_connection()
        collections = client.get_collections()

        for collection_info in collections.collections:
            collection_name = collection_info.name
            client.delete_collection(collection_name)

    async def create_vector_index(self, index_name: str, index_property_name: str):
        """
        Create a vector index for improved search performance.
        In Qdrant, indexes are created automatically with collections.

        Parameters:
        -----------
        - index_name (str): Name of the index.
        - index_property_name (str): Property name to index on.
        """
        # Qdrant creates indexes automatically with collection creation
        await self.create_collection(
            f"{index_name}_{index_property_name}", payload_schema=IndexSchema
        )

    async def index_data_points(
        self, index_name: str, index_property_name: str, data_points: List[DataPoint]
    ):
        """
        Index data points for improved search performance.

        Parameters:
        -----------
        - index_name (str): Name of the index to create/update.
        - index_property_name (str): Property name to index on.
        - data_points (List[DataPoint]): Data points to index.
        """
        await self.create_data_points(
            f"{index_name}_{index_property_name}",
            [
                IndexSchema(
                    id=str(data_point.id),
                    text=getattr(data_point, data_point.metadata["index_fields"][0]),
                )
                for data_point in data_points
            ],
        )

    def get_data_point_schema(self, model_type: Any) -> Any:
        """
        Get or transform a data point schema for Qdrant.

        Parameters:
        -----------
        - model_type (Any): The model type to get schema for.

        Returns:
        --------
        - Any: The schema object (returns input unchanged for Qdrant).
        """
        # Qdrant doesn't require schema transformation
        return model_type

    @classmethod
    async def create_dataset(
        cls, dataset_id: Optional[UUID], user: Optional[Any]
    ) -> dict:
        """
        Return connection info for a Qdrant instance for the given dataset.

        Parameters:
        -----------
        - dataset_id: UUID of the dataset.
        - user: User object (not used in Qdrant).

        Returns:
        --------
        - dict: Connection info for Qdrant instance.
        """
        # For Qdrant, datasets can be separated using collection prefixes
        # Return configuration for creating a collection with dataset-specific prefix
        return {
            "collection_prefix": f"dataset_{dataset_id}_" if dataset_id else "default_",
            "url": None,  # Will use default server URL
            "api_key": None,  # Will use default API key
        }

    async def delete_dataset(self, dataset_id: UUID, user: Any) -> None:
        """
        Delete the vector database (collections) for the given dataset.

        Parameters:
        -----------
        - dataset_id: UUID of the dataset.
        - user: User object.
        """
        client = await self.get_connection()
        collections = client.get_collections()

        # Delete all collections with the dataset prefix
        prefix = f"dataset_{dataset_id}_"
        for collection_info in collections.collections:
            collection_name = collection_info.name
            if collection_name.startswith(prefix):
                client.delete_collection(collection_name)
