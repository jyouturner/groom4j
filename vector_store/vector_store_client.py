import os
from typing import List, Dict, Optional, Any, Tuple
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
import logging

logger = logging.getLogger(__name__)

class QdrantVectorStore:
    """Client for Qdrant vector database operations"""
    
    def __init__(self, collection_name: str = "java_assistant", vector_size: int = 384, url: Optional[str] = None, skip_payload_indexes: bool = False):
        """Initialize Qdrant vector store client
        
        Args:
            collection_name: Name of the Qdrant collection
            vector_size: Dimension of vectors to store
            url: Optional URL for Qdrant server
            skip_payload_indexes: Whether to skip creating payload indexes (useful for local testing)
        """
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.skip_payload_indexes = skip_payload_indexes
        
        # Use provided URL or check environment
        self.cloud_url = url or os.environ.get("QDRANT_URL")
        self.cloud_api_key = os.environ.get("QDRANT_API_KEY")
        
        if self.cloud_url:
            # debug
            print(f"Initializing Qdrant cloud client at {self.cloud_url} with API key {self.cloud_api_key[-6:]}")
            self.client = QdrantClient(url=self.cloud_url, api_key=self.cloud_api_key)
            logger.info(f"Initialized Qdrant cloud client at {self.cloud_url}")
        else:
            # Fall back to local Qdrant instance
            self.client = QdrantClient(":memory:")  # In-memory for testing
            logger.info("Initialized local in-memory Qdrant client")
    
    def initialize_collection(self, vector_size: Optional[int] = None):
        """Initialize or validate collection with specified vector size"""
        if vector_size is None:
            vector_size = self.vector_size
            
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            if not exists:
                # Create collection with specified size and indices
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    ),
                    optimizers_config=models.OptimizersConfigDiff(
                        indexing_threshold=10000
                    )
                )
                # Add metadata indices only if not skipped
                if not self.skip_payload_indexes:
                    self._create_payload_indexes()
                    
                logger.info(f"Created collection '{self.collection_name}' with vector size {vector_size}")
            else:
                # Validate vector size matches
                collection_info = self.client.get_collection(self.collection_name)
                if collection_info.config.params.vectors.size != vector_size:
                    raise ValueError(
                        f"Collection {self.collection_name} exists with different vector size "
                        f"({collection_info.config.params.vectors.size} != {vector_size})"
                    )
                logger.info(f"Using existing collection '{self.collection_name}'")
                
        except Exception as e:
            logger.error(f"Error initializing collection: {str(e)}")
            raise
    
    def _create_payload_indexes(self):
        """Create payload indexes for the collection"""
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="project_id",
            field_schema=models.PayloadSchemaType.KEYWORD
        )
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="entry_type",
            field_schema=models.PayloadSchemaType.KEYWORD
        )
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="timestamp",
            field_schema=models.PayloadSchemaType.INTEGER
        )
    
    def store_embedding(
        self, 
        vector: List[float], 
        text: str, 
        metadata: Dict[str, Any],
        entry_id: Optional[str] = None
    ) -> str:
        """Store a vector embedding with associated text and metadata"""
        try:
            # Generate a unique ID if not provided
            if entry_id is None:
                import uuid
                entry_id = str(uuid.uuid4())
            
            # Prepare the point
            point = models.PointStruct(
                id=entry_id,
                vector=vector,
                payload={
                    "text": text,
                    **metadata
                }
            )
            
            # Upsert the point
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            return entry_id
        except Exception as e:
            print(f"Error storing embedding: {str(e)}")
            return None
    
    def search_similar(
        self, 
        query_vector: List[float], 
        project_id: Optional[str] = None,
        entry_type: Optional[str] = None,
        limit: int = 5, 
        score_threshold: float = 0.75
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors with optional filtering"""
        try:
            # Prepare filter conditions
            filter_conditions = []
            if project_id:
                filter_conditions.append(
                    models.FieldCondition(
                        key="project_id",
                        match=models.MatchValue(value=project_id)
                    )
                )
            if entry_type:
                filter_conditions.append(
                    models.FieldCondition(
                        key="entry_type",
                        match=models.MatchValue(value=entry_type)
                    )
                )
            
            # Prepare the search filter
            search_filter = None
            if filter_conditions:
                search_filter = models.Filter(
                    must=filter_conditions
                )
            
            # Use search instead of query_points for vector similarity search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold,
                search_params=models.SearchParams(
                    hnsw_ef=128,
                    exact=False
                )
            )
            
            # Format results - updated to handle ScoredPoint objects
            results = []
            for result in search_results:
                result_dict = {
                    "id": result.id,
                    "text": result.payload.get("text", ""),
                    "score": result.score,
                    **{k: v for k, v in result.payload.items() if k != "text"}
                }
                results.append(result_dict)
            
            return results
        except Exception as e:
            logger.error(f"Error searching similar vectors: {str(e)}")
            return []
    
    def get_by_id(self, entry_id: str) -> Dict[str, Any]:
        """Retrieve a specific entry by ID"""
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[entry_id]
            )
            
            if result and len(result) > 0:
                point = result[0]
                return {
                    "id": point.id,
                    "text": point.payload.get("text", ""),
                    **{k: v for k, v in point.payload.items() if k != "text"}
                }
            return None
        except Exception as e:
            print(f"Error retrieving entry: {str(e)}")
            return None
    
    def delete_by_id(self, entry_id: str) -> bool:
        """Delete an entry by ID"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[entry_id]
                )
            )
            return True
        except Exception as e:
            print(f"Error deleting entry: {str(e)}")
            return False
    
    def delete_by_filter(
        self, 
        project_id: Optional[str] = None,
        entry_type: Optional[str] = None,
        older_than_timestamp: Optional[int] = None
    ) -> bool:
        """Delete entries matching filter criteria"""
        try:
            # Prepare filter conditions
            filter_conditions = []
            if project_id:
                filter_conditions.append(
                    models.FieldCondition(
                        key="project_id",
                        match=models.MatchValue(value=project_id)
                    )
                )
            if entry_type:
                filter_conditions.append(
                    models.FieldCondition(
                        key="entry_type",
                        match=models.MatchValue(value=entry_type)
                    )
                )
            if older_than_timestamp:
                filter_conditions.append(
                    models.FieldCondition(
                        key="timestamp",
                        range=models.Range(lt=older_than_timestamp)
                    )
                )
            
            # Prepare the filter
            if not filter_conditions:
                print("No filter conditions specified for deletion")
                return False
            
            delete_filter = models.Filter(
                must=filter_conditions
            )
            
            # Perform the deletion
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=delete_filter
                )
            )
            return True
        except Exception as e:
            print(f"Error deleting entries by filter: {str(e)}")
            return False
